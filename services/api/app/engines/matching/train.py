"""Train the learned pair scorer (Stage 3d) and write app/engines/matching/models/scorer.json.

    python -m app.engines.matching.train            # needs scikit-learn (dev only); runtime needs only numpy

Data: synthetic ledgers from the scenario generator with their own seeds. The golden benchmark sets
(seeds 101/202/303) are never used for training or calibration, so the gate stays an honest holdout.
Later (Stage 3f) reviewer labels from match_label join the same pipeline.

Steps: features for every candidate pair → monotonic gradient-boosted trees → isotonic calibration on a separate
ledger → risk-controlled auto threshold: the lowest probability at which the 95% upper bound of the error rate
of auto-matched pairs (Clopper-Pearson) stays below 0.5%.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from app.engines.benchmark.evaluate import _canonical
from app.engines.benchmark.model import Dataset
from app.engines.benchmark.scenarios import generate
from app.engines.matching import candidates as cand
from app.engines.matching import engine, learned

TRAIN_SEEDS = (11, 12, 13)
CALIBRATION_SEED = 21
SIZE = 100_000
ALPHA = 0.005  # max auto-match error rate the threshold must guarantee
CONFIDENCE = 0.95
PROBABILITY_FLOOR = 0.98  # never auto-match below this calibrated probability, whatever the bound allows


def positives(ds: Dataset) -> set[frozenset[str]]:
    """True 1:1 pairs, counting an exact duplicate's twin as equally correct."""
    lines = {x.id: x for x in ds.lines}
    pos = {
        g.line_ids
        for g in ds.truth
        if len(g.line_ids) == 2 and {lines[i].side for i in g.line_ids} == {"A", "B"}
    }
    for g in ds.truth:
        if g.twin_of:
            extra = next(iter(g.line_ids))
            for p in list(pos):
                if g.twin_of in p:
                    pos.add(frozenset({extra, *(p - {g.twin_of})}))
    return pos


def collect(ds: Dataset) -> tuple[np.ndarray, np.ndarray]:
    pos = positives(ds)
    by_pair: dict[tuple[str, str], tuple[list[cand.Prepared], list[cand.Prepared]]] = defaultdict(
        lambda: ([], [])
    )
    for line in ds.lines:
        by_pair[line.pair][0 if line.side == "A" else 1].append(cand.prepare(line))
    rows: list[list[float]] = []
    labels: list[int] = []
    for key in sorted(by_pair):
        _, _, entries = engine.candidates_with_features(*by_pair[key])
        for a, b, f in entries:
            rows.append(engine.learned_row(a, b, f))
            labels.append(int(frozenset((a.line.id, b.line.id)) in pos))
    return np.asarray(rows, dtype=np.float64), np.asarray(labels, dtype=np.int8)


def export(est: Any) -> tuple[list[dict[str, Any]], float]:
    """Flatten sklearn HistGradientBoosting predictors into plain arrays (no pickle, no sklearn at runtime)."""
    trees = []
    for (predictor,) in est._predictors:
        nodes = predictor.nodes
        n = len(nodes)
        is_leaf = nodes["is_leaf"].astype(bool)
        value = nodes["value"].astype(float)
        left, right = nodes["left"].astype(int), nodes["right"].astype(int)
        # Node values for path attribution: count-weighted mean of the leaves below (consistent with leaf scale).
        node_value = value.copy()
        counts = nodes["count"].astype(float)
        for i in range(n - 1, -1, -1):
            if not is_leaf[i]:
                lc, rc = counts[left[i]], counts[right[i]]
                node_value[i] = (node_value[left[i]] * lc + node_value[right[i]] * rc) / max(lc + rc, 1.0)
        trees.append(
            {
                "feature": nodes["feature_idx"].astype(int).tolist(),
                "threshold": nodes["num_threshold"].astype(float).tolist(),
                "left": left.tolist(),
                "right": right.tolist(),
                "is_leaf": is_leaf.tolist(),
                "value": value.tolist(),
                "node_value": node_value.tolist(),
                "depth": int(nodes["depth"].max()) + 1,
            }
        )
    return trees, float(np.ravel(est._baseline_prediction)[0])


