"""Read models for runs and proposals, and the adapter that feeds them into the Runs/Review screens."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import MatchGroup, MatchRun, Tenant
from app.schemas import read as s
from app.services import display as fmt
from app.services.matching import group_lines


def run_out(run: MatchRun) -> s.RunOut:
    duration = (
        int((run.finished_at - run.started_at).total_seconds() * 1000)
        if run.started_at and run.finished_at
        else None
    )
    return s.RunOut(
        id=run.code,
        status=run.status,
        scope=run.scope or {},
        engine_version=run.engine_version,
        rules=run.rules or [],
        started_at=fmt.second(run.started_at) if run.started_at else None,
        duration_ms=duration,
        metrics=run.metrics or {},
        error=run.error,
    )


def runs(db: Session, tenant: Tenant, limit: int = 50) -> list[MatchRun]:
    return list(
        db.scalars(
            select(MatchRun)
            .where(MatchRun.tenant_id == tenant.id)
            .order_by(MatchRun.code.desc())
            .limit(limit)
        )
    )


def get_run(db: Session, tenant: Tenant, code: str) -> MatchRun:
    run = db.scalar(select(MatchRun).where(MatchRun.tenant_id == tenant.id, MatchRun.code == code))
    if run is None:
        raise NotFoundError(f"Run '{code}' not found.", code="run_not_found")
    return run


def proposals(
    db: Session,
    tenant: Tenant,
    run_code: str | None = None,
    status: str | None = None,
    decision: str | None = None,
    limit: int = 100,
    code: str | None = None,
    order: str = "exposure",
    actor: Any = None,
) -> list[s.ProposalOut]:
    q = (
        select(MatchGroup, MatchRun.code)
        .join(MatchRun, MatchRun.id == MatchGroup.run_id)
        .where(MatchGroup.tenant_id == tenant.id)
    )
    if run_code:
        q = q.where(MatchRun.code == run_code)
    if status:
        q = q.where(MatchGroup.status == status)
    if decision:
        q = q.where(MatchGroup.decision == decision)
    if code:
        q = q.where(MatchGroup.code == code)
    from app.services.workflow import entity_clause

    if (scope := entity_clause(actor, MatchGroup.entity_pair)) is not None:
        q = q.where(scope)
    # "learning" (3f): a random sample of open suggestions. Measured on the settlement-lag benchmark with 300
    # reviewer answers: random +7.1 pp auto rate, closest-to-50% +3.0, closest-to-threshold +2.1. Borderline
    # items resemble each other; a representative mix teaches the model more. Default: largest exposure first.
    ordering = (
        (func.random(), MatchGroup.code)
        if order == "learning"
        else (MatchGroup.exposure_usd.desc(), MatchGroup.code)
    )
    rows = db.execute(q.order_by(*ordering).limit(limit)).all()
    members = group_lines(db, [g for g, _ in rows])
    out = []
    for g, run_code_ in rows:
        out.append(
            s.ProposalOut(
                id=g.code,
                run=run_code_,
                type=g.match_type,
                decision=g.decision,
                status=g.status,
                confidence=g.confidence,
                exposure_usd=fmt.number(g.exposure_usd),
                residual_usd=fmt.number(g.residual_usd),
                entity_pair=g.entity_pair,
                rules=g.rule_ids,
                explanation=g.explanation,
                lines=[
                    s.ProposalLineOut(
                        id=t.code,
                        side=side,
                        entity=t.entity_code,
                        counterparty=t.counterparty_code,
                        amount=fmt.number(t.amount),
                        currency=t.currency,
                        amount_usd=fmt.number(t.amount_usd) if t.amount_usd is not None else None,
                        value_date=t.value_date.isoformat(),
                        reference=t.reference_norm,
                        description=t.description,
                    )
                    for side, t in sorted(members[g.id], key=lambda m: m[0])
                ],
            )
        )
    return out


def proposal(db: Session, tenant: Tenant, code: str) -> s.ProposalOut:
    found = proposals(db, tenant, code=code, limit=1)
    if not found:
        raise NotFoundError(f"Proposal '{code}' not found.", code="proposal_not_found")
    return found[0]


def _money(usd: float) -> str:
    return (
        f"${usd / 1e6:.1f}M"
        if abs(usd) >= 1e6
        else f"${usd / 1e3:.0f}K"
        if abs(usd) >= 1e3
        else f"${usd:,.0f}"
    )


def _duration(ms: int | None) -> str:
    if ms is None:
        return "—"
    return f"{ms / 1000:.1f}s" if ms < 60_000 else f"{ms / 60_000:.0f}m"


FEATURE_LABEL = {
    "amount": "Amount",
    "reference": "Reference",
    "date": "Date",
    "rule": "Rule",
    "ambiguity": "Ambiguity",
    "residual": "Residual",
    "family": "Partial family",
    "learned": "Learned model",
    "size": "Group size",
}


def workspace(db: Session, tenant: Tenant, snapshot: dict[str, Any]) -> dict[str, Any]:
    """The Runs/Review screens' payload: real runs and proposals where they exist, demo content elsewhere."""
    real_runs = runs(db, tenant, limit=20)
    if not real_runs:
        return snapshot
    data = dict(snapshot)
    rows = []
    for run in real_runs:
        m = run.metrics or {}
        lines = int(m.get("lines", 0) or 0)
        exposure = float(m.get("open_exposure_usd", 0) or 0)
        n_pending = int(m.get("suggested", 0) or 0)
        out = run_out(run)
        status = {"Completed": "Review Required" if n_pending else "Completed"}.get(run.status, run.status)
        rows.append(
            {
                "id": run.code,
                "type": "Intercompany",
                "entity": run.scope.get("entity") or "All entities",
                "period": m.get("period", "—"),
                "status": status,
                "progress": 100 if run.status in ("Completed", "Failed") else 50,
                "matchRate": f"{100 * float(m.get('auto_rate', 0) or 0):.1f}%",
                "exposure": _money(exposure),
                "exposureValue": round(exposure / 1e6, 1),
                "materiality": "High" if exposure > 100e6 else "Medium" if exposure > 10e6 else "Low",
                "start": (out.started_at or "—")[-8:-3],
                "duration": _duration(out.duration_ms),
                "ruleVersion": "rules " + ", ".join(r["id"] for r in run.rules)
                if run.rules
                else "rules: none",
                "modelVersion": run.engine_version.split(" ")[0],
                "dataSource": "ledger (" + ", ".join(m.get("entities", [])) + ")",
                "transactionsProcessed": f"{lines:,}",
                "rulesExecuted": [r["id"] for r in run.rules],
                "runtimeBreakdown": [
                    {"step": k.title(), "time": f"{v}s"} for k, v in (m.get("timings_s") or {}).items()
                ],
                "exceptionSummary": f"{int(m.get('unmatched', 0) or 0):,} open · {_money(exposure)} exposure",
            }
        )
    data["runs"] = rows

    latest = real_runs[0]
    pending = proposals(db, tenant, run_code=latest.code, status="proposed", limit=16)
    if pending:

        def a_side(p: s.ProposalOut) -> s.ProposalLineOut:
            return next((x for x in p.lines if x.side == "A"), p.lines[0])

        def b_side(p: s.ProposalOut) -> s.ProposalLineOut:  # reversal groups sit on one side
            return next((x for x in p.lines if x.side == "B"), p.lines[-1])

        data["sideA"] = [
            {
                "id": p.id,
                "invoice": a_side(p).reference or "—",
                "reference": b_side(p).reference or "—",
                "amount": a_side(p).amount,
                "currency": a_side(p).currency,
                "date": fmt.day(_d(a_side(p).value_date)),
                "entity": a_side(p).entity,
                "counterparty": a_side(p).counterparty,
                "businessUnit": "Intercompany",
                "description": a_side(p).description or "",
                "slaRemaining": "48h remaining",
                "status": _residual_label(p.explanation),
                "attachments": [],
            }
            for p in pending
        ]
        top = pending[0]
        expl: dict[str, Any] = dict(top.explanation)
        alternatives = expl.get("alternatives", []) or []
        others = [x for x in top.lines if x.side == "B"] or top.lines[1:]  # every counterpart of a group
        data["sideB"] = [
            {
                "id": x.id,
                "invoice": x.reference or "—",
                "amount": x.amount,
                "date": fmt.day(_d(x.value_date)),
                "entity": x.entity,
                "score": round(100 * top.confidence, 1),
                "status": "Candidate" if top.type == "1:1" else f"{top.type} part",
            }
            for x in others
        ] + [
            {
                "id": alt["txn"],
                "invoice": "—",
                "amount": 0,
                "date": "—",
                "entity": b_side(top).entity,
                "score": round(100 * float(alt["probability"]), 1),
                "status": "Alternative",
            }
            for alt in alternatives
        ]
        contributions = {k: v for k, v in (expl.get("contributions") or {}).items() if k != "prior"}
        total = sum(abs(v) for v in contributions.values()) or 1.0
        features = expl.get("features") or {}
        sm = dict(snapshot["suggestedMatch"])
        sm.update(
            {
                "type": top.type,
                "confidence": f"{100 * top.confidence:.1f}%",
                "amountImpact": _money(float(top.exposure_usd)),
                "materiality": "High"
                if top.exposure_usd > 1e6
                else "Medium"
                if top.exposure_usd > 5e4
                else "Low",
                "risk": "Low" if top.confidence >= 0.95 else "Medium",
                "rule": " + ".join(top.rules) or "Scored match",
                "ruleVersion": latest.engine_version.split(" ")[0],
                "exposureReduction": _money(float(top.exposure_usd)),
                "queueSize": int((latest.metrics or {}).get("suggested", len(pending))),
                "confidenceBreakdown": [
                    {"label": FEATURE_LABEL.get(k, k.title()), "weight": round(100 * abs(v) / total)}
                    for k, v in sorted(contributions.items(), key=lambda kv: -abs(kv[1]))
                ],
                "why": [
                    f"Amount gap {100 * float(features.get('amount_gap', 0)):.2f}% (${float(features.get('amount_gap_usd', 0)):,.2f})",
                    f"Reference: {_ref_story(features)}",
                    f"Date variance {features.get('date_gap_days', '—')} days",
                    f"Entity relationship: {top.entity_pair.replace('-', ' ↔ ')} (intercompany)",
                    f"Found by: {', '.join(expl.get('blocking', []) or ['—'])}",
                    *(
                        [f"Residual: {features['residual']['label']}. {features['residual']['detail']}"]
                        if isinstance(features.get("residual"), dict)
                        else []
                    ),
                    *(
                        [
                            f"ufme Assist ({expl['judge']['confidence']}% sure, "
                            f"{expl['judge']['cause'].replace('_', ' ')}): {expl['judge']['note']}"
                        ]
                        if isinstance(expl.get("judge"), dict)
                        else []
                    ),
                    *(
                        [f"Duplicate posting(s) also open: {', '.join(features['duplicate_postings'])}"]
                        if features.get("duplicate_postings")
                        else []
                    ),
                    *(f"Needs review: {b}" for b in (expl.get("model") or {}).get("blockers", [])),
                    *(
                        f"Would auto-match: {c.removeprefix('would be auto-matched if ')}"
                        for c in (expl.get("model") or {}).get("counterfactuals", [])
                    ),
                ],
            }
        )
        data["suggestedMatch"] = sm
    return data


def _d(iso: str) -> Any:
    from datetime import date

    return date.fromisoformat(iso)


def _ref_story(f: dict[str, Any]) -> str:
    if f.get("ref_root"):
        return (
            f"shared reference family {f['ref_root']} ({f.get('items_a', 0)} : {f.get('items_b', 0)} items)"
        )
    if f.get("ref_exact"):
        return "exact match"
    if f.get("ref_canonical_exact"):
        return "match after OCR normalisation"
    if f.get("ref_affix"):
        return "match after prefix/suffix strip"
    if f.get("ref_in_description"):
        return "found in counterparty description"
    if f.get("ref_edit_distance") == 1:
        return "one-character difference (typo)"
    if f.get("ref_missing"):
        return "missing on one side (amount/date evidence)"
    return "partial"


def _residual_label(explanation: Any) -> str:
    features = (explanation or {}).get("features") or {}
    res = features.get("residual") if isinstance(features, dict) else None
    return str(res.get("label", "Suggested")) if isinstance(res, dict) else "Suggested"
