"""Agent harness: agent_run + agent_event (tenant-scoped, row-level security)

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-30
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.db import tenancy

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_run",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent", sa.String(48), nullable=False),
        sa.Column("actor", sa.String(120), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("page", sa.String(120), nullable=True),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False),
        sa.Column("tool_calls", sa.Integer(), nullable=False),
        sa.Column("subagents", sa.Integer(), nullable=False),
        sa.Column("egress", sa.Boolean(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=False),
    )
    op.create_index("ix_agent_run_tenant_id", "agent_run", ["tenant_id"])
    op.create_index("ix_agent_run_tenant_started", "agent_run", ["tenant_id", "started_at"])
    op.create_table(
        "agent_event",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("agent_run.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(24), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_event_tenant_id", "agent_event", ["tenant_id"])
    op.create_index("ix_agent_event_run_seq", "agent_event", ["run_id", "seq"])
    tenancy.install(op.get_bind())


def downgrade() -> None:
    op.drop_table("agent_event")
    op.drop_table("agent_run")