def clopper_pearson_upper(errors: int, n: int, conf: float = CONFIDENCE) -> float:
    from scipy.stats import beta

    return 1.0 if n == 0 else (1.0 if errors >= n else float(beta.ppf(conf, errors + 1, n - errors)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--size", type=int, default=SIZE)
    parser.add_argument("--out", type=Path, default=learned.ARTIFACT)
    args = parser.parse_args()

    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.isotonic import IsotonicRegression

    started = time.time()
    xs, ys = [], []
    for seed in TRAIN_SEEDS:
        x, y = collect(generate(args.size, seed))
        xs.append(x)
        ys.append(y)
        print(f"seed {seed}: {len(y):,} candidate pairs, {int(y.sum()):,} true")
    x_train, y_train = np.vstack(xs), np.concatenate(ys)

    est = HistGradientBoostingClassifier(
        max_iter=120,
        learning_rate=0.1,
        max_depth=5,
        min_samples_leaf=40,
        l2_regularization=1.0,
        monotonic_cst=learned.MONOTONIC,
        early_stopping=False,
        random_state=0,
    )
    est.fit(x_train, y_train)
    trees, baseline = export(est)
    print(f"trained {len(trees)} trees on {len(y_train):,} pairs in {time.time() - started:.0f}s")

    # Calibration on a separate ledger: isotonic map from raw score to probability.
    calib_ds = generate(args.size, CALIBRATION_SEED)
    x_cal, y_cal = collect(calib_ds)
    draft = learned.TreeModel.from_json(
        {
            "trees": trees,
            "baseline": baseline,
            "calibration": {"x": [-50, 50], "y": [0, 1]},
            "auto_threshold": 1.0,
        }
    )
    raw_cal = draft.raw(x_cal)
    exported_ok = np.allclose(raw_cal, est.decision_function(x_cal), atol=1e-6)
    iso = IsotonicRegression(out_of_bounds="clip", y_min=1e-6, y_max=1 - 1e-6).fit(raw_cal, y_cal)
    cal_x = np.asarray(iso.X_thresholds_, dtype=float)
    cal_y = np.asarray(iso.y_thresholds_, dtype=float)
    if len(cal_x) > 400:  # keep the artifact small; piecewise-linear interpolation between kept knots
        keep = np.unique(np.linspace(0, len(cal_x) - 1, 400).astype(int))
        cal_x, cal_y = cal_x[keep], cal_y[keep]

    # Risk-controlled auto threshold on the calibration ledger, measured on what the engine would really
    # auto-match (assigned, within policy, clear margin), not on raw candidates.
    artifact = {
        "version": "scorer-v1",
        "features": learned.FEATURE_NAMES,
        "monotonic": learned.MONOTONIC,
        "trees": trees,
        "baseline": baseline,
        "learning_rate": 0.1,
        "calibration": {"x": cal_x.tolist(), "y": cal_y.tolist()},
        "auto_threshold": 1.01,  # measurement pass: nothing auto, so groups claim their lines exactly as in production
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(artifact))
    learned.load.cache_clear()
    result = engine.run(calib_ds.lines, workers=1)
    eligible = []
    for p in result.predictions:
        d = result.details[p.line_ids]
        if len(p.line_ids) != 2 or not isinstance(d, engine.PairResult):
            continue
        within_policy = d.features["amount_gap"] <= engine.POLICY_TOLERANCE
        alts = result.alternatives.get(p.line_ids, [])
        margin_ok = (
            not alts or d.log_odds - math.log(max(alts[0][1], 1e-9) / max(1 - alts[0][1], 1e-9)) >= 1.0
        )
        if within_policy and margin_ok:  # the engine's other auto conditions, independent of the threshold
            eligible.append(p)
    preds = _canonical(calib_ds, eligible)
    truth2 = positives(calib_ds)
    scored = sorted(((p.confidence, p.line_ids in truth2) for p in preds), reverse=True)
    threshold, errors = 1.0, 0
    best = (1.0, 0, 0, 0.0)
    for covered, (conf, ok) in enumerate(scored, start=1):
        errors += 0 if ok else 1
        ub = clopper_pearson_upper(errors, covered)
        if ub <= ALPHA:
            best = (conf, covered, errors, ub)
    threshold = max(best[0], PROBABILITY_FLOOR)  # proven bound AND a confidence a reviewer would accept
    artifact["auto_threshold"] = threshold

    # Calibration quality on the calibration ledger's candidate pairs (10-bin ECE).
    p_cal = np.interp(raw_cal, cal_x, cal_y)
    bins = np.minimum((p_cal * 10).astype(int), 9)
    ece = float(
        sum(
            abs(p_cal[bins == k].mean() - y_cal[bins == k].mean()) * (bins == k).mean()
            for k in range(10)
            if (bins == k).any()
        )
    )
    artifact["meta"] = {
        "train_seeds": list(TRAIN_SEEDS),
        "calibration_seed": CALIBRATION_SEED,
        "size": args.size,
        "train_pairs": len(y_train),
        "train_positive": int(y_train.sum()),
        "trees": len(trees),
        "alpha": ALPHA,
        "probability_floor": PROBABILITY_FLOOR,
        "conformal_threshold": round(best[0], 6),
        "confidence": CONFIDENCE,
        "auto_eligible_calibration": len(scored),
        "auto_covered_calibration": best[1],
        "auto_errors_calibration": best[2],
        "auto_error_upper_bound": round(best[3], 6),
        "candidate_ece": round(ece, 5),
        "export_matches_sklearn": bool(exported_ok),
        "trained_seconds": round(time.time() - started, 1),
    }
    args.out.write_text(json.dumps(artifact, separators=(",", ":")))
    learned.load.cache_clear()
    print(json.dumps(artifact["meta"], indent=2))
    print(f"auto threshold {threshold:.6f} -> {args.out}")
    return 0 if exported_ok and math.isfinite(threshold) else 1


if __name__ == "__main__":
    raise SystemExit(main())
