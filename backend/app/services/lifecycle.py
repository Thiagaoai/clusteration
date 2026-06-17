import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import Job, JobStatus, JobType, SSHStatus, Template, VM, VMStatus
from app.services.proxmox import ProxmoxClient, ProxmoxError, ProxmoxTimeoutError


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso_now() -> str:
    return utcnow().isoformat()


async def seed_templates(db: AsyncSession, settings: Settings) -> None:
    seed = [
        {
            "os": "debian",
            "name": "Debian 13 cloud-init (stable/latest)",
            "proxmox_template_vmid": settings.TEMPLATE_DEBIAN_VMID,
            "defaults": {"family": "os", "version": "13/trixie", "min_disk_gb": 12},
        },
        {
            "os": "ubuntu",
            "name": "Ubuntu 26.04 LTS cloud-init (latest LTS)",
            "proxmox_template_vmid": settings.TEMPLATE_UBUNTU_VMID,
            "defaults": {"family": "os", "version": "26.04/resolute", "min_disk_gb": 12},
        },
        {
            "os": "fedora",
            "name": "Fedora Cloud 44 cloud-init (latest)",
            "proxmox_template_vmid": settings.TEMPLATE_FEDORA_VMID,
            "defaults": {"family": "os", "version": "44", "min_disk_gb": 12},
        },
        {
            "os": "hermes",
            "name": "Hermes AI image (prebuilt)",
            "proxmox_template_vmid": settings.TEMPLATE_HERMES_VMID,
            "defaults": {"family": "ai", "base": "ubuntu", "bundle": "hermes", "min_disk_gb": 16},
        },
        {
            "os": "openclaw",
            "name": "OpenClaw AI image (prebuilt)",
            "proxmox_template_vmid": settings.TEMPLATE_OPENCLAW_VMID,
            "defaults": {"family": "ai", "base": "ubuntu", "bundle": "openclaw", "min_disk_gb": 16},
        },
        {
            "os": "claude",
            "name": "Claude CLI image (prebuilt)",
            "proxmox_template_vmid": settings.TEMPLATE_CLAUDE_VMID,
            "defaults": {"family": "ai", "base": "ubuntu", "bundle": "claude", "min_disk_gb": 16},
        },
    ]
    existing = {row.os: row for row in (await db.scalars(select(Template))).all()}
    for item in seed:
        row = existing.get(item["os"])
        defaults = {
            "enabled": True,
            "node": settings.PROXMOX_DEFAULT_NODE,
            **item.get("defaults", {}),
        }
        if row is None:
            db.add(
                Template(
                    os=item["os"],
                    name=item["name"],
                    proxmox_template_vmid=item["proxmox_template_vmid"],
                    defaults=defaults,
                )
            )
        else:
            # keep the clone-target node in sync with the configured default node,
            # so changing PROXMOX_DEFAULT_NODE in the env propagates on next deploy
            merged = {**defaults, **(row.defaults or {})}
            merged["node"] = settings.PROXMOX_DEFAULT_NODE
            if row.name != item["name"]:
                row.name = item["name"]
            if row.proxmox_template_vmid != item["proxmox_template_vmid"]:
                row.proxmox_template_vmid = item["proxmox_template_vmid"]
            if row.defaults != merged:
                row.defaults = merged
    await db.commit()


async def mark_orphaned_running_as_failed(db: AsyncSession) -> None:
    jobs = (
        await db.scalars(select(Job).where(Job.status == JobStatus.running.value))
    ).all()
    for job in jobs:
        job.status = JobStatus.failed.value
        job.error = "job interrompido por restart do serviço"
        if job.vm_id and job.meta and job.meta.get("target_vmid"):
            vm = await db.get(VM, job.vm_id)
            if vm and vm.proxmox_vmid is None:
                vm.proxmox_vmid = int(job.meta["target_vmid"])
                vm.node = str(job.meta.get("node") or vm.node)
    # A restart kills in-flight work, so any VM left in a transient state (e.g. stuck
    # in "deleting") would never recover — and a perpetually-transient VM keeps the
    # dashboard auto-refreshing. Surface them as error so they can be acted on again.
    transient = (
        VMStatus.creating.value,
        VMStatus.provisioning.value,
        VMStatus.starting.value,
        VMStatus.stopping.value,
        VMStatus.rebooting.value,
        VMStatus.deleting.value,
    )
    stuck = (await db.scalars(select(VM).where(VM.status.in_(transient), VM.deleted_at.is_(None)))).all()
    for vm in stuck:
        vm.status = VMStatus.error.value
    await db.commit()


