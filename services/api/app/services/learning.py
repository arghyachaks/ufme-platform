"""Learning loop (Stage 3f): reviewer decisions -> tenant model -> gated, audited promotion -> drift watch.

1. Labels. Every decision on a proposal (review accept/reject, approval, approval rejection, manual match)
   is stored with the scorer's feature row at that moment, so training never depends on re-running a ledger.
2. Train. A tenant adapter on top of the shipped scorer (app.engines.matching.adapt), recalibrated, with the
   auto threshold re-proven. It is registered as a `candidate` with its evidence.
3. Gate. A candidate may be promoted only if it (a) never auto-matches a held-out rejected pair, (b) is at
   least as good as the active model on held-out decisions, (c) keeps precision 1.0, ECE < 2% and its auto
   rate (within 0.5 pp) on the golden holdouts. Promotion needs a Controller who is not the person who asked
   for the training (four eyes on a model change, control MDL-01), and can be rolled back in one step.
4. Drift. Each run's proposals are compared with the model's reference profile (PSI per feature and on the
   score); reviewer outcomes are compared with the probabilities the model gave them.
"""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.engines.benchmark.model import Line
from app.engines.matching import adapt, drift, engine, learned
from app.models import LedgerTxn, MatchGroup, MatchLabel, MatchMember, MatchRun, ScorerModel, Tenant
from app.services import audit

MAX_AUTO_RATE_DROP = 0.005
MAX_ECE = 0.02


# ---------------------------------------------------------------- labels


def line_of(t: LedgerTxn) -> Line:
    return Line(
        id=t.code,
        entity=t.entity_code,
        counterparty=t.counterparty_code,
        amount=float(t.amount),
        currency=t.currency,
        amount_usd=float(t.amount_usd or 0),
        value_date=t.value_date,
        posting_date=t.posting_date or t.value_date,
        reference=t.reference_raw or "",
        reference_norm=t.reference_norm,
        description=t.description or "",
        account=t.account or "",
    )


def _pair_lines(db: Session, group: MatchGroup) -> tuple[Line, Line] | None:
    rows = db.execute(
        select(MatchMember.side, LedgerTxn)
        .join(LedgerTxn, LedgerTxn.id == MatchMember.txn_id)
        .where(MatchMember.group_id == group.id)
    ).all()
    if len(rows) != 2 or {s for s, _ in rows} != {"A", "B"}:
        return None  # groups (1:M, M:M) are not scored by the pair model
    by_side = {s: line_of(t) for s, t in rows}
    return by_side["A"], by_side["B"]


def vector_for(db: Session, group: MatchGroup) -> tuple[list[float] | None, bool | None]:
    """The scorer row for a 1:1 group: from what the engine recorded, or computed fresh for a manual match."""
    pair = _pair_lines(db, group)
    if pair is None:
        return None, None
    a, b = pair
    expl = group.explanation or {}
    f = expl.get("features") or {}
    # Proposed by the engine: its features as they were when it scored the pair. Manual match: recompute.
    features = {**f, "blocking": expl.get("blocking", [])} if "ref_exact" in f else engine.features_for(a, b)
    within = float(features.get("amount_gap", 1.0)) <= engine.POLICY_TOLERANCE
    return [round(v, 6) for v in adapt.row(features, a, b)], within


def record(
    db: Session,
    tenant: Tenant,
    group: MatchGroup,
    *,
    outcome: int,
    source: str,
    actor: str,
    reason: str | None = None,
) -> MatchLabel:
    """One reviewer decision as training data. The latest label per group wins (an accepted suggestion can
    still be rejected at approval)."""
    vector, within = vector_for(db, group)
    run = db.get(MatchRun, group.run_id)
    label = MatchLabel(
        tenant_id=tenant.id,
        group_id=group.id,
        action="accept" if outcome else "reject",
        actor=actor,
        reason=reason,
        model_confidence=group.confidence,
        features=(group.explanation or {}).get("features", {}),
        label=outcome,
        source=source,
        vector=vector,
        within_policy=within,
        model_version=run.engine_version if run is not None else None,
    )
    db.add(label)
    return label


