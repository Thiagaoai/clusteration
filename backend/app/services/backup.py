"""Automated, consistent SQLite backups of the panel database.

The panel DB records which VMs / IPs / exposures exist; losing it (e.g. an
ephemeral container path wiped on redeploy) recreated the orphaned-public-IP
outage. This takes periodic *consistent* snapshots (SQLite online-backup API,
safe while the app is writing) into a rotated directory on the persistent
/data volume. Off-box copies to a Proxmox node are layered on top of this.
"""

import asyncio
import glob
import logging
import os
import sqlite3
from datetime import UTC, datetime

from sqlalchemy.engine import make_url

from app.core.config import Settings

logger = logging.getLogger(__name__)

_PREFIX = "vmpanel-"
_SUFFIX = ".db"


def sqlite_db_path(database_url: str) -> str | None:
    """Return the on-disk path for a sqlite DATABASE_URL, else None."""
    try:
        url = make_url(database_url)
    except Exception:
        return None
    if url.get_backend_name() != "sqlite":
        return None
    return url.database or None


def _run_backup(db_path: str, backup_dir: str, keep: int) -> str:
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(backup_dir, f"{_PREFIX}{stamp}{_SUFFIX}")
    src = sqlite3.connect(db_path)
    try:
        dst = sqlite3.connect(dest)
        try:
            src.backup(dst)  # atomic, consistent copy even under concurrent writes
        finally:
            dst.close()
    finally:
        src.close()
    # rotate: keep the newest `keep` snapshots
    snaps = sorted(glob.glob(os.path.join(backup_dir, f"{_PREFIX}*{_SUFFIX}")))
    for old in snaps[:-keep] if keep > 0 else []:
        try:
            os.remove(old)
        except OSError:
            pass
    return dest


async def make_backup(settings: Settings) -> str | None:
    """Take one consistent snapshot now. Returns the path, or None if not sqlite."""
    db_path = sqlite_db_path(settings.DATABASE_URL)
    if not db_path or not os.path.exists(db_path):
        return None
    keep = max(1, settings.BACKUP_KEEP)
    return await asyncio.to_thread(_run_backup, db_path, settings.BACKUP_DIR, keep)


async def backup_loop(settings: Settings) -> None:
    """Background task: snapshot on boot, then every BACKUP_INTERVAL_HOURS."""
    if sqlite_db_path(settings.DATABASE_URL) is None:
        logger.info("backup_loop: DATABASE_URL não é sqlite, backups in-app desativados")
        return
    interval = max(1, settings.BACKUP_INTERVAL_HOURS) * 3600
    while True:
        try:
            dest = await make_backup(settings)
            if dest:
                logger.info("backup do DB criado: %s", dest)
        except Exception:
            logger.exception("backup do DB falhou")
        await asyncio.sleep(interval)