async def create_vm_job(db: AsyncSession, settings: Settings, job: Job, vm: VM, root_password: str) -> None:
    template = await db.scalar(select(Template).where(Template.os == vm.template))
    if template is None:
        raise RuntimeError("template não encontrado")
    await provision_vm_from_template(db, settings, job, vm, template, root_password, phase="create")


async def reinstall_vm_job(
    db: AsyncSession,
    settings: Settings,
    job: Job,
    vm: VM,
    root_password: str,
    template_os: str | None,
) -> None:
    target_os = template_os or vm.template
    template = await db.scalar(select(Template).where(Template.os == target_os))
    if template is None:
        raise RuntimeError("template não encontrado")
    if template.defaults and template.defaults.get("enabled") is False:
        raise RuntimeError("template desabilitado")

    vm.status = VMStatus.deleting.value
    vm.ssh_status = SSHStatus.pending.value
    await db.commit()

    async with ProxmoxClient(settings) as proxmox:
        await destroy_existing_vm(db, proxmox, job, vm, operation="reinstall-destroy")

    vm.template = template.os
    vm.proxmox_vmid = None
    vm.ip_address = None
    vm.node = (template.defaults or {}).get("node") or settings.PROXMOX_DEFAULT_NODE
    vm.status = VMStatus.provisioning.value
    await db.commit()

    await provision_vm_from_template(db, settings, job, vm, template, root_password, phase="reinstall")


