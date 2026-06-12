import uuid
from datetime import UTC, datetime
from urllib.parse import quote

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import Job, JobStatus, JobType, SSHStatus, Template, VM, VMStatus
from app.services.proxmox import ProxmoxClient, ProxmoxError


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso_now() -> str:
    return utcnow().isoformat()


async def seed_templates(db: AsyncSession, settings: Settings) -> None:
    seed = [
        {"os": "debian", "name": "debian-13-cloudinit-template", "proxmox_template_vmid": 9000},
        {"os": "ubuntu", "name": "ubuntu-2404-cloudinit-template", "proxmox_template_vmid": 9001},
    ]
    existing = {row.os: row for row in (await db.scalars(select(Template))).all()}
    for item in seed:
        row = existing.get(item["os"])
        if row is None:
            db.add(Template(defaults={"enabled": True, "node": settings.PROXMOX_DEFAULT_NODE}, **item))
        else:
            # keep the clone-target node in sync with the configured default node,
            # so changing PROXMOX_DEFAULT_NODE in the env propagates on next deploy
            defaults = dict(row.defaults or {})
            if defaults.get("node") != settings.PROXMOX_DEFAULT_NODE:
                defaults["node"] = settings.PROXMOX_DEFAULT_NODE
                row.defaults = defaults
    await db.commit()


async def mark_orphaned_running_as_failed(db: AsyncSession) -> None:
    jobs = (
        await db.scalars(select(Job).where(Job.status == JobStatus.running.value))
    ).all()
    for job in jobs:
        job.status = JobStatus.failed.value
        job.error = "job interrompido por restart do serviço"
    await db.commit()


async def create_vm_job(db: AsyncSession, settings: Settings, job: Job, vm: VM, root_password: str) -> None:
    template = await db.scalar(select(Template).where(Template.os == vm.template))
    if template is None:
        raise RuntimeError("template não encontrado")

    async with ProxmoxClient(settings) as proxmox:
        new_vmid = await proxmox.next_id()
        upid = await proxmox.post(
            f"/nodes/{vm.node}/qemu/{template.proxmox_template_vmid}/clone",
            data={"newid": new_vmid, "name": vm.hostname, "full": 1},
        )
        await set_job_meta(db, job, {"upid": upid, "node": vm.node, "operation": "clone", "polled_at": iso_now()})
        await proxmox.wait_for_task(vm.node, upid)

        vm.proxmox_vmid = new_vmid
        vm.status = VMStatus.provisioning.value
        await db.commit()

        await proxmox.put(
            f"/nodes/{vm.node}/qemu/{new_vmid}/config",
            data={
                "ciuser": "root",
                "cipassword": root_password,
                "sshkeys": quote(settings.CONSOLE_SSH_PUBLIC_KEY.strip(), safe=""),
                "ipconfig0": settings.CLOUDINIT_IPCONFIG,
                "nameserver": settings.CLOUDINIT_NAMESERVER,
                "cores": vm.cpu,
                "memory": vm.memory_mb,
                "onboot": 1,
            },
        )
        await proxmox.put(
            f"/nodes/{vm.node}/qemu/{new_vmid}/resize",
            data={"disk": "scsi0", "size": f"{vm.disk_gb}G"},
        )
        upid = await proxmox.post(f"/nodes/{vm.node}/qemu/{new_vmid}/status/start")
        await set_job_meta(db, job, {"upid": upid, "node": vm.node, "operation": "start", "polled_at": iso_now()})
        await proxmox.wait_for_task(vm.node, upid)

        vm.status = VMStatus.running.value
        await db.commit()

        vm.ip_address = await proxmox.wait_for_ip(vm.node, new_vmid)
        await db.commit()

        # Cloud-init templates ship with a baked machine-id, so every clone requests the
        # same DHCP lease and collides on one IP — which makes the backend SSH to itself
        # and breaks the web console. Reset the machine-id (agent is reachable now) and
        # reboot so this VM gets its own unique lease, then refresh the recorded IP.
        try:
            await proxmox.reset_machine_id(vm.node, new_vmid)
            reboot_upid = await proxmox.post(f"/nodes/{vm.node}/qemu/{new_vmid}/status/reboot")
            await set_job_meta(db, job, {"upid": reboot_upid, "node": vm.node, "operation": "reboot-uniq", "polled_at": iso_now()})
            await proxmox.wait_for_task(vm.node, reboot_upid)
            vm.ip_address = await proxmox.wait_for_ip(vm.node, new_vmid)
            await db.commit()
        except ProxmoxError:
            # Non-fatal: the VM exists and runs; console SSH may need a manual reset.
            pass


async def power_job(db: AsyncSession, settings: Settings, job: Job, vm: VM, operation: JobType) -> None:
    if vm.proxmox_vmid is None:
        raise RuntimeError("VM ainda não possui VMID Proxmox")

    endpoints = {
        JobType.start_vm: ("start", VMStatus.starting, VMStatus.running),
        JobType.stop_vm: ("shutdown", VMStatus.stopping, VMStatus.stopped),
        JobType.reboot_vm: ("reboot", VMStatus.rebooting, VMStatus.running),
    }
    action, transient, final = endpoints[operation]
    vm.status = transient.value
    if operation == JobType.start_vm:
        vm.ssh_status = SSHStatus.pending.value
    await db.commit()

    async with ProxmoxClient(settings) as proxmox:
        upid = await proxmox.post(f"/nodes/{vm.node}/qemu/{vm.proxmox_vmid}/status/{action}")
        await set_job_meta(db, job, {"upid": upid, "node": vm.node, "operation": action, "polled_at": iso_now()})
        await proxmox.wait_for_task(vm.node, upid)
        vm.status = final.value
        if operation == JobType.start_vm:
            vm.ip_address = await proxmox.wait_for_ip(vm.node, vm.proxmox_vmid)
        await db.commit()


async def delete_vm_job(db: AsyncSession, settings: Settings, job: Job, vm: VM) -> None:
    vm.status = VMStatus.deleting.value
    await db.commit()
    if vm.proxmox_vmid is not None:
        async with ProxmoxClient(settings) as proxmox:
            upid = await proxmox.delete(
                f"/nodes/{vm.node}/qemu/{vm.proxmox_vmid}",
                params={"purge": 1, "destroy-unreferenced-disks": 1},
            )
            await set_job_meta(db, job, {"upid": upid, "node": vm.node, "operation": "delete", "polled_at": iso_now()})
            await proxmox.wait_for_task(vm.node, upid)
    vm.status = VMStatus.deleted.value
    vm.deleted_at = utcnow()
    await db.commit()


async def enqueue_ssh_check(db: AsyncSession, vm_id: uuid.UUID) -> Job:
    job = Job(type=JobType.ssh_readiness_check.value, status=JobStatus.queued.value, vm_id=vm_id, meta={})
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def set_job_meta(db: AsyncSession, job: Job, patch: dict) -> None:
    job.meta = {**(job.meta or {}), **patch}
    await db.commit()