def _latest_labels(db: Session, tenant: Tenant) -> list[MatchLabel]:
    latest = (
        select(MatchLabel.group_id, func.max(MatchLabel.created_at).label("at"))
        .where(MatchLabel.tenant_id == tenant.id, MatchLabel.label.is_not(None))
        .group_by(MatchLabel.group_id)
        .subquery()
    )
    return list(
        db.scalars(
            select(MatchLabel)
            .join(latest, (latest.c.group_id == MatchLabel.group_id) & (latest.c.at == MatchLabel.created_at))
            .where(MatchLabel.tenant_id == tenant.id)
            .order_by(MatchLabel.created_at)
        )
    )


def dataset(db: Session, tenant: Tenant) -> adapt.LabelSet:
    labels = [
        x for x in _latest_labels(db, tenant) if x.vector and len(x.vector) == len(learned.FEATURE_NAMES)
    ]
    if not labels:
        empty = np.empty((0, len(learned.FEATURE_NAMES)))
        return adapt.LabelSet(empty, np.empty(0, dtype=np.int8), np.empty(0, dtype=bool), [])
    return adapt.LabelSet(
        np.asarray([x.vector for x in labels], dtype=np.float64),
        np.asarray([int(x.label or 0) for x in labels], dtype=np.int8),
        np.asarray([bool(x.within_policy) for x in labels]),
        [str(x.group_id) for x in labels],
    )


# ---------------------------------------------------------------- registry


def active(db: Session, tenant: Tenant) -> ScorerModel | None:
    return db.scalar(
        select(ScorerModel).where(ScorerModel.tenant_id == tenant.id, ScorerModel.status == "active")
    )


def materialize(model: ScorerModel) -> str:
    """Write a registry model to this process's cache (immutable files, named by tenant and version)."""
    assert model.artifact is not None
    return str(adapt.write(model.artifact, Path(settings.model_dir) / str(model.tenant_id)))


def scorer_path(db: Session, tenant: Tenant) -> str | None:
    """What the engine should score this tenant with: its promoted model, or None for the shipped scorer."""
    m = active(db, tenant)
    return materialize(m) if m is not None and m.artifact else None


def _shipped() -> dict[str, Any]:
    return json.loads(learned.ARTIFACT.read_text())


def _next_version(db: Session, tenant: Tenant) -> str:
    n = (
        db.scalar(select(func.count()).select_from(ScorerModel).where(ScorerModel.tenant_id == tenant.id))
        or 0
    )
    return f"{tenant.slug}-adapt-{n + 1:03d}"[:64]


def request_training(db: Session, tenant: Tenant, actor: str) -> ScorerModel:
    labels = dataset(db, tenant)
    if len(labels) < settings.learning_min_labels:
        raise ConflictError(
            f"The model needs at least {settings.learning_min_labels} reviewer decisions to learn from; "
            f"there are {len(labels)} so far.",
            code="not_enough_labels",
        )
    busy = db.scalar(
        select(ScorerModel).where(ScorerModel.tenant_id == tenant.id, ScorerModel.status == "training")
    )
    if busy is not None:
        raise ConflictError(f"{busy.version} is already training.", code="training_in_progress")
    shipped = _shipped()
    model = ScorerModel(
        tenant_id=tenant.id,
        version=_next_version(db, tenant),
        status="training",
        base_version=shipped.get("version", "scorer"),
        metrics={},
        gate={},
        label_count=len(labels),
        trained_by=actor,
    )
    db.add(model)
    audit.record(
        db,
        tenant_id=tenant.id,
        actor=actor,
        action="model.training_requested",
        object_type="scorer_model",
        object_id=model.version,
        control="MDL-01",
        after={"labels": len(labels), "base": model.base_version},
    )
    db.flush()
    return model


def train(db: Session, model: ScorerModel) -> ScorerModel:
    """Run in the worker: fit, measure, gate. Never promotes."""
    tenant = db.get(Tenant, model.tenant_id)
    assert tenant is not None
    labels = dataset(db, tenant)
    try:
        artifact = adapt.train_candidate(
            _shipped(), labels, model.version, Path(tempfile.mkdtemp(prefix="ufme-train-"))
        )
        model.artifact = artifact
        model.metrics = artifact["meta"]
        model.gate = evaluate_gate(db, tenant, model, labels)
        model.status = "candidate"
    except Exception as exc:  # recorded on the model, not swallowed: the UI shows why
        model.status, model.error = "failed", f"{type(exc).__name__}: {exc}"[:2000]
    audit.record(
        db,
        tenant_id=tenant.id,
        actor="system",
        action=f"model.{'trained' if model.status == 'candidate' else 'training_failed'}",
        object_type="scorer_model",
        object_id=model.version,
        control="MDL-01",
        after={"status": model.status, "gate_passed": (model.gate or {}).get("passed"), "error": model.error},
    )
    db.flush()
    return model


