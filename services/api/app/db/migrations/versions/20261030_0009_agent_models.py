"""Agent harness: tenant model registry (four-eyes approval) and agent bindings (RLS)

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-30
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.db import tenancy

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _base() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "agent_model",
        *_base(),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("base_url", sa.String(300), nullable=True),
        sa.Column("api_key_env", sa.String(80), nullable=True),
        sa.Column("price_in", sa.Numeric(12, 6), nullable=False),
        sa.Column("price_out", sa.Numeric(12, 6), nullable=False),
        sa.Column("allows_confidential", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("requested_by", sa.String(120), nullable=False),
        sa.Column("approved_by", sa.String(120), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index("ix_agent_model_tenant_id", "agent_model", ["tenant_id"])
    op.create_index("uq_agent_model_tenant_name", "agent_model", ["tenant_id", "name"], unique=True)
    op.create_table(
        "agent_binding",
        *_base(),
        sa.Column("role", sa.String(48), nullable=False),
        sa.Column("models", sa.JSON(), nullable=False),
        sa.Column("updated_by", sa.String(120), nullable=False),
    )
    op.create_index("ix_agent_binding_tenant_id", "agent_binding", ["tenant_id"])
    op.create_index("uq_agent_binding_tenant_role", "agent_binding", ["tenant_id", "role"], unique=True)
    tenancy.install(op.get_bind())


def downgrade() -> None:
    op.drop_table("agent_binding")
    op.drop_table("agent_model")
