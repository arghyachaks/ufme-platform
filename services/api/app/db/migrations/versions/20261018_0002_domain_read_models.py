"""Stage 1 domain tables: exceptions, cases, comments, rules, policies, sources, DQ issues, controls, snapshots

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-18
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY = sa.Numeric(20, 4)


def _base(table: str) -> list:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=f"pk_{table}"),
    ]


def _tenant_scoped(table: str, *columns: sa.Column) -> None:
    op.create_table(
        table,
        *_base(table),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        *columns,
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name=f"fk_{table}_tenant_id_tenant", ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "code", name=f"uq_{table}_tenant_code"),
    )
    op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])


def upgrade() -> None:
    op.add_column("legal_entity", sa.Column("recon_owner", sa.String(120), nullable=True))

    _tenant_scoped(
        "exception_item",
        sa.Column("entity_code", sa.String(16), nullable=False),
        sa.Column("counterparty", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("owner", sa.String(120), nullable=False),
        sa.Column("root_cause", sa.String(200), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=False),
    )
    _tenant_scoped(
        "recon_case",
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("entity_code", sa.String(16), nullable=False),
        sa.Column("exposure", MONEY, nullable=False),
        sa.Column("priority", sa.String(16), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("assignee", sa.String(120), nullable=False),
        sa.Column("exception_codes", sa.JSON(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "case_comment",
        *_base("case_comment"),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("author", sa.String(120), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["recon_case.id"], name="fk_case_comment_case_id_recon_case", ondelete="CASCADE"),
    )
    op.create_index("ix_case_comment_case_id", "case_comment", ["case_id"])
    _tenant_scoped(
        "match_rule",
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("scope", sa.String(48), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("tolerance", sa.String(64), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("hit_rate", sa.Float(), nullable=False),
        sa.Column("precision", sa.Float(), nullable=False),
        sa.Column("version", sa.String(24), nullable=False),
        sa.Column("edited_on", sa.Date(), nullable=False),
        sa.Column("edited_by", sa.String(120), nullable=False),
    )
    _tenant_scoped(
        "policy",
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(48), nullable=False),
        sa.Column("version", sa.String(24), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("owner", sa.String(120), nullable=False),
        sa.Column("effective_on", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("thresholds", sa.JSON(), nullable=False),
    )
    _tenant_scoped(
        "data_source",
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("system", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_24h", sa.Integer(), nullable=False),
        sa.Column("latency_min", sa.Integer(), nullable=False),
        sa.Column("schedule", sa.String(64), nullable=False),
    )
    _tenant_scoped(
        "dq_issue",
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("check_name", sa.String(200), nullable=False),
        sa.Column("field", sa.String(64), nullable=False),
        sa.Column("failing", sa.Integer(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("auto_fixed", sa.Boolean(), nullable=False),
    )
    _tenant_scoped(
        "control_test",
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("owner", sa.String(120), nullable=False),
        sa.Column("last_run_on", sa.Date(), nullable=True),
        sa.Column("result", sa.String(16), nullable=False),
        sa.Column("evidence", sa.Integer(), nullable=False),
    )
    op.create_table(
        "snapshot",
        *_base("snapshot"),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_snapshot_tenant_id_tenant", ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "key", name="uq_snapshot_tenant_key"),
    )
    op.create_index("ix_snapshot_tenant_id", "snapshot", ["tenant_id"])


def downgrade() -> None:
    for table in ("snapshot", "control_test", "dq_issue", "data_source", "policy", "match_rule", "case_comment",
                  "recon_case", "exception_item"):
        op.drop_table(table)
    with op.batch_alter_table("legal_entity") as batch:
        batch.drop_column("recon_owner")
