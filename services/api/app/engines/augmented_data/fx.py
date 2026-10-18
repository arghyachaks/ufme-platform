"""FX enrichment: convert amounts to USD using the latest rate on or before the value date (max 7 days back)."""

import bisect
import math
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

MAX_STALENESS = timedelta(days=7)
CENT = Decimal("0.0001")


class FxTable:
    def __init__(self, rates: list[tuple[date, str, Decimal]]):
        self._dates: dict[str, list[date]] = {}
        self._rates: dict[str, list[Decimal]] = {}
        for d, ccy, rate in sorted(rates):
            self._dates.setdefault(ccy, []).append(d)
            self._rates.setdefault(ccy, []).append(rate)

    def rate(self, currency: str, on: date) -> Decimal | None:
        if currency == "USD":
            return Decimal(1)
        dates = self._dates.get(currency)
        if not dates:
            return None
        i = bisect.bisect_right(dates, on) - 1
        if i < 0 or on - dates[i] > MAX_STALENESS:
            return None
        return self._rates[currency][i]

    def to_usd(self, amount: Decimal, currency: str, on: date) -> tuple[Decimal | None, Decimal | None]:
        rate = self.rate(currency, on)
        if rate is None:
            return None, None
        return (amount * rate).quantize(CENT, rounding=ROUND_HALF_UP), rate


# Synthetic demo rates (USD per unit) — clearly labelled source "synthetic-demo"; real tenants upload or sync rates.
DEMO_BASE_RATES = {"GBP": 1.27, "EUR": 1.09, "INR": 0.0120, "SGD": 0.74, "BRL": 0.18}


def synthetic_rate(currency: str, on: date) -> Decimal:
    if currency == "USD":
        return Decimal(1)
    base = DEMO_BASE_RATES[currency]
    wobble = 1 + 0.01 * math.sin(on.toordinal() / 9 + len(currency) * 7 + ord(currency[0]))
    return Decimal(str(round(base * wobble, 8)))