async def provision_vm_from_template(
    db: AsyncSession,
    settings: Settings,
    job: Job,
    vm: VM,
    template: Template,
    root_password: str,
    phase: str,
) -> None:
    preferred_node = (template.defaults or {}).get("node") or settings.PROXMOX_DEFAULT_NODE
    vm.node = preferred_node
    vm.template = template.os
    vm.ssh_status = SSHStatus.pending.value
    await db.commit()

    async with ProxmoxClient(settings) as proxmox:
        await set_job_meta(
            db,
            job,
            {
                "operation": f"{phase}:resolve-template",
                "template": template.os,
                "template_vmid": template.proxmox_template_vmid,
                "polled_at": iso_now(),
            },
        )
        vm.node = await proxmox.resolve_template_node(preferred_node, template.proxmox_template_vmid)
        await db.commit()
        await set_job_meta(
            db,
            job,
            {"operation": f"{phase}:allocate-vmid", "node": vm.node, "polled_at": iso_now()},
        )
        new_vmid = await proxmox.next_id()
        upid = await proxmox.post(
            f"/nodes/{vm.node}/qemu/{template.proxmox_template_vmid}/clone",
            data={"newid": new_vmid, "name": vm.hostname, "full": 1},
        )
        await set_job_meta(
            db,
            job,
            {
                "upid": upid,
                "node": vm.node,
                "operation": f"{phase}:clone",
                "template": template.os,
                "template_vmid": template.proxmox_template_vmid,
                "target_vmid": new_vmid,
                "polled_at": iso_now(),
            },
        )
        await proxmox.wait_for_task(vm.node, upid)

        vm.proxmox_vmid = new_vmid
        vm.status = VMStatus.provisioning.value
        await db.commit()

        await set_job_meta(
            db,
            job,
            {"operation": f"{phase}:config-cloudinit", "target_vmid": new_vmid, "polled_at": iso_now()},
        )
        await proxmox.put(
            f"/nodes/{vm.node}/qemu/{new_vmid}/config",
            data={
                "ciuser": "root",
                "cipassword": root_password,
                "sshkeys": settings.CONSOLE_SSH_PUBLIC_KEY.strip(),
                "ipconfig0": settings.CLOUDINIT_IPCONFIG,
                "nameserver": settings.CLOUDINIT_NAMESERVER,
                "cores": vm.cpu,
                "memory": vm.memory_mb,
                "onboot": 1,
            },
        )
        await ensure_disk_size(db, proxmox, job, vm, new_vmid, phase)
        upid = await proxmox.post(f"/nodes/{vm.node}/qemu/{new_vmid}/status/start")
        await set_job_meta(
            db,
            job,
            {"upid": upid, "node": vm.node, "operation": f"{phase}:start", "polled_at": iso_now()},
        )
        await proxmox.wait_for_task(vm.node, upid)

        vm.status = VMStatus.running.value
        await db.commit()

        try:
            await set_job_meta(
                db,
                job,
                {"operation": f"{phase}:wait-ip", "node": vm.node, "target_vmid": new_vmid, "polled_at": iso_now()},
            )
            vm.ip_address = await proxmox.wait_for_ip(vm.node, new_vmid, timeout=600.0)
            await db.commit()
        except ProxmoxTimeoutError as exc:
            vm.ssh_status = SSHStatus.failed.value
            await set_job_meta(
                db,
                job,
                {"warning": str(exc), "operation": f"{phase}:wait-ip", "polled_at": iso_now()},
            )
            await db.commit()
            return

        # Cloud-init templates ship with a baked machine-id, so every clone requests the
        # same DHCP lease and collides on one IP. Reset it and reboot once to force a
        # unique lease before exposing SSH in the panel.
        try:
            await set_job_meta(
                db,
                job,
                {"operation": f"{phase}:reset-machine-id", "node": vm.node, "target_vmid": new_vmid, "polled_at": iso_now()},
            )
            await proxmox.reset_machine_id(vm.node, new_vmid)
            reboot_upid = await proxmox.post(f"/nodes/{vm.node}/qemu/{new_vmid}/status/reboot")
            await set_job_meta(
                db,
                job,
                {
                    "upid": reboot_upid,
                    "node": vm.node,
                    "operation": f"{phase}:reboot-uniq",
                    "polled_at": iso_now(),
                },
            )
            await proxmox.wait_for_task(vm.node, reboot_upid)
            await set_job_meta(
                db,
                job,
                {"operation": f"{phase}:wait-ip-after-reboot", "node": vm.node, "target_vmid": new_vmid, "polled_at": iso_now()},
            )
            vm.ip_address = await proxmox.wait_for_ip(vm.node, new_vmid, timeout=300.0)
            await db.commit()
        except ProxmoxError:
            # Non-fatal: the VM exists and runs; console SSH may need a manual reset.
            pass
        await set_job_meta(
            db,
            job,
            {"operation": f"{phase}:ready", "node": vm.node, "target_vmid": new_vmid, "polled_at": iso_now()},
        )


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
        vm.node = await proxmox.resolve_vm_node(vm.node, vm.proxmox_vmid)
        upid = await proxmox.post(f"/nodes/{vm.node}/qemu/{vm.proxmox_vmid}/status/{action}")
        await set_job_meta(db, job, {"upid": upid, "node": vm.node, "operation": action, "polled_at": iso_now()})
        await proxmox.wait_for_task(vm.node, upid)
        vm.status = final.value
        if operation in (JobType.start_vm, JobType.reboot_vm):
            try:
                vm.ip_address = await proxmox.wait_for_ip(vm.node, vm.proxmox_vmid, timeout=300.0)
            except ProxmoxTimeoutError as exc:
                vm.ssh_status = SSHStatus.failed.value
                await set_job_meta(db, job, {"warning": str(exc), "operation": f"{action}:wait-ip"})
        await db.commit()


