"""Stage 3f: reviewer labels, tenant adapter, promotion gate (four eyes, MDL-01), rollback, drift, active learning."""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.engines.benchmark.model import Line
from app.engines.benchmark.scenarios import golden
from app.engines.data_quality.normalize import normalize_reference
from app.engines.matching import adapt, drift, engine, learned
from app.engines.matching.train import collect
from app.models import AuditEvent, MatchLabel
from app.seed import seed_demo

ANALYST = {"X-Ufme-User": "priya.nair@example.com"}
MANAGER = {"X-Ufme-User": "arjun.rao@example.com"}
CONTROLLER = {"X-Ufme-User": "daniel.ortiz@example.com"}
DIRECTOR = {"X-Ufme-User": "liam.walsh@example.com"}


# ---------------------------------------------------------------- engine level


@pytest.fixture(scope="module")
def small_rows() -> tuple[np.ndarray, np.ndarray]:
    return collect(golden("small"))


def test_adapter_keeps_every_monotonic_guarantee(small_rows: tuple[np.ndarray, np.ndarray]) -> None:
    pytest.importorskip("sklearn")
    base = json.loads(learned.ARTIFACT.read_text())
    x, y = small_rows
    # Adversarial labels: claim long-lagged pairs are matches. The adapter may learn that, but never by
    # breaking a constraint (e.g. it can't make a *larger* date gap score higher than a smaller one).
    lagged = x[:, learned.FEATURE_NAMES.index("date_gap_days")] >= 5
    labels_x, labels_y = x[lagged][:200], np.ones(min(200, int(lagged.sum())), dtype=np.int8)
    trees, shift = adapt.fit(base, labels_x, labels_y, x, y, rounds=6)
    combined = learned.TreeModel.from_json(adapt.combine(base, trees, shift))
    original = learned.TreeModel.from_json(base)
    assert len(combined.trees) == len(original.trees) + 6
    rng = np.random.default_rng(3)
    for feature, direction in [(f, m) for f, m in learned.FEATURES if m]:
        i = learned.FEATURE_NAMES.index(feature)
        lo, hi = {"amount_gap_log": (-7, 0), "amount_gap_usd_log": (-2, 6), "date_gap_days": (0, 60)}.get(
            feature, (0, 10)
        )
        for _ in range(10):
            row = x[rng.integers(len(x))].copy()
            grid = np.repeat(row[None, :], 12, axis=0)
            grid[:, i] = np.linspace(lo, hi, 12)
            assert (np.diff(combined.raw(grid)) * direction >= -1e-9).all(), feature
    # ... and it moved toward the labels: lagged pairs score higher than before.
    assert combined.raw(labels_x).mean() > original.raw(labels_x).mean()


def test_labelset_split_is_stratified_and_deterministic() -> None:
    y = np.asarray([1] * 40 + [0] * 8, dtype=np.int8)
    labels = adapt.LabelSet(
        np.zeros((48, len(learned.FEATURE_NAMES))), y, np.ones(48, dtype=bool), [str(i) for i in range(48)]
    )
    train, hold = labels.split()
    assert len(train) + len(hold) == 48 and int(hold.y.sum()) == 10 and int((hold.y == 0).sum()) == 2
    assert labels.split()[1].ids == hold.ids


def test_drift_is_quiet_on_the_same_population_and_alerts_on_a_shift(
    small_rows: tuple[np.ndarray, np.ndarray],
) -> None:
    x, _ = small_rows
    scores = learned.load().proba(x)  # type: ignore[union-attr]
    ref = drift.profile(x, scores)
    same = drift.compare(ref, x, scores)
    assert same["status"] == "ok" and same["max_psi"] < 0.01
    shifted = x.copy()
    shifted[:, learned.FEATURE_NAMES.index("date_gap_days")] += 9  # a tenant that books 9 days late
    moved = drift.compare(ref, shifted, scores)
    assert moved["status"] == "alert" and moved["feature"] == "date_gap_days"
    assert drift.compare(None, x, scores)["status"] == "unknown"


def test_features_for_a_manual_pair_match_what_the_engine_records() -> None:
    def ln(i: str, e: str, cp: str, usd: float, ref: str) -> Line:
        d = datetime(2026, 8, 10).date()
        return Line(i, e, cp, usd, "USD", usd, d, d, ref, normalize_reference(ref), "IC recharge", "1910")

    a, b = ln("a", "UK02", "US01", 48210.55, "INV-88123"), ln("b", "US01", "UK02", -48210.55, "INV-88123")
    res = engine.run([a, b])
    [p] = res.predictions
    d = res.details[p.line_ids]
    assert adapt.row(d.features, d.a, d.b) == adapt.row(engine.features_for(b, a), a, b)


