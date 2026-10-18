"""Row-level data quality checks. Blocking failures quarantine the row; warnings are recorded and auto-fixed."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.engines.data_quality import normalize as n

# check id → (human label, field, severity, blocking)
CHECKS: dict[str, tuple[str, str, str, bool]] = {
    "missing_field": ("Missing required field", "*", "High", True),
    "missing_counterparty": ("Missing counterparty code", "counterparty", "High", True),
    "invalid_amount": ("Amount is not a number", "amount", "High", True),
    "invalid_currency": ("Currency not ISO-4217", "currency", "Medium", True),
    "invalid_date": ("Unparseable value date", "value_date", "High", True),
    "unknown_entity": ("Unknown legal entity", "entity", "High", True),
    "duplicate_line": ("Duplicate line in batch", "external_id", "High", True),
    "currency_case": ("Currency code not upper case", "currency", "Low", False),
    "reference_noise": ("Reference contains whitespace/noise", "reference", "Low", False),
    "future_dated": ("Future-dated posting", "value_date", "Low", False),
    "zero_amount": ("Zero amount", "amount", "Low", False),
    "missing_fx_rate": ("No FX rate for date/currency", "currency", "Medium", False),
    "self_counterparty": ("Counterparty equals entity", "counterparty", "Medium", True),
}


@dataclass
class CheckedRow:
    line_no: int
    raw: dict[str, str]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    external_id: str | None = None
    entity: str = ""
    counterparty: str = ""
    account: str | None = None
    amount: Decimal | None = None
    currency: str = ""
    value_date: date | None = None
    posting_date: date | None = None
    reference_raw: str | None = None
    reference_norm: str | None = None
    description: str | None = None

    @property
    def ok(self) -> bool:
        return not self.errors


def check_row(
    line_no: int,
    raw: dict[str, str],
    mapping: dict[str, str],
    *,
    known_entities: set[str],
    today: date,
    seen: set[tuple[object, ...]],
) -> CheckedRow:
    def get(name: str) -> str | None:
        header = mapping.get(name)
        value = raw.get(header) if header else None
        return value.strip() if isinstance(value, str) else value

    row = CheckedRow(line_no=line_no, raw=raw)
    row.external_id = get("external_id") or None
    row.entity = n.normalize_code(get("entity"))
    row.counterparty = n.normalize_code(get("counterparty"))
    row.account = get("account") or None
    row.description = get("description") or None

    missing = [f for f in n.REQUIRED if f != "counterparty" and not get(f)]
    if missing:
        row.errors.append("missing_field")
    if not row.counterparty:
        row.errors.append("missing_counterparty")

    amount_text = get("amount")
    if amount_text:
        row.amount = n.parse_amount(amount_text)
        if row.amount is None:
            row.errors.append("invalid_amount")
        elif row.amount == 0:
            row.warnings.append("zero_amount")

    currency_text = get("currency") or ""
    row.currency = currency_text.upper()
    if currency_text:
        if row.currency not in n.ISO_CURRENCIES:
            row.errors.append("invalid_currency")
        elif currency_text != row.currency:
            row.warnings.append("currency_case")

    date_text = get("value_date")
    if date_text:
        row.value_date = n.parse_date(date_text)
        if row.value_date is None:
            row.errors.append("invalid_date")
        elif row.value_date > today:
            row.warnings.append("future_dated")
    row.posting_date = n.parse_date(get("posting_date"))

    if row.entity and row.entity not in known_entities:
        row.errors.append("unknown_entity")
    if row.entity and row.entity == row.counterparty:
        row.errors.append("self_counterparty")

    row.reference_raw = get("reference") or None
    row.reference_norm = n.normalize_reference(row.reference_raw)
    # Hyphens/slashes are normal formatting; whitespace and case problems are noise worth reporting.
    raw_ref = row.reference_raw
    if raw_ref and (raw_ref != raw_ref.strip() or " " in raw_ref or raw_ref != raw_ref.upper()):
        row.warnings.append("reference_noise")

    if row.ok:
        key = (
            ("id", row.external_id)
            if row.external_id
            else (
                "content",
                row.entity,
                row.counterparty,
                row.amount,
                row.currency,
                row.value_date,
                row.reference_norm,
            )
        )
        if key in seen:
            row.errors.append("duplicate_line")
        else:
            seen.add(key)
    return row
