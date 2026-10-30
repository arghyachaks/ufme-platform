"""The benchmark itself must be trustworthy before it judges any engine."""

import json
import random
from collections import Counter
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from app.engines.benchmark import baseline
from app.engines.benchmark.__main__ import MANIFEST, check_floor, export_csv
from app.engines.benchmark.evaluate import evaluate
from app.engines.benchmark.model import Dataset, Line, Prediction, TruthGroup
from app.engines.benchmark.scenarios import SCENARIOS, fingerprint, generate, golden

FLOORS = Path(__file__).resolve().parents[2] / "benchmarks"


def _line(i: str, entity: str, cp: str, usd: float, ref: str = "R1", d: int = 1) -> Line:
    return Line(i, entity, cp, usd, "USD", usd, date(2026, 8, d), date(2026, 8, d), ref, ref, "", "1910")


# ---- generator ------------------------------------------------------------------------------------------
def test_generator_is_deterministic_and_complete() -> None:
    a, b = generate(3_000, seed=5), generate(3_000, seed=5)
    assert fingerprint(a) == fingerprint(b)
    assert fingerprint(a) != fingerprint(generate(3_000, seed=6))
    ids = [i for g in a.truth for i in g.line_ids]
    assert len(ids) == len(set(ids)) == len(a.lines)  # every line in exactly one truth group


def test_every_scenario_is_generated() -> None:
    seen = Counter(g.scenario for g in generate(20_000, seed=9).truth)
    missing = set(SCENARIOS) - set(seen)
    assert not missing, missing
    assert {"duplicate_extra", "reversal_pair"} <= set(seen)


def test_true_groups_net_to_zero_except_designed_residuals() -> None:
    ds = generate(10_000, seed=3)
    lines = {x.id: x for x in ds.lines}
    residual = {"fx_source_mismatch", "bank_fee", "withholding_tax"}
    for g in ds.truth:
        if len(g.line_ids) > 1 and g.scenario not in residual:
            total = sum(lines[i].amount_usd for i in g.line_ids)
            size = sum(abs(lines[i].amount_usd) for i in g.line_ids) / 2
            assert abs(total) <= max(1.0, 0.002 * size), (g.scenario, total)


def test_generation_order_is_hidden() -> None:
    ds = generate(2_000, seed=4)
    lines = [x.id for x in ds.lines]
    assert lines != sorted(lines)  # shuffled
    positions = {x.id: n for n, x in enumerate(ds.lines)}
    pairs = [g for g in ds.truth if len(g.line_ids) == 2]
    adjacent = sum(1 for g in pairs if abs(positions[min(g.line_ids)] - positions[max(g.line_ids)]) == 1)
    assert adjacent / len(pairs) < 0.05


def test_golden_small_matches_manifest() -> None:
    manifest = json.loads(MANIFEST.read_text())
    assert fingerprint(golden("small")) == manifest["small"]["sha256"]


# ---- evaluator ------------------------------------------------------------------------------------------
def _toy() -> Dataset:
    lines = [
        _line("a1", "UK02", "US01", -100),
        _line("b1", "US01", "UK02", 100),  # clean pair
        _line("a2", "UK02", "US01", -60),
        _line("a3", "UK02", "US01", -40),
        _line("b2", "US01", "UK02", 100),  # 1:M
        _line("o1", "US01", "UK02", 77),  # orphan
        _line("d1", "UK02", "US01", -100, ref="X9"),  # decoy
    ]
    truth = [
        TruthGroup("g1", "clean", frozenset({"a1", "b1"})),
        TruthGroup("g2", "split_1m", frozenset({"a2", "a3", "b2"})),
        TruthGroup("g3", "orphan", frozenset({"o1"})),
        TruthGroup("g4", "decoy_same_amount", frozenset({"d1"})),
    ]
    return Dataset("toy", lines, truth, 0, "test")


def test_perfect_predictions_score_one() -> None:
    ds = _toy()
    preds = [Prediction(g.line_ids, 0.99, "auto") for g in ds.truth if len(g.line_ids) > 1]
    r = evaluate(ds, preds)
    assert r.pair["f1"] == r.group["f1"] == r.exposure["f1"] == 1.0
    assert r.auto == {"precision": 1.0, "rate": 1.0, "lines": 5}
    assert r.decoy_false_match_rate == r.orphan_false_match_rate == 0.0


