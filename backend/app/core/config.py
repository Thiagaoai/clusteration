from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

SOURCE_BUILD_ID = "2026-06-17-vm-create-flow-v1"
UNSET_BUILD_IDS = {"", "dev", "unknown"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"
    APP_BUILD_ID: str = "dev"
    SECRET_KEY: str = "dev-only-change-me"
    SESSION_MAX_AGE: int = 86400
    SESSION_SAME_SITE: Literal["lax", "strict", "none"] = "lax"
    SESSION_HTTPS_ONLY: bool = False
    CORS_ORIGINS: str = ""

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = ""

    DATABASE_URL: str = "sqlite+aiosqlite:////data/vmpanel.db"

    # Automated SQLite backups (no-op when DATABASE_URL is not sqlite)
    BACKUP_DIR: str = "/data/backups"
    BACKUP_INTERVAL_HOURS: int = 6
    BACKUP_KEEP: int = 28

    # Password reset via email (SMTP). When SMTP_HOST is empty the feature is disabled.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_STARTTLS: bool = True
    RESET_EMAIL_TO: str = ""
    RESET_CODE_TTL_MINUTES: int = 15

    PROXMOX_HOST: str = ""
    PROXMOX_TOKEN_ID: str = ""
    PROXMOX_TOKEN_SECRET: str = ""
    PROXMOX_DEFAULT_NODE: str = "pve1"
    PROXMOX_DEFAULT_STORAGE: str = "local-lvm"
    PROXMOX_DEFAULT_BRIDGE: str = "vmbr0"
    TEMPLATE_DEBIAN_VMID: int = 9000
    TEMPLATE_UBUNTU_VMID: int = 9001
    TEMPLATE_FEDORA_VMID: int = 9002
    TEMPLATE_HERMES_VMID: int = 9010
    TEMPLATE_OPENCLAW_VMID: int = 9011
    TEMPLATE_CLAUDE_VMID: int = 9012

    CLOUDINIT_NAMESERVER: str = "1.1.1.1"
    CLOUDINIT_IPCONFIG: str = "ip=dhcp"

    CONSOLE_SSH_PRIVATE_KEY: str = ""
    CONSOLE_SSH_PUBLIC_KEY: str = ""
    CONSOLE_SSH_USER: str = "root"
    CONSOLE_SSH_PORT: int = 22
    TERMINAL_SESSION_TTL_SECONDS: int = 300

    EXPOSURE_BASE_DOMAIN: str = "apps.exemplo.internal"
    EXPOSURE_PROXY_SECRET: str = ""

    WORKER_MODE: Literal["inprocess", "arq"] = "inprocess"
    REDIS_URL: str = "redis://localhost:6379/0"

    VM_SIZE_DEFAULT: str = "small"
    VM_DISK_CHOICES: list[int] = Field(default_factory=lambda: [12, 16, 36, 64, 100])


VM_SIZES = {
    "small": {"cpu": 1, "memory_mb": 2048, "label": "1 vCPU / 2 GB"},
    "medium": {"cpu": 2, "memory_mb": 4096, "label": "2 vCPU / 4 GB"},
}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def effective_build_id(settings: Settings) -> str:
    configured = (settings.APP_BUILD_ID or "").strip()
    if configured and configured not in UNSET_BUILD_IDS:
        return configured
    return SOURCE_BUILD_ID
