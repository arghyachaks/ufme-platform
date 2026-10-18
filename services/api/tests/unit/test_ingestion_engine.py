from datetime import date
from decimal import Decimal

from app.engines.augmented_data.fx import FxTable, synthetic_rate
from app.engines.connectors.synthetic import generate
from app.engines.data_quality import checks as dq
from app.engines.data_quality import normalize as n

TODAY = date(2026, 10, 18)
ENTITIES = {"US01", "UK02", "DE03"}
MAPPING = n.map_columns(
    ["document_id", "company_code", "trading_partner", "amount", "currency", "document_date", "reference"]
)


def check(**overrides: str) -> dq.CheckedRow:
    raw = {
        "document_id": "D1",
        "company_code": "US01",
        "trading_partner": "UK02",
        "amount": "1,000.50",
        "currency": "USD",
        "document_date": "2026-08-12",
        "reference": "IC-1",
    } | overrides
    return dq.check_row(2, raw, MAPPING, known_entities=ENTITIES, today=TODAY, seen=set())


def test_column_mapping_understands_erp_headers() -> None:
    m = n.map_columns(["BUKRS", "VBUND", "WRBTR", "WAERS", "BLDAT", "XBLNR"])
    assert m == {
        "entity": "BUKRS",
        "counterparty": "VBUND",
        "amount": "WRBTR",
        "currency": "WAERS",
        "value_date": "BLDAT",
        "reference": "XBLNR",
    }
    assert n.map_columns(["foo", "Company Code"], {"amount": "foo"})["amount"] == "foo"


def test_amount_and_date_parsing() -> None:
    assert n.parse_amount("1,234.50") == Decimal("1234.50")
    assert n.parse_amount("(200)") == Decimal("-200")
    assert n.parse_amount("75.00-") == Decimal("-75.00")
    assert n.parse_amount("n/a") is None and n.parse_amount("") is None and n.parse_amount("inf") is None
    for text in ("2026-08-12", "12/08/2026", "12-Aug-2026", "12.08.2026", "20260812"):
        assert n.parse_date(text) == date(2026, 8, 12)
    assert n.parse_date("31/31/2026") is None


def test_reference_normalization() -> None:
    assert n.normalize_reference(" ic loan-uk02 /0817 ") == "ICLOANUK020817"
    assert n.normalize_reference("  ") is None


def test_clean_row_passes() -> None:
    row = check()
    assert row.ok and row.amount == Decimal("1000.50") and not row.warnings


def test_blocking_checks() -> None:
    assert "invalid_currency" in check(currency="XX").errors
    assert "missing_counterparty" in check(trading_partner="").errors
    assert "invalid_amount" in check(amount="abc").errors
    assert "invalid_date" in check(document_date="soon").errors
    assert "unknown_entity" in check(company_code="ZZ99").errors
    assert "self_counterparty" in check(trading_partner="US01").errors
    assert "missing_field" in check(amount="").errors


def test_warnings_are_auto_fixed() -> None:
    row = check(currency="gbp", reference=" ic 1 ", document_date="2026-12-01")
    assert row.ok
    assert row.currency == "GBP" and row.reference_norm == "IC1"
    assert set(row.warnings) == {"currency_case", "reference_noise", "future_dated"}


def test_duplicates_within_batch() -> None:
    seen: set[tuple[object, ...]] = set()
    raw = {
        "document_id": "D1",
        "company_code": "US01",
        "trading_partner": "UK02",
        "amount": "1",
        "currency": "USD",
        "document_date": "2026-08-12",
    }
    first = dq.check_row(2, raw, MAPPING, known_entities=ENTITIES, today=TODAY, seen=seen)
    second = dq.check_row(3, dict(raw), MAPPING, known_entities=ENTITIES, today=TODAY, seen=seen)
    assert first.ok and second.errors == ["duplicate_line"]


def test_fx_table_uses_latest_rate_within_a_week() -> None:
    fx = FxTable([(date(2026, 8, 1), "GBP", Decimal("1.25")), (date(2026, 8, 10), "GBP", Decimal("1.30"))])
    assert fx.rate("GBP", date(2026, 8, 5)) == Decimal("1.25")
    assert fx.rate("GBP", date(2026, 8, 10)) == Decimal("1.30")
    assert fx.rate("GBP", date(2026, 8, 20)) is None  # stale
    assert fx.rate("GBP", date(2026, 7, 1)) is None
    assert fx.rate("EUR", date(2026, 8, 5)) is None
    assert fx.to_usd(Decimal("100"), "USD", date(2026, 8, 5)) == (Decimal("100.0000"), Decimal(1))
    assert fx.to_usd(Decimal("100"), "GBP", date(2026, 8, 5)) == (Decimal("125.0000"), Decimal("1.25"))


def test_synthetic_generator_is_deterministic_and_noisy() -> None:
    a = list(generate(2_000, seed=3))
    assert a == list(generate(2_000, seed=3))
    assert len(a) == 2_000
    assert {r["company_code"] for r in a} == {"US01", "UK02", "DE03", "IN04", "SG05", "BR06"}
    assert any(r["currency"] == "XX" for r in a) and any(r["trading_partner"] == "" for r in a)
    assert any(r["reference"].startswith(" ") for r in a)
    assert synthetic_rate("USD", date(2026, 8, 1)) == 1
