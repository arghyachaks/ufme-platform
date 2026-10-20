"""Matching runs: load open ledger lines → engine → persist proposals; reviewer decisions become labels."""

import logging
import time
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.engines.benchmark.model import Line
from app.engines.matching import engine
from app.engines.matching.rules import Rule
from app.models import LedgerTxn, MatchGroup, MatchLabel, MatchMember, MatchRule, MatchRun, Tenant
from app.services import audit

logger = logging.getLogger("ufme.matching")
CLOSED = ("matched", "accepted")  # lines in these groups are no longer open


def _next_code(db: Session, model: Any, tenant: Tenant, prefix: str, width: int = 5) -> int:
    return (db.scalar(select(func.count()).select_from(model).where(model.tenant_id == tenant.id)) or 0) + 1


def load_rules(db: Session, tenant: Tenant) -> list[Rule]:
    # Deterministic order: rule order affects fast paths and the audit trail.
    rows = db.scalars(
        select(MatchRule)
        .where(
            MatchRule.tenant_id == tenant.id, MatchRule.enabled.is_(True), MatchRule.definition.is_not(None)
        )
        .order_by(MatchRule.priority, MatchRule.code)
    )
    return [Rule.from_definition(r.code, r.name, r.definition or {}, priority=r.priority) for r in rows]


def open_lines(
    db: Session, tenant: Tenant, entity: str | None = None
) -> tuple[list[Line], dict[str, LedgerTxn], int]:
    closed = (
        select(MatchMember.txn_id)
        .join(MatchGroup, MatchGroup.id == MatchMember.group_id)
        .where(MatchGroup.tenant_id == tenant.id, MatchGroup.status.in_(CLOSED))
    )
    q = select(LedgerTxn).where(LedgerTxn.tenant_id == tenant.id, LedgerTxn.id.not_in(closed))
    if entity:
        q = q.where((LedgerTxn.entity_code == entity) | (LedgerTxn.counterparty_code == entity))
    lines: list[Line] = []
    by_id: dict[str, LedgerTxn] = {}
    skipped = 0
    for t in db.scalars(q):
        if t.amount_usd is None:  # no FX rate: cannot be compared across currencies
            skipped += 1
            continue
        key = str(t.id)
        by_id[key] = t
        lines.append(
            Line(
                id=key,
                entity=t.entity_code,
                counterparty=t.counterparty_code,
                amount=float(t.amount),
                currency=t.currency,
                amount_usd=float(t.amount_usd),
                value_date=t.value_date,
                posting_date=t.posting_date or t.value_date,
                reference=t.reference_raw or "",
                reference_norm=t.reference_norm,
                description=t.description or "",
                account=t.account or "",
            )
        )
    return lines, by_id, skipped


def create_run(db: Session, tenant: Tenant, entity: str | None = None, actor: str = "api") -> MatchRun:
    if db.scalar(
        select(func.count())
        .select_from(MatchRun)
        .where(MatchRun.tenant_id == tenant.id, MatchRun.status.in_(("Queued", "Running")))
    ):
        raise ConflictError("A matching run is already in progress.", code="run_in_progress")
    n = _next_code(db, MatchRun, tenant, "RUN")
    run = MatchRun(
        tenant_id=tenant.id,
        code=f"RUN-{n:05d}",
        status="Queued",
        scope={"entity": entity},
        engine_version=engine.ENGINE_VERSION,
        rules=[],
        metrics={},
        requested_by=actor,
    )
    db.add(run)
    db.flush()
    return run


