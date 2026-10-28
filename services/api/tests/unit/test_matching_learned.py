"""Stage 3d: learned scorer artifact, monotonic guarantees, risk-controlled threshold, explanations, fallback."""

import json

import numpy as np
import pytest

from app.engines.benchmark.evaluate import evaluate
from app.engines.benchmark.scenarios import golden
from app.engines.matching import engine, learned


@pytest.fixture
def model() -> learned.TreeModel:
    learned.load.cache_clear()
    m = learned.load()
    assert m is not None, "models/scorer.json must ship with the engine"
    return m


def _row(**overrides: float) -> list[float]:
    base = dict.fromkeys(learned.FEATURE_NAMES, 0.0)
    base.update(
        amount_gap_log=-4.0,
        amount_gap_usd_log=-1.0,
        amount_usd_log=4.0,
        date_gap_days=1.0,
        ref_similarity=0.5,
        ref_edit_distance=4.0,
        ambiguity=1.0,
        n_sources=1.0,
    )
    base.update(overrides)
    return [base[f] for f in learned.FEATURE_NAMES]


def test_artifact_is_well_formed(model: learned.TreeModel) -> None:
    data = json.loads(learned.ARTIFACT.read_text())
    assert data["features"] == learned.FEATURE_NAMES and data["monotonic"] == learned.MONOTONIC
    assert model.meta["export_matches_sklearn"] is True
    assert model.auto_threshold >= 0.98  # probability floor: never auto-match below 98% calibrated
    assert model.meta["auto_error_upper_bound"] <= model.meta["alpha"] == 0.005
    assert not set(model.meta["train_seeds"]) & {101, 202, 303}  # golden sets are a true holdout


@pytest.mark.parametrize(("feature", "direction"), [(f, m) for f, m in learned.FEATURES if m != 0])
def test_monotonic_in_every_constrained_feature(
    model: learned.TreeModel, feature: str, direction: int
) -> None:
    lo, hi = {"amount_gap_log": (-7, 0), "amount_gap_usd_log": (-2, 6), "date_gap_days": (0, 60)}.get(
        feature, (0, 10)
    )
    rng = np.random.default_rng(7)
    for _ in range(25):  # random contexts: the guarantee must hold everywhere, not just on average
        ctx = _row(
            ref_exact=float(rng.integers(0, 2)),
            ref_missing=float(rng.integers(0, 2)),
            ambiguity=float(rng.integers(1, 6)),
            date_gap_days=float(rng.integers(0, 20)),
        )
        grid = np.linspace(lo, hi, 15)
        x = np.asarray([ctx] * len(grid))
        x[:, learned.FEATURE_NAMES.index(feature)] = grid
        p = model.proba(x)
        diffs = np.diff(p) * direction
        assert (diffs >= -1e-9).all(), f"{feature} broke monotonicity: {p}"


def test_calibrated_and_better_than_hand_scorer_on_holdout(model: learned.TreeModel) -> None:
    ds = golden("small")
    report = evaluate(ds, engine.run(ds.lines).predictions, "engine")
    assert report.auto["precision"] == 1.0 and report.auto["rate"] >= 0.9
    assert report.calibration_error is not None and report.calibration_error < 0.02


def test_suggestions_carry_drivers_and_counterfactuals(model: learned.TreeModel) -> None:
    # Same reference, same day, but amounts 15% apart (a fee or withholding residual): a classic suggestion.
    residual = _row(
        amount_gap_log=float(np.log10(0.15)),
        amount_gap_usd_log=5.4,
        amount_usd_log=6.2,
        date_gap_days=0.0,
        ref_exact=1.0,
        ref_similarity=1.0,
        ref_edit_distance=0.0,
        n_sources=4.0,
    )
    e = learned.explain(model, residual, model.auto_threshold, within_policy=True, margin_ok=True)
    assert e["model"] == "scorer-v1" and e["drivers"] and all("log_odds" in d for d in e["drivers"])
    assert e["probability"] < model.auto_threshold
    assert any("amounts agreed" in c for c in e["counterfactuals"])
    assert any(d["label"].startswith("Amounts differ by 15.0") for d in e["drivers"])
    blocked = learned.explain(model, residual, model.auto_threshold, within_policy=False, margin_ok=False)
    assert len(blocked["blockers"]) == 2
    assert learned.describe("ref_conflict", 0) == "No conflicting references"
    assert learned.describe("date_gap_days", 3) == "Date difference 3 days"

    # On real suggestions, a reviewer is always told why it was not auto-matched.
    ds = golden("small")
    result = engine.run(ds.lines)
    explained = [d.explain for d in result.details.values() if getattr(d, "explain", None)]
    assert explained and all(
        x["blockers"] or x["counterfactuals"] or x["probability"] < model.auto_threshold for x in explained
    )


def test_hand_scorer_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UFME_SCORER", "hand")
    learned.load.cache_clear()
    try:
        assert learned.load() is None
        ds = golden("small")
        report = evaluate(ds, engine.run(ds.lines).predictions, "engine")
        assert report.auto["precision"] == 1.0  # the engine still works without the model
    finally:
        monkeypatch.delenv("UFME_SCORER")
        learned.load.cache_clear()
