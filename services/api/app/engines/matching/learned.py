"""Learned pair scorer (Stage 3d): monotonic gradient-boosted trees + isotonic calibration + a risk-controlled
auto-match threshold.

The model is trained offline (`python -m app.engines.matching.train`) and shipped as plain JSON arrays, so the
runtime needs only numpy: no scikit-learn, no pickles, no version coupling. Inference is vectorised per entity
pair. If the artifact is missing (or UFME_SCORER=hand) the engine keeps the hand-set log-odds scorer.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

ARTIFACT = Path(__file__).resolve().parent / "models" / "scorer.json"

# (feature, monotonic direction): +1 more of it can only raise the score, -1 only lower it, 0 free.
# Monotonicity is what makes a learned scorer safe to audit: a closer amount never lowers confidence.
FEATURES: list[tuple[str, int]] = [
    ("amount_gap_log", -1),  # log10 of the relative amount gap
    ("amount_gap_usd_log", -1),
    ("amount_usd_log", 0),  # size of the item (big items are rarer, decoys cluster small)
    ("date_gap_days", -1),
    ("ref_exact", 1),
    ("ref_canonical_exact", 1),
    ("ref_affix", 1),
    ("ref_in_description", 1),
    ("digits_equal", 1),
    ("ref_typo", 1),
    ("ref_similarity", 1),
    ("ref_edit_distance", -1),
    ("ref_conflict", -1),
    ("ref_missing", 0),
    ("ambiguity", -1),
    ("n_sources", 1),
    ("same_account", 1),
    ("desc_similarity", 1),  # 3e: descriptions describe the same kind of transaction
    ("text_ambiguity", -1),  # 3e: look-alikes that also share the description
]
FEATURE_NAMES = [f for f, _ in FEATURES]
MONOTONIC = [m for _, m in FEATURES]


def vectorize(f: dict[str, Any], amount_usd: float, same_account: bool) -> list[float]:
    gap = max(float(f["amount_gap"]), 1e-7)
    return [
        math.log10(gap),
        math.log10(max(float(f["amount_gap_usd"]), 0.01)),
        math.log10(max(abs(amount_usd), 1.0)),
        float(min(f["date_gap_days"], 60)),
        float(f["ref_exact"]),
        float(f["ref_canonical_exact"]),
        float(f["ref_affix"]),
        float(f["ref_in_description"]),
        float(f["digits_equal"]),
        float(f["ref_edit_distance"] == 1 and f["ref_strong"]),
        float(f["ref_similarity"]),
        float(min(f["ref_edit_distance"], 10)),
        float(f["ref_conflict"]),
        float(f["ref_missing"]),
        float(min(f["ambiguity"], 10)),
        float(len(f.get("blocking", []))),
        float(same_account),
        float(f.get("desc_similarity", 0.0)),
        float(min(f.get("text_ambiguity", 1), 10)),
    ]


@dataclass
class TreeModel:
    """Additive tree ensemble in flat arrays (sklearn HistGradientBoosting layout), plus calibration."""

    trees: list[dict[str, np.ndarray]]
    baseline: float
    learning_rate: float
    cal_x: np.ndarray  # isotonic calibration: raw log-odds -> probability, piecewise linear
    cal_y: np.ndarray
    auto_threshold: float  # calibrated probability above which auto-matching is risk-controlled
    meta: dict[str, Any]

    def raw(self, x: np.ndarray) -> np.ndarray:
        """Raw additive score (log-odds before calibration) for rows of x, vectorised over rows."""
        out = np.full(x.shape[0], self.baseline, dtype=np.float64)
        rows = np.arange(x.shape[0])
        for t in self.trees:
            node = np.zeros(x.shape[0], dtype=np.int64)
            for _ in range(int(t["depth"][0])):
                leaf = t["is_leaf"][node]
                if leaf.all():
                    break
                go_left = x[rows, t["feature"][node]] <= t["threshold"][node]
                nxt = np.where(go_left, t["left"][node], t["right"][node])
                node = np.where(leaf, node, nxt)
            out += t["value"][node]
        return out

    def proba(self, x: np.ndarray) -> np.ndarray:
        return np.interp(self.raw(x), self.cal_x, self.cal_y)

    def contributions(self, row: list[float]) -> dict[str, float]:
        """Per-feature attribution of one prediction (path attribution over the trees), in raw log-odds."""
        contrib = dict.fromkeys(FEATURE_NAMES, 0.0)
        for t in self.trees:
            node = 0
            while not t["is_leaf"][node]:
                feat = int(t["feature"][node])
                child = int(t["left"][node] if row[feat] <= t["threshold"][node] else t["right"][node])
                contrib[FEATURE_NAMES[feat]] += float(t["node_value"][child] - t["node_value"][node])
                node = child
        return {k: round(v, 3) for k, v in contrib.items() if abs(v) >= 0.005}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> TreeModel:
        trees = []
        for t in data["trees"]:
            trees.append(
                {
                    "feature": np.asarray(t["feature"], dtype=np.int64),
                    "threshold": np.asarray(t["threshold"], dtype=np.float64),
                    "left": np.asarray(t["left"], dtype=np.int64),
                    "right": np.asarray(t["right"], dtype=np.int64),
                    "is_leaf": np.asarray(t["is_leaf"], dtype=bool),
                    "value": np.asarray(t["value"], dtype=np.float64),
                    "node_value": np.asarray(t["node_value"], dtype=np.float64),
                    "depth": np.asarray([t["depth"]], dtype=np.int64),
                }
            )
        return cls(
            trees=trees,
            baseline=float(data["baseline"]),
            learning_rate=float(data.get("learning_rate", 1.0)),
            cal_x=np.asarray(data["calibration"]["x"], dtype=np.float64),
            cal_y=np.asarray(data["calibration"]["y"], dtype=np.float64),
            auto_threshold=float(data["auto_threshold"]),
            meta={**data.get("meta", {}), "version": data.get("version", "scorer")},
        )


@lru_cache(maxsize=4)
def load(path: str | None = None) -> TreeModel | None:
    """The shipped scorer, or (3f) a tenant's promoted model at `path`. Cached per path: a model file is
    immutable once written (its name carries its version), so a cached copy never goes stale."""
    artifact = Path(path) if path else ARTIFACT
    if os.environ.get("UFME_SCORER", "learned") == "hand" or not artifact.exists():
        return None
    data = json.loads(artifact.read_text())
    if data.get("features") != FEATURE_NAMES:
        return None  # artifact from another feature layout: never score with mismatched columns
    return TreeModel.from_json(data)


_IDX = {name: i for i, name in enumerate(FEATURE_NAMES)}
# Counterfactual edits a reviewer can act on: (label, {feature: value}).
_WHAT_IFS: list[tuple[str, dict[str, float]]] = [
    (
        "both sides carried the same reference",
        {"ref_exact": 1, "ref_missing": 0, "ref_similarity": 1, "ref_edit_distance": 0, "ref_conflict": 0},
    ),
    ("no other open item had a near-identical amount", {"ambiguity": 1}),
    ("the value dates were the same", {"date_gap_days": 0}),
    ("the amounts agreed to the cent", {"amount_gap_log": -7.0, "amount_gap_usd_log": -2.0}),
]
_LABEL = {
    "amount_gap_log": "Amount agreement",
    "amount_gap_usd_log": "Amount difference (USD)",
    "amount_usd_log": "Item size",
    "date_gap_days": "Date difference",
    "ref_exact": "Exact reference",
    "ref_canonical_exact": "Reference after OCR clean-up",
    "ref_affix": "Reference with prefix/suffix",
    "ref_in_description": "Reference in description",
    "digits_equal": "Same reference digits",
    "ref_typo": "Reference one typo apart",
    "ref_similarity": "Reference similarity",
    "ref_edit_distance": "Reference edits",
    "ref_conflict": "Conflicting references",
    "ref_missing": "Reference missing",
    "ambiguity": "Look-alike candidates",
    "n_sources": "Found by several searches",
    "same_account": "Same GL account",
    "desc_similarity": "Description match",
    "text_ambiguity": "Look-alikes with the same description",
}


_FLAGS = {
    "ref_exact": ("Exact reference match", "References not identical"),
    "ref_canonical_exact": ("References equal after OCR clean-up", "Not an OCR variant"),
    "ref_affix": ("Reference differs only by a prefix/suffix", "No prefix/suffix variant"),
    "ref_in_description": ("Reference found in the description", "Reference not in description"),
    "digits_equal": ("Same reference digits", "Reference digits differ"),
    "ref_typo": ("References one typo apart", "Not a one-typo difference"),
    "ref_conflict": ("Conflicting references", "No conflicting references"),
    "ref_missing": ("Reference missing on one side", "Both sides have a reference"),
    "same_account": ("Same GL account", "Different GL accounts"),
}


def describe(feature: str, value: float) -> str:
    """A driver in words, with the value that drove it."""
    if feature in _FLAGS:
        return _FLAGS[feature][0 if value >= 0.5 else 1]
    if feature == "amount_gap_log":
        return f"Amounts differ by {100 * 10**value:.3f}%"
    if feature == "amount_gap_usd_log":
        return f"Amount difference ${10**value:,.2f}"
    if feature == "amount_usd_log":
        return f"Item size ${10**value:,.0f}"
    if feature == "date_gap_days":
        return f"Date difference {int(value)} day{'s' if int(value) != 1 else ''}"
    if feature == "ref_similarity":
        return f"Reference similarity {100 * value:.0f}%"
    if feature == "ref_edit_distance":
        return (
            "References differ by 10+ characters" if value >= 10 else f"References {int(value)} edit(s) apart"
        )
    if feature == "ambiguity":
        return f"{int(value)} candidate(s) with a near-identical amount"
    if feature == "desc_similarity":
        return f"Descriptions {100 * value:.0f}% alike"
    if feature == "text_ambiguity":
        return f"{int(value)} look-alike(s) with the same description"
    if feature == "n_sources":
        return f"Found by {int(value)} independent search(es)"
    return _LABEL.get(feature, feature)


def explain(
    model: TreeModel, row: list[float], threshold: float, within_policy: bool, margin_ok: bool
) -> dict[str, Any]:
    """Why the model scored a suggestion as it did, and what would have made it an auto-match."""
    p = float(model.proba(np.asarray([row]))[0])
    drivers = sorted(model.contributions(row).items(), key=lambda kv: -abs(kv[1]))[:6]
    blockers: list[str] = []
    if not within_policy:
        blockers.append("amount difference is outside the 0.5% tolerance policy")
    if not margin_ok:
        blockers.append("another candidate scores almost as high, so a person should choose")
    what_ifs: list[str] = []
    if p < threshold:
        for label, edit in _WHAT_IFS:
            alt = list(row)
            for k, v in edit.items():
                alt[_IDX[k]] = v
            p_alt = float(model.proba(np.asarray([alt]))[0])
            if p_alt >= threshold:
                what_ifs.append(f"would be auto-matched if {label} ({100 * p_alt:.1f}%)")
    return {
        "model": model.meta.get("version", "scorer"),
        "probability": round(p, 6),
        "auto_threshold": round(threshold, 6),
        "drivers": [{"label": describe(k, row[_IDX[k]]), "feature": k, "log_odds": v} for k, v in drivers],
        "blockers": blockers,
        "counterfactuals": what_ifs,
    }
