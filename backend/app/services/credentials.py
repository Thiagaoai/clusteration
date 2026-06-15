"""Runtime-mutable admin credential — DB-backed so the password can be reset/changed.

Seeded from the env ADMIN_PASSWORD_HASH on first boot; afterwards the DB row is
authoritative. The env hash stays as a break-glass fallback if the row is missing.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import pwd, verify_login
from app.core.config import Settings
from app.models import AdminCredential

logger = logging.getLogger(__name__)


def norm_username(username: str | None) -> str:
    return (username or "").strip().casefold()


async def seed_admin_credential(db: AsyncSession, settings: Settings) -> None:
    uname = norm_username(settings.ADMIN_USERNAME)
    if not uname:
        return
    existing = await db.scalar(select(AdminCredential).where(AdminCredential.username == uname))
    if existing:
        return
    if settings.ADMIN_PASSWORD_HASH:
        password_hash = settings.ADMIN_PASSWORD_HASH
    else:
        return
    db.add(AdminCredential(username=uname, password_hash=password_hash))
    await db.commit()


async def verify_admin(db: AsyncSession, username: str, password: str, settings: Settings) -> bool:
    if norm_username(username) != norm_username(settings.ADMIN_USERNAME):
        return False
    cred = await db.scalar(
        select(AdminCredential).where(AdminCredential.username == norm_username(settings.ADMIN_USERNAME))
    )
    if cred is not None:
        try:
            return pwd.verify(password, cred.password_hash)
        except Exception:
            return False
    # No DB row yet — fall back to the env credential.
    return verify_login(username, password, settings)


async def set_admin_password(db: AsyncSession, settings: Settings, new_password: str) -> None:
    uname = norm_username(settings.ADMIN_USERNAME)
    cred = await db.scalar(select(AdminCredential).where(AdminCredential.username == uname))
    new_hash = pwd.hash(new_password)
    if cred is not None:
        cred.password_hash = new_hash
    else:
        db.add(AdminCredential(username=uname, password_hash=new_hash))
    await db.commit()