def test_train_candidate_end_to_end_on_small_ledgers(
    tmp_path: Path, small_rows: tuple[np.ndarray, np.ndarray]
) -> None:
    """The real pipeline (simulated reviewers -> adapter -> recalibration -> threshold proof) on small data."""
    pytest.importorskip("sklearn")
    from app.engines.benchmark.learning_eval import reviewer_labels, settlement_lag
    from app.engines.benchmark.scenarios import generate

    tenant = settlement_lag(generate(4000, 51))
    labels = reviewer_labels(tenant, budget=60, strategy="random")
    assert len(labels) >= adapt.MIN_LABELS and labels.within_policy.any()
    other = reviewer_labels(tenant, budget=60, strategy="threshold")
    assert sorted(other.ids) != sorted(labels.ids)  # different picks from the same pool

    base = json.loads(learned.ARTIFACT.read_text())
    art = adapt.train_candidate(
        base, labels, "t-adapt-001", tmp_path, calibration_size=3000, anchor=small_rows
    )
    meta = art["meta"]
    assert art["version"] == "t-adapt-001" and art["adapter_trees"] == adapt.ROUNDS
    assert art["auto_threshold"] >= meta["probability_floor"] == 0.98
    assert meta["auto_error_upper_bound"] <= meta["alpha"] and meta["base_version"] == base["version"]
    assert meta["holdout"]["labels"] == meta["labels_holdout"] and "reference_profile" in meta
    path = adapt.write(art, tmp_path)
    assert adapt.write(art, tmp_path) == path  # immutable: never rewritten
    model = learned.load(str(path))
    assert model is not None and model.meta["version"] == "t-adapt-001"
    with pytest.raises(ValueError, match="reviewer decisions"):
        adapt.train_candidate(base, labels._take(np.arange(len(labels)) < 5), "x", tmp_path)


def test_shipped_scorer_carries_a_reference_profile() -> None:
    meta = learned.load().meta  # type: ignore[union-attr]
    assert set(meta["reference_profile"]["features"]) == {*learned.FEATURE_NAMES, "score"}


# ---------------------------------------------------------------- service + API


