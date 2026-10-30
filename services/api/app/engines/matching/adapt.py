"""Tenant adaptation (Stage 3f): learn from reviewer decisions without retraining from scratch.

A full retrain takes ~25 minutes and needs the synthetic corpus. A tenant's labels say something narrower: "on
our ledgers, pairs like this are (not) the same transaction". So the shipped scorer is kept as it is and a small
additive *adapter* is boosted on top of it (Newton steps of logistic loss, starting from the shipped model's
log-odds), on the tenant's labels plus a synthetic anchor set that stops it forgetting the general case.

Safety properties carried over from 3d:
- every adapter tree has the same monotonic constraints, so the sum stays monotone (a closer amount never
  lowers confidence, a conflicting reference never raises it);
- the result is the same flat JSON artifact (trees appended), so runtime, explanations and audit are unchanged;
- calibration is refitted and the auto threshold is re-proven (Clopper-Pearson, alpha 0.5%) before the model
  can even be proposed; promotion is a separate, gated, audited step (app.services.learning).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from app.engines.benchmark.model import Line
from app.engines.matching import learned

ROUNDS = 40
LEARNING_RATE = 0.15
MAX_DEPTH = 3
MIN_LEAF = 20
LABEL_WEIGHT = 20.0  # one reviewer decision outweighs one synthetic anchor pair
MIN_LABELS = 30  # below this the adapter can't be validated, so it isn't trained
POLICY_TOLERANCE = 0.005  # mirror of engine.POLICY_TOLERANCE (kept here to avoid an import cycle)


def row(features: dict[str, Any], a: Line, b: Line) -> list[float]:
    """The scorer's feature vector for a pair, from the features the engine recorded for it."""
    same_account = bool(a.account) and a.account == b.account
    return learned.vectorize(features, a.amount_usd, same_account)


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35, 35)))


def fit(
    base: dict[str, Any],
    x_labels: np.ndarray,
    y_labels: np.ndarray,
    x_anchor: np.ndarray,
    y_anchor: np.ndarray,
    rounds: int = ROUNDS,
    learning_rate: float = LEARNING_RATE,
) -> tuple[list[dict[str, Any]], float]:
    """Adapter trees (already shrunk by the learning rate) and the baseline shift to add to `base`."""
    from sklearn.ensemble import HistGradientBoostingRegressor

    from app.engines.matching.train import export

    model = learned.TreeModel.from_json(base)
    x = np.vstack([x_labels, x_anchor])
    y = np.concatenate([y_labels, y_anchor]).astype(np.float64)
    w = np.concatenate([np.full(len(y_labels), LABEL_WEIGHT), np.ones(len(y_anchor))])
    raw = model.raw(x)
    trees: list[dict[str, Any]] = []
    shift = 0.0
    for _ in range(rounds):
        p = _sigmoid(raw)
        h = np.clip(p * (1 - p), 1e-4, None)
        z = np.clip((y - p) / h, -4.0, 4.0)  # Newton step target for logistic loss
        reg = HistGradientBoostingRegressor(
            max_iter=1,
            learning_rate=1.0,
            max_depth=MAX_DEPTH,
            min_samples_leaf=MIN_LEAF,
            l2_regularization=1.0,
            monotonic_cst=learned.MONOTONIC,
            early_stopping=False,
            random_state=0,
        )
        reg.fit(x, z, sample_weight=w * h)
        (tree,), b0 = export(reg)
        for key in ("value", "node_value"):
            tree[key] = [learning_rate * v for v in tree[key]]
        trees.append(tree)
        shift += learning_rate * b0
        raw = raw + learning_rate * reg.predict(x)  # predict() = b0 + tree(x)
    return trees, shift


def combine(base: dict[str, Any], trees: list[dict[str, Any]], shift: float) -> dict[str, Any]:
    """Base artifact + adapter: one additive ensemble, so the runtime needs nothing new."""
    return {
        **base,
        "trees": [*base["trees"], *trees],
        "baseline": float(base["baseline"]) + shift,
        "adapter_trees": len(trees),
        "base_trees": len(base["trees"]),
    }


@dataclass
class LabelSet:
    """Reviewer decisions as scorer rows. `within_policy` mirrors the engine's tolerance gate: a label outside
    it can never become an auto-match whatever the model says, so it can't count against the threshold."""

    x: np.ndarray
    y: np.ndarray
    within_policy: np.ndarray
    ids: list[str]

    def __len__(self) -> int:
        return len(self.y)

    def split(self, holdout: float = 0.25, seed: int = 0) -> tuple[LabelSet, LabelSet]:
        """Stratified by label so the holdout always has both outcomes when the data does."""
        rng = np.random.default_rng(seed)
        test = np.zeros(len(self.y), dtype=bool)
        for cls in (0, 1):
            idx = np.flatnonzero(self.y == cls)
            rng.shuffle(idx)
            test[idx[: math.ceil(len(idx) * holdout)]] = True
        return self._take(~test), self._take(test)

    def _take(self, mask: np.ndarray) -> LabelSet:
        return LabelSet(
            self.x[mask],
            self.y[mask],
            self.within_policy[mask],
            [i for i, m in zip(self.ids, mask, strict=True) if m],
        )