def evaluate_gate(db: Session, tenant: Tenant, model: ScorerModel, labels: adapt.LabelSet) -> dict[str, Any]:
    """The promotion checks, computed once at training time and stored as evidence."""
    from app.engines.benchmark.evaluate import evaluate
    from app.engines.benchmark.scenarios import golden

    assert model.artifact is not None
    candidate_path = materialize(model)
    candidate = learned.load(candidate_path)
    assert candidate is not None
    active_path = scorer_path(db, tenant)
    current = learned.load(active_path)
    _, holdout = labels.split()  # the same split train_candidate held back
    cmp = adapt.compare(candidate, current, holdout)
    checks: list[dict[str, Any]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    c, a = cmp["candidate"], cmp["active"]
    check(
        "No wrong auto-match on held-out decisions",
        c.get("would_auto_wrong", 0) == 0,
        f"{c.get('would_auto_wrong', 0)} of {c.get('labels', 0)} held-out decisions would be auto-matched wrongly",
    )
    if a is not None and c.get("labels"):
        check(
            "At least as good as the active model on held-out decisions",
            c["log_loss"] <= a["log_loss"] + 1e-9 or c["would_auto_correct"] > a["would_auto_correct"],
            f"log loss {c['log_loss']} vs {a['log_loss']}; would auto-match {c['would_auto_correct']} "
            f"correct pairs vs {a['would_auto_correct']}",
        )
    golden_report: dict[str, Any] = {}
    for name in filter(None, settings.learning_gate_golden.split(",")):
        ds = golden(name)
        after = evaluate(
            ds, engine.run(ds.lines, keep_candidates=True, scorer=candidate_path).predictions, "c"
        )
        before = evaluate(ds, engine.run(ds.lines, keep_candidates=True, scorer=active_path).predictions, "a")
        golden_report[name] = {
            "before": {
                "auto_rate": before.auto["rate"],
                "precision": before.auto["precision"],
                "ece": before.calibration_error,
            },
            "after": {
                "auto_rate": after.auto["rate"],
                "precision": after.auto["precision"],
                "ece": after.calibration_error,
            },
        }
        check(
            f"Golden {name}: auto precision 100%",
            after.auto["precision"] >= 1.0,
            f"{after.auto['precision']:.4f}",
        )
        check(
            f"Golden {name}: calibration error under 2%",
            after.calibration_error is not None and after.calibration_error < MAX_ECE,
            f"{after.calibration_error}",
        )
        check(
            f"Golden {name}: auto rate held",
            after.auto["rate"] >= before.auto["rate"] - MAX_AUTO_RATE_DROP,
            f"{after.auto['rate']:.4f} vs {before.auto['rate']:.4f}",
        )
    check(
        "Auto threshold proven at 0.5% error (95% confidence)",
        model.artifact["meta"]["auto_error_upper_bound"] <= model.artifact["meta"]["alpha"],
        f"upper bound {model.artifact['meta']['auto_error_upper_bound']}",
    )
    return {
        "passed": all(x["ok"] for x in checks),
        "checks": checks,
        "holdout": cmp,
        "golden": golden_report,
        "shadow": shadow(db, tenant, candidate, current),
    }


def shadow(
    db: Session,
    tenant: Tenant,
    candidate: learned.TreeModel,
    current: learned.TreeModel | None,
    limit: int = 50_000,
) -> dict[str, Any]:
    """Re-score the latest run's open suggestions: how many would the candidate have auto-matched?"""
    run = db.scalar(
        select(MatchRun)
        .where(MatchRun.tenant_id == tenant.id, MatchRun.status == "Completed")
        .order_by(MatchRun.code.desc())
    )
    if run is None:
        return {"run": None}
    groups = list(
        db.scalars(
            select(MatchGroup)
            .where(
                MatchGroup.run_id == run.id, MatchGroup.status == "proposed", MatchGroup.match_type == "1:1"
            )
            .limit(limit)
        )
    )
    rows, within = [], []
    for g in groups:
        v, w = vector_for(db, g)
        if v is not None:
            rows.append(v)
            within.append(bool(w))
    if not rows:
        return {"run": run.code, "suggestions": 0}
    x, ok = np.asarray(rows), np.asarray(within)
    p_new = candidate.proba(x)
    auto_new = int(((p_new >= candidate.auto_threshold) & ok).sum())
    auto_old = int(((current.proba(x) >= current.auto_threshold) & ok).sum()) if current is not None else 0
    return {
        "run": run.code,
        "suggestions": len(rows),
        "would_auto_match": auto_new,
        "would_auto_match_active": auto_old,
    }


def promote(db: Session, tenant: Tenant, version: str, actor: Any) -> ScorerModel:
    from app.services.workflow import RANK

    model = db.scalar(
        select(ScorerModel).where(ScorerModel.tenant_id == tenant.id, ScorerModel.version == version)
    )
    if model is None:
        raise NotFoundError(f"Model '{version}' not found.", code="model_not_found")
    if actor.rank < RANK["Controller"]:
        raise ForbiddenError(
            f"Promoting a model needs a Controller or above; you are {actor.role}.",
            code="insufficient_authority",
        )
    if actor.email.lower() == model.trained_by.lower():
        raise ForbiddenError(
            "The person who requested the training can't also promote the model (four eyes on model changes).",
            code="sod_model_change",
        )
    if model.status not in ("candidate", "retired"):
        raise ConflictError(
            f"{version} is {model.status}; only a candidate or retired model can be promoted.",
            code="model_not_promotable",
        )
    if not (model.gate or {}).get("passed"):
        failed = [c["name"] for c in (model.gate or {}).get("checks", []) if not c["ok"]]
        raise ConflictError(
            f"{version} did not pass the promotion gate: {'; '.join(failed) or 'not evaluated'}.",
            code="gate_failed",
        )
    previous = active(db, tenant)
    now = datetime.now(UTC)
    if previous is not None:
        previous.status = "retired"
    model.status, model.promoted_by, model.promoted_at = "active", actor.email, now
    audit.record(
        db,
        tenant_id=tenant.id,
        actor=actor.email,
        action="model.promoted",
        object_type="scorer_model",
        object_id=version,
        control="MDL-01",
        before={"active": previous.version if previous is not None else "shipped"},
        after={"active": version, "gate": "passed"},
    )
    db.flush()
    return model


def rollback(db: Session, tenant: Tenant, actor: Any) -> ScorerModel | None:
    """Retire the active model and restore the previously promoted one (or the shipped scorer)."""
    from app.services.workflow import RANK

    if actor.rank < RANK["Controller"]:
        raise ForbiddenError(
            f"Rolling back a model needs a Controller or above; you are {actor.role}.",
            code="insufficient_authority",
        )
    current = active(db, tenant)
    if current is None:
        raise ConflictError("The shipped scorer is already in use.", code="nothing_to_roll_back")
    current.status = "rolled_back"
    restored = db.scalar(
        select(ScorerModel)
        .where(
            ScorerModel.tenant_id == tenant.id,
            ScorerModel.status == "retired",
            ScorerModel.promoted_at.is_not(None),
            ScorerModel.id != current.id,
        )
        .order_by(ScorerModel.promoted_at.desc())
    )
    if restored is not None:
        restored.status = "active"
    audit.record(
        db,
        tenant_id=tenant.id,
        actor=actor.email,
        action="model.rolled_back",
        object_type="scorer_model",
        object_id=current.version,
        control="MDL-01",
        before={"active": current.version},
        after={"active": restored.version if restored is not None else "shipped"},
    )
    db.flush()
    return restored


# ---------------------------------------------------------------- drift


def run_drift(result: engine.EngineResult, scorer: str | None) -> dict[str, Any]:
    """Drift of a run's scored pairs against the profile stored with the model that scored them."""
    model = learned.load(scorer)
    if model is None:
        return {"status": "unknown", "reason": "hand scorer"}
    x, scores = drift.of_result(result)
    return drift.compare(model.meta.get("reference_profile"), x, scores)


def outcome_drift(db: Session, tenant: Tenant, last: int = 500) -> dict[str, Any]:
    """Are reviewers accepting suggestions as often as the model said they would?"""
    rows = list(
        db.execute(
            select(MatchLabel.model_confidence, MatchLabel.label)
            .where(MatchLabel.tenant_id == tenant.id, MatchLabel.label.is_not(None))
            .order_by(MatchLabel.created_at.desc())
            .limit(last)
        )
    )
    if len(rows) < 30:
        return {"status": "unknown", "decisions": len(rows)}
    expected = float(np.mean([r[0] for r in rows]))
    actual = float(np.mean([r[1] for r in rows]))
    gap = actual - expected
    return {
        "status": "alert" if abs(gap) >= 0.15 else "watch" if abs(gap) >= 0.07 else "ok",
        "decisions": len(rows),
        "expected_accept_rate": round(expected, 4),
        "actual_accept_rate": round(actual, 4),
        "gap": round(gap, 4),
    }


# ---------------------------------------------------------------- status for the UI


def status(db: Session, tenant: Tenant) -> dict[str, Any]:
    labels = _latest_labels(db, tenant)
    usable = [x for x in labels if x.vector]
    by_source: dict[str, int] = {}
    for x in labels:
        by_source[x.source or "legacy"] = by_source.get(x.source or "legacy", 0) + 1
    models = list(
        db.scalars(
            select(ScorerModel)
            .where(ScorerModel.tenant_id == tenant.id)
            .order_by(ScorerModel.created_at.desc())
            .limit(20)
        )
    )
    current = next((m for m in models if m.status == "active"), None)
    shipped = _shipped()
    run = db.scalar(
        select(MatchRun)
        .where(MatchRun.tenant_id == tenant.id, MatchRun.status == "Completed")
        .order_by(MatchRun.code.desc())
    )
    since = sum(
        1
        for x in usable
        if current is None or current.promoted_at is None or x.created_at > current.promoted_at
    )
    return {
        "active": current.version if current is not None else shipped.get("version", "scorer"),
        "activeIsShipped": current is None,
        "labels": {
            "total": len(labels),
            "usable": len(usable),
            "accepted": sum(1 for x in labels if x.label == 1),
            "rejected": sum(1 for x in labels if x.label == 0),
            "bySource": by_source,
            "sinceActive": since,
            "minimum": settings.learning_min_labels,
        },
        "canTrain": len(usable) >= settings.learning_min_labels
        and not any(m.status == "training" for m in models),
        "models": [model_out(m) for m in models],
        "recent": [
            {
                "at": x.created_at.isoformat() if x.created_at else None,
                "match": code,
                "actor": x.actor,
                "outcome": "Accepted" if x.label == 1 else "Rejected",
                "source": x.source,
                "modelScore": round(float(x.model_confidence), 4),
                "reason": x.reason,
            }
            for x, code in db.execute(
                select(MatchLabel, MatchGroup.code)
                .join(MatchGroup, MatchGroup.id == MatchLabel.group_id)
                .where(MatchLabel.tenant_id == tenant.id, MatchLabel.label.is_not(None))
                .order_by(MatchLabel.created_at.desc())
                .limit(25)
            )
        ],
        "drift": {
            "run": run.code if run is not None else None,
            "features": (run.metrics or {}).get("drift") if run is not None else None,
            "outcomes": outcome_drift(db, tenant),
        },
    }


def model_out(m: ScorerModel) -> dict[str, Any]:
    meta = m.metrics or {}
    return {
        "version": m.version,
        "status": m.status,
        "base": m.base_version,
        "labels": m.label_count,
        "trainedBy": m.trained_by,
        "trainedAt": m.created_at.isoformat() if m.created_at else None,
        "promotedBy": m.promoted_by,
        "promotedAt": m.promoted_at.isoformat() if m.promoted_at else None,
        "autoThreshold": (m.artifact or {}).get("auto_threshold"),
        "seconds": meta.get("trained_seconds"),
        "holdout": meta.get("holdout"),
        "gate": m.gate or {},
        "error": m.error,
    }
