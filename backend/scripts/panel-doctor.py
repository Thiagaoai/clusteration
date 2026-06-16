#!/usr/bin/env python3
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.config import get_settings
from app.core.readiness import missing_runtime_settings
from app.db.session import AsyncSessionLocal
from app.models import Template
from app.services.proxmox import ProxmoxAuthError, ProxmoxClient, ProxmoxError


async def main() -> int:
    settings = get_settings()
    missing = missing_runtime_settings(settings)
    if missing:
        print("FAIL runtime config missing:", ", ".join(missing))
        return 1
    print("OK runtime config present")

    async with AsyncSessionLocal() as db:
        templates = (await db.scalars(select(Template).order_by(Template.os))).all()
        if not templates:
            print("FAIL no templates seeded; run: alembic upgrade head && restart app")
            return 1
        print("OK templates:", ", ".join(f"{t.os}:{t.proxmox_template_vmid}" for t in templates))

    try:
        async with ProxmoxClient(settings) as proxmox:
            next_id = await proxmox.next_id()
            print(f"OK Proxmox auth/API nextid={next_id}")
            for template in templates:
                preferred_node = (template.defaults or {}).get("node") or settings.PROXMOX_DEFAULT_NODE
                node = await proxmox.resolve_template_node(preferred_node, template.proxmox_template_vmid)
                disk_gb = await proxmox.vm_disk_size_gb(node, template.proxmox_template_vmid)
                disk_text = f", disk={disk_gb}GB" if disk_gb else ""
                print(f"OK template {template.os}:{template.proxmox_template_vmid} on {node}{disk_text}")
    except ProxmoxAuthError as exc:
        print(f"FAIL Proxmox auth: {exc}")
        print("Check PROXMOX_TOKEN_ID/PROXMOX_TOKEN_SECRET and API token permissions.")
        return 1
    except ProxmoxError as exc:
        print(f"FAIL Proxmox API: {exc}")
        return 1

    print("READY panel can create VMs if templates exist on Proxmox.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
