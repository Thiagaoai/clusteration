from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class VMCreate(BaseModel):
    hostname: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,126}[a-zA-Z0-9])?$")
    template: str
    size: str = "small"
    disk_gb: int = 12
    root_password: str = Field(min_length=8, max_length=256)


class DeleteVM(BaseModel):
    confirm_hostname: str


class ReinstallVM(BaseModel):
    confirm_hostname: str
    template: str | None = None
    root_password: str = Field(min_length=8, max_length=256)


class ExposureCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=63, pattern=r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
    port: int = Field(ge=1, le=65535)


class VMActions(BaseModel):
    can_start: bool
    can_stop: bool
    can_reboot: bool
    can_terminal: bool
    can_delete: bool
    can_reinstall: bool = False
    can_recheck: bool = False


class VMOut(BaseModel):
    id: UUID
    hostname: str
    template: str
    cpu: int
    memory_mb: int
    disk_gb: int
    status: str
    ssh_status: str
    ip_address: str | None
    created_at: datetime | None
    actions: VMActions
    last_error: str | None = None


class JobOut(BaseModel):
    id: UUID
    type: str
    status: str
    error: str | None
    meta: dict
    vm_id: UUID | None
    created_at: datetime | None
    updated_at: datetime | None
