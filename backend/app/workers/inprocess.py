import asyncio
import logging
import uuid

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models import Job, JobStatus, JobType, VM, VMStatus
from app.services.lifecycle import create_vm_job, delete_vm_job, enqueue_ssh_check, power_job, reinstall_vm_job
from app.services.terminal import check_ssh_ready

logger = logging.getLogger(__name__)
JOB_QUEUE: asyncio.Queue[dict] = asyncio.Queue()


async def enqueue(payload: dict) -> None:
    await JOB_QUEUE.put(payload)


async def worker_loop() -> None:
    while True:
        payload = await JOB_QUEUE.get()
        try:
            await dispatch(payload)
        except Exception:
            logger.exception("job falhou job_id=%s", payload.get("job_id"))
        finally:
            JOB_QUEUE.task_done()


async def dispatch(payload: dict) -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as db:
        job = await db.get(Job, uuid.UUID(payload["job_id"]))
        if job is None:
            return
        vm = await db.get(VM, uuid.UUID(payload["vm_id"])) if payload.get("vm_id") else None
        job.status = JobStatus.running.value
        await db.commit()
        try:
            if job.type == JobType.create_vm.value:
                if vm is None:
                    raise RuntimeError("VM não encontrada")
                await create_vm_job(db, settings, job, vm, payload["root_password"])
                job.status = JobStatus.success.value
                await db.commit()
                ssh_job = await enqueue_ssh_check(db, vm.id)
                await enqueue({"type": JobType.ssh_readiness_check.value, "job_id": str(ssh_job.id), "vm_id": str(vm.id)})
            elif job.type == JobType.reinstall_vm.value:
                if vm is None:
                    raise RuntimeError("VM não encontrada")
                template_os = payload.get("template") or (job.meta or {}).get("template")
                await reinstall_vm_job(db, settings, job, vm, payload["root_password"], template_os)
                job.status = JobStatus.success.value
                await db.commit()
                ssh_job = await enqueue_ssh_check(db, vm.id)
                await enqueue({"type": JobType.ssh_readiness_check.value, "job_id": str(ssh_job.id), "vm_id": str(vm.id)})
            elif job.type in (JobType.start_vm.value, JobType.stop_vm.value, JobType.reboot_vm.value):
                if vm is None:
                    raise RuntimeError("VM não encontrada")
                await power_job(db, settings, job, vm, JobType(job.type))
                job.status = JobStatus.success.value
                await db.commit()
                if job.type in (JobType.start_vm.value, JobType.reboot_vm.value):
                    ssh_job = await enqueue_ssh_check(db, vm.id)
                    await enqueue({"type": JobType.ssh_readiness_check.value, "job_id": str(ssh_job.id), "vm_id": str(vm.id)})
            elif job.type == JobType.delete_vm.value:
                if vm is None:
                    raise RuntimeError("VM não encontrada")
                await delete_vm_job(db, settings, job, vm)
                job.status = JobStatus.success.value
                await db.commit()
            elif job.type == JobType.ssh_readiness_check.value:
                if vm is None:
                    raise RuntimeError("VM não encontrada")
                await check_ssh_ready(db, settings, vm)
                job.status = JobStatus.success.value
                await db.commit()
        except Exception as exc:
            if vm is not None:
                # a failed delete must not leave the VM stuck in "deleting" forever
                # (that state keeps the dashboard auto-refreshing) — surface it as error
                vm.status = VMStatus.error.value
            job.status = JobStatus.failed.value
            job.error = sanitize_job_error(exc)
            await db.commit()


def sanitize_job_error(exc: Exception) -> str:
    message = str(exc) or exc.__class__.__name__
    return message[:500]


async def requeue_queued_jobs() -> None:
    async with AsyncSessionLocal() as db:
        jobs = (await db.scalars(select(Job).where(Job.status == JobStatus.queued.value))).all()
        for job in jobs:
            if job.type in (JobType.create_vm.value, JobType.reinstall_vm.value):
                job.status = JobStatus.failed.value
                job.error = f"job {job.type} pendente não pode ser retomado porque a senha root não é persistida"
            else:
                await enqueue({"type": job.type, "job_id": str(job.id), "vm_id": str(job.vm_id) if job.vm_id else None})
        await db.commit()
