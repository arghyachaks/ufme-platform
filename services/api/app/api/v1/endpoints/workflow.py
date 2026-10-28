"""Stage 4 endpoints: approvals, manual matches, sign-off, cases, exception status and acting user."""

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import CurrentActor, CurrentTenant, DbSession
from app.models import ExceptionItem, LegalEntity
from app.schemas.read import (
    ActorOut,
    ApprovalDecisionIn,
    ApprovalOut,
    ApprovalStepOut,
    CaseCreateIn,
    CaseOut,
    CaseUpdateIn,
    CommentIn,
    ExceptionOut,
    ExceptionStatusIn,
    ManualMatchIn,
    ManualMatchOut,
    SignoffOut,
)
from app.services import cases, read, workflow
from app.services.matching_read import _money

router = APIRouter()


# ---------------------------------------------------------------- acting user


@router.get("/me", response_model=ActorOut)
def me(actor: CurrentActor) -> ActorOut:
    return ActorOut(email=actor.email, name=actor.name, role=actor.role, entities=actor.entities)


@router.get("/users/acting", response_model=list[ActorOut])
def actors(db: DbSession, tenant: CurrentTenant) -> list[ActorOut]:
    return [ActorOut(**u) for u in workflow.users(db, tenant)]


# ---------------------------------------------------------------- approvals


def _approval_out(r: Any, open_exceptions: set[str], now: datetime) -> ApprovalOut:
    due = r.sla_due_at if r.sla_due_at.tzinfo else r.sla_due_at.replace(tzinfo=UTC)
    hours = int((due - now).total_seconds() // 3600)
    closed = r.status in ("Approved", "Rejected")
    sla = r.status if closed else (f"{hours}h remaining" if hours >= 0 else f"{-hours}h overdue")
    return ApprovalOut(
        id=r.code,
        match_id=r.match_code,
        kind=r.kind,
        submitted_by=r.submitted_by_name,
        entity=r.entity_code,
        exposure=_money(float(r.exposure_usd)),
        exposure_usd=float(r.exposure_usd),
        materiality=r.materiality,
        confidence=f"{100 * r.confidence:.1f}%",
        date=f"{r.submitted_at:%d %b}",
        stage=r.required_role,
        sla=sla,
        sla_overdue=not closed and hours < 0,
        exception_open=any(e in r.entity_code for e in open_exceptions),
        rationale=r.rationale or "Submitted from the review queue.",
        documents=r.documents,
        trail=r.trail,
        confidence_factors=r.factors,
        status=r.status,
        approvals=[
            ApprovalStepOut(name=a["name"], role=a["role"], at=a["at"][:16].replace("T", " "))
            for a in r.approvals
        ],
        approvals_needed=r.approvals_needed,
    )


def _open_exception_entities(db: DbSession, tenant: CurrentTenant) -> set[str]:
    return set(
        db.scalars(
            select(ExceptionItem.entity_code).where(
                ExceptionItem.tenant_id == tenant.id,
                ExceptionItem.severity == "Critical",
                ExceptionItem.status != "Resolved",
            )
        )
    )


@router.get("/approvals", response_model=list[ApprovalOut])
def list_approvals(
    db: DbSession, tenant: CurrentTenant, status: Annotated[str | None, Query()] = "open"
) -> list[ApprovalOut]:
    now, ex = datetime.now(UTC), _open_exception_entities(db, tenant)
    return [_approval_out(r, ex, now) for r in workflow.list_approvals(db, tenant, status)]


@router.post("/approvals/{code}/{action}", response_model=ApprovalOut)
def decide_approval(
    code: str,
    action: Literal["approve", "reject", "request-info"],
    db: DbSession,
    tenant: CurrentTenant,
    actor: CurrentActor,
    body: ApprovalDecisionIn | None = None,
) -> ApprovalOut:
    r = workflow.decide_approval(db, tenant, code, action, actor, body.comment if body else None)
    return _approval_out(r, _open_exception_entities(db, tenant), datetime.now(UTC))


# ---------------------------------------------------------------- manual match


@router.post("/recon/manual-matches", response_model=ManualMatchOut, status_code=201)
def create_manual_match(
    body: ManualMatchIn, db: DbSession, tenant: CurrentTenant, actor: CurrentActor
) -> ManualMatchOut:
    group, req = workflow.manual_match(db, tenant, body.txn_ids, actor, body.rationale)
    return ManualMatchOut(
        match_id=group.code,
        approval_id=req.code,
        type=group.match_type,
        variance_usd=float(group.residual_usd),
        stage=req.required_role,
    )


@router.get("/recon/unmatched")
def unmatched(
    db: DbSession,
    tenant: CurrentTenant,
    pair: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 40,
) -> dict[str, Any]:
    return workflow.unmatched(db, tenant, pair, limit)


# ---------------------------------------------------------------- sign-off and controls


@router.get("/signoff", response_model=list[SignoffOut])
def signoff_overview(db: DbSession, tenant: CurrentTenant) -> list[SignoffOut]:
    entities = db.scalars(
        select(LegalEntity.code).where(LegalEntity.tenant_id == tenant.id).order_by(LegalEntity.code)
    )
    return [SignoffOut(**workflow.readiness(db, tenant, e)) for e in entities]


@router.post("/signoff/{entity}/sign", response_model=SignoffOut)
def sign(entity: str, db: DbSession, tenant: CurrentTenant, actor: CurrentActor) -> SignoffOut:
    return SignoffOut(**workflow.sign(db, tenant, entity, actor))


@router.post("/audit/controls/evaluate")
def evaluate_controls(db: DbSession, tenant: CurrentTenant, actor: CurrentActor) -> list[dict[str, Any]]:
    return [
        {"id": c.code, "name": c.name, "result": c.result, "lastRun": str(c.last_run_on)}
        for c in workflow.evaluate_controls(db, tenant, actor.email)
    ]


# ---------------------------------------------------------------- cases and exceptions


def _case_out(db: DbSession, tenant: CurrentTenant, code: str) -> CaseOut:
    return next(c for c in read.cases(db, tenant) if c.id == code)


@router.post("/cases", response_model=CaseOut, status_code=201)
def create_case(body: CaseCreateIn, db: DbSession, tenant: CurrentTenant, actor: CurrentActor) -> CaseOut:
    case = cases.create_case(db, tenant, actor, body.exception_ids, body.title, body.assignee, body.priority)
    return _case_out(db, tenant, case.code)


@router.patch("/cases/{code}", response_model=CaseOut)
def update_case(
    code: str, body: CaseUpdateIn, db: DbSession, tenant: CurrentTenant, actor: CurrentActor
) -> CaseOut:
    cases.update_case(db, tenant, code, actor, body.model_dump(exclude_none=True))
    return _case_out(db, tenant, code)


@router.post("/cases/{code}/comments", response_model=CaseOut, status_code=201)
def add_comment(
    code: str, body: CommentIn, db: DbSession, tenant: CurrentTenant, actor: CurrentActor
) -> CaseOut:
    cases.comment(db, tenant, code, actor, body.text)
    return _case_out(db, tenant, code)


@router.post("/exceptions/{code}/status", response_model=ExceptionOut)
def exception_status(
    code: str, body: ExceptionStatusIn, db: DbSession, tenant: CurrentTenant, actor: CurrentActor
) -> ExceptionOut:
    cases.set_exception_status(db, tenant, code, actor, body.status, body.note)
    return next(e for e in read.exceptions(db, tenant) if e.id == code)
