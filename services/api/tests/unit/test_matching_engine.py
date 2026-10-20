"""Matching engine (3b): features, rules, scoring, global assignment, and benchmark floors."""

import random
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from app.engines.benchmark.__main__ import check_floor
from app.engines.benchmark.evaluate import blocking_recall, evaluate
from app.engines.benchmark.model import Dataset, Line
from app.engines.benchmark.scenarios import generate, golden
from app.engines.matching import candidates as cand
from app.engines.matching import engine
from app.engines.matching.assignment import max_weight_assignment
from app.engines.matching.rules import Rule, default_rules
from app.engines.matching.text import affix, canonical, digit_core, edit_distance, jaro_winkler

FLOORS = Path(__file__).resolve().parents[2] / "benchmarks"


def line(
    i: str, entity: str, cp: str, usd: float, ref: str = "ICL0001481", d: int = 10, desc: str = ""
) -> Line:
    return Line(i, entity, cp, usd, "USD", usd, date(2026, 8, d), date(2026, 8, d), ref, ref, desc, "1910")


def features(a: Line, b: Line) -> dict:
    return engine.pair_features(cand.prepare(a), cand.prepare(b), set(), 1)


# ---- text primitives ------------------------------------------------------------------------------------
def test_text_primitives() -> None:
    assert round(jaro_winkler("MARTHA", "MARHTA"), 4) == 0.9611
    assert edit_distance("ICL0001481", "ICL0001418") == 1  # adjacent transposition counts once
    assert canonical("ICLOOO1481") == canonical("1C10001481")  # OCR confusions collapse
    assert (
        affix("SGINV004412", "INV004412") and affix("INV0044121", "INV004412") and not affix("INV1", "INV12")
    )
    assert digit_core("SGINV004412DE03") == "4412"


# ---- features: the decoy problem that defeats Jaro-Winkler ----------------------------------------------
def test_structured_ids_with_shared_prefix_are_a_conflict_not_a_match() -> None:
    a = line("a", "DE03", "US01", 1000, ref="ICUS01DE03032108")
    b = line("b", "US01", "DE03", -1000, ref="ICUS01DE03036062")
    f = features(a, b)
    assert jaro_winkler("ICUS01DE03032108", "ICUS01DE03036062") > 0.9  # why JW alone is unsafe
    assert f["ref_conflict"] and not f["ref_strong"]
    assert engine.score(f)[1]["reference"] < 0


@pytest.mark.parametrize(
    ("ref_b", "flag"),
    [
        ("ICL0001481", "ref_exact"),
        ("1CL000I48I", "ref_canonical_exact"),
        ("SGICL0001481", "ref_affix"),
        ("ICL0001418", "ref_strong"),
    ],
)
def test_reference_variants_are_strong(ref_b: str, flag: str) -> None:
    f = features(line("a", "DE03", "US01", 500), line("b", "US01", "DE03", -500, ref=ref_b))
    assert f[flag] and f["ref_strong"]


def test_reference_in_description() -> None:
    a = line("a", "DE03", "US01", 500, ref="ICL0001481")
    b = line("b", "US01", "DE03", -500, ref="", desc="Settlement of ICL-0001481 per agreement")
    assert features(a, b)["ref_in_description"]


def test_score_is_monotonic_in_amount_gap_and_date_gap() -> None:
    a = line("a", "DE03", "US01", 10_000)
    prev = float("inf")
    for usd in (10_000, 9_995, 9_970, 9_940, 9_800, 9_000):
        lo, _ = engine.score(features(a, line("b", "US01", "DE03", -usd)))
        assert lo <= prev
        prev = lo
    prev = float("inf")
    for d in (10, 12, 16, 22, 28):
        lo, _ = engine.score(features(a, line("b", "US01", "DE03", -10_000, d=d)))
        assert lo <= prev
        prev = lo


# ---- rules DSL --------------------------------------------------------------------------------------------
def test_rule_dsl() -> None:
    rule = Rule.from_definition(
        "X",
        "x",
        {
            "all": [{"feature": "amount_gap", "op": "lte", "value": 0.01}],
            "any": [[{"feature": "ref_exact", "op": "eq", "value": True}]],
            "action": "auto",
            "confidence": 0.99,
        },
    )
    assert rule.matches({"amount_gap": 0.001, "ref_exact": True})
    assert not rule.matches({"amount_gap": 0.001, "ref_exact": False})
    assert not rule.matches({"amount_gap": None, "ref_exact": True})
    with pytest.raises(ValueError):
        Rule.from_definition("Y", "y", {"all": [{"feature": "a", "op": "~=", "value": 1}]})
    assert [r.id for r in default_rules()] == ["R-001", "R-002", "R-003", "R-004"]


