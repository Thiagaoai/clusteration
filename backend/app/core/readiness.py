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

