from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentTenant, DbSession
from app.schemas.read import AdminOut
from app.services import matching_read, read

router = APIRouter()


@router.get("/admin", response_model=AdminOut)
def admin(db: DbSession, tenant: CurrentTenant) -> AdminOut:
    return read.admin(db, tenant)


@router.get("/ops")
def ops(db: DbSession, tenant: CurrentTenant) -> Any:
    return read.snapshot(db, tenant, "ops")


@router.get("/graph")
def graph(db: DbSession, tenant: CurrentTenant) -> Any:
    return read.snapshot(db, tenant, "graph")


@router.get("/workspace/recon")
def workspace_recon(db: DbSession, tenant: CurrentTenant) -> Any:
    """Dashboard/Reconciliation screens' combined payload."""
    return matching_read.workspace(db, tenant, read.snapshot(db, tenant, "workspace.recon"))


@router.get("/workspace/dashboard")
def workspace_dashboard(db: DbSession, tenant: CurrentTenant) -> Any:
    return read.snapshot(db, tenant, "workspace.dashboard")