def test_disabling_rules_changes_explanations_not_safety() -> None:
    ds = generate(2_000, seed=13)
    with_rules = evaluate(ds, engine.match(ds.lines))
    without = evaluate(ds, engine.match(ds.lines, rules=[]))
    assert without.auto["precision"] >= 0.995 and with_rules.auto["precision"] >= 0.995


# ---- global assignment beats greedy ---------------------------------------------------------------------
def test_assignment_is_globally_optimal() -> None:
    # Greedy would take (0,0)=9 then (1,1)=1 → 10; optimal is (0,1)+(1,0) = 8+8 = 16.
    assert sorted(max_weight_assignment([[9, 8], [8, 1]])) == [(0, 1), (1, 0)]
    assert max_weight_assignment([]) == []


def test_engine_resolves_a_conflict_globally() -> None:
    # Two A lines compete for b1; the exact-reference pair must win and the other finds its own partner.
    a1 = line("a1", "DE03", "US01", 1000, ref="INV0000111")
    a2 = line("a2", "DE03", "US01", 1000, ref="INV0000222")
    b1 = line("b1", "US01", "DE03", -1000, ref="INV0000111")
    b2 = line("b2", "US01", "DE03", -1000, ref="INV0000222", d=11)
    got = {p.line_ids for p in engine.match([a1, a2, b1, b2])}
    assert got == {frozenset({"a1", "b1"}), frozenset({"a2", "b2"})}


def test_predictions_carry_explanations_and_alternatives() -> None:
    ds = generate(1_000, seed=4)
    res = engine.run(ds.lines)
    assert res.predictions
    for p in res.predictions[:50]:
        detail = res.details[p.line_ids]
        assert detail.contributions and p.reasons
        assert 0.5 <= p.confidence <= 1
        assert p.decision in ("auto", "suggest")
        assert p.decision != "auto" or detail.features["amount_gap"] <= engine.POLICY_TOLERANCE


# ---- metamorphic properties on the real engine ----------------------------------------------------------
@pytest.fixture(scope="module")
def sample() -> Dataset:
    return generate(4_000, seed=17)


def _sets(lines: list[Line]) -> set[frozenset[str]]:
    return {p.line_ids for p in engine.match(lines)}


def test_engine_is_order_independent(sample: Dataset) -> None:
    shuffled = list(sample.lines)
    random.Random(3).shuffle(shuffled)
    assert _sets(sample.lines) == _sets(shuffled)


def test_engine_is_invariant_to_usd_scaling(sample: Dataset) -> None:
    scaled = [replace(x, amount_usd=x.amount_usd * 1.37) for x in sample.lines]
    # The $60 absolute fee window is not scale-free, so allow a tiny difference in candidate sets.
    a, b = _sets(sample.lines), _sets(scaled)
    assert len(a & b) / len(a | b) >= 0.995


def test_engine_noise_never_increases_confidence(sample: Dataset) -> None:
    res = engine.run(sample.lines)
    lines = {x.id: x for x in sample.lines}
    clean = [p for p in res.predictions if "R-001" in p.reasons][:100]
    noisy = dict(lines)
    for p in clean:
        i = sorted(p.line_ids)[0]
        noisy[i] = replace(
            lines[i],
            amount_usd=lines[i].amount_usd * 1.004,
            value_date=lines[i].value_date.replace(day=min(lines[i].value_date.day + 2, 28)),
        )
    after = {p.line_ids: p.confidence for p in engine.match(list(noisy.values()))}
    for p in clean:
        assert after.get(p.line_ids, 0.0) <= p.confidence + 1e-9


# ---- benchmark floors -----------------------------------------------------------------------------------
def test_engine_beats_baseline_and_meets_floor() -> None:
    ds = golden("small")
    res = engine.run(ds.lines)
    report = evaluate(ds, res.predictions, "engine")
    report.blocking_recall = blocking_recall(ds, res.candidate_pairs)
    assert check_floor(report, FLOORS / "floor_small_engine.json") == []
    base = evaluate(ds, __import__("app.engines.benchmark.baseline", fromlist=["match"]).match(ds.lines))
    assert report.pair["f1"] > base.pair["f1"] and report.auto["rate"] > base.auto["rate"]
    assert report.auto["precision"] >= 0.995
