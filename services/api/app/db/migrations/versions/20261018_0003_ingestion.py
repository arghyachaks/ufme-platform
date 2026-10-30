"""Ingestion: fx_rate, ingestion_batch, ledger_txn, quarantined_row; dq_issue status + batch

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-18
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MONEY = sa.Numeric(20, 4)
RATE = sa.Numeric(20, 10)


def _base(table: str) -> list:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=f"pk_{table}"),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name=f"fk_{table}_tenant_id_tenant", ondelete="CASCADE"),
    ]


def upgrade() -> None:
    op.create_table(
        "fx_rate",
        *_base("fx_rate"),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("rate_to_usd", RATE, nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.UniqueConstraint("tenant_id", "rate_date", "currency", name="uq_fx_rate_tenant_date_ccy"),
    )
    op.create_index("ix_fx_rate_tenant_id", "fx_rate", ["tenant_id"])

    op.create_table(
        "ingestion_batch",
        *_base("ingestion_batch"),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("rows_total", sa.Integer(), nullable=False),
        sa.Column("rows_loaded", sa.Integer(), nullable=False),
        sa.Column("rows_quarantined", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("storage_path", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["data_source.id"], name="fk_ingestion_batch_source_id_data_source", ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_ingestion_batch_tenant_code"),
    )
    op.create_index("ix_ingestion_batch_tenant_id", "ingestion_batch", ["tenant_id"])
    op.create_index("ix_ingestion_batch_source_id", "ingestion_batch", ["source_id"])

    op.create_table(
        "ledger_txn",
        *_base("ledger_txn"),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("entity_code", sa.String(16), nullable=False),
        sa.Column("counterparty_code", sa.String(120), nullable=False),
        sa.Column("account", sa.String(64), nullable=True),
        sa.Column("amount", MONEY, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("amount_usd", MONEY, nullable=True),
        sa.Column("fx_rate", RATE, nullable=True),
        sa.Column("value_date", sa.Date(), nullable=False),
        sa.Column("posting_date", sa.Date(), nullable=True),
        sa.Column("reference_raw", sa.String(255), nullable=True),
        sa.Column("reference_norm", sa.String(255), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("raw", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["ingestion_batch.id"], name="fk_ledger_txn_batch_id_ingestion_batch", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["data_source.id"], name="fk_ledger_txn_source_id_data_source", ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_ledger_txn_tenant_code"),
    )
    op.create_index("ix_ledger_txn_tenant_id", "ledger_txn", ["tenant_id"])
    op.create_index("ix_ledger_txn_batch_id", "ledger_txn", ["batch_id"])
    op.create_index("ix_ledger_txn_pair", "ledger_txn", ["tenant_id", "entity_code", "counterparty_code", "value_date"])
    op.create_index("ix_ledger_txn_reference", "ledger_txn", ["tenant_id", "reference_norm"])
    op.create_index("ix_ledger_txn_external", "ledger_txn", ["tenant_id", "source_id", "external_id"])

    op.create_table(
        "quarantined_row",
        *_base("quarantined_row"),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("raw", sa.JSON(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["ingestion_batch.id"], name="fk_quarantined_row_batch_id_ingestion_batch", ondelete="CASCADE"),
    )
    op.create_index("ix_quarantined_row_tenant_id", "quarantined_row", ["tenant_id"])
    op.create_index("ix_quarantined_row_batch_id", "quarantined_row", ["batch_id"])

    with op.batch_alter_table("dq_issue") as batch:
        batch.add_column(sa.Column("status", sa.String(16), nullable=False, server_default="Open"))
        batch.add_column(sa.Column("batch_id", sa.Uuid(), nullable=True))
        batch.create_foreign_key("fk_dq_issue_batch_id_ingestion_batch", "ingestion_batch", ["batch_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    with op.batch_alter_table("dq_issue") as batch:
        batch.drop_constraint("fk_dq_issue_batch_id_ingestion_batch", type_="foreignkey")
        batch.drop_column("batch_id")
        batch.drop_column("status")
    for table in ("quarantined_row", "ledger_txn", "ingestion_batch", "fx_rate"):
        op.drop_table(table)
