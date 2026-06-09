"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid_type():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        from sqlalchemy.dialects import postgresql

        return postgresql.UUID(as_uuid=True)
    return sa.String(length=36)


def _json_type():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        from sqlalchemy.dialects import postgresql

        return postgresql.JSONB()
    return sa.JSON()


def upgrade() -> None:
    uuid_type = _uuid_type()
    json_type = _json_type()

    op.create_table(
        "vms",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("hostname", sa.String(128), nullable=False),
        sa.Column("template", sa.String(64), nullable=False),
        sa.Column("cpu", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("memory_mb", sa.Integer(), nullable=False, server_default="2048"),
        sa.Column("disk_gb", sa.Integer(), nullable=False, server_default="12"),
        sa.Column("proxmox_vmid", sa.Integer(), nullable=True),
        sa.Column("node", sa.String(128), nullable=False, server_default="pve"),
        sa.Column("status", sa.String(32), nullable=False, server_default="creating"),
        sa.Column("ssh_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_vms_deleted_at", "vms", ["deleted_at"])

    op.create_table(
        "jobs",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("vm_id", uuid_type, sa.ForeignKey("vms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metadata", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_jobs_vm_id", "jobs", ["vm_id"])

    op.create_table(
        "terminal_sessions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("vm_id", uuid_type, sa.ForeignKey("vms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_terminal_sessions_vm_id", "terminal_sessions", ["vm_id"])

    op.create_table(
        "vm_exposures",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("vm_id", uuid_type, sa.ForeignKey("vms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.String(63), nullable=False, unique=True),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_vm_exposures_vm_id", "vm_exposures", ["vm_id"])

    op.create_table(
        "templates",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("os", sa.String(64), nullable=False, unique=True),
        sa.Column("proxmox_template_vmid", sa.Integer(), nullable=False),
        sa.Column("defaults", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("templates")
    op.drop_index("ix_vm_exposures_vm_id", table_name="vm_exposures")
    op.drop_table("vm_exposures")
    op.drop_index("ix_terminal_sessions_vm_id", table_name="terminal_sessions")
    op.drop_table("terminal_sessions")
    op.drop_index("ix_jobs_vm_id", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_vms_deleted_at", table_name="vms")
    op.drop_table("vms")

