import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, TypeDecorator

from app.db.base import Base


class GUID(TypeDecorator):
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None or isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class JSONType(TypeDecorator):
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB)
        return dialect.type_descriptor(JSON)


class VMStatus(str, enum.Enum):
    creating = "creating"
    provisioning = "provisioning"
    stopped = "stopped"
    starting = "starting"
    running = "running"
    stopping = "stopping"
    rebooting = "rebooting"
    deleting = "deleting"
    deleted = "deleted"
    error = "error"


class SSHStatus(str, enum.Enum):
    pending = "pending"
    ready = "ready"
    failed = "failed"


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    success = "success"
    failed = "failed"


class JobType(str, enum.Enum):
    create_vm = "create_vm"
    start_vm = "start_vm"
    stop_vm = "stop_vm"
    reboot_vm = "reboot_vm"
    delete_vm = "delete_vm"
    ssh_readiness_check = "ssh_readiness_check"


class TerminalSessionStatus(str, enum.Enum):
    pending = "pending"
    connected = "connected"
    closed = "closed"
    expired = "expired"
    error = "error"


class VM(Base):
    __tablename__ = "vms"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    hostname: Mapped[str] = mapped_column(String(128), nullable=False)
    template: Mapped[str] = mapped_column(String(64), nullable=False)
    cpu: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    memory_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=2048)
    disk_gb: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    proxmox_vmid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    node: Mapped[str] = mapped_column(String(128), nullable=False, default="pve")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=VMStatus.creating.value)
    ssh_status: Mapped[str] = mapped_column(String(32), nullable=False, default=SSHStatus.pending.value)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    jobs: Mapped[list["Job"]] = relationship(back_populates="vm", passive_deletes=True)
    terminal_sessions: Mapped[list["TerminalSession"]] = relationship(
        back_populates="vm", cascade="all, delete-orphan"
    )
    exposures: Mapped[list["VMExposure"]] = relationship(back_populates="vm", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=JobStatus.queued.value)
    vm_id: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("vms.id", ondelete="SET NULL"))
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONType(), default=dict, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    vm: Mapped[VM | None] = relationship(back_populates="jobs")


class TerminalSession(Base):
    __tablename__ = "terminal_sessions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    vm_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("vms.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=TerminalSessionStatus.pending.value
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    vm: Mapped[VM] = relationship(back_populates="terminal_sessions")


class VMExposure(Base):
    __tablename__ = "vm_exposures"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    vm_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("vms.id", ondelete="CASCADE"), nullable=False)
    slug: Mapped[str] = mapped_column(String(63), unique=True, nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    vm: Mapped[VM] = relationship(back_populates="exposures")


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    os: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    proxmox_template_vmid: Mapped[int] = mapped_column(Integer, nullable=False)
    defaults: Mapped[dict[str, Any]] = mapped_column(JSONType(), default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditEvent(Base):
    """Append-only record of admin actions: who did what, to which VM, from where, when."""

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONType(), default=dict, nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdminCredential(Base):
    """Runtime-mutable admin password (so it can be reset/changed without a redeploy).

    Seeded from the env ADMIN_PASSWORD/HASH on first boot; afterwards this is authoritative.
    """

    __tablename__ = "admin_credentials"

    username: Mapped[str] = mapped_column(String(128), primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PasswordReset(Base):
    """Short-lived, single-use, hashed password-reset codes emailed to the admin."""

    __tablename__ = "password_resets"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

