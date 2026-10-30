"""Matching runs: load open ledger lines → engine → persist proposals; reviewer decisions become labels."""

import logging
import time
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, NamedTuple

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.engines.benchmark.model import Line
from app.engines.matching import engine
from app.engines.matching.rules import Rule
from app.models import LedgerTxn, MatchGroup, MatchMember, MatchRule, MatchRun, Tenant
from app.services import audit, learning, workflow
from app.services.ingestion import bulk_insert
from app.services.workflow import Actor

logger = logging.getLogger("ufme.matching")
STALE_RUN_AFTER = timedelta(hours=1)
CLOSED = ("matched", "accepted", "pending_approval")  # lines in these groups are no longer open


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


class TxnRef(NamedTuple):
    """What persistence needs from a ledger line: its row id and human code (not a full ORM object)."""

    id: uuid.UUID
    code: str


def open_lines(
    db: Session, tenant: Tenant, entity: str | None = None
) -> tuple[list[Line], dict[str, TxnRef], int]:
    """Open (unmatched) ledger lines. Selects columns, not ORM entities: ~700K identity-mapped objects cost
    gigabytes and pushed parallel runs into out-of-memory kills."""
    # NOT EXISTS (an anti-join), not NOT IN: with ~500K members NOT IN degrades to a per-row subplan.
    closed = (
        select(MatchMember.id)
        .join(MatchGroup, MatchGroup.id == MatchMember.group_id)
        .where(
            MatchMember.txn_id == LedgerTxn.id,
            MatchGroup.tenant_id == tenant.id,
            MatchGroup.status.in_(CLOSED),
        )
    )
    t = LedgerTxn
    q = select(
        t.id,
        t.code,
        t.entity_code,
        t.counterparty_code,
        t.amount,
        t.currency,
        t.amount_usd,
        t.value_date,
        t.posting_date,
        t.reference_raw,
        t.reference_norm,
        t.description,
        t.account,
    ).where(t.tenant_id == tenant.id, ~closed.exists())
    if entity:
        q = q.where((t.entity_code == entity) | (t.counterparty_code == entity))
    lines: list[Line] = []
    by_id: dict[str, TxnRef] = {}
    skipped = 0
    for row in db.execute(q.execution_options(yield_per=50_000)):
        if row.amount_usd is None:  # no FX rate: cannot be compared across currencies
            skipped += 1
            continue
        key = str(row.id)
        by_id[key] = TxnRef(row.id, row.code)
        lines.append(
            Line(
                id=key,
                entity=row.entity_code,
                counterparty=row.counterparty_code,
                amount=float(row.amount),
                currency=row.currency,
                amount_usd=float(row.amount_usd),
                value_date=row.value_date,
                posting_date=row.posting_date or row.value_date,
                reference=row.reference_raw or "",
                reference_norm=row.reference_norm,
                description=row.description or "",
                account=row.account or "",
            )
        )
    return lines, by_id, skipped


