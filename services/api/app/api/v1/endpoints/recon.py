from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Query

from app.api.deps import CurrentTenant, DbSession
from app.core.config import settings
from app.schemas.read import DecisionIn, ProposalOut, RunOut, RunRequest
from app.services import matching, matching_read

router = APIRouter(prefix="/recon")


@router.post("/runs", response_model=RunOut, status_code=202)
def start_run(
    db: DbSession, tenant: CurrentTenant, background: BackgroundTasks, body: RunRequest | None = None
) -> RunOut:
    run = matching.create_run(db, tenant, entity=(body.entity if body else None))
    if settings.ingest_inline:
        matching.execute_run(db, run)
    else:
        from app.workers.tasks import match_run

        background.add_task(match_run.delay, str(run.id))
    return matching_read.run_out(run)


@router.get("/runs", response_model=list[RunOut])
def list_runs(db: DbSession, tenant: CurrentTenant) -> list[RunOut]:
    return [matching_read.run_out(r) for r in matching_read.runs(db, tenant)]


@router.get("/runs/{code}", response_model=RunOut)
def get_run(code: str, db: DbSession, tenant: CurrentTenant) -> RunOut:
    return matching_read.run_out(matching_read.get_run(db, tenant, code))


@router.get("/proposals", response_model=list[ProposalOut])
def list_proposals(
    db: DbSession,
    tenant: CurrentTenant,
    run: str | None = None,
    status: str | None = None,
    decision: str | None = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 100,
) -> list[ProposalOut]:
    return matching_read.proposals(db, tenant, run, status, decision, limit)


@router.post("/proposals/{code}/{action}", response_model=ProposalOut)
def decide(
    code: str,
    action: Literal["accept", "reject"],
    db: DbSession,
    tenant: CurrentTenant,
    body: DecisionIn | None = None,
) -> ProposalOut:
    group = matching.decide(db, tenant, code, action, actor="api", reason=body.reason if body else None)
    return matching_read.proposal(db, tenant, group.code)
