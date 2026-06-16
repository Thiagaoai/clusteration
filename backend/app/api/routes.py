import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.core.config import VM_SIZES, get_settings
from app.core.errors import AppHTTPException
from app.core.readiness import database_durability, missing_runtime_settings
from app.db.session import get_db
from app.models import (
    AuditEvent,
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
from app.schemas.vms import DeleteVM, ExposureCreate, JobOut, ReinstallVM, VMCreate, VMOut
from app.services.audit import record_audit
from app.services.lifecycle import enqueue_ssh_check
from app.services.proxmox import ProxmoxAuthError, ProxmoxClient, ProxmoxError
from app.workers.inprocess import enqueue

router = APIRouter(prefix="/api", dependencies=[Depends(require_admin)])


@router.post("/vms", status_code=201)
async def create_vm(payload: VMCreate, request: Request, db: AsyncSession = Depends(get_db)):
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

    min_disk_gb = int((template.defaults or {}).get("min_disk_gb") or 0)
    effective_disk_gb = max(payload.disk_gb, min_disk_gb)
    size = VM_SIZES[payload.size]
    vm = VM(
        hostname=payload.hostname,
        template=payload.template,
        cpu=size["cpu"],
        memory_mb=size["memory_mb"],
        disk_gb=effective_disk_gb,
        node=(template.defaults or {}).get("node") or settings.PROXMOX_DEFAULT_NODE,
        status=VMStatus.creating.value,
        ssh_status=SSHStatus.pending.value,
    )
    db.add(vm)
    await db.flush()
    job = Job(type=JobType.create_vm.value, status=JobStatus.queued.value, vm_id=vm.id, meta={})
    db.add(job)
    await _audit_vm(
        db,
        request,
        "vm.create",
        vm,
        template=payload.template,
        size=payload.size,
        disk_gb=effective_disk_gb,
        requested_disk_gb=payload.disk_gb,
    )
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
    errors: dict[uuid.UUID, Job] = {}
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
                errors.setdefault(job.vm_id, job)
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
                "defaults": template.defaults or {},
                "min_disk_gb": int((template.defaults or {}).get("min_disk_gb") or 0),
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


@router.get("/system/status")
async def system_status(db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    template_count = await db.scalar(select(func.count()).select_from(Template))
    return {
        "runtime_ready": not missing_runtime_settings(settings),
        "missing_runtime": missing_runtime_settings(settings),
        "database": database_durability(settings),
        "templates_configured": template_count or 0,
        "worker_mode": settings.WORKER_MODE,
        "build": settings.APP_BUILD_ID,
        "proxmox_check_url": "/api/system/proxmox",
    }


@router.get("/system/proxmox")
async def proxmox_diagnostics(db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    checks: list[dict] = []
    missing = missing_runtime_settings(settings)
    if missing:
        return {
            "ok": False,
            "checks": [
                {
                    "name": "runtime",
                    "ok": False,
                    "message": "variáveis ausentes: " + ", ".join(missing),
                }
            ],
            "setup_hint": proxmox_setup_hint(),
        }

    templates = (await db.scalars(select(Template).order_by(Template.os))).all()
    checks.append(
        {
            "name": "runtime",
            "ok": True,
            "message": "variáveis obrigatórias presentes",
        }
    )

    try:
        async with ProxmoxClient(settings) as proxmox:
            next_id = await proxmox.next_id()
            checks.append({"name": "nextid", "ok": True, "message": f"Proxmox API OK; próximo VMID {next_id}"})

            storage_checks: dict[str, dict] = {}
            template_results = []
            for template in templates:
                preferred_node = (template.defaults or {}).get("node") or settings.PROXMOX_DEFAULT_NODE
                node = await proxmox.resolve_template_node(preferred_node, template.proxmox_template_vmid)
                disk_gb = await proxmox.vm_disk_size_gb(node, template.proxmox_template_vmid)
                storage_key = f"{node}/{settings.PROXMOX_DEFAULT_STORAGE}"
                if storage_key not in storage_checks:
                    try:
                        await proxmox.get(f"/nodes/{node}/storage/{settings.PROXMOX_DEFAULT_STORAGE}/status")
                        storage_checks[storage_key] = {
                            "name": f"storage:{storage_key}",
                            "ok": True,
                            "message": "storage acessível pelo token",
                        }
                    except ProxmoxError as exc:
                        storage_checks[storage_key] = {
                            "name": f"storage:{storage_key}",
                            "ok": False,
                            "message": str(exc),
                        }
                template_results.append(
                    {
                        "os": template.os,
                        "vmid": template.proxmox_template_vmid,
                        "node": node,
                        "disk_gb": disk_gb,
                    }
                )
            checks.extend(storage_checks.values())
            checks.append(
                {
                    "name": "templates",
                    "ok": True,
                    "message": f"{len(template_results)} templates resolvidos",
                    "items": template_results,
                }
            )
    except ProxmoxAuthError as exc:
        checks.append({"name": "proxmox-auth", "ok": False, "message": str(exc)})
    except ProxmoxError as exc:
        checks.append({"name": "proxmox-api", "ok": False, "message": str(exc)})

    ok = all(check.get("ok") for check in checks)
    return {"ok": ok, "checks": checks, "setup_hint": proxmox_setup_hint() if not ok else None}


@router.get("/audit")
async def list_audit(db: AsyncSession = Depends(get_db), limit: int = 100, offset: int = 0):
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    rows = (
        await db.scalars(
            select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset)
        )
    ).all()
    return {"events": [serialize_audit(event) for event in rows]}


@router.get("/jobs")
async def list_jobs(db: AsyncSession = Depends(get_db), limit: int = 50, offset: int = 0):
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    rows = (
        await db.scalars(
            select(Job).order_by(Job.created_at.desc()).limit(limit).offset(offset)
        )
    ).all()
    vm_ids = [job.vm_id for job in rows if job.vm_id is not None]
    vms = {}
    if vm_ids:
        vms = {vm.id: vm for vm in (await db.scalars(select(VM).where(VM.id.in_(vm_ids)))).all()}
    return {
        "jobs": [
            {
                "id": str(job.id),
                "type": job.type,
                "status": job.status,
                "error": job.error,
                "meta": job.meta or {},
                "vm_id": str(job.vm_id) if job.vm_id else None,
                "vm_hostname": vms[job.vm_id].hostname if job.vm_id in vms else None,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            }
            for job in rows
        ]
    }


def proxmox_setup_hint() -> str:
    return (
        "No shell do Proxmox, use roles built-in para evitar privilégio inválido: "
        "pveum user add panel@pve || true; "
        "pveum aclmod / -user panel@pve -role PVEVMAdmin; "
        "pveum aclmod /storage/local-lvm -user panel@pve -role PVEDatastoreAdmin; "
        "pveum aclmod /storage/local -user panel@pve -role PVEDatastoreAdmin; "
        "pveum user token add panel@pve clusteration --privsep 0"
    )


@router.get("/vms/{vm_id}")
async def get_vm(vm_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> VMOut:
    return serialize_vm(await get_live_vm(db, vm_id))


@router.post("/vms/{vm_id}/start", status_code=202)
async def start_vm(vm_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    vm = await get_live_vm(db, vm_id)
    if vm.status not in (VMStatus.stopped.value, VMStatus.error.value):
        raise AppHTTPException("INVALID_STATE", "VM não pode ser iniciada neste estado", 409)
    await _audit_vm(db, request, "vm.start", vm)
    return await enqueue_power_job(db, vm, JobType.start_vm)


@router.post("/vms/{vm_id}/stop", status_code=202)
async def stop_vm(vm_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    vm = await get_live_vm(db, vm_id)
    if vm.status != VMStatus.running.value:
        raise AppHTTPException("INVALID_STATE", "VM não está running", 409)
    await _audit_vm(db, request, "vm.stop", vm)
    return await enqueue_power_job(db, vm, JobType.stop_vm)


@router.post("/vms/{vm_id}/reboot", status_code=202)
async def reboot_vm(vm_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    vm = await get_live_vm(db, vm_id)
    if vm.status != VMStatus.running.value:
        raise AppHTTPException("INVALID_STATE", "VM não está running", 409)
    await _audit_vm(db, request, "vm.reboot", vm)
    return await enqueue_power_job(db, vm, JobType.reboot_vm)


@router.post("/vms/{vm_id}/reinstall", status_code=202)
async def reinstall_vm(
    vm_id: uuid.UUID,
    payload: ReinstallVM,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    missing = missing_runtime_settings(settings)
    if missing:
        raise AppHTTPException(
            "PROXMOX_NOT_CONFIGURED",
            "configure o .env antes de reinstalar VMs: " + ", ".join(missing),
            400,
        )
    vm = await get_live_vm(db, vm_id)
    if payload.confirm_hostname != vm.hostname:
        raise AppHTTPException("HOSTNAME_MISMATCH", "hostname de confirmação não confere", 400)
    if vm.status not in (VMStatus.running.value, VMStatus.stopped.value, VMStatus.error.value):
        raise AppHTTPException("INVALID_STATE", "VM não pode ser reinstalada neste estado", 409)

    template_os = payload.template or vm.template
    template = await db.scalar(select(Template).where(Template.os == template_os))
    if template is None:
        raise AppHTTPException("TEMPLATE_NOT_FOUND", "template não encontrado", 404)
    if template.defaults and template.defaults.get("enabled") is False:
        raise AppHTTPException("TEMPLATE_DISABLED", "template desabilitado", 400)

    job = Job(
        type=JobType.reinstall_vm.value,
        status=JobStatus.queued.value,
        vm_id=vm.id,
        meta={"template": template_os},
    )
    db.add(job)
    await _audit_vm(
        db,
        request,
        "vm.reinstall",
        vm,
        previous_template=vm.template,
        next_template=template_os,
        proxmox_vmid=vm.proxmox_vmid,
        ip_address=vm.ip_address,
        node=vm.node,
    )
    await db.commit()
    await db.refresh(job)
    await enqueue(
        {
            "type": JobType.reinstall_vm.value,
            "job_id": str(job.id),
            "vm_id": str(vm.id),
            "root_password": payload.root_password,
            "template": template_os,
        }
    )
    return {"job_id": str(job.id), "status": "queued"}


@router.delete("/vms/{vm_id}", status_code=202)
async def delete_vm(vm_id: uuid.UUID, payload: DeleteVM, request: Request, db: AsyncSession = Depends(get_db)):
    vm = await get_live_vm(db, vm_id)
    if payload.confirm_hostname != vm.hostname:
        raise AppHTTPException("HOSTNAME_MISMATCH", "hostname de confirmação não confere", 400)
    if vm.status not in (VMStatus.running.value, VMStatus.stopped.value, VMStatus.error.value):
        raise AppHTTPException("INVALID_STATE", "VM não pode ser deletada neste estado", 409)
    job = Job(type=JobType.delete_vm.value, status=JobStatus.queued.value, vm_id=vm.id, meta={})
    db.add(job)
    await _audit_vm(db, request, "vm.delete", vm, proxmox_vmid=vm.proxmox_vmid, ip_address=vm.ip_address, node=vm.node, status_before=vm.status)
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
    ttl = max(60, int(get_settings().TERMINAL_SESSION_TTL_SECONDS))
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl)
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


def serialize_vm(vm: VM, last_error: Job | str | None = None) -> VMOut:
    running = vm.status == VMStatus.running.value
    ssh_ready = vm.ssh_status == SSHStatus.ready.value
    error_text = last_error.error if isinstance(last_error, Job) else last_error
    error_at = last_error.created_at if isinstance(last_error, Job) else None
    error_type = last_error.type if isinstance(last_error, Job) else None
    actions = {
        "can_start": vm.status in (VMStatus.stopped.value, VMStatus.error.value),
        "can_stop": running,
        "can_reboot": running,
        "can_terminal": running and ssh_ready,
        "can_delete": vm.status in (VMStatus.running.value, VMStatus.stopped.value, VMStatus.error.value),
        "can_reinstall": vm.status in (VMStatus.running.value, VMStatus.stopped.value, VMStatus.error.value),
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
        last_error=error_text if vm.status == VMStatus.error.value or (running and not ssh_ready) else None,
        last_error_at=error_at if vm.status == VMStatus.error.value or (running and not ssh_ready) else None,
        last_error_job_type=error_type if vm.status == VMStatus.error.value or (running and not ssh_ready) else None,
    )


async def _audit_vm(db: AsyncSession, request: Request, action: str, vm: VM, **detail) -> None:
    await record_audit(
        db,
        action=action,
        request=request,
        actor=get_settings().ADMIN_USERNAME,
        target_type="vm",
        target_id=vm.id,
        target_label=vm.hostname,
        detail=detail or {},
    )


def serialize_audit(event: AuditEvent) -> dict:
    return {
        "id": str(event.id),
        "action": event.action,
        "actor": event.actor,
        "source_ip": event.source_ip,
        "target_type": event.target_type,
        "target_id": event.target_id,
        "target_label": event.target_label,
        "detail": event.detail or {},
        "request_id": event.request_id,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