def create_run(db: Session, tenant: Tenant, entity: str | None = None, actor: str = "api") -> MatchRun:
    # A run whose worker died (restart, OOM) would otherwise block every future run.
    stale_before = datetime.now(UTC) - STALE_RUN_AFTER
    for stuck in db.scalars(
        select(MatchRun).where(
            MatchRun.tenant_id == tenant.id,
            MatchRun.status.in_(("Queued", "Running")),
            func.coalesce(MatchRun.started_at, MatchRun.created_at) < stale_before,
        )
    ):
        stuck.status, stuck.error = (
            "Failed",
            "Abandoned: no progress within the time limit (worker restarted?)",
        )
        stuck.finished_at = datetime.now(UTC)
        audit.record(
            db,
            tenant_id=tenant.id,
            actor="system",
            action="match_run.abandoned",
            object_type="match_run",
            object_id=stuck.code,
            control="IC-03",
        )
    db.flush()
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
        engine_version=engine.version_label(learning.scorer_path(db, tenant)),
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
            scorer = learning.scorer_path(db, tenant)  # 3f: the tenant's promoted model, else the shipped one
            run.engine_version = engine.version_label(scorer)
            result = engine.run(lines, rules, keep_candidates=False, scorer=scorer)
            drift_report = learning.run_drift(result, scorer)
            t2 = time.perf_counter()
            base = _next_code(db, MatchGroup, tenant, "MT")
            auto = suggested = 0
            matched_ids: set[str] = set()
            groups: list[dict[str, Any]] = []
            members: list[dict[str, Any]] = []
            for offset, pred in enumerate(sorted(result.predictions, key=lambda p: -p.confidence)):
                detail = result.details[pred.line_ids]
                a, b = detail.a, detail.b
                members_of = getattr(detail, "lines", None) or [a, b]  # groups (3c) carry all their lines
                matched_ids |= set(pred.line_ids)
                gid = uuid.uuid4()
                groups.append(
                    {
                        "id": gid,
                        "tenant_id": tenant.id,
                        "code": f"MT-{base + offset:06d}",
                        "run_id": run.id,
                        "match_type": getattr(detail, "match_type", "1:1"),
                        "decision": pred.decision,
                        "status": "matched" if pred.decision == "auto" else "proposed",
                        "confidence": pred.confidence,
                        "exposure_usd": Decimal(
                            str(round(getattr(detail, "exposure_usd", abs(a.amount_usd)), 4))
                        ),
                        "residual_usd": Decimal(str(round(detail.features["amount_gap_usd"], 4))),
                        "entity_pair": "-".join(a.pair),
                        "rule_ids": detail.rules,
                        "explanation": {
                            "features": {
                                k: (
                                    [by_id[x].code for x in v if x in by_id]
                                    if k == "duplicate_postings"
                                    else v
                                )
                                for k, v in detail.features.items()
                                if k != "blocking"
                            },
                            "blocking": detail.features["blocking"],
                            "contributions": {k: round(v, 3) for k, v in detail.contributions.items()},
                            "alternatives": [
                                {"txn": by_id[x].code, "probability": p}
                                for x, p in result.alternatives.get(pred.line_ids, [])
                                if x in by_id
                            ],
                            # 3d: learned-model drivers, blockers and counterfactuals (suggestions only)
                            **(
                                {"model": getattr(detail, "explain", None)}
                                if getattr(detail, "explain", None)
                                else {}
                            ),
                        },
                    }
                )
                members += [{"group_id": gid, "txn_id": by_id[x.id].id, "side": x.side} for x in members_of]
                auto += pred.decision == "auto"
                suggested += pred.decision == "suggest"
            # COPY, not ORM objects: ~270K groups + ~540K members per 1M lines would otherwise flush for minutes.
            db.flush()
            bulk_insert(db, MatchGroup, groups)
            bulk_insert(db, MatchMember, members)
            t3 = time.perf_counter()
            unmatched = [x for x in lines if x.id not in matched_ids]
            run.metrics = {
                "lines": len(lines),
                "skipped_no_fx": skipped,
                "candidates": result.candidate_count,
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
                "drift": drift_report,  # 3f: inputs vs the scoring model's reference profile (PSI)
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
    db: Session, tenant: Tenant, code: str, action: str, actor: Actor, reason: str | None = None
) -> MatchGroup:
    """Reject closes the proposal. Accept submits it for approval under the matrix (Stage 4): the lines stay
    locked while it waits, and the group becomes `accepted` only when the approval completes."""
    group = db.scalar(select(MatchGroup).where(MatchGroup.tenant_id == tenant.id, MatchGroup.code == code))
    if group is None:
        raise NotFoundError(f"Proposal '{code}' not found.", code="proposal_not_found")
    if group.status != "proposed":
        raise ConflictError(
            f"{code} is already {group.status.replace('_', ' ')}.", code="proposal_not_pending"
        )
    before = group.status
    learning.record(  # 3f: training data for the tenant model, with the scorer row as it was
        db,
        tenant,
        group,
        outcome=int(action == "accept"),
        source=f"review_{action}",
        actor=actor.email,
        reason=reason,
    )
    if action == "accept":
        workflow.submit(db, tenant, group, actor, "review", reason or "Reviewed and accepted from the queue.")
    else:
        group.status = "rejected"
        group.decided_by, group.decided_at = actor.email, datetime.now(UTC)
    audit.record(
        db,
        tenant_id=tenant.id,
        actor=actor.email,
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
    for i in range(0, len(ids), 10_000):  # Postgres caps a statement at 65,535 bind parameters
        rows = db.execute(
            select(MatchMember.group_id, MatchMember.side, LedgerTxn)
            .join(LedgerTxn, LedgerTxn.id == MatchMember.txn_id)
            .where(MatchMember.group_id.in_(ids[i : i + 10_000]))
        )
        for gid, side, txn in rows:
            out[gid].append((side, txn))
    return out