def label_metrics(model: learned.TreeModel, labels: LabelSet) -> dict[str, Any]:
    """How a model treats reviewer decisions it was not trained on."""
    if len(labels) == 0:
        return {"labels": 0}
    p = model.proba(labels.x)
    auto = (p >= model.auto_threshold) & labels.within_policy
    eps = 1e-6
    logloss = float(-np.mean(labels.y * np.log(p + eps) + (1 - labels.y) * np.log(1 - p + eps)))
    return {
        "labels": len(labels),
        "positives": int(labels.y.sum()),
        "log_loss": round(logloss, 4),
        "accuracy": round(float(np.mean((p >= 0.5) == (labels.y == 1))), 4),
        "would_auto_correct": int((auto & (labels.y == 1)).sum()),
        "would_auto_wrong": int((auto & (labels.y == 0)).sum()),  # must be 0 for promotion
    }


def write(artifact: dict[str, Any], directory: Path) -> Path:
    """Model files are immutable and named by version, so the engine's per-path cache is always correct."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{artifact['version']}.json"
    if not path.exists():
        import json

        path.write_text(json.dumps(artifact, separators=(",", ":")))
    return path


ANCHOR_SEED = 41  # synthetic anchor ledger: not a training, calibration or golden seed
ANCHOR_SIZE = 20_000
ANCHOR_ROWS = 150_000
CALIBRATION_SIZE = 50_000


def anchor_rows(size: int = ANCHOR_SIZE, rows: int = ANCHOR_ROWS) -> tuple[np.ndarray, np.ndarray]:
    from app.engines.benchmark.scenarios import generate
    from app.engines.matching.train import collect

    x, y = collect(generate(size, ANCHOR_SEED))
    if len(y) > rows:  # keep every positive, subsample the (plentiful) negatives
        rng = np.random.default_rng(0)
        pos = np.flatnonzero(y == 1)
        neg = rng.choice(np.flatnonzero(y == 0), size=max(rows - len(pos), 0), replace=False)
        keep = np.sort(np.concatenate([pos, neg]))
        x, y = x[keep], y[keep]
    return x, y


def train_candidate(
    base: dict[str, Any],
    labels: LabelSet,
    version: str,
    workdir: Path,
    calibration_size: int = CALIBRATION_SIZE,
    anchor: tuple[np.ndarray, np.ndarray] | None = None,
) -> dict[str, Any]:
    """Base scorer + adapter trained on 75% of the labels, recalibrated, threshold re-proven; the other 25% of
    the labels are kept back to judge it against the active model (see `compare`)."""
    import time

    from app.engines.benchmark.scenarios import generate
    from app.engines.matching.train import (
        ALPHA,
        CALIBRATION_SEED,
        PROBABILITY_FLOOR,
        calibration_ece,
        collect,
        fit_isotonic,
        risk_threshold,
    )

    # Reviewers mostly accept (suggestions are usually right), so labels may be all one outcome: the synthetic
    # anchor supplies the other side of the boundary.
    if len(labels) < MIN_LABELS:
        raise ValueError(f"need at least {MIN_LABELS} reviewer decisions, have {len(labels)}")
    started = time.time()
    train, holdout = labels.split()
    x_anchor, y_anchor = anchor if anchor is not None else anchor_rows()
    trees, shift = fit(base, train.x, train.y, x_anchor, y_anchor)
    artifact = combine({k: v for k, v in base.items() if k != "meta"}, trees, shift)
    artifact["version"] = version

    # Recalibrate on a synthetic ledger with known truth plus the tenant's own (training) labels.
    calib_ds = generate(calibration_size, CALIBRATION_SEED)
    x_cal, y_cal = collect(calib_ds)
    draft = learned.TreeModel.from_json({**artifact, "auto_threshold": 1.0})
    raw = np.concatenate([draft.raw(x_cal), draft.raw(train.x)])
    ys = np.concatenate([y_cal, train.y]).astype(float)
    weight = np.concatenate([np.ones(len(y_cal)), np.full(len(train.y), LABEL_WEIGHT / 4)])
    cal_x, cal_y = fit_isotonic(raw, ys, weight)
    artifact["calibration"] = {"x": cal_x.tolist(), "y": cal_y.tolist()}

    best, eligible, reference = risk_threshold(calib_ds, artifact, workdir / f"{version}.measure.json")
    artifact["auto_threshold"] = max(best[0], PROBABILITY_FLOOR)
    model = learned.TreeModel.from_json(artifact)
    artifact["meta"] = {
        "base_version": base.get("version", "scorer"),
        "adapter": {"rounds": len(trees), "learning_rate": LEARNING_RATE, "max_depth": MAX_DEPTH},
        "labels_train": len(train),
        "labels_holdout": len(holdout),
        "alpha": ALPHA,
        "probability_floor": PROBABILITY_FLOOR,
        "conformal_threshold": round(best[0], 6),
        "auto_eligible_calibration": eligible,
        "auto_covered_calibration": best[1],
        "auto_errors_calibration": best[2],
        "auto_error_upper_bound": round(best[3], 6),
        "candidate_ece": round(calibration_ece(model.proba(x_cal), y_cal.astype(float)), 5),
        "holdout": label_metrics(model, holdout),
        "trained_seconds": round(time.time() - started, 1),
        "reference_profile": reference,
    }
    return artifact


def compare(
    candidate: learned.TreeModel, active: learned.TreeModel | None, holdout: LabelSet
) -> dict[str, Any]:
    """Both models on the reviewer decisions the candidate never saw."""
    return {
        "candidate": label_metrics(candidate, holdout),
        "active": label_metrics(active, holdout) if active is not None else None,
    }
