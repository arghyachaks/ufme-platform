"""Stage 3b matching: match_run, match_group, match_member, match_label; match_rule.definition

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-20
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY = sa.Numeric(20, 4)


def _base(table: str, coded: bool = True) -> list:
    cols = [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=f"pk_{table}"),
    ]
    if coded:
        cols += [
            sa.Column("tenant_id", sa.Uuid(), nullable=False),
            sa.Column("code", sa.String(32), nullable=False),
            sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name=f"fk_{table}_tenant_id_tenant", ondelete="CASCADE"),
            sa.UniqueConstraint("tenant_id", "code", name=f"uq_{table}_tenant_code"),
        ]
    return cols


def upgrade() -> None:
    with op.batch_alter_table("match_rule") as batch:
        batch.add_column(sa.Column("definition", sa.JSON(), nullable=True))

    op.create_table(
        "match_run",
        *_base("match_run"),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("engine_version", sa.String(64), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("requested_by", sa.String(120), nullable=False),
    )
    op.create_index("ix_match_run_tenant_id", "match_run", ["tenant_id"])

    op.create_table(
        "match_group",
        *_base("match_group"),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("match_type", sa.String(8), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("exposure_usd", MONEY, nullable=False),
        sa.Column("residual_usd", MONEY, nullable=False),
        sa.Column("entity_pair", sa.String(40), nullable=False),
        sa.Column("rule_ids", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.JSON(), nullable=False),
        sa.Column("decided_by", sa.String(120), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["match_run.id"], name="fk_match_group_run_id_match_run", ondelete="CASCADE"),
    )
    op.create_index("ix_match_group_tenant_id", "match_group", ["tenant_id"])
    op.create_index("ix_match_group_run_id", "match_group", ["run_id"])
    op.create_index("ix_match_group_tenant_status", "match_group", ["tenant_id", "status"])

    op.create_table(
        "match_member",
        *_base("match_member", coded=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("txn_id", sa.Uuid(), nullable=False),
        sa.Column("side", sa.String(1), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["match_group.id"], name="fk_match_member_group_id_match_group", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["txn_id"], ["ledger_txn.id"], name="fk_match_member_txn_id_ledger_txn", ondelete="CASCADE"),
    )
    op.create_index("ix_match_member_group_id", "match_member", ["group_id"])
    op.create_index("ix_match_member_txn_id", "match_member", ["txn_id"])

    op.create_table(
        "match_label",
        *_base("match_label", coded=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("actor", sa.String(120), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("model_confidence", sa.Float(), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_match_label_tenant_id_tenant", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["match_group.id"], name="fk_match_label_group_id_match_group", ondelete="CASCADE"),
    )
    op.create_index("ix_match_label_tenant_id", "match_label", ["tenant_id"])
    op.create_index("ix_match_label_group_id", "match_label", ["group_id"])


def downgrade() -> None:
    for table in ("match_label", "match_member", "match_group", "match_run"):
        op.drop_table(table)
    with op.batch_alter_table("match_rule") as batch:
        batch.drop_column("definition")
