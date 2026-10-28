"""Stage 3c: 1:M, M:1 and M:M groups from reference families, same-side reversals, and their precedence."""

from datetime import date

from app.engines.benchmark.model import Line
from app.engines.data_quality.normalize import normalize_reference
from app.engines.matching import engine, groups


def ln(
    i: str,
    entity: str,
    cp: str,
    usd: float,
    ref: str,
    d: int = 10,
    ccy: str = "USD",
    local: float | None = None,
) -> Line:
    return Line(
        i,
        entity,
        cp,
        usd if local is None else local,
        ccy,
        usd,
        date(2026, 8, d),
        date(2026, 8, d),
        ref,
        normalize_reference(ref),
        "",
        "1910",
    )


def by_size(preds: list) -> dict[int, list]:
    out: dict[int, list] = {}
    for p in preds:
        out.setdefault(len(p.line_ids), []).append(p)
    return out


def test_reference_roots() -> None:
    assert groups.ref_root("INV-000015/SG05") == ("INV000015SG05", False)
    assert groups.ref_root("INV-000015/SG05/2") == ("INV000015SG05", False)  # split suffix stripped
    assert groups.ref_root("NET-IN04-DE03-00088-A1") == groups.ref_root("NET-IN04-DE03-00088")
    assert groups.ref_root("REV-ICL0000102") == ("ICL0000102", True)
    assert groups.ref_root("AB-1") == (None, False)  # too short to be a reliable family


def test_split_one_to_many_is_auto_matched() -> None:
    lines = [
        ln("w", "UK02", "US01", 9010.83, "INV-7781/UK02"),
        ln("p1", "US01", "UK02", -2906.51, "INV-7781/UK02", 11),
        ln("p2", "US01", "UK02", -1828.47, "INV-7781/UK02/2", 12),
        ln("p3", "US01", "UK02", -4275.85, "INV-7781/UK02/3", 13),
    ]
    res = engine.run(lines)
    [g] = by_size(res.predictions)[4]
    assert g.decision == "auto" and "G-REF-FAMILY" in g.reasons
    detail = res.details[g.line_ids]
    assert (
        detail.match_type == "1:M" and round(detail.exposure_usd, 2) == 9010.83
    )  # UK02 < US01: A side is one


def test_netting_many_to_many() -> None:
    lines = [
        ln("a0", "DE03", "IN04", -11491.82, "NET-IN04-DE03-00088", 12),
        ln("a1", "DE03", "IN04", -21347.26, "NET-IN04-DE03-00088", 12),
        ln("b0", "IN04", "DE03", 25465.08, "NET-IN04-DE03-00088-A0"),
        ln("b1", "IN04", "DE03", 7374.00, "NET-IN04-DE03-00088-A1"),
    ]
    res = engine.run(lines)
    [g] = res.predictions
    assert len(g.line_ids) == 4 and res.details[g.line_ids].match_type == "M:M" and g.decision == "auto"


def test_reversal_pair_cancels_in_booking_currency() -> None:
    # Same side, SGD booked; USD differs only because the FX rate moved a day.
    lines = [
        ln("o", "SG05", "DE03", 396620.83, "ICL0000102", 5, "SGD", 510000.00),
        ln("r", "SG05", "DE03", -396433.76, "REV-ICL0000102", 6, "SGD", -510000.00),
    ]
    res = engine.run(lines)
    [g] = res.predictions
    assert (
        g.line_ids == {"o", "r"} and res.details[g.line_ids].match_type == "reversal" and g.decision == "auto"
    )


def test_partial_family_is_suggested_not_auto() -> None:
    # A look-alike shares the reference; only the true subset nets, so the group goes to a human.
    lines = [
        ln("w", "UK02", "US01", 1000.00, "INV-9001/UK02"),
        ln("p1", "US01", "UK02", -600.00, "INV-9001/UK02", 11),
        ln("p2", "US01", "UK02", -400.00, "INV-9001/UK02/2", 11),
        ln("x", "US01", "UK02", -250.00, "INV-9001/UK02/3", 11),
    ]
    res = engine.run(lines)
    grouped = [p for p in res.predictions if len(p.line_ids) == 3]
    assert len(grouped) == 1 and grouped[0].line_ids == {"w", "p1", "p2"} and grouped[0].decision == "suggest"
    assert "x" not in {i for p in res.predictions for i in p.line_ids}


def test_no_reference_no_group() -> None:
    # Amounts net exactly but nothing links the lines: never grouped (that is where false matches live).
    lines = [
        ln("w", "UK02", "US01", 1000.00, ""),
        ln("p1", "US01", "UK02", -600.00, "", 11),
        ln("p2", "US01", "UK02", -400.00, "", 12),
    ]
    assert not [p for p in engine.run(lines).predictions if len(p.line_ids) > 2]


def test_family_outside_tolerance_is_left_open() -> None:
    lines = [
        ln("w", "UK02", "US01", 1000.00, "INV-5555/UK02"),
        ln("p1", "US01", "UK02", -600.00, "INV-5555/UK02", 11),
        ln("p2", "US01", "UK02", -300.00, "INV-5555/UK02/2", 11),  # 10% short: not a split
    ]
    assert not [p for p in engine.run(lines).predictions if len(p.line_ids) > 2]
