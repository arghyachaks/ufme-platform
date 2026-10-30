"""Learning loop: label outcomes + feature vectors on match_label, scorer_model registry

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-30
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("match_label", sa.Column("label", sa.SmallInteger(), nullable=True))
    op.add_column("match_label", sa.Column("source", sa.String(24), nullable=True))
    op.add_column("match_label", sa.Column("vector", sa.JSON(), nullable=True))
    op.add_column("match_label", sa.Column("within_policy", sa.Boolean(), nullable=True))
    op.add_column("match_label", sa.Column("model_version", sa.String(64), nullable=True))
    op.create_table(
        "scorer_model",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("base_version", sa.String(64), nullable=False),
        sa.Column("artifact", sa.JSON(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("gate", sa.JSON(), nullable=False),
        sa.Column("label_count", sa.Integer(), nullable=False),
        sa.Column("trained_by", sa.String(120), nullable=False),
        sa.Column("promoted_by", sa.String(120), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_scorer_model"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_scorer_model_tenant_id_tenant", ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "version", name="uq_scorer_model_tenant_version"),
    )
    op.create_index("ix_scorer_model_tenant_id", "scorer_model", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_scorer_model_tenant_id", table_name="scorer_model")
    op.drop_table("scorer_model")
    for col in ("model_version", "within_policy", "vector", "source", "label"):
        op.drop_column("match_label", col)
