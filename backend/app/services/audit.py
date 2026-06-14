"""Append-only admin audit trail — answers 'who did what, to which VM, from where, when'."""

import logging

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvent

logger = logging.getLogger(__name__)


def client_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


async def record_audit(
    db: AsyncSession,
    *,
    action: str,
    request: Request | None = None,
    actor: str | None = None,
    target_type: str | None = None,
    target_id: object | None = None,
    target_label: str | None = None,
    detail: dict | None = None,
    commit: bool = False,
) -> None:
    """Add an audit row to the session. Never raises — auditing must not break the action it records.

    By default the row is added to the caller's transaction (commits atomically with the
    action). Pass commit=True for endpoints that don't otherwise commit (e.g. login).
    """
    try:
        event = AuditEvent(
            action=action,
            actor=actor,
            source_ip=client_ip(request),
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            target_label=target_label,
            detail=detail or {},
            request_id=getattr(getattr(request, "state", None), "request_id", None) if request else None,
        )
        db.add(event)
        if commit:
            await db.commit()
    except Exception:
        logger.exception("falha ao registrar audit action=%s", action)
