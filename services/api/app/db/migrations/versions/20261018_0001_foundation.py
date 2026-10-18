"""Foundation: tenant, legal_entity, role, app_user, user_role, audit_event

Revision ID: 0001
Revises:
Create Date: 2026-10-18
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "tenant",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("region", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_tenant"),
        sa.UniqueConstraint("slug", name="uq_tenant_slug"),
    )
    op.create_table(
        "legal_entity",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("country", sa.String(64), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_legal_entity_tenant_id_tenant", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_legal_entity"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_legal_entity_tenant_code"),
    )
    op.create_index("ix_legal_entity_tenant_id", "legal_entity", ["tenant_id"])
    op.create_table(
        "role",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_role_tenant_id_tenant", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_role"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
    )
    op.create_index("ix_role_tenant_id", "role", ["tenant_id"])
    op.create_table(
        "app_user",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False),
        sa.Column("external_subject", sa.String(255), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_app_user_tenant_id_tenant", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_app_user"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_app_user_tenant_email"),
        sa.UniqueConstraint("external_subject", name="uq_app_user_external_subject"),
    )
    op.create_index("ix_app_user_tenant_id", "app_user", ["tenant_id"])
    op.create_table(
        "user_role",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("entity_codes", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], name="fk_user_role_user_id_app_user", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["role.id"], name="fk_user_role_role_id_role", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_user_role"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_role_user_role"),
    )
    op.create_index("ix_user_role_user_id", "user_role", ["user_id"])
    op.create_index("ix_user_role_role_id", "user_role", ["role_id"])
    op.create_table(
        "audit_event",
        sa.Column("seq", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), sa.Identity(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(320), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("object_type", sa.String(64), nullable=False),
        sa.Column("object_id", sa.String(128), nullable=False),
        sa.Column("entity_code", sa.String(16), nullable=True),
        sa.Column("control", sa.String(32), nullable=True),
        sa.Column("request_id", sa.String(128), nullable=True),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
        sa.Column("prev_hash", sa.String(64), nullable=True),
        sa.Column("hash", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"], name="fk_audit_event_tenant_id_tenant"),
        sa.PrimaryKeyConstraint("seq", name="pk_audit_event"),
    )
    op.create_index("ix_audit_event_tenant_id", "audit_event", ["tenant_id"])
    op.create_index("ix_audit_event_occurred_at", "audit_event", ["occurred_at"])
    op.create_index("ix_audit_event_tenant_object", "audit_event", ["tenant_id", "object_type", "object_id"])
    if op.get_bind().dialect.name == "postgresql":
        # Append-only: block UPDATE/DELETE on the audit trail at the database level.
        op.execute("""
            CREATE OR REPLACE FUNCTION audit_event_immutable() RETURNS trigger AS $$
            BEGIN RAISE EXCEPTION 'audit_event is append-only'; END; $$ LANGUAGE plpgsql;
        """)
        op.execute("""
            CREATE TRIGGER audit_event_no_change BEFORE UPDATE OR DELETE ON audit_event
            FOR EACH ROW EXECUTE FUNCTION audit_event_immutable();
        """)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS audit_event_no_change ON audit_event")
        op.execute("DROP FUNCTION IF EXISTS audit_event_immutable()")
    op.drop_table("audit_event")
    op.drop_table("user_role")
    op.drop_table("app_user")
    op.drop_table("role")
    op.drop_table("legal_entity")
    op.drop_table("tenant")
