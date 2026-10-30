"""Tenant isolation in the database: Postgres row-level security.

Every table with a `tenant_id` column gets a policy: a row is visible (and writable) only when its tenant_id equals
the transaction's `app.tenant_id` setting. API requests run their transactions as the restricted role `ufme_app`
(`SET LOCAL ROLE`), with the caller's tenant pinned, so a query that forgets its tenant filter returns nothing from
other tenants instead of leaking them. Background jobs, seeding and migrations keep the owner role: they work
across tenants by design and are not reachable by users.

Locally the database user is a superuser (superusers bypass RLS), which is exactly why requests switch role.
In the cloud the owner should be a plain role and the same policies apply.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.core.config import settings

APP_ROLE = "ufme_app"
POLICY = "tenant_isolation"


def pin_tenant(db: Session, tenant_id: uuid.UUID | None) -> None:
    """Pin this session's transactions to one tenant (re-applied after every commit)."""
    db.info["tenant_id"] = tenant_id
    _apply(db, db.connection())


def unpin(db: Session) -> None:
    """Back to the owner role for the rest of this transaction (system work, test setup)."""
    db.info.pop("tenant_id", None)
    conn = db.connection()
    if conn.dialect.name == "postgresql":
        conn.exec_driver_sql("RESET ROLE")
        conn.execute(text("SELECT set_config('app.tenant_id', '', true)"))


@event.listens_for(Session, "after_begin")
def _after_begin(session: Session, transaction: Any, connection: Connection) -> None:
    if session.info.get("tenant_id") is not None:
        _apply(session, connection)


def _apply(session: Session, conn: Connection) -> None:
    tenant_id = session.info.get("tenant_id")
    if tenant_id is None or not settings.rls_enabled or conn.dialect.name != "postgresql":
        return
    conn.exec_driver_sql(f"SET LOCAL ROLE {APP_ROLE}")
    conn.execute(text("SELECT set_config('app.tenant_id', :t, true)"), {"t": str(tenant_id)})


def tenant_tables(conn: Connection) -> list[str]:
    rows = conn.execute(
        text(
            "SELECT table_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND column_name = 'tenant_id' ORDER BY table_name"
        )
    )
    return [r[0] for r in rows]


def install(conn: Connection) -> list[str]:
    """Create the app role, grant it data access, and put a policy on every tenant table. Idempotent."""
    if conn.dialect.name != "postgresql":
        return []
    conn.exec_driver_sql(
        f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN "
        f"CREATE ROLE {APP_ROLE} NOLOGIN NOSUPERUSER NOBYPASSRLS; END IF; END $$"
    )
    conn.exec_driver_sql(f"GRANT {APP_ROLE} TO CURRENT_USER")  # so the owner may SET ROLE to it
    conn.exec_driver_sql(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")
    conn.exec_driver_sql(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {APP_ROLE}")
    conn.exec_driver_sql(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE}")
    conn.exec_driver_sql(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_ROLE}"
    )
    conn.exec_driver_sql(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {APP_ROLE}"
    )
    tables = tenant_tables(conn)
    for table in tables:
        conn.exec_driver_sql(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        conn.exec_driver_sql(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
        conn.exec_driver_sql(f'DROP POLICY IF EXISTS {POLICY} ON "{table}"')
        conn.exec_driver_sql(
            f'CREATE POLICY {POLICY} ON "{table}" '
            "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
            "WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
        )
    return tables


def uninstall(conn: Connection) -> None:
    if conn.dialect.name != "postgresql":
        return
    for table in tenant_tables(conn):
        conn.exec_driver_sql(f'DROP POLICY IF EXISTS {POLICY} ON "{table}"')
        conn.exec_driver_sql(f'ALTER TABLE "{table}" NO FORCE ROW LEVEL SECURITY')
        conn.exec_driver_sql(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
