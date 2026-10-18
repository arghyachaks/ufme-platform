"""Pure parsing/normalization helpers for ledger lines (no database access)."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

# Column aliases seen in ERP/bank extracts → canonical field.
COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "external_id": ("id", "external_id", "document_id", "doc_id", "document", "belnr", "line_id"),
    "entity": ("entity", "company_code", "company", "bukrs", "entity_code", "legal_entity"),
    "counterparty": (
        "counterparty",
        "ic_partner",
        "trading_partner",
        "partner",
        "vbund",
        "counterparty_code",
    ),
    "account": ("account", "gl_account", "hkont", "gl"),
    "amount": ("amount", "amt", "value", "wrbtr", "amount_doc"),
    "currency": ("currency", "ccy", "waers", "curr"),
    "value_date": ("value_date", "date", "document_date", "bldat", "txn_date"),
    "posting_date": ("posting_date", "budat", "post_date"),
    "reference": ("reference", "ref", "ic_reference", "xblnr", "invoice_ref"),
    "description": ("description", "text", "sgtxt", "memo", "narrative"),
}
REQUIRED = ("entity", "counterparty", "amount", "currency", "value_date")

# ISO 4217 codes UFME accepts (extend as tenants onboard).
ISO_CURRENCIES = frozenset(
    [
        "USD",
        "EUR",
        "GBP",
        "INR",
        "SGD",
        "BRL",
        "JPY",
        "CNY",
        "CHF",
        "CAD",
        "AUD",
        "HKD",
        "SEK",
        "NOK",
        "DKK",
        "PLN",
        "MXN",
        "ZAR",
        "AED",
        "SAR",
        "KRW",
        "NZD",
        "THB",
        "MYR",
        "IDR",
        "PHP",
    ]
)
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y", "%d.%m.%Y", "%Y%m%d", "%d %b %Y")
_REF_NOISE = re.compile(r"[^A-Z0-9]")


def _key(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", header.strip().lower()).strip("_")


def map_columns(headers: list[str], overrides: dict[str, str] | None = None) -> dict[str, str]:
    """Return {canonical_field: source_header}. Overrides map canonical → header explicitly."""
    by_key = {_key(h): h for h in headers}
    mapping: dict[str, str] = {}
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in by_key:
                mapping[field] = by_key[alias]
                break
    for field, header in (overrides or {}).items():
        if header in headers:
            mapping[field] = header
    return mapping


def parse_amount(text: str | None) -> Decimal | None:
    if text is None:
        return None
    s = text.strip().replace(",", "").replace(" ", "")
    if not s:
        return None
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    if s.endswith("-"):  # SAP-style trailing minus
        negative, s = True, s[:-1]
    try:
        value = Decimal(s)
    except InvalidOperation:
        return None
    if not value.is_finite():
        return None
    return -value if negative else value


def parse_date(text: str | None) -> date | None:
    if not text or not text.strip():
        return None
    s = text.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def normalize_reference(text: str | None) -> str | None:
    if text is None:
        return None
    norm = _REF_NOISE.sub("", text.upper())
    return norm or None


def normalize_code(text: str | None) -> str:
    return (text or "").strip().upper()
