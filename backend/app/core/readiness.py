from sqlalchemy.engine import make_url

from app.core.config import Settings


def missing_runtime_settings(settings: Settings) -> list[str]:
    required = {
        "PROXMOX_HOST": settings.PROXMOX_HOST,
        "PROXMOX_TOKEN_ID": settings.PROXMOX_TOKEN_ID,
        "PROXMOX_TOKEN_SECRET": settings.PROXMOX_TOKEN_SECRET,
        "CONSOLE_SSH_PRIVATE_KEY": settings.CONSOLE_SSH_PRIVATE_KEY,
        "CONSOLE_SSH_PUBLIC_KEY": settings.CONSOLE_SSH_PUBLIC_KEY,
    }
    missing = [key for key, value in required.items() if not str(value or "").strip()]
    if settings.PROXMOX_TOKEN_SECRET.strip().lower() in {"change-me", "secret", "placeholder"}:
        missing.append("PROXMOX_TOKEN_SECRET")
    return sorted(set(missing))


def is_runtime_ready(settings: Settings) -> bool:
    return not missing_runtime_settings(settings)


def database_durability(settings: Settings) -> dict:
    try:
        url = make_url(settings.DATABASE_URL)
    except Exception:
        return {
            "backend": "unknown",
            "database": "",
            "durable": False,
            "message": "DATABASE_URL inválida",
        }
    backend = url.get_backend_name()
    if backend == "sqlite":
        db_path = url.database or ""
        durable = db_path.startswith("/data/")
        return {
            "backend": "sqlite",
            "database": db_path,
            "durable": durable,
            "backup_dir": settings.BACKUP_DIR,
            "message": (
                "SQLite em /data com volume persistente"
                if durable
                else "SQLite fora de /data: risco de reset em rebuild/redeploy"
            ),
        }
    return {
        "backend": backend,
        "database": url.host or backend,
        "durable": True,
        "message": "Banco externo/persistente gerenciado fora do container",
    }
