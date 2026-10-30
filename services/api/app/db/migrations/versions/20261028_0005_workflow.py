"""Workflow: approval_request, period_signoff

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-28
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY = sa.Numeric(20, 4)


def _base(table: str) -> list:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.PrimaryKeyConstraint("id", name=f"pk_{table}"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name=f"fk_{table}_tenant_id_tenant", ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "code", name=f"uq_{table}_tenant_code"),
    ]


def upgrade() -> None:
    op.create_table(
        "approval_request",
        *_base("approval_request"),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=True),
        sa.Column("match_code", sa.String(32), nullable=False),
        sa.Column("entity_code", sa.String(40), nullable=False),
        sa.Column("exposure_usd", MONEY, nullable=False),
        sa.Column("materiality", sa.String(8), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("required_role", sa.String(32), nullable=False),
        sa.Column("approvals_needed", sa.Integer(), nullable=False),
        sa.Column("approvals", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("submitted_by", sa.String(320), nullable=False),
        sa.Column("submitted_by_name", sa.String(200), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("documents", sa.JSON(), nullable=False),
        sa.Column("factors", sa.JSON(), nullable=False),
        sa.Column("trail", sa.JSON(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["group_id"], ["match_group.id"], name="fk_approval_request_group_id_match_group", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_approval_request_tenant_id", "approval_request", ["tenant_id"])
    op.create_index("ix_approval_request_group_id", "approval_request", ["group_id"])
    op.create_index("ix_approval_request_status", "approval_request", ["status"])
    op.create_table(
        "period_signoff",
        *_base("period_signoff"),
        sa.Column("entity_code", sa.String(16), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("signatures", sa.JSON(), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_period_signoff_tenant_id", "period_signoff", ["tenant_id"])
    # Speeds up the proposals and transactions lists (filtered by tenant + run / status, ordered by code).
    op.create_index("ix_match_group_tenant_run_status", "match_group", ["tenant_id", "run_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_match_group_tenant_run_status", table_name="match_group")
    op.drop_table("period_signoff")
    op.drop_table("approval_request")
