"""Does the learning loop learn?

    python -m app.engines.benchmark.learning_eval --budget 300 --out tmp/learning_eval.json

A simulated tenant books one entity (SG05) on settlement date, 8-14 days after its counterparties: a habit the
shipped scorer has never seen, so it sends correct pairs to review. Simulated reviewers label a budget of those
suggestions from ground truth (at random, as the product's queue does, or by uncertainty / closeness to the auto
threshold for comparison); the adapter is
trained on the labels; then both models score a *fresh* ledger from the same tenant (different seed) and the
unshifted golden holdouts, where nothing may get worse.

Result (2026-10-30, 300 decisions, 20K-line ledgers): auto rate on the fresh tenant ledger 87.1% before;
random 94.2%, uncertainty 90.1%, threshold 89.2%; precision 1.0 throughout; golden small unchanged.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import random
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

from app.engines.benchmark.evaluate import evaluate
from app.engines.benchmark.model import Dataset
from app.engines.benchmark.scenarios import generate, golden
from app.engines.matching import adapt, engine, learned

TENANT_ENTITY = "SG05"


def settlement_lag(ds: Dataset, entity: str = TENANT_ENTITY, seed: int = 0) -> Dataset:
    rnd = random.Random(seed)
    lines = []
    for line in ds.lines:
        if line.entity == entity:
            d = dt.timedelta(days=rnd.randint(8, 14))
            line = dataclasses.replace(
                line, value_date=line.value_date + d, posting_date=line.posting_date + d
            )
        lines.append(line)
    return dataclasses.replace(ds, lines=lines, name=f"{ds.name}+{entity}-settlement-lag")


def reviewer_labels(ds: Dataset, budget: int, strategy: str, scorer: str | None = None) -> adapt.LabelSet:
    """Simulated reviewers: accept a suggestion if it is the true pair, reject it otherwise."""
    from app.engines.matching.train import positives

    truth = positives(ds)
    result = engine.run(ds.lines, workers=None, keep_candidates=False, scorer=scorer)
    pool = []
    for p in result.predictions:
        d = result.details[p.line_ids]
        if p.decision != "suggest" or not isinstance(d, engine.PairResult):
            continue
        pool.append((p, d))
    if strategy == "uncertainty":  # closest to 50%
        pool.sort(key=lambda t: abs(t[0].confidence - 0.5))
    elif strategy == "threshold":  # just below the auto-match line
        pool.sort(key=lambda t: abs(t[0].confidence - 0.98))
    else:  # random: what the product's "teach the model" queue serves
        random.Random(1).shuffle(pool)
    chosen = pool[:budget]
    x = np.asarray([adapt.row(d.features, d.a, d.b) for _, d in chosen], dtype=np.float64)
    y = np.asarray([int(p.line_ids in truth) for p, _ in chosen], dtype=np.int8)
    within = np.asarray([d.features["amount_gap"] <= engine.POLICY_TOLERANCE for _, d in chosen])
    return adapt.LabelSet(x, y, within, [",".join(sorted(p.line_ids)) for p, _ in chosen])


def score(ds: Dataset, scorer: str | None) -> dict[str, Any]:
    r = evaluate(ds, engine.run(ds.lines, keep_candidates=True, scorer=scorer).predictions, "engine")
    return {
        "auto_rate": r.auto["rate"],
        "auto_precision": r.auto["precision"],
        "recall": r.pair["recall"],
        "ece": r.calibration_error,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--size", type=int, default=20_000)
    parser.add_argument("--budget", type=int, default=300, help="reviewer decisions available for training")
    parser.add_argument("--strategy", choices=["random", "uncertainty", "threshold", "all"], default="random")
    parser.add_argument("--golden", default="small,medium")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    started = time.time()
    base = json.loads(learned.ARTIFACT.read_text())
    labelled_ds = settlement_lag(generate(args.size, 51))
    fresh_ds = settlement_lag(generate(args.size, 52), seed=1)
    report: dict[str, Any] = {"size": args.size, "budget": args.budget, "tenant": "SG05 books 8-14 days late"}
    report["before"] = {"tenant_fresh": score(fresh_ds, None)}
    print("before", json.dumps(report["before"]))

    anchor = adapt.anchor_rows()
    work = Path(tempfile.mkdtemp(prefix="ufme-learn-"))
    strategies = ["random", "uncertainty", "threshold"] if args.strategy == "all" else [args.strategy]
    for strategy in strategies:
        labels = reviewer_labels(labelled_ds, args.budget, strategy)
        artifact = adapt.train_candidate(base, labels, f"eval-{strategy}", work, anchor=anchor)
        path = adapt.write(artifact, work)
        after: dict[str, Any] = {
            "labels": len(labels),
            "labels_positive": int(labels.y.sum()),
            "auto_threshold": round(artifact["auto_threshold"], 6),
            "holdout": artifact["meta"]["holdout"],
            "trained_seconds": artifact["meta"]["trained_seconds"],
            "tenant_fresh": score(fresh_ds, str(path)),
        }
        for name in filter(None, args.golden.split(",")):
            g = golden(name)
            after[f"golden_{name}"] = {"before": score(g, None), "after": score(g, str(path))}
        report[strategy] = after
        print(strategy, json.dumps(after))
    report["wall_s"] = round(time.time() - started, 1)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
