"""Run the matching benchmark.

python -m app.engines.benchmark --dataset medium --matcher baseline
python -m app.engines.benchmark --dataset small --check benchmarks/floor_small_baseline.json
python -m app.engines.benchmark --dataset small --export-csv /tmp/bench   # lines.csv + truth.csv for ingestion
"""

import argparse
import csv
import json
import sys
import time
from collections.abc import Callable
from pathlib import Path

from app.engines.benchmark import baseline
from app.engines.benchmark.evaluate import Report, blocking_recall, evaluate
from app.engines.benchmark.model import Dataset, Line, Prediction
from app.engines.benchmark.scenarios import GOLDEN, fingerprint, generate, golden
from app.engines.matching import engine

MATCHERS: dict[str, Callable[[list[Line]], list[Prediction]]] = {
    "baseline": baseline.match,
    "engine": engine.match,
}
MANIFEST = Path(__file__).resolve().parents[3] / "benchmarks" / "datasets.json"
# Metrics guarded by the regression gate (higher is better unless listed in LOWER_IS_BETTER).
GUARDED = ["pair.f1", "pair.precision", "group.f1", "exposure.f1", "auto.precision", "auto.rate"]
LOWER_IS_BETTER = ["decoy_false_match_rate", "orphan_false_match_rate"]
OPTIONAL = ["blocking_recall"]  # guarded when present in both reports
TOLERANCE = 0.002
MAX_CALIBRATION_ERROR = 0.02  # 3d exit criterion: confidence must mean what it says


def _get(report: dict[str, object], path: str) -> float:
    value: object = report
    for part in path.split("."):
        value = value[part]  # type: ignore[index]
    return float(value)  # type: ignore[arg-type]


def check_floor(report: Report, floor_path: Path) -> list[str]:
    floor = json.loads(floor_path.read_text())
    current = report.as_dict()
    failures = []
    for key in GUARDED:
        if _get(current, key) < _get(floor, key) - TOLERANCE:
            failures.append(f"{key}: {_get(current, key):.4f} < floor {_get(floor, key):.4f}")
    for key in OPTIONAL:
        if (
            current.get(key) is not None
            and floor.get(key) is not None
            and _get(current, key) < _get(floor, key) - TOLERANCE / 10
        ):
            failures.append(f"{key}: {_get(current, key):.5f} < floor {_get(floor, key):.5f}")
    for key in LOWER_IS_BETTER:
        if _get(current, key) > _get(floor, key) + TOLERANCE:
            failures.append(f"{key}: {_get(current, key):.4f} > floor {_get(floor, key):.4f}")
    ece, ece_floor = current.get("calibration_error"), floor.get("calibration_error")
    if (
        isinstance(ece, (int, float))
        and isinstance(ece_floor, (int, float))
        and (ece > float(ece_floor) + 0.005 or (ece_floor <= MAX_CALIBRATION_ERROR < ece))
    ):
        failures.append(
            f"calibration_error: {ece:.4f} (floor {ece_floor:.4f}, limit {MAX_CALIBRATION_ERROR})"
        )
    return failures


def verify_fingerprint(ds: Dataset) -> str | None:
    if not MANIFEST.exists():
        return None
    expected = json.loads(MANIFEST.read_text()).get(ds.name, {}).get("sha256")
    actual = fingerprint(ds)
    if expected and expected != actual:
        return f"dataset '{ds.name}' changed (fingerprint {actual[:12]} != {expected[:12]}); bump the version and re-baseline deliberately"
    return None


def export_csv(ds: Dataset, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with (out / "lines.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "document_id",
                "company_code",
                "trading_partner",
                "gl_account",
                "amount",
                "currency",
                "document_date",
                "posting_date",
                "reference",
                "text",
            ]
        )
        for x in ds.lines:
            w.writerow(
                [
                    x.id,
                    x.entity,
                    x.counterparty,
                    x.account,
                    f"{x.amount:.2f}",
                    x.currency,
                    x.value_date.isoformat(),
                    x.posting_date.isoformat(),
                    x.reference,
                    x.description,
                ]
            )
    with (out / "truth.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["group_id", "scenario", "difficulty", "document_id"])
        for g in ds.truth:
            for i in sorted(g.line_ids):
                w.writerow([g.id, g.scenario, g.difficulty, i])


def summary(r: Report) -> str:
    rows = [
        f"{r.matcher} on {r.dataset} ({r.lines:,} lines, {r.seconds:.1f}s)",
        f"  pair      P {r.pair['precision']:.4f}  R {r.pair['recall']:.4f}  F1 {r.pair['f1']:.4f}",
        f"  group     P {r.group['precision']:.4f}  R {r.group['recall']:.4f}  F1 {r.group['f1']:.4f}",
        f"  exposure  P {r.exposure['precision']:.4f}  R {r.exposure['recall']:.4f}  F1 {r.exposure['f1']:.4f}",
        f"  auto      precision {r.auto['precision']:.4f}  rate {r.auto['rate']:.4f}",
        f"  decoys wrongly matched {r.decoy_false_match_rate:.2%}   orphans wrongly matched {r.orphan_false_match_rate:.2%}",
        f"  calibration error (ECE) {r.calibration_error if r.calibration_error is not None else 0:.4f}",
        "  by scenario:",
    ]
    for name, m in r.by_scenario.items():
        if "f1" in m and "total" not in m:
            rows.append(f"    {name:<22} P {m['precision']:.3f}  R {m['recall']:.3f}  F1 {m['f1']:.3f}")
        else:
            rows.append(f"    {name:<22} wrongly matched {m.get('wrongly_matched', 0)}/{m.get('total', 0)}")
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dataset", default="small", help=f"golden set ({', '.join(GOLDEN)}) or 'custom'")
    parser.add_argument("--size", type=int, default=10_000, help="size for --dataset custom")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--matcher", default="baseline", choices=sorted(MATCHERS))
    parser.add_argument("--out", type=Path, help="write the JSON report here")
    parser.add_argument("--check", type=Path, help="fail if metrics regress below this floor report")
    parser.add_argument("--export-csv", type=Path, help="write lines.csv + truth.csv and exit")
    args = parser.parse_args()

    ds = golden(args.dataset) if args.dataset in GOLDEN else generate(args.size, args.seed)
    if problem := verify_fingerprint(ds):
        print(f"ERROR: {problem}")
        return 2
    if args.export_csv:
        export_csv(ds, args.export_csv)
        print(f"exported {len(ds.lines):,} lines and {len(ds.truth):,} truth groups to {args.export_csv}")
        return 0
    started = time.perf_counter()
    if args.matcher == "engine":
        result = engine.run(ds.lines)
        report = evaluate(ds, result.predictions, args.matcher, time.perf_counter() - started)
        report.blocking_recall = blocking_recall(ds, result.candidate_pairs)
    else:
        report = evaluate(ds, MATCHERS[args.matcher](ds.lines), args.matcher, time.perf_counter() - started)
    print(summary(report))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report.as_dict(), indent=2) + "\n")
    if args.check:
        failures = check_floor(report, args.check)
        if failures:
            print("REGRESSION:\n  " + "\n  ".join(failures))
            return 1
        print(f"no regression vs {args.check.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