async def delete_vm_job(db: AsyncSession, settings: Settings, job: Job, vm: VM) -> None:
    vm.status = VMStatus.deleting.value
    await db.commit()
    if vm.proxmox_vmid is not None:
        async with ProxmoxClient(settings) as proxmox:
            await destroy_existing_vm(db, proxmox, job, vm, operation="delete")
    vm.status = VMStatus.deleted.value
    vm.deleted_at = utcnow()
    await db.commit()


async def destroy_existing_vm(
    db: AsyncSession,
    proxmox: ProxmoxClient,
    job: Job,
    vm: VM,
    operation: str,
) -> None:
    if vm.proxmox_vmid is None:
        return
    try:
        vm.node = await proxmox.resolve_vm_node(vm.node, vm.proxmox_vmid)
        await db.commit()
    except ProxmoxError as exc:
        if "não encontrado" in str(exc):
            return
        raise
    # Proxmox refuses to destroy a running VM ("VM is running - destroy failed"),
    # so stop it first if it is up. Best-effort: if status check fails (for
    # example, VM is already gone), fall through and let destroy report reality.
    try:
        current = await proxmox.get(f"/nodes/{vm.node}/qemu/{vm.proxmox_vmid}/status/current")
        if isinstance(current, dict) and current.get("status") == "running":
            stop_upid = await proxmox.post(f"/nodes/{vm.node}/qemu/{vm.proxmox_vmid}/status/stop")
            await set_job_meta(
                db,
                job,
                {
                    "upid": stop_upid,
                    "node": vm.node,
                    "operation": f"{operation}:stop",
                    "polled_at": iso_now(),
                },
            )
            await proxmox.wait_for_task(vm.node, stop_upid)
    except ProxmoxError:
        pass
    upid = await proxmox.delete(
        f"/nodes/{vm.node}/qemu/{vm.proxmox_vmid}",
        params={"purge": 1, "destroy-unreferenced-disks": 1},
    )
    await set_job_meta(
        db,
        job,
        {"upid": upid, "node": vm.node, "operation": operation, "polled_at": iso_now()},
    )
    await proxmox.wait_for_task(vm.node, upid)


async def ensure_disk_size(
    db: AsyncSession,
    proxmox: ProxmoxClient,
    job: Job,
    vm: VM,
    vmid: int,
    phase: str,
) -> None:
    await set_job_meta(
        db,
        job,
        {"operation": f"{phase}:resize-check", "target_vmid": vmid, "polled_at": iso_now()},
    )
    current_gb = await proxmox.vm_disk_size_gb(vm.node, vmid)
    requested_gb = int(vm.disk_gb)
    if current_gb is not None and requested_gb <= current_gb:
        if requested_gb < current_gb:
            vm.disk_gb = current_gb
            await set_job_meta(
                db,
                job,
                {
                    "operation": f"{phase}:resize-skip",
                    "disk_requested_gb": requested_gb,
                    "disk_effective_gb": current_gb,
                    "warning": "template já possui disco maior; resize para baixo foi ignorado",
                    "polled_at": iso_now(),
                },
            )
        return
    await proxmox.put(
        f"/nodes/{vm.node}/qemu/{vmid}/resize",
        data={"disk": "scsi0", "size": f"{requested_gb}G"},
    )
    await set_job_meta(
        db,
        job,
        {
            "operation": f"{phase}:resize",
            "disk_requested_gb": requested_gb,
            "disk_previous_gb": current_gb,
            "polled_at": iso_now(),
        },
    )


async def enqueue_ssh_check(db: AsyncSession, vm_id: uuid.UUID) -> Job:
    job = Job(type=JobType.ssh_readiness_check.value, status=JobStatus.queued.value, vm_id=vm_id, meta={})
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def set_job_meta(db: AsyncSession, job: Job, patch: dict) -> None:
    job.meta = {**(job.meta or {}), **patch}
    await db.commit()
