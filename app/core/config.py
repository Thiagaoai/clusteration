from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev-only-change-me"
    SESSION_MAX_AGE: int = 86400

    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = ""

    DATABASE_URL: str = "sqlite+aiosqlite:///./vmpanel.db"

    PROXMOX_HOST: str = "https://10.1.10.209:8006"
    PROXMOX_TOKEN_ID: str = ""
    PROXMOX_TOKEN_SECRET: str = ""
    PROXMOX_DEFAULT_NODE: str = "pve"
    PROXMOX_DEFAULT_STORAGE: str = "local-lvm"
    PROXMOX_DEFAULT_BRIDGE: str = "vmbr0"

    CLOUDINIT_NAMESERVER: str = "1.1.1.1"
    CLOUDINIT_IPCONFIG: str = "ip=dhcp"

    CONSOLE_SSH_PRIVATE_KEY: str = ""
    CONSOLE_SSH_PUBLIC_KEY: str = ""
    CONSOLE_SSH_USER: str = "root"
    CONSOLE_SSH_PORT: int = 22

    EXPOSURE_BASE_DOMAIN: str = "apps.exemplo.internal"
    EXPOSURE_PROXY_SECRET: str = ""

    WORKER_MODE: Literal["inprocess", "arq"] = "inprocess"
    REDIS_URL: str = "redis://localhost:6379/0"

    VM_SIZE_DEFAULT: str = "small"
    VM_DISK_CHOICES: list[int] = Field(default_factory=lambda: [12, 36, 64, 100])


VM_SIZES = {
    "small": {"cpu": 1, "memory_mb": 2048, "label": "1 vCPU / 2 GB"},
    "medium": {"cpu": 2, "memory_mb": 4096, "label": "2 vCPU / 4 GB"},
}


@lru_cache
def get_settings() -> Settings:
    return Settings()

