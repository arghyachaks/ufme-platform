"""Drift monitoring (Stage 3f): is the model still seeing the kind of pairs it was calibrated on?

Each model carries a reference profile of the pairs it scored on its calibration ledger (decile edges and the
share in each bin, per feature and on the score). Each run is compared with it by the population stability
index (PSI): < 0.10 stable, 0.10-0.25 watch, >= 0.25 alert. PSI only says the inputs moved; whether that hurts is
answered by reviewer outcomes (app.services.learning.outcome_drift) and, ultimately, by retraining + the gate.

    python -m app.engines.matching.drift      # (re)write the shipped scorer's reference profile
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from app.engines.matching import learned

PSI_WATCH, PSI_ALERT = 0.10, 0.25
MIN_PAIRS = 200
COLUMNS = [*learned.FEATURE_NAMES, "score"]


def _shares(edges: np.ndarray, col: np.ndarray) -> np.ndarray:
    return np.bincount(np.searchsorted(edges, col, side="right"), minlength=len(edges) + 1) / max(len(col), 1)


def profile(x: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    out: dict[str, Any] = {"n": len(x), "features": {}}
    for i, name in enumerate(COLUMNS):
        col = scores if name == "score" else x[:, i]
        edges = np.unique(np.quantile(col, np.linspace(0, 1, 11)[1:-1]).round(6))  # stored == used
        out["features"][name] = {
            "edges": edges.tolist(),
            "share": _shares(edges, col).round(6).tolist(),
        }
    return out


def psi(ref: dict[str, Any], col: np.ndarray) -> float:
    edges = np.asarray(ref["edges"], dtype=float)
    expected = np.clip(np.asarray(ref["share"], dtype=float), 1e-4, None)
    actual = np.clip(_shares(edges, col), 1e-4, None)
    return float(np.sum((actual - expected) * np.log(actual / expected)))


def compare(reference: dict[str, Any] | None, x: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    if not reference:
        return {"status": "unknown", "reason": "no reference profile"}
    if len(x) < MIN_PAIRS:
        return {"status": "unknown", "reason": "too few pairs", "pairs": len(x)}
    by_col = {
        name: round(psi(reference["features"][name], scores if name == "score" else x[:, i]), 4)
        for i, name in enumerate(COLUMNS)
        if name in reference["features"]
    }
    name, worst = max(by_col.items(), key=lambda kv: kv[1])
    status = "alert" if worst >= PSI_ALERT else "watch" if worst >= PSI_WATCH else "ok"
    top = dict(sorted(by_col.items(), key=lambda kv: -kv[1])[:5])
    return {"status": status, "max_psi": worst, "feature": name, "top": top, "pairs": len(x)}


def of_result(result: Any) -> tuple[np.ndarray, np.ndarray]:
    """Scorer rows and probabilities of a run's 1:1 predictions (what the model actually decided on)."""
    from app.engines.matching import adapt, engine

    rows, scores = [], []
    for p in result.predictions:
        d = result.details[p.line_ids]
        if isinstance(d, engine.PairResult):
            rows.append(adapt.row(d.features, d.a, d.b))
            scores.append(p.confidence)
    width = len(learned.FEATURE_NAMES)
    return np.asarray(rows, dtype=float).reshape(-1, width), np.asarray(scores, dtype=float)


def main() -> int:
    from app.engines.benchmark.scenarios import generate
    from app.engines.matching import engine
    from app.engines.matching.train import CALIBRATION_SEED

    data = json.loads(learned.ARTIFACT.read_text())
    learned.load.cache_clear()
    x, s = of_result(engine.run(generate(50_000, CALIBRATION_SEED).lines, keep_candidates=False))
    data.setdefault("meta", {})["reference_profile"] = profile(x, s)
    learned.ARTIFACT.write_text(json.dumps(data, separators=(",", ":")))
    print(f"reference profile from {len(x):,} pairs -> {learned.ARTIFACT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
