from fastapi import APIRouter, Header, Query
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models import VM, VMExposure

router = APIRouter()


@router.get("/internal/exposure-upstream")
async def exposure_upstream(host: str = Query(...), x_proxy_secret: str | None = Header(default=None)):
    settings = get_settings()
    if not settings.EXPOSURE_PROXY_SECRET or x_proxy_secret != settings.EXPOSURE_PROXY_SECRET:
        return []

    normalized = host.split(":", 1)[0].strip().lower()
    suffix = "." + settings.EXPOSURE_BASE_DOMAIN.lower()
    if not normalized.endswith(suffix):
        return []
    slug = normalized[: -len(suffix)]

    async with AsyncSessionLocal() as db:
        exposure = await db.scalar(select(VMExposure).where(VMExposure.slug == slug, VMExposure.enabled.is_(True)))
        if exposure is None:
            return []
        vm = await db.get(VM, exposure.vm_id)
        if vm is None or vm.deleted_at is not None or not vm.ip_address:
            return []
        return [{"dial": f"{vm.ip_address}:{exposure.port}"}]

