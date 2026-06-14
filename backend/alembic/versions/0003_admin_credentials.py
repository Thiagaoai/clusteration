"""admin_credentials + password_resets

Revision ID: 0003_admin_credentials
Revises: 0002_audit_events
Create Date: 2026-06-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_admin_credentials"
down_revision: str | None = "0002_audit_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid_type():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        from sqlalchemy.dialects import postgresql

        return postgresql.UUID(as_uuid=True)
    return sa.String(length=36)


def upgrade() -> None:
    op.create_table(
        "admin_credentials",
        sa.Column("username", sa.String(128), primary_key=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "password_resets",
        sa.Column("id", _uuid_type(), primary_key=True),
        sa.Column("username", sa.String(128), nullable=False),
        sa.Column("code_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_password_resets_created_at", "password_resets", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_password_resets_created_at", table_name="password_resets")
    op.drop_table("password_resets")
    op.drop_table("admin_credentials")
