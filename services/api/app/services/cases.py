"""Case management and exception resolution. Every change is audited with before/after state."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, NotFoundError
from app.models import CaseComment, ExceptionItem, ReconCase, Tenant
from app.services import audit
from app.services.workflow import Actor, PolicyViolation, require_writer

CASE_STATUSES = ("Open", "In progress", "Escalated", "Pending approval", "Closed")
EXCEPTION_STATUSES = ("New", "Investigating", "Escalated", "Resolved")
PRIORITY_SLA_H = {"Critical": 8, "High": 24, "Medium": 72, "Low": 120}


def _case(db: Session, tenant: Tenant, code: str) -> ReconCase:
    c = db.scalar(
        select(ReconCase)
        .options(selectinload(ReconCase.comments))
        .where(ReconCase.tenant_id == tenant.id, ReconCase.code == code)
    )
    if c is None:
        raise NotFoundError(f"Case '{code}' not found.", code="case_not_found")
    return c


def _exception(db: Session, tenant: Tenant, code: str) -> ExceptionItem:
    e = db.scalar(
        select(ExceptionItem).where(ExceptionItem.tenant_id == tenant.id, ExceptionItem.code == code)
    )
    if e is None:
        raise NotFoundError(f"Exception '{code}' not found.", code="exception_not_found")
    return e


def create_case(
    db: Session,
    tenant: Tenant,
    actor: Actor,
    exception_codes: list[str],
    title: str | None,
    assignee: str | None,
    priority: str | None,
    now: datetime | None = None,
) -> ReconCase:
    require_writer(actor)
    now = now or datetime.now(UTC)
    if not exception_codes:
        raise PolicyViolation("A case needs at least one exception.", code="no_exceptions")
    items = [_exception(db, tenant, c) for c in sorted(set(exception_codes))]
    entities = {e.entity_code for e in items}
    sev_order = ["Low", "Medium", "High", "Critical"]
    prio = priority or max((e.severity for e in items), key=sev_order.index)
    n = (
        db.scalar(select(func.count()).select_from(ReconCase).where(ReconCase.tenant_id == tenant.id)) or 0
    ) + 1
    case = ReconCase(
        tenant_id=tenant.id,
        code=f"CS-{2000 + n}",
        title=title
        or f"{items[0].entity_code} ↔ {items[0].counterparty}: {items[0].kind.lower()} investigation",
        entity_code=sorted(entities)[0],
        exposure=sum((Decimal(e.amount) for e in items), Decimal(0)),
        priority=prio,
        status="Open",
        assignee=assignee or actor.name,
        exception_codes=[e.code for e in items],
        opened_at=now,
        due_at=now + timedelta(hours=PRIORITY_SLA_H.get(prio, 72)),
    )
    db.add(case)
    for e in items:
        if e.status == "New":
            e.status = "Investigating"
    audit.record(
        db,
        tenant_id=tenant.id,
        actor=actor.email,
        action="case.created",
        object_type="recon_case",
        object_id=case.code,
        entity_code=case.entity_code,
        after={"exceptions": case.exception_codes, "assignee": case.assignee, "priority": prio},
        occurred_at=now,
    )
    db.flush()
    return case


def update_case(db: Session, tenant: Tenant, code: str, actor: Actor, changes: dict[str, Any]) -> ReconCase:
    require_writer(actor)
    case = _case(db, tenant, code)
    if case.status == "Closed" and changes.get("status") not in (None, "Open"):
        raise ConflictError(f"{code} is closed. Reopen it first.", code="case_closed")
    if changes.get("status") and changes["status"] not in CASE_STATUSES:
        raise PolicyViolation(f"Unknown status '{changes['status']}'.", code="bad_status")
    before = {k: getattr(case, k) for k in ("status", "assignee", "priority")}
    for k in ("status", "assignee", "priority"):
        if changes.get(k):
            setattr(case, k, changes[k])
    if changes.get("status") == "Escalated":
        case.priority = "Critical"
    if changes.get("status") == "Closed":
        for e in db.scalars(
            select(ExceptionItem).where(
                ExceptionItem.tenant_id == tenant.id, ExceptionItem.code.in_(case.exception_codes)
            )
        ):
            e.status = "Resolved"
    after = {k: getattr(case, k) for k in ("status", "assignee", "priority")}
    if after != before:
        audit.record(
            db,
            tenant_id=tenant.id,
            actor=actor.email,
            action="case.updated",
            object_type="recon_case",
            object_id=code,
            entity_code=case.entity_code,
            before=before,
            after=after,
        )
    db.flush()
    return case


def comment(db: Session, tenant: Tenant, code: str, actor: Actor, body: str) -> ReconCase:
    text = body.strip()
    if not text:
        raise PolicyViolation("Comment is empty.", code="empty_comment")
    case = _case(db, tenant, code)
    now = datetime.now(UTC)
    case.comments.append(CaseComment(author=actor.name, posted_at=now, body=text[:4000]))
    audit.record(
        db,
        tenant_id=tenant.id,
        actor=actor.email,
        action="case.commented",
        object_type="recon_case",
        object_id=code,
        entity_code=case.entity_code,
        after={"chars": len(text)},
    )
    db.flush()
    return case


def set_exception_status(
    db: Session, tenant: Tenant, code: str, actor: Actor, status: str, note: str | None = None
) -> ExceptionItem:
    require_writer(actor)
    if status not in EXCEPTION_STATUSES:
        raise PolicyViolation(f"Unknown status '{status}'.", code="bad_status")
    e = _exception(db, tenant, code)
    before = e.status
    e.status = status
    audit.record(
        db,
        tenant_id=tenant.id,
        actor=actor.email,
        action="exception.status_changed",
        object_type="exception_item",
        object_id=code,
        entity_code=e.entity_code,
        before={"status": before},
        after={"status": status, "note": note},
    )
    db.flush()
    return e
