from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Body, Query
from fastapi.responses import StreamingResponse

from app.agents import admin, ops, registry
from app.api.deps import CurrentActor, CurrentTenant, DbSession

router = APIRouter(prefix="/agents")


@router.get("/overview")
def overview(
    db: DbSession, tenant: CurrentTenant, actor: CurrentActor, days: int = Query(7, ge=1, le=90)
) -> dict[str, Any]:
    return ops.overview(db, tenant, actor, days)


@router.get("/models")
def models(db: DbSession, tenant: CurrentTenant) -> dict[str, Any]:
    from sqlalchemy import select

    from app.models.agents import AgentModel

    registered = {
        m.name: admin.row(m) for m in db.scalars(select(AgentModel).where(AgentModel.tenant_id == tenant.id))
    }
    out = [registered.get(n) or s.public() for n, s in registry.models(db, tenant.id).items()]
    return {"models": out, "bindings": registry.bindings(db, tenant.id), "roles": sorted(admin.ROLES)}


@router.post("/models", status_code=201)
def propose_model(
    db: DbSession, tenant: CurrentTenant, actor: CurrentActor, body: dict[str, Any] = Body(...)
) -> dict[str, Any]:
    return admin.row(admin.propose(db, tenant, actor, body))


@router.post("/models/{name}/approve")
def approve_model(name: str, db: DbSession, tenant: CurrentTenant, actor: CurrentActor) -> dict[str, Any]:
    return admin.row(admin.approve(db, tenant, actor, name))


@router.post("/models/{name}/block")
def block_model(name: str, db: DbSession, tenant: CurrentTenant, actor: CurrentActor) -> dict[str, Any]:
    return admin.row(admin.block(db, tenant, actor, name))


@router.put("/bindings/{role}")
def set_binding(
    role: str,
    db: DbSession,
    tenant: CurrentTenant,
    actor: CurrentActor,
    models: list[str] = Body(..., embed=True),
) -> dict[str, list[str]]:
    return admin.bind(db, tenant, actor, role, models)


@router.get("/runs/{run_id}")
def run(run_id: str, db: DbSession, tenant: CurrentTenant, actor: CurrentActor) -> dict[str, Any]:
    return ops.run_detail(db, tenant, actor, run_id)


# ---------------------------------------------------------------- Recon Investigator (HITL)

_NDJSON = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@router.get("/investigator/pairs")
def investigator_pairs(db: DbSession, tenant: CurrentTenant, actor: CurrentActor) -> list[dict[str, Any]]:
    """Entity pairs in the person's scope with open suggestions, most exposure first."""
    from sqlalchemy import func, select

    from app.models.matching import MatchGroup

    rows = db.execute(
        select(MatchGroup.entity_pair, func.count(), func.sum(MatchGroup.exposure_usd))
        .where(MatchGroup.tenant_id == tenant.id, MatchGroup.status == "proposed")
        .group_by(MatchGroup.entity_pair)
        .order_by(func.sum(MatchGroup.exposure_usd).desc())
    ).all()
    return [{"pair": p, "open": int(n), "exposureUsd": float(x or 0)} for p, n, x in rows if actor.covers(p)][
        :40
    ]


@router.get("/investigator/runs")
def investigator_runs(db: DbSession, tenant: CurrentTenant, actor: CurrentActor) -> list[dict[str, Any]]:
    from sqlalchemy import select

    from app.models.agents import AgentRun

    runs = db.scalars(
        select(AgentRun)
        .where(AgentRun.tenant_id == tenant.id, AgentRun.agent == "investigator")
        .order_by(AgentRun.started_at.desc())
        .limit(50)
    )
    out = []
    for r in runs:
        pair = str((r.summary or {}).get("pair", ""))
        if actor.covers(pair):
            out.append(ops.run_row(r) | {"pair": pair, "pending": (r.summary or {}).get("pending")})
    return out[:20]


@router.post("/investigator/runs")
def investigator_start(
    db: DbSession, tenant: CurrentTenant, actor: CurrentActor, body: dict[str, Any] = Body(...)
) -> StreamingResponse:
    from app.agents import investigator

    gen = investigator.start(db, tenant, actor, str(body.get("pair", "")), body.get("question") or None)
    first = next(gen, None)  # validation errors (scope, role) surface as normal HTTP errors, before streaming
    return StreamingResponse(_chain(first, gen), media_type="application/x-ndjson", headers=_NDJSON)


@router.post("/runs/{run_id}/decide")
def decide(
    run_id: str, db: DbSession, tenant: CurrentTenant, actor: CurrentActor, body: dict[str, Any] = Body(...)
) -> StreamingResponse:
    from app.agents import investigator

    gen = investigator.decide(
        db, tenant, actor, run_id, str(body.get("decision", "")), body.get("args"), body.get("comment")
    )
    first = next(gen, None)
    return StreamingResponse(_chain(first, gen), media_type="application/x-ndjson", headers=_NDJSON)


def _chain(first: str | None, rest: Iterator[str]) -> Iterator[str]:
    if first is not None:
        yield first
    yield from rest
