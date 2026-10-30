"""Workflow: approval matrix, segregation of duties, manual matches, sign-off and data-driven controls.

Policy (seeded P-01..P-03, enforced here on the server, never only in the UI):
- Approval matrix: < 50K Manager, 50K to 1M Controller, > 1M Finance Director.
- Segregation of duties: nobody approves their own submission; > 1M needs two different approvers.
- Tolerance: a manual match nets to within min(0.5% of exposure, 500 USD).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, false, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, ConflictError, ForbiddenError, NotFoundError
from app.models import (
    ApprovalRequest,
    AppUser,
    ControlTest,
    ExceptionItem,
    LedgerTxn,
    MatchGroup,
    MatchMember,
    MatchRun,
    PeriodSignoff,
    Role,
    Tenant,
    UserRole,
)
from app.services import audit, learning

RANK = {"Analyst": 0, "Manager": 1, "Controller": 2, "Finance Director": 3}
HIERARCHY = ["Manager", "Controller", "Finance Director"]
DUAL_CONTROL_USD = Decimal("1000000")
TOLERANCE_PCT, TOLERANCE_CAP_USD = Decimal("0.005"), Decimal("500")
SLA_HOURS = {"Manager": 24, "Controller": 24, "Finance Director": 48}
SIGNOFF_STEPS = [
    ("Manager", "Manager signed"),
    ("Controller", "Controller signed"),
    ("Finance Director", "Signed off"),
]


class PolicyViolation(AppError):
    status_code = 422
    title = "Policy violation"


@dataclass
class Actor:
    email: str
    name: str
    role: str
    entities: list[str] = field(default_factory=list)

    @property
    def rank(self) -> int:
        return RANK.get(self.role, -1)

    def covers(self, entity: str) -> bool:
        return "All" in self.entities or any(e in entity for e in self.entities)


def resolve_actor(db: Session, tenant: Tenant, email: str | None) -> Actor:
    """Until SSO the acting user comes from the X-Ufme-User header, defaulting to the demo analyst."""
    email = (email or settings.demo_user).strip().lower()
    row = db.execute(
        select(AppUser, Role.name, UserRole.entity_codes)
        .join(UserRole, UserRole.user_id == AppUser.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(AppUser.tenant_id == tenant.id, func.lower(AppUser.email) == email)
    ).first()
    if row is None:
        raise ForbiddenError(f"Unknown user '{email}'.", code="unknown_user")
    user, role, entities = row
    return Actor(email=user.email, name=user.display_name, role=role, entities=list(entities or []))


# ---------------------------------------------------------------- authorization


def entity_clause(actor: Actor | None, column: Any) -> ColumnElement[bool] | None:
    """SQL filter for the entities a user is assigned to (None = no restriction)."""
    if actor is None or "All" in actor.entities:
        return None
    return or_(*[column.contains(e) for e in actor.entities]) if actor.entities else false()


def require_scope(actor: Actor, entity: str) -> None:
    if not actor.covers(entity):
        raise ForbiddenError(f"You aren't assigned to {entity}.", code="entity_out_of_scope")


def require_writer(actor: Actor) -> None:
    """Auditors (and anyone without a workflow role) can see everything in scope but change nothing."""
    if actor.rank < RANK["Analyst"]:
        raise ForbiddenError(f"{actor.role} access is read-only.", code="read_only_role")


def users(db: Session, tenant: Tenant) -> list[dict[str, Any]]:
    rows = db.execute(
        select(AppUser.email, AppUser.display_name, Role.name, UserRole.entity_codes)
        .join(UserRole, UserRole.user_id == AppUser.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(AppUser.tenant_id == tenant.id, AppUser.status != "Disabled")
        .order_by(AppUser.display_name)
    )
    return [{"email": e, "name": n, "role": r, "entities": ents} for e, n, r, ents in rows]


# ---------------------------------------------------------------- approval matrix


def required_role(exposure: Decimal) -> str:
    if exposure < 50_000:
        return "Manager"
    return "Controller" if exposure <= DUAL_CONTROL_USD else "Finance Director"


def materiality(exposure: Decimal) -> str:
    return "High" if exposure > 1_000_000 else "Medium" if exposure >= 250_000 else "Low"


def _code(db: Session, model: Any, tenant: Tenant, prefix: str) -> str:
    n = (db.scalar(select(func.count()).select_from(model).where(model.tenant_id == tenant.id)) or 0) + 1
    return f"{prefix}-{n:05d}"


def _stamp(now: datetime, text: str) -> str:
    return f"{now:%d %b %H:%M} {text}"


def submit(
    db: Session,
    tenant: Tenant,
    group: MatchGroup,
    actor: Actor,
    kind: str,
    rationale: str,
    now: datetime | None = None,
) -> ApprovalRequest:
    now = now or datetime.now(UTC)
    exposure = Decimal(group.exposure_usd)
    role = required_role(exposure)
    contrib = group.explanation.get("contributions", {}) if group.explanation else {}
    total = sum(abs(v) for v in contrib.values()) or 1.0
    factors = [
        {"label": k.replace("_", " ").capitalize(), "weight": round(100 * abs(v) / total)}
        for k, v in sorted(contrib.items(), key=lambda kv: -abs(kv[1]))[:4]
    ]
    req = ApprovalRequest(
        tenant_id=tenant.id,
        code=_code(db, ApprovalRequest, tenant, "AP"),
        kind=kind,
        group_id=group.id,
        match_code=group.code,
        entity_code=group.entity_pair,
        exposure_usd=exposure,
        materiality=materiality(exposure),
        confidence=group.confidence,
        required_role=role,
        approvals_needed=2 if exposure > DUAL_CONTROL_USD else 1,
        approvals=[],
        status="Pending",
        submitted_by=actor.email,
        submitted_by_name=actor.name,
        submitted_at=now,
        sla_due_at=now + timedelta(hours=SLA_HOURS[role]),
        rationale=rationale,
        documents=[],
        factors=factors,
        trail=[
            _stamp(now, f"submitted by {actor.name}"),
            _stamp(now, "policy check passed"),
            _stamp(now, f"routed to {role}" + (" (dual control)" if exposure > DUAL_CONTROL_USD else "")),
        ],
    )
    group.status = "pending_approval"
    db.add(req)
    audit.record(
        db,
        tenant_id=tenant.id,
        actor=actor.email,
        action="approval.submitted",
        object_type="match_group",
        object_id=group.code,
        entity_code=group.entity_pair,
        control="IC-05",
        after={"approval": req.code, "required_role": role, "exposure_usd": str(exposure)},
    )
    db.flush()
    return req


def list_approvals(
    db: Session, tenant: Tenant, status: str | None = "open", actor: Actor | None = None
) -> list[ApprovalRequest]:
    q = select(ApprovalRequest).where(ApprovalRequest.tenant_id == tenant.id)
    if (scope := entity_clause(actor, ApprovalRequest.entity_code)) is not None:
        q = q.where(scope)
    if status == "open":
        q = q.where(ApprovalRequest.status.in_(("Pending", "Info requested")))
    elif status:
        q = q.where(ApprovalRequest.status == status)
    return list(db.scalars(q.order_by(ApprovalRequest.sla_due_at, ApprovalRequest.code)))


def get_approval(db: Session, tenant: Tenant, code: str) -> ApprovalRequest:
    req = db.scalar(
        select(ApprovalRequest).where(ApprovalRequest.tenant_id == tenant.id, ApprovalRequest.code == code)
    )
    if req is None:
        raise NotFoundError(f"Approval '{code}' not found.", code="approval_not_found")
    return req


def decide_approval(
    db: Session,
    tenant: Tenant,
    code: str,
    action: str,
    actor: Actor,
    comment: str | None = None,
    now: datetime | None = None,
) -> ApprovalRequest:
    now = now or datetime.now(UTC)
    req = get_approval(db, tenant, code)
    require_scope(actor, req.entity_code)
    if req.status not in ("Pending", "Info requested"):
        raise ConflictError(f"{code} is already {req.status.lower()}.", code="approval_closed")

    def deny(reason: str, err_code: str, control: str) -> None:
        audit.record(
            db,
            tenant_id=tenant.id,
            actor=actor.email,
            action="approval.denied",
            object_type="approval_request",
            object_id=code,
            entity_code=req.entity_code,
            control=control,
            after={"attempted": action, "reason": err_code},
        )
        db.commit()  # the denial itself is evidence: keep it even though the request fails
        raise ForbiddenError(reason, code=err_code)

    if actor.email.lower() == req.submitted_by.lower():
        deny(
            "You can't approve or reject your own submission (segregation of duties).",
            "sod_self_approval",
            "SOD-01",
        )
    # Dual control: one approval must come from the matrix role; the second may be any other Controller or above.
    senior_done = any(RANK.get(a["role"], -1) >= RANK[req.required_role] for a in req.approvals)
    needed = RANK["Controller"] if (req.approvals_needed > 1 and senior_done) else RANK[req.required_role]
    if actor.rank < needed:
        who = "Controller" if needed == RANK["Controller"] else req.required_role
        deny(
            f"{req.match_code} needs a {who} or above; you are {actor.role}.",
            "insufficient_authority",
            "IC-05",
        )
    if any(a["actor"].lower() == actor.email.lower() for a in req.approvals):
        deny(
            "You've already approved this; a second, different approver is required.",
            "duplicate_approver",
            "IC-07",
        )

    before = {"status": req.status, "approvals": len(req.approvals)}
    group = db.get(MatchGroup, req.group_id) if req.group_id else None
    if action == "approve":
        req.approvals = [
            *req.approvals,
            {"actor": actor.email, "name": actor.name, "role": actor.role, "at": now.isoformat()},
        ]
        if len(req.approvals) >= req.approvals_needed:
            req.status, req.decided_at = "Approved", now
            req.trail = [*req.trail, _stamp(now, f"approved by {actor.name}")]
            if group is not None:
                group.status, group.decided_by, group.decided_at = "accepted", actor.email, now
                learning.record(
                    db, tenant, group, outcome=1, source="approved", actor=actor.email, reason=comment
                )
        else:
            req.trail = [*req.trail, _stamp(now, f"first approval by {actor.name}; awaiting second approver")]
    elif action == "reject":
        req.status, req.decided_at = "Rejected", now
        req.trail = [
            *req.trail,
            _stamp(now, f"rejected by {actor.name}" + (f": {comment}" if comment else "")),
        ]
        if group is not None:
            group.status, group.decided_by, group.decided_at = "rejected", actor.email, now
            learning.record(
                db, tenant, group, outcome=0, source="approval_reject", actor=actor.email, reason=comment
            )
    else:  # request-info
        req.status = "Info requested"
        req.trail = [
            *req.trail,
            _stamp(now, f"{actor.name} requested information" + (f": {comment}" if comment else "")),
        ]
    audit.record(
        db,
        tenant_id=tenant.id,
        actor=actor.email,
        action=f"approval.{action.replace('-', '_')}",
        object_type="approval_request",
        object_id=code,
        entity_code=req.entity_code,
        control="IC-07" if req.approvals_needed > 1 else "IC-05",
        before=before,
        after={"status": req.status, "approvals": len(req.approvals), "comment": comment},
        occurred_at=now,
    )
    db.flush()
    return req


# ---------------------------------------------------------------- manual matches


def manual_match(
    db: Session, tenant: Tenant, txn_codes: list[str], actor: Actor, rationale: str
) -> tuple[MatchGroup, ApprovalRequest]:
    require_writer(actor)
    codes = sorted(set(txn_codes))
    if len(codes) < 2:
        raise PolicyViolation("Pick at least one item on each side.", code="too_few_items")
    txns = list(
        db.scalars(select(LedgerTxn).where(LedgerTxn.tenant_id == tenant.id, LedgerTxn.code.in_(codes)))
    )
    missing = set(codes) - {t.code for t in txns}
    if missing:
        raise NotFoundError(f"Unknown items: {', '.join(sorted(missing))}.", code="txn_not_found")
    if any(t.amount_usd is None for t in txns):
        raise PolicyViolation("An item has no FX rate, so it can't be compared in USD.", code="missing_fx")
    taken = set(
        db.scalars(
            select(LedgerTxn.code)
            .join(MatchMember, MatchMember.txn_id == LedgerTxn.id)
            .join(MatchGroup, MatchGroup.id == MatchMember.group_id)
            .where(
                LedgerTxn.id.in_([t.id for t in txns]),
                MatchGroup.status.in_(("matched", "accepted", "pending_approval")),
            )
        )
    )
    if taken:
        raise ConflictError(f"Already matched: {', '.join(sorted(taken))}.", code="already_matched")
    pairs = {tuple(sorted((t.entity_code, t.counterparty_code))) for t in txns}
    if len(pairs) != 1:
        raise PolicyViolation("All items must belong to the same intercompany pair.", code="mixed_pairs")
    side = {t.code: ("A" if t.entity_code < t.counterparty_code else "B") for t in txns}
    a = [t for t in txns if side[t.code] == "A"]
    b = [t for t in txns if side[t.code] == "B"]
    if not a or not b:
        raise PolicyViolation("Pick at least one item on each side.", code="one_sided")
    sum_a = sum((Decimal(t.amount_usd or 0) for t in a), Decimal(0))
    sum_b = sum((Decimal(t.amount_usd or 0) for t in b), Decimal(0))
    exposure = max(abs(sum_a), abs(sum_b))
    gap = abs(sum_a + sum_b)
    allowed = min(exposure * TOLERANCE_PCT, TOLERANCE_CAP_USD)
    if gap > allowed:
        raise PolicyViolation(
            f"Variance {gap:,.2f} USD is above the tolerance policy limit of {allowed:,.2f} USD "
            f"(0.5% of exposure, capped at 500 USD).",
            code="tolerance_exceeded",
            extra={"variance_usd": float(gap), "allowed_usd": float(allowed)},
        )
    pair = pairs.pop()
    require_scope(actor, "-".join(pair))
    n = (
        db.scalar(select(func.count()).select_from(MatchGroup).where(MatchGroup.tenant_id == tenant.id)) or 0
    ) + 1
    run = db.scalar(select(MatchRun).where(MatchRun.tenant_id == tenant.id).order_by(MatchRun.code.desc()))
    if run is None:
        raise ConflictError("Run a reconciliation first.", code="no_run")
    mtype = f"{'1' if len(a) == 1 else 'M'}:{'1' if len(b) == 1 else 'M'}"
    group = MatchGroup(
        tenant_id=tenant.id,
        code=f"MT-{n:06d}",
        run_id=run.id,
        match_type=mtype,
        decision="manual",
        status="proposed",
        confidence=1.0,
        exposure_usd=exposure.quantize(Decimal("0.0001")),
        residual_usd=gap.quantize(Decimal("0.0001")),
        entity_pair="-".join(pair),
        rule_ids=["MANUAL"],
        explanation={
            "features": {"amount_gap_usd": float(gap), "items_a": len(a), "items_b": len(b)},
            "contributions": {"amount": 1.0},
            "manual": {"by": actor.email, "rationale": rationale},
        },
    )
    group.members = [MatchMember(txn_id=t.id, side=side[t.code]) for t in txns]
    db.add(group)
    db.flush()
    req = submit(db, tenant, group, actor, "manual", rationale)
    return group, req


# ---------------------------------------------------------------- controls computed from data


def evaluate_controls(db: Session, tenant: Tenant, actor: str = "system") -> list[ControlTest]:
    approved = list(
        db.scalars(
            select(ApprovalRequest).where(
                ApprovalRequest.tenant_id == tenant.id, ApprovalRequest.status == "Approved"
            )
        )
    )
    latest = db.scalar(select(MatchRun).where(MatchRun.tenant_id == tenant.id).order_by(MatchRun.code.desc()))
    results = {
        "IC-03": latest is not None and latest.status == "Completed",
        "IC-05": all(
            any(RANK.get(a["role"], -1) >= RANK[r.required_role] for a in r.approvals) for r in approved
        ),
        "IC-07": all(
            len({a["actor"] for a in r.approvals}) >= 2
            for r in approved
            if Decimal(r.exposure_usd) > DUAL_CONTROL_USD
        ),
        "SOD-01": all(all(a["actor"] != r.submitted_by for a in r.approvals) for r in approved),
    }
    today = datetime.now(UTC).date()
    controls = list(db.scalars(select(ControlTest).where(ControlTest.tenant_id == tenant.id)))
    for c in controls:
        if c.code in results:
            new = "Pass" if results[c.code] else "Fail"
            if new != c.result:
                audit.record(
                    db,
                    tenant_id=tenant.id,
                    actor=actor,
                    action="control.evaluated",
                    object_type="control_test",
                    object_id=c.code,
                    control=c.code,
                    before={"result": c.result},
                    after={"result": new},
                )
            c.result, c.last_run_on = new, today
            c.evidence = c.evidence + 1
    db.flush()
    return controls


# ---------------------------------------------------------------- period sign-off


def _period(now: datetime) -> str:
    return f"{now:%Y-%m}"


def readiness(db: Session, tenant: Tenant, entity: str, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    open_ex = list(
        db.scalars(
            select(ExceptionItem).where(
                ExceptionItem.tenant_id == tenant.id,
                ExceptionItem.entity_code == entity,
                ExceptionItem.status.not_in(("Resolved", "Closed")),
            )
        )
    )
    critical = [e for e in open_ex if e.severity == "Critical"]
    pending = (
        db.scalar(
            select(func.count())
            .select_from(ApprovalRequest)
            .where(
                ApprovalRequest.tenant_id == tenant.id,
                ApprovalRequest.entity_code.contains(entity),
                ApprovalRequest.status.in_(("Pending", "Info requested")),
            )
        )
        or 0
    )
    failing = list(
        db.scalars(
            select(ControlTest.code).where(ControlTest.tenant_id == tenant.id, ControlTest.result == "Fail")
        )
    )
    latest = db.scalar(select(MatchRun).where(MatchRun.tenant_id == tenant.id).order_by(MatchRun.code.desc()))
    run_ok = latest is not None and latest.status == "Completed"
    blockers = []
    if not run_ok:
        blockers.append("No completed reconciliation run this period")
    if pending:
        blockers.append(f"{pending} approval(s) still pending for {entity}")
    if critical:
        blockers.append(f"{len(critical)} critical exception(s) open for {entity}")
    if failing:
        blockers.append(f"Failing control(s): {', '.join(failing)}")
    checklist = [
        {"label": "Reconciliation complete", "done": run_ok},
        {"label": "Approvals complete", "done": pending == 0},
        {"label": "Controls passed", "done": not failing},
        {"label": "Critical exceptions resolved", "done": not critical},
    ]
    score = round(100 * sum(1 for c in checklist if c["done"]) / len(checklist))
    so = signoff_row(db, tenant, entity, _period(now))
    return {
        "entity": entity,
        "period": _period(now),
        "status": so.status if so else "Open",
        "signatures": so.signatures if so else [],
        "openExceptions": len(open_ex),
        "criticalExceptions": len(critical),
        "pendingApprovals": pending,
        "failingControls": failing,
        "checklist": checklist,
        "readiness": score,
        "blockers": blockers,
        "ready": not blockers,
        "nextSigner": _next_step(so.status if so else "Open"),
    }


def signoff_row(db: Session, tenant: Tenant, entity: str, period: str) -> PeriodSignoff | None:
    return db.scalar(
        select(PeriodSignoff).where(
            PeriodSignoff.tenant_id == tenant.id, PeriodSignoff.code == f"{entity}-{period}"
        )
    )


def _next_step(status: str) -> str | None:
    order = ["Open"] + [s for _, s in SIGNOFF_STEPS]
    i = order.index(status) if status in order else 0
    return SIGNOFF_STEPS[i][0] if i < len(SIGNOFF_STEPS) else None


def sign(
    db: Session, tenant: Tenant, entity: str, actor: Actor, now: datetime | None = None
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    evaluate_controls(db, tenant, actor.email)
    state = readiness(db, tenant, entity, now)
    if state["blockers"]:
        raise ConflictError(
            "Sign-off is blocked: " + "; ".join(state["blockers"]) + ".",
            code="signoff_blocked",
            extra={"blockers": state["blockers"]},
        )
    nxt = state["nextSigner"]
    if nxt is None:
        raise ConflictError(f"{entity} is already signed off for {state['period']}.", code="already_signed")
    if actor.rank < RANK[nxt]:
        raise ForbiddenError(
            f"The next signature needs a {nxt} or above; you are {actor.role}.", code="insufficient_authority"
        )
    # A senior signer covers the lower steps too: a Controller's signature moves the entity to "Controller signed".
    step = max((r for r, _ in SIGNOFF_STEPS if RANK[r] <= actor.rank), key=lambda r: RANK[r])
    if not actor.covers(entity):
        raise ForbiddenError(f"You aren't assigned to {entity}.", code="entity_out_of_scope")
    period = state["period"]
    so = signoff_row(db, tenant, entity, period)
    if so is None:
        so = PeriodSignoff(
            tenant_id=tenant.id,
            code=f"{entity}-{period}",
            entity_code=entity,
            period=period,
            status="Open",
            signatures=[],
        )
        db.add(so)
    if any(sig["actor"] == actor.email for sig in so.signatures):
        raise ForbiddenError("Each sign-off step needs a different person.", code="duplicate_signer")
    before = so.status
    so.status = dict(SIGNOFF_STEPS)[step]
    so.signatures = [
        *so.signatures,
        {"actor": actor.email, "name": actor.name, "role": actor.role, "step": step, "at": now.isoformat()},
    ]
    if so.status == "Signed off":
        so.signed_at = now
    audit.record(
        db,
        tenant_id=tenant.id,
        actor=actor.email,
        action="signoff.signed",
        object_type="period_signoff",
        object_id=so.code,
        entity_code=entity,
        control="IC-03",
        before={"status": before},
        after={"status": so.status, "step": step},
        occurred_at=now,
    )
    db.flush()
    return readiness(db, tenant, entity, now)


def unmatched(
    db: Session, tenant: Tenant, pair: str | None = None, limit: int = 40, actor: Actor | None = None
) -> dict[str, Any]:
    """Open items for Manual Match: both sides of one intercompany pair, largest first (USD, absolute)."""
    taken = (
        select(MatchMember.id)
        .join(MatchGroup, MatchGroup.id == MatchMember.group_id)
        .where(
            MatchMember.txn_id == LedgerTxn.id,
            MatchGroup.tenant_id == tenant.id,
            MatchGroup.status.in_(("matched", "accepted", "pending_approval", "proposed")),
        )
    )
    base = select(LedgerTxn).where(
        LedgerTxn.tenant_id == tenant.id, LedgerTxn.amount_usd.is_not(None), ~taken.exists()
    )
    if pair and actor is not None:
        require_scope(actor, pair)
    if not pair:  # cheap default: the pair of the largest pending suggestion (an index-backed lookup)
        q = select(MatchGroup.entity_pair).where(
            MatchGroup.tenant_id == tenant.id, MatchGroup.status == "proposed"
        )
        if (scope := entity_clause(actor, MatchGroup.entity_pair)) is not None:
            q = q.where(scope)
        pair = db.scalar(q.order_by(MatchGroup.exposure_usd.desc()).limit(1))
    if pair:
        e1, _, e2 = pair.partition("-")
    else:
        top = db.execute(
            select(LedgerTxn.entity_code, LedgerTxn.counterparty_code, func.count())
            .where(LedgerTxn.tenant_id == tenant.id, ~taken.exists())
            .group_by(LedgerTxn.entity_code, LedgerTxn.counterparty_code)
            .order_by(func.count().desc())
            .limit(1)
        ).first()
        if top is None:
            return {"pair": None, "sideA": [], "sideB": []}
        e1, e2 = sorted((top[0], top[1]))
        if actor is not None and not actor.covers(f"{e1}-{e2}"):
            return {"pair": None, "sideA": [], "sideB": []}

    def side(entity: str, cp: str) -> list[dict[str, Any]]:
        rows = db.scalars(
            base.where(LedgerTxn.entity_code == entity, LedgerTxn.counterparty_code == cp)
            .order_by(func.abs(LedgerTxn.amount_usd).desc())
            .limit(limit)
        )
        return [
            {
                "id": t.code,
                "invoice": t.reference_raw or t.reference_norm or "—",
                "amount": round(abs(float(t.amount_usd or 0)), 2),
                "currency": "USD",
                "originalAmount": float(t.amount),
                "originalCurrency": t.currency,
                "date": f"{t.value_date:%d %b}",
                "entity": t.entity_code,
                "counterparty": t.counterparty_code,
                "description": t.description or "",
                "attachments": [],
                "exceptionRisk": "High" if abs(float(t.amount_usd or 0)) > 250_000 else "Medium",
            }
            for t in rows
        ]

    a, b = sorted((e1, e2))
    return {"pair": f"{a}-{b}", "sideA": side(a, b), "sideB": side(b, a)}
