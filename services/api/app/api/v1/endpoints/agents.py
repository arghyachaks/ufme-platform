from typing import Any

from fastapi import APIRouter, Query

from app.agents import ops, registry
from app.api.deps import CurrentActor, CurrentTenant, DbSession

router = APIRouter(prefix="/agents")


@router.get("/overview")
def overview(
    db: DbSession, tenant: CurrentTenant, actor: CurrentActor, days: int = Query(7, ge=1, le=90)
) -> dict[str, Any]:
    return ops.overview(db, tenant, actor, days)


@router.get("/models")
def models() -> list[dict[str, Any]]:
    return [m.public() for m in registry.models().values()]


@router.get("/runs/{run_id}")
def run(run_id: str, db: DbSession, tenant: CurrentTenant, actor: CurrentActor) -> dict[str, Any]:
    return ops.run_detail(db, tenant, actor, run_id)