def execute_run(db: Session, run: MatchRun) -> MatchRun:
    tenant = db.get(Tenant, run.tenant_id)
    assert tenant is not None
    run.status, run.started_at = "Running", run.started_at or datetime.now(UTC)
    db.flush()
    try:
        with db.begin_nested():
            t0 = time.perf_counter()
            rules = load_rules(db, tenant)
            run.rules = [{"id": r.id, "name": r.name, "priority": r.priority} for r in rules]
            lines, by_id, skipped = open_lines(db, tenant, run.scope.get("entity"))
            # Earlier pending proposals are replaced by this run's view of the open items.
            db.execute(
                update(MatchGroup)
                .where(MatchGroup.tenant_id == tenant.id, MatchGroup.status == "proposed")
                .values(status="superseded")
            )
            t1 = time.perf_counter()
            result = engine.run(lines, rules)
            t2 = time.perf_counter()
            base = _next_code(db, MatchGroup, tenant, "MT")
            auto = suggested = 0
            matched_ids: set[str] = set()
            for offset, pred in enumerate(sorted(result.predictions, key=lambda p: -p.confidence)):
                detail = result.details[pred.line_ids]
                a, b = detail.a, detail.b
                matched_ids |= set(pred.line_ids)
                exposure = Decimal(str(round(abs(a.amount_usd), 4)))
                group = MatchGroup(
                    tenant_id=tenant.id,
                    code=f"MT-{base + offset:06d}",
                    run_id=run.id,
                    match_type="1:1",
                    decision=pred.decision,
                    status="matched" if pred.decision == "auto" else "proposed",
                    confidence=pred.confidence,
                    exposure_usd=exposure,
                    residual_usd=Decimal(str(round(detail.features["amount_gap_usd"], 4))),
                    entity_pair="-".join(a.pair),
                    rule_ids=detail.rules,
                    explanation={
                        "features": {k: v for k, v in detail.features.items() if k != "blocking"},
                        "blocking": detail.features["blocking"],
                        "contributions": {k: round(v, 3) for k, v in detail.contributions.items()},
                        "alternatives": [
                            {"txn": by_id[x].code, "probability": p}
                            for x, p in result.alternatives.get(pred.line_ids, [])
                            if x in by_id
                        ],
                    },
                )
                group.members = [
                    MatchMember(txn_id=by_id[a.id].id, side=a.side),
                    MatchMember(txn_id=by_id[b.id].id, side=b.side),
                ]
                db.add(group)
                auto += pred.decision == "auto"
                suggested += pred.decision == "suggest"
            t3 = time.perf_counter()
            unmatched = [x for x in lines if x.id not in matched_ids]
            run.metrics = {
                "lines": len(lines),
                "skipped_no_fx": skipped,
                "candidates": len(result.candidate_pairs),
                "auto": auto,
                "suggested": suggested,
                "unmatched": len(unmatched),
                "auto_rate": round(2 * auto / len(lines), 4) if lines else 0.0,
                "open_exposure_usd": round(sum(abs(x.amount_usd) for x in unmatched if x.side == "A"), 2),
                "timings_s": {
                    "load": round(t1 - t0, 2),
                    "engine": round(t2 - t1, 2),
                    "persist": round(t3 - t2, 2),
                },
                "entities": sorted({x.entity for x in lines}),
                "period": _period(lines),
            }
            run.status = "Completed"
    except Exception as exc:
        logger.exception("Matching run %s failed", run.code)
        run.status, run.error = "Failed", str(exc)[:2000]
    run.finished_at = datetime.now(UTC)
    audit.record(
        db,
        tenant_id=run.tenant_id,
        actor=run.requested_by,
        action=f"match_run.{run.status.lower()}",
        object_type="match_run",
        object_id=run.code,
        control="IC-03",
        after={k: run.metrics.get(k) for k in ("lines", "auto", "suggested", "unmatched")}
        | {"error": run.error},
    )
    db.flush()
    return run


def _period(lines: list[Line]) -> str:
    if not lines:
        return "—"
    months = sorted(
        {x.value_date.strftime("%b %Y") for x in lines}, key=lambda m: datetime.strptime(m, "%b %Y")
    )
    return months[0] if len(months) == 1 else f"{months[0]} - {months[-1]}"


def decide(
    db: Session, tenant: Tenant, code: str, action: str, actor: str, reason: str | None = None
) -> MatchGroup:
    group = db.scalar(select(MatchGroup).where(MatchGroup.tenant_id == tenant.id, MatchGroup.code == code))
    if group is None:
        raise NotFoundError(f"Proposal '{code}' not found.", code="proposal_not_found")
    if group.status != "proposed":
        raise ConflictError(f"{code} is already {group.status}.", code="proposal_not_pending")
    before = group.status
    group.status = "accepted" if action == "accept" else "rejected"
    group.decided_by, group.decided_at = actor, datetime.now(UTC)
    db.add(
        MatchLabel(
            tenant_id=tenant.id,
            group_id=group.id,
            action=action,
            actor=actor,
            reason=reason,
            model_confidence=group.confidence,
            features=group.explanation.get("features", {}),
        )
    )
    audit.record(
        db,
        tenant_id=tenant.id,
        actor=actor,
        action=f"match.{action}ed",
        object_type="match_group",
        object_id=code,
        control="IC-03",
        before={"status": before},
        after={"status": group.status, "reason": reason},
    )
    db.flush()
    return group


def group_lines(db: Session, groups: list[MatchGroup]) -> dict[Any, list[tuple[str, LedgerTxn]]]:
    ids = [g.id for g in groups]
    out: dict[Any, list[tuple[str, LedgerTxn]]] = defaultdict(list)
    if not ids:
        return out
    rows = db.execute(
        select(MatchMember.group_id, MatchMember.side, LedgerTxn)
        .join(LedgerTxn, LedgerTxn.id == MatchMember.txn_id)
        .where(MatchMember.group_id.in_(ids))
    )
    for gid, side, txn in rows:
        out[gid].append((side, txn))
    return out