def test_mistakes_are_counted_where_they_belong() -> None:
    ds = _toy()
    preds = [
        Prediction(frozenset({"d1", "b1"}), 0.9, "auto"),  # decoy taken instead of the true partner
        Prediction(frozenset({"a2", "b2"}), 0.7, "suggest"),
    ]  # half of the split
    r = evaluate(ds, preds)
    assert (r.pair["precision"], r.pair["tp"], r.pair["fp"], r.pair["fn"]) == (0.5, 1, 1, 2)
    assert r.pair["recall"] == pytest.approx(1 / 3, abs=1e-4)
    assert r.group["tp"] == 0 and r.group["fn"] == 2
    assert r.auto["precision"] == 0.0 and r.auto["rate"] == 0.0
    assert r.decoy_false_match_rate == 1.0 and r.orphan_false_match_rate == 0.0
    assert r.by_scenario["split_1m"]["fn"] == 1 and r.by_scenario["clean"]["fn"] == 1


def test_floor_check_detects_regressions(tmp_path: Path) -> None:
    ds = golden("small")
    good = evaluate(ds, baseline.match(ds.lines), "baseline")
    floor = tmp_path / "floor.json"
    floor.write_text(json.dumps(good.as_dict()))
    assert check_floor(good, floor) == []
    worse = evaluate(ds, baseline.match(ds.lines)[: len(ds.lines) // 4], "baseline")
    assert any(f.startswith("pair.f1") for f in check_floor(worse, floor))


def test_csv_export(tmp_path: Path) -> None:
    ds = generate(300, seed=2)
    export_csv(ds, tmp_path)
    assert len((tmp_path / "lines.csv").read_text().splitlines()) == len(ds.lines) + 1
    assert len((tmp_path / "truth.csv").read_text().splitlines()) == len(ds.lines) + 1


# ---- baseline must not regress on the frozen small set --------------------------------------------------
def test_baseline_meets_recorded_floor() -> None:
    ds = golden("small")
    report = evaluate(ds, baseline.match(ds.lines), "baseline")
    assert check_floor(report, FLOORS / "floor_small_baseline.json") == []


# ---- metamorphic tests: properties any correct matcher must satisfy -------------------------------------
def _sets(preds: list[Prediction]) -> set[frozenset[str]]:
    return {p.line_ids for p in preds}


@pytest.fixture(scope="module")
def sample() -> Dataset:
    return generate(4_000, seed=11)


def test_result_is_independent_of_line_order(sample: Dataset) -> None:
    shuffled = list(sample.lines)
    random.Random(1).shuffle(shuffled)
    assert _sets(baseline.match(sample.lines)) == _sets(baseline.match(shuffled))


def test_result_is_independent_of_id_naming(sample: Dataset) -> None:
    rename = {x.id: f"Z{n:07d}" for n, x in enumerate(reversed(sample.lines))}
    renamed = [replace(x, id=rename[x.id]) for x in sample.lines]
    renamed_ds = Dataset(
        sample.name,
        renamed,
        [
            replace(
                g,
                line_ids=frozenset(rename[i] for i in g.line_ids),
                twin_of=rename[g.twin_of] if g.twin_of else None,
            )
            for g in sample.truth
        ],
        sample.seed,
        sample.version,
    )
    # Truly indistinguishable lines (exact twins, identical no-reference round amounts) may pair differently
    # by id; the score may move by at most half a point.
    a = evaluate(sample, baseline.match(sample.lines)).as_dict()
    b = evaluate(renamed_ds, baseline.match(renamed)).as_dict()
    for key in ("pair", "group"):
        assert abs(a[key]["f1"] - b[key]["f1"]) <= 0.005, key


def test_result_is_invariant_to_currency_scaling(sample: Dataset) -> None:
    scaled = [replace(x, amount_usd=x.amount_usd * 1.37) for x in sample.lines]
    assert _sets(baseline.match(sample.lines)) == _sets(baseline.match(scaled))


def test_removing_a_partner_unmatches_a_clean_line(sample: Dataset) -> None:
    clean = [g for g in sample.truth if g.scenario == "clean"][:50]
    removed = {sorted(g.line_ids)[1] for g in clean}
    kept = {sorted(g.line_ids)[0] for g in clean}
    preds = baseline.match([x for x in sample.lines if x.id not in removed])
    auto_ids = {i for p in preds if p.decision == "auto" for i in p.line_ids}
    assert not (kept & auto_ids)  # never auto-matched to something else


def test_noise_never_increases_confidence(sample: Dataset) -> None:
    lines = {x.id: x for x in sample.lines}
    clean = [g for g in sample.truth if g.scenario == "clean"][:100]
    before = {p.line_ids: p.confidence for p in baseline.match(sample.lines)}
    noisy = dict(lines)
    for g in clean:
        i = sorted(g.line_ids)[0]
        noisy[i] = replace(
            lines[i],
            reference_norm=(lines[i].reference_norm or "") + "Q",
            amount_usd=lines[i].amount_usd * 1.003,
        )
    after = {p.line_ids: p.confidence for p in baseline.match(list(noisy.values()))}
    for g in clean:
        assert after.get(g.line_ids, 0.0) <= before.get(g.line_ids, 0.0)