@pytest.fixture
def api(
    db: Session, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    seed_demo(db, now=datetime(2026, 10, 18, 12, 0, tzinfo=UTC))
    monkeypatch.setattr(settings, "ingest_inline", True)
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    monkeypatch.setattr(settings, "model_dir", str(tmp_path / "models"))
    monkeypatch.setattr(settings, "learning_min_labels", 4)
    monkeypatch.setattr(settings, "learning_gate_golden", "")  # the golden gate is exercised by the benchmark

    def fast_candidate(
        base: dict[str, Any], labels: adapt.LabelSet, version: str, workdir: Path, **_: Any
    ) -> dict[str, Any]:
        # The real fit takes minutes; the registry, gate and four-eyes flow are what this test is about.
        return {
            **base,
            "version": version,
            "meta": {
                **base.get("meta", {}),
                "alpha": 0.005,
                "auto_error_upper_bound": 0.0001,
                "labels_train": len(labels),
                "trained_seconds": 0.0,
            },
        }

    monkeypatch.setattr(adapt, "train_candidate", fast_candidate)
    assert client.post("/api/v1/data/sources/SRC-01/sync?rows=3000").status_code == 202
    assert client.post("/api/v1/recon/runs", headers=ANALYST).status_code == 202
    yield client


def _label(api: TestClient, accept: int, reject: int) -> None:
    pending = api.get("/api/v1/recon/proposals?status=proposed&limit=5000", headers=DIRECTOR).json()
    one_to_one = [p for p in pending if p["type"] == "1:1"]
    assert len(one_to_one) >= accept + reject
    for p in one_to_one[:accept]:
        assert api.post(f"/api/v1/recon/proposals/{p['id']}/accept", headers=DIRECTOR).status_code == 200
    for p in one_to_one[accept : accept + reject]:
        assert api.post(f"/api/v1/recon/proposals/{p['id']}/reject", headers=DIRECTOR).status_code == 200


def test_reviewer_decisions_become_training_rows(api: TestClient, db: Session) -> None:
    before = api.get("/api/v1/learning/status").json()
    assert before["activeIsShipped"] and not before["canTrain"] and before["labels"]["usable"] == 0
    _label(api, accept=2, reject=2)
    rows = list(db.scalars(select(MatchLabel).where(MatchLabel.label.is_not(None))))
    assert sorted(r.source for r in rows) == ["review_accept"] * 2 + ["review_reject"] * 2
    assert all(r.vector and len(r.vector) == len(learned.FEATURE_NAMES) for r in rows)
    assert all(r.model_version and "scorer" in r.model_version for r in rows)
    status = api.get("/api/v1/learning/status").json()
    assert status["labels"]["usable"] == 4 and status["labels"]["rejected"] == 2 and status["canTrain"]
    assert status["drift"]["features"]["status"] in ("ok", "watch", "alert", "unknown")


def test_too_few_labels_is_a_clear_conflict(api: TestClient) -> None:
    r = api.post("/api/v1/learning/train", headers=ANALYST)
    assert r.status_code == 409 and r.json()["code"] == "not_enough_labels"


def test_train_gate_four_eyes_promote_and_rollback(api: TestClient, db: Session) -> None:
    _label(api, accept=3, reject=1)
    trained = api.post("/api/v1/learning/train", headers=CONTROLLER)
    assert trained.status_code == 202, trained.text
    m = trained.json()
    assert m["status"] == "candidate" and m["gate"]["passed"], m["gate"]
    assert {c["name"] for c in m["gate"]["checks"]} >= {"No wrong auto-match on held-out decisions"}
    assert m["gate"]["shadow"]["run"] == "RUN-00001"  # re-scored (every suggestion here was already decided)

    version = m["version"]
    deny = api.post(f"/api/v1/learning/models/{version}/promote", headers=MANAGER)
    assert deny.status_code == 403 and deny.json()["code"] == "insufficient_authority"
    self_promote = api.post(f"/api/v1/learning/models/{version}/promote", headers=CONTROLLER)
    assert self_promote.status_code == 403 and self_promote.json()["code"] == "sod_model_change"
    ok = api.post(f"/api/v1/learning/models/{version}/promote", headers=DIRECTOR)
    assert ok.status_code == 200 and ok.json()["status"] == "active"

    status = api.get("/api/v1/learning/status").json()
    assert status["active"] == version and not status["activeIsShipped"]
    # The next run is scored by the tenant model, and says so in its audit record.
    run = api.post("/api/v1/recon/runs", headers=ANALYST).json()
    done = api.get(f"/api/v1/recon/runs/{run['id']}").json()
    assert done["status"] == "Completed" and version in done["engineVersion"]

    assert api.post("/api/v1/learning/rollback", headers=MANAGER).status_code == 403
    back = api.post("/api/v1/learning/rollback", headers=CONTROLLER)
    assert back.status_code == 200 and back.json()["active"] == "shipped"
    assert api.get("/api/v1/learning/status").json()["activeIsShipped"]
    actions = set(db.scalars(select(AuditEvent.action).where(AuditEvent.control == "MDL-01")))
    assert actions >= {"model.training_requested", "model.trained", "model.promoted", "model.rolled_back"}


def test_gate_failure_blocks_promotion(api: TestClient, db: Session) -> None:
    _label(api, accept=3, reject=1)
    m = api.post("/api/v1/learning/train", headers=CONTROLLER).json()
    from app.models import ScorerModel

    row = db.scalar(select(ScorerModel).where(ScorerModel.version == m["version"]))
    assert row is not None
    row.gate = {
        **row.gate,
        "passed": False,
        "checks": [{"name": "Golden medium: auto precision 100%", "ok": False, "detail": "0.9990"}],
    }
    db.flush()
    r = api.post(f"/api/v1/learning/models/{m['version']}/promote", headers=DIRECTOR)
    assert (
        r.status_code == 409 and r.json()["code"] == "gate_failed" and "Golden medium" in r.json()["detail"]
    )


def test_review_queue_can_serve_a_sample_for_learning(api: TestClient) -> None:
    every = api.get("/api/v1/recon/proposals?status=proposed&limit=5000", headers=DIRECTOR).json()
    sample = api.get(
        "/api/v1/recon/proposals?status=proposed&order=learning&limit=3", headers=DIRECTOR
    ).json()
    ids = [r["id"] for r in sample]
    assert len(ids) == len(set(ids)) == min(3, len(every)) and set(ids) <= {r["id"] for r in every}
