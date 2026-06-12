import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.core.config import VM_SIZES, get_settings
from app.core.errors import AppHTTPException
from app.core.readiness import missing_runtime_settings
from app.db.session import get_db
from app.models import (
    Job,
    JobStatus,
    JobType,
    SSHStatus,
    Template,
    TerminalSession,
    TerminalSessionStatus,
    VM,
    VMExposure,
    VMStatus,
)
from app.schemas.vms import DeleteVM, ExposureCreate, JobOut, VMCreate, VMOut
from app.services.lifecycle import enqueue_ssh_check
from app.workers.inprocess import enqueue

router = APIRouter(prefix="/api", dependencies=[Depends(require_admin)])


@router.post("/vms", status_code=201)
async def create_vm(payload: VMCreate, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    missing = missing_runtime_settings(settings)
    if missing:
        raise AppHTTPException(
            "PROXMOX_NOT_CONFIGURED",
            "configure o .env antes de criar VMs: " + ", ".join(missing),
            400,
        )
    if payload.size not in VM_SIZES:
        raise AppHTTPException("VALIDATION_ERROR", "tamanho inválido", 400)
    if payload.disk_gb not in settings.VM_DISK_CHOICES:
        raise AppHTTPException("VALIDATION_ERROR", "disco inválido", 400)
    template = await db.scalar(select(Template).where(Template.os == payload.template))
    if template is None:
        raise AppHTTPException("TEMPLATE_NOT_FOUND", "template não encontrado", 404)
    if template.defaults and template.defaults.get("enabled") is False:
        raise AppHTTPException("TEMPLATE_DISABLED", "template desabilitado", 400)

    size = VM_SIZES[payload.size]
    vm = VM(
        hostname=payload.hostname,
        template=payload.template,
        cpu=size["cpu"],
        memory_mb=size["memory_mb"],
        disk_gb=payload.disk_gb,
        node=(template.defaults or {}).get("node") or settings.PROXMOX_DEFAULT_NODE,
        status=VMStatus.creating.value,
        ssh_status=SSHStatus.pending.value,
    )
    db.add(vm)
    await db.flush()
    job = Job(type=JobType.create_vm.value, status=JobStatus.queued.value, vm_id=vm.id, meta={})
    db.add(job)
    await db.commit()
    await db.refresh(vm)
    await db.refresh(job)
    await enqueue(
        {
            "type": JobType.create_vm.value,
            "job_id": str(job.id),
            "vm_id": str(vm.id),
            "root_password": payload.root_password,
        }
    )
    return {"vm_id": str(vm.id), "job_id": str(job.id), "status": "creating"}


@router.get("/vms")
async def list_vms(db: AsyncSession = Depends(get_db)):
    vms = (await db.scalars(select(VM).where(VM.deleted_at.is_(None)).order_by(VM.created_at.desc()))).all()
    errors: dict[uuid.UUID, str] = {}
    if vms:
        jobs = (
            await db.scalars(
                select(Job)
                .where(Job.vm_id.in_([vm.id for vm in vms]), Job.error.is_not(None))
                .order_by(Job.created_at.desc())
            )
        ).all()
        for job in jobs:
            if job.vm_id is not None:
                errors.setdefault(job.vm_id, job.error)
    return {"vms": [serialize_vm(vm, errors.get(vm.id)) for vm in vms]}


@router.get("/templates")
async def list_templates(db: AsyncSession = Depends(get_db)):
    templates = (await db.scalars(select(Template).order_by(Template.os))).all()
    return {
        "templates": [
            {
                "name": template.name,
                "os": template.os,
                "enabled": (template.defaults or {}).get("enabled") is not False,
            }
            for template in templates
        ]
    }


@router.get("/options")
async def options():
    settings = get_settings()
    return {
        "sizes": {key: {"label": value["label"], "cpu": value["cpu"], "memory_mb": value["memory_mb"]} for key, value in VM_SIZES.items()},
        "disk_choices": settings.VM_DISK_CHOICES,
        "missing_runtime": missing_runtime_settings(settings),
    }


@router.get("/readiness")
async def readiness():
    missing = missing_runtime_settings(get_settings())
    return {"ready": not missing, "missing": missing}


@router.get("/vms/{vm_id}")
async def get_vm(vm_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> VMOut:
    return serialize_vm(await get_live_vm(db, vm_id))


@router.post("/vms/{vm_id}/start", status_code=202)
async def start_vm(vm_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    vm = await get_live_vm(db, vm_id)
    if vm.status not in (VMStatus.stopped.value, VMStatus.error.value):
        raise AppHTTPException("INVALID_STATE", "VM não pode ser iniciada neste estado", 409)
    return await enqueue_power_job(db, vm, JobType.start_vm)


@router.post("/vms/{vm_id}/stop", status_code=202)
async def stop_vm(vm_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    vm = await get_live_vm(db, vm_id)
    if vm.status != VMStatus.running.value:
        raise AppHTTPException("INVALID_STATE", "VM não está running", 409)
    return await enqueue_power_job(db, vm, JobType.stop_vm)


@router.post("/vms/{vm_id}/reboot", status_code=202)
async def reboot_vm(vm_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    vm = await get_live_vm(db, vm_id)
    if vm.status != VMStatus.running.value:
        raise AppHTTPException("INVALID_STATE", "VM não está running", 409)
    return await enqueue_power_job(db, vm, JobType.reboot_vm)


@router.delete("/vms/{vm_id}", status_code=202)
async def delete_vm(vm_id: uuid.UUID, payload: DeleteVM, db: AsyncSession = Depends(get_db)):
    vm = await get_live_vm(db, vm_id)
    if payload.confirm_hostname != vm.hostname:
        raise AppHTTPException("HOSTNAME_MISMATCH", "hostname de confirmação não confere", 400)
    if vm.status not in (VMStatus.running.value, VMStatus.stopped.value, VMStatus.error.value):
        raise AppHTTPException("INVALID_STATE", "VM não pode ser deletada neste estado", 409)
    job = Job(type=JobType.delete_vm.value, status=JobStatus.queued.value, vm_id=vm.id, meta={})
    db.add(job)
    await db.commit()
    await db.refresh(job)
    await enqueue({"type": JobType.delete_vm.value, "job_id": str(job.id), "vm_id": str(vm.id)})
    return {"job_id": str(job.id), "status": "queued"}


@router.get("/jobs/{job_id}")
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> JobOut:
    job = await db.get(Job, job_id)
    if job is None:
        raise AppHTTPException("VALIDATION_ERROR", "job não encontrado", 404)
    return JobOut(
        id=job.id,
        type=str(job.type),
        status=str(job.status),
        error=job.error,
        meta=job.meta or {},
        vm_id=job.vm_id,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post("/vms/{vm_id}/terminal/session", status_code=201)
async def create_terminal_session(vm_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    vm = await get_live_vm(db, vm_id)
    if vm.status != VMStatus.running.value or vm.ssh_status != SSHStatus.ready.value:
        raise AppHTTPException("TERMINAL_NOT_READY", "terminal ainda não está pronto", 409)
    expires_at = datetime.now(UTC) + timedelta(seconds=60)
    ts = TerminalSession(vm_id=vm.id, status=TerminalSessionStatus.pending.value, expires_at=expires_at)
    db.add(ts)
    await db.commit()
    await db.refresh(ts)
    return {
        "session_id": str(ts.id),
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "terminal_url": f"/vms/{vm.id}/terminal?session={ts.id}",
    }


@router.post("/vms/{vm_id}/ssh-check", status_code=202)
async def recheck_ssh(vm_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    vm = await get_live_vm(db, vm_id)
    if vm.status != VMStatus.running.value:
        raise AppHTTPException("INVALID_STATE", "a VM precisa estar running para checar o SSH", 409)
    vm.ssh_status = SSHStatus.pending.value
    await db.commit()
    job = await enqueue_ssh_check(db, vm.id)
    await enqueue({"type": JobType.ssh_readiness_check.value, "job_id": str(job.id), "vm_id": str(vm.id)})
    return {"job_id": str(job.id), "status": "queued"}


@router.get("/vms/{vm_id}/exposures")
async def list_exposures(vm_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await get_live_vm(db, vm_id)
    exposures = (await db.scalars(select(VMExposure).where(VMExposure.vm_id == vm_id))).all()
    return {"exposures": [{"id": str(e.id), "slug": e.slug, "port": e.port, "enabled": e.enabled} for e in exposures]}


@router.post("/vms/{vm_id}/exposures", status_code=201)
async def create_exposure(vm_id: uuid.UUID, payload: ExposureCreate, db: AsyncSession = Depends(get_db)):
    vm = await get_live_vm(db, vm_id)
    existing = await db.scalar(select(VMExposure).where(VMExposure.slug == payload.slug))
    if existing:
        raise AppHTTPException("EXPOSURE_SLUG_TAKEN", "slug já está em uso", 409)
    exposure = VMExposure(vm_id=vm.id, slug=payload.slug, port=payload.port, enabled=True)
    db.add(exposure)
    await db.commit()
    await db.refresh(exposure)
    return {"id": str(exposure.id), "slug": exposure.slug, "port": exposure.port, "enabled": exposure.enabled}


@router.delete("/vms/{vm_id}/exposures/{exposure_id}", status_code=204)
async def delete_exposure(vm_id: uuid.UUID, exposure_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await get_live_vm(db, vm_id)
    exposure = await db.get(VMExposure, exposure_id)
    if exposure and exposure.vm_id == vm_id:
        await db.delete(exposure)
        await db.commit()
    return Response(status_code=204)


async def get_live_vm(db: AsyncSession, vm_id: uuid.UUID) -> VM:
    vm = await db.get(VM, vm_id)
    if vm is None or vm.deleted_at is not None:
        raise AppHTTPException("VM_NOT_FOUND", "VM não encontrada", 404)
    return vm


async def enqueue_power_job(db: AsyncSession, vm: VM, job_type: JobType):
    job = Job(type=job_type.value, status=JobStatus.queued.value, vm_id=vm.id, meta={})
    db.add(job)
    await db.commit()
    await db.refresh(job)
    await enqueue({"type": job_type.value, "job_id": str(job.id), "vm_id": str(vm.id)})
    return {"job_id": str(job.id), "status": "queued"}


def serialize_vm(vm: VM, last_error: str | None = None) -> VMOut:
    running = vm.status == VMStatus.running.value
    ssh_ready = vm.ssh_status == SSHStatus.ready.value
    actions = {
        "can_start": vm.status in (VMStatus.stopped.value, VMStatus.error.value),
        "can_stop": running,
        "can_reboot": running,
        "can_terminal": running and ssh_ready,
        "can_delete": vm.status in (VMStatus.running.value, VMStatus.stopped.value, VMStatus.error.value),
        "can_recheck": running and not ssh_ready,
    }
    return VMOut(
        id=vm.id,
        hostname=vm.hostname,
        template=vm.template,
        cpu=vm.cpu,
        memory_mb=vm.memory_mb,
        disk_gb=vm.disk_gb,
        status=vm.status,
        ssh_status=vm.ssh_status,
        ip_address=vm.ip_address,
        created_at=vm.created_at,
        actions=actions,
        last_error=last_error if vm.status == VMStatus.error.value or (running and not ssh_ready) else None,
    )

