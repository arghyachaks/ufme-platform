"""Measure the residual classifier and the local LLM judge against ground truth.

    python -m app.engines.benchmark.judge_eval                    # rule classifier only (fast, any machine)
    python -m app.engines.benchmark.judge_eval --llm 300 --out r.json   # + LLM judge on a sample (needs Ollama)

Uses its own seed (not a golden set). Ground truth: the scenario that produced each suggested pair.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from app.engines.benchmark.scenarios import generate
from app.engines.matching import engine, residual

EXPECTED = {
    "withholding_tax": "withholding_tax",
    "bank_fee": "bank_fee",
    "fx_source_mismatch": "fx_rate_difference",
    "fx_rounding": "rounding",
}


def suggestions(size: int, seed: int) -> list[dict[str, Any]]:
    ds = generate(size, seed)
    truth_of = {i: g for g in ds.truth for i in g.line_ids}
    result = engine.run(ds.lines, workers=1, keep_candidates=False)
    out = []
    for p in result.predictions:
        if p.decision != "suggest" or len(p.line_ids) != 2:
            continue
        d = result.details[p.line_ids]
        if not isinstance(d, engine.PairResult):
            continue
        ga, gb = truth_of[d.a.id], truth_of[d.b.id]
        same = ga is gb
        out.append(
            {
                "a": d.a,
                "b": d.b,
                "scenario": ga.scenario if same else "wrong_pair",
                "same_transaction": same,
                "expected": EXPECTED.get(ga.scenario) if same else None,
                "residual": residual.classify(d.a, d.b),
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--size", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=31)
    parser.add_argument(
        "--llm", type=int, default=0, help="judge this many sampled suggestions with the local model"
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    rows = suggestions(args.size, args.seed)
    labelled = [r for r in rows if r["expected"]]
    decided = [r for r in labelled if r["residual"].cause != "fee_or_fx"]
    rule_ok = sum(r["residual"].cause == r["expected"] for r in decided)
    flagged_ambiguous = len(labelled) - len(decided)
    by_scen: dict[str, Counter[str]] = defaultdict(Counter)
    for r in labelled:
        by_scen[r["scenario"]][r["residual"].cause] += 1
    report: dict[str, Any] = {
        "seed": args.seed,
        "size": args.size,
        "suggestions": len(rows),
        "wrong_pairs_suggested": sum(not r["same_transaction"] for r in rows),
        "rule": {
            "labelled": len(labelled),
            "accuracy_when_decided": round(rule_ok / len(decided), 4) if decided else None,
            "flagged_ambiguous": flagged_ambiguous,
            "coverage": round(len(decided) / len(labelled), 4) if labelled else None,
            "confusion": {k: dict(v) for k, v in sorted(by_scen.items())},
        },
    }
    print(json.dumps(report, indent=2))

    if args.llm:
        from app.services.judge import judge

        rng = random.Random(7)
        sample = rng.sample(rows, min(args.llm, len(rows)))
        n = cause_ok = cause_n = same_ok = agree = 0
        latencies: list[float] = []
        mistakes: list[dict[str, Any]] = []
        started = time.time()
        for r in sample:
            v = judge(r["a"], r["b"], r["residual"])
            if v is None:
                continue
            n += 1
            latencies.append(v.seconds)
            same_ok += v.same_transaction == r["same_transaction"]
            agree += v.cause == r["residual"].cause
            if r["expected"]:
                cause_n += 1
                cause_ok += v.cause == r["expected"]
                if v.cause != r["expected"] and len(mistakes) < 8:
                    mistakes.append({"expected": r["expected"], "judge": v.cause, "note": v.note})
        latencies.sort()
        report["llm"] = {
            "judged": n,
            "unavailable": len(sample) - n,
            "cause_accuracy": round(cause_ok / cause_n, 4) if cause_n else None,
            "same_transaction_accuracy": round(same_ok / n, 4) if n else None,
            "agrees_with_rule": round(agree / n, 4) if n else None,
            "latency_p50_s": round(latencies[len(latencies) // 2], 2) if latencies else None,
            "latency_p95_s": round(latencies[int(len(latencies) * 0.95)], 2) if latencies else None,
            "wall_s": round(time.time() - started, 1),
            "examples_of_disagreement_with_truth": mistakes,
        }
        print(json.dumps(report["llm"], indent=2))
    if args.out:
        args.out.write_text(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
