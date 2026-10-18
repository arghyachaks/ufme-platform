"""Synthetic intercompany ledger generator — realistic noise for tests, demos and load testing.

python -m app.engines.connectors.synthetic --rows 100000 --out ic_aug.csv
"""

import argparse
import csv
import random
from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from app.engines.augmented_data.fx import synthetic_rate

ENTITY_CURRENCY = {"US01": "USD", "UK02": "GBP", "DE03": "EUR", "IN04": "INR", "SG05": "SGD", "BR06": "BRL"}
HEADERS = [
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
KINDS = ["IC loan", "IC service fee", "IC royalty", "IC recharge", "IC dividend"]


def _fmt(amount: Decimal) -> str:
    return f"{amount:.2f}"


def generate(
    rows: int, seed: int = 7, period: date = date(2026, 8, 1), dirty_rate: float = 0.02
) -> Iterator[dict[str, str]]:
    """Yield about `rows` ledger lines: mirrored IC pairs with FX gaps, timing gaps, splits, orphans and dirt."""
    rnd = random.Random(seed)
    entities = list(ENTITY_CURRENCY)
    produced = 0
    k = 0
    while produced < rows:
        k += 1
        a, b = rnd.sample(entities, 2)
        day = period + timedelta(days=rnd.randrange(28))
        usd = Decimal(rnd.choice([rnd.randint(500, 50_000), rnd.randint(50_000, 2_000_000)]))
        ref = f"IC-{a}-{b}-{seed:04d}{k:07d}"
        kind = rnd.choice(KINDS)

        def line(
            entity: str,
            partner: str,
            amount_usd: Decimal,
            when: date,
            reference: str,
            n: int,
            k: int = k,
            kind: str = kind,
            a: str = a,
            b: str = b,
        ) -> dict[str, str]:
            ccy = ENTITY_CURRENCY[entity]
            local = (amount_usd / synthetic_rate(ccy, when)).quantize(Decimal("0.01"))
            return {
                "document_id": f"{entity}-{seed:04d}{k:07d}-{n}",  # unique per pull (seed)
                "company_code": entity,
                "trading_partner": partner,
                "gl_account": "1910" if amount_usd > 0 else "2910",
                "amount": _fmt(local),
                "currency": ccy,
                "document_date": when.isoformat(),
                "posting_date": when.isoformat(),
                "reference": reference,
                "text": f"{kind} {a}->{b}",
            }

        out = [line(a, b, usd, day, ref, 1)]
        r = rnd.random()
        b_ref = ref if rnd.random() > 0.2 else f" {ref.lower().replace('-', ' / ')} "  # reference noise
        if r < 0.04:
            pass  # orphan: counterparty never booked it
        elif r < 0.07:  # split settlement 1:M
            parts = rnd.randint(2, 3)
            share = (usd / parts).quantize(Decimal("0.01"))
            for i in range(parts):
                amt = share if i < parts - 1 else usd - share * (parts - 1)
                out.append(line(b, a, -amt, day + timedelta(days=rnd.randint(0, 6)), b_ref, i + 1))
        else:
            fx_gap = Decimal(str(1 + rnd.uniform(-0.004, 0.004))) if rnd.random() < 0.08 else Decimal(1)
            when = day + timedelta(days=rnd.randint(1, 5)) if rnd.random() < 0.1 else day
            out.append(line(b, a, -(usd * fx_gap), when, b_ref, 1))

        for row in out:
            if rnd.random() < dirty_rate:
                defect = rnd.choice(["currency", "partner", "amount", "duplicate", "case"])
                if defect == "currency":
                    row["currency"] = "XX"
                elif defect == "partner":
                    row["trading_partner"] = ""
                elif defect == "amount":
                    row["amount"] = "n/a"
                elif defect == "case":
                    row["currency"] = row["currency"].lower()
                elif defect == "duplicate":
                    produced += 1
                    yield dict(row)
            produced += 1
            yield row
            if produced >= rows:
                return


def write_csv(path: Path, rows: int, seed: int = 7) -> int:
    count = 0
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADERS)
        writer.writeheader()
        for row in generate(rows, seed):
            writer.writerow(row)
            count += 1
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(f"wrote {write_csv(args.out, args.rows, args.seed)} rows to {args.out}")
