"""Agent harness: agent_run.status fits "awaiting_approval" (runs paused for a person's decision)

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-30
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("agent_run", "status", type_=sa.String(24), existing_nullable=False)


def downgrade() -> None:
    op.alter_column("agent_run", "status", type_=sa.String(16), existing_nullable=False)
