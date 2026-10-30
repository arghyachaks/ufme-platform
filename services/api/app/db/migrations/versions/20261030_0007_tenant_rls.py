"""Tenant isolation: restricted app role + row-level security on every tenant table

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-30
"""
from collections.abc import Sequence

from alembic import op

from app.db import tenancy

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    tenancy.install(op.get_bind())


def downgrade() -> None:
    tenancy.uninstall(op.get_bind())
