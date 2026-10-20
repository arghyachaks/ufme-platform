"""Ground-truth scenario generator (v2): realistic intercompany ledgers where every line knows its true match.

Each "event" draws one scenario from the library below and emits the lines both entities would book, plus the
truth group(s). Decoys and orphans are truth singletons: a correct engine must leave them unmatched.
"""

import hashlib
import random
from collections.abc import Callable
from dataclasses import replace
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from itertools import pairwise

from app.engines.augmented_data.fx import synthetic_rate
from app.engines.benchmark.model import Dataset, Line, TruthGroup
from app.engines.data_quality.normalize import normalize_reference

GENERATOR_VERSION = "2.1"  # 2.1: decoys carry unrelated references (2.0 decoys were one edit away)
ENTITY_CURRENCY = {"US01": "USD", "UK02": "GBP", "DE03": "EUR", "IN04": "INR", "SG05": "SGD", "BR06": "BRL"}
PERIOD_START = date(2026, 8, 1)
KINDS = ["IC loan", "IC service fee", "IC royalty", "IC recharge", "IC dividend", "IC interest"]

# scenario → (weight, difficulty)
SCENARIOS: dict[str, tuple[float, int]] = {
    "clean": (38, 1),
    "fx_source_mismatch": (7, 2),
    "fx_rounding": (4, 1),
    "timing_lag": (7, 1),
    "period_cutoff": (3, 2),
    "bank_fee": (4, 2),
    "withholding_tax": (2, 2),
    "split_1m": (5, 2),
    "bundle_m1": (4, 2),
    "netting_mm": (2, 3),
    "ref_typo": (4, 2),
    "ref_ocr": (2, 2),
    "ref_prefix": (2, 1),
    "ref_truncated": (1, 2),
    "ref_missing": (2, 3),
    "ref_in_description": (1, 3),
    "duplicate_posting": (2, 2),
    "reversal_repost": (1, 3),
    "orphan": (4, 1),
    "decoy_same_amount": (3, 3),
    "decoy_same_ref": (2, 3),
}
SINGLETON_SCENARIOS = {"orphan", "decoy_same_amount", "decoy_same_ref", "duplicate_extra"}

_KEYBOARD = {
    c: n
    for c, n in zip(
        "1234567890QWERTYUIOPASDFGHJKLZXCVBNM", "2134567809WQRETYIUPOSADGFJHLKXZVCNBM", strict=True
    )
}
_OCR = {"0": "O", "O": "0", "1": "I", "I": "1", "5": "S", "S": "5", "8": "B", "B": "8"}
CENT = Decimal("0.01")


def _usd_to_local(usd: Decimal, ccy: str, on: date) -> Decimal:
    return (usd / synthetic_rate(ccy, on)).quantize(CENT, rounding=ROUND_HALF_UP)


def _local_to_usd(local: Decimal, ccy: str, on: date) -> float:
    return float((local * synthetic_rate(ccy, on)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


class _Builder:
    def __init__(self, seed: int):
        self.rnd = random.Random(seed)
        self.seed = seed
        self.lines: list[Line] = []
        self.truth: list[TruthGroup] = []
        self._n = 0
        self._g = 0

    # ---- primitives ---------------------------------------------------------------------------------
    def line(
        self,
        entity: str,
        partner: str,
        local: Decimal,
        when: date,
        reference: str,
        kind: str,
        posting: date | None = None,
        description: str | None = None,
    ) -> Line:
        self._n += 1
        ccy = ENTITY_CURRENCY[entity]
        line = Line(
            id=f"L{self.seed:03d}-{self._n:08d}",
            entity=entity,
            counterparty=partner,
            amount=float(local),
            currency=ccy,
            amount_usd=_local_to_usd(local, ccy, when),
            value_date=when,
            posting_date=posting or when,
            reference=reference,
            reference_norm=normalize_reference(reference),
            description=description or f"{kind} {entity}->{partner}",
            account="1910" if local > 0 else "2910",
        )
        self.lines.append(line)
        return line

    def group(
        self, scenario: str, lines: list[Line], difficulty: int | None = None, twin_of: str | None = None
    ) -> None:
        self._g += 1
        self.truth.append(
            TruthGroup(
                id=f"G{self.seed:03d}-{self._g:07d}",
                scenario=scenario,
                line_ids=frozenset(x.id for x in lines),
                difficulty=difficulty if difficulty is not None else SCENARIOS.get(scenario, (0, 2))[1],
                twin_of=twin_of,
            )
        )

    def amount_usd(self) -> Decimal:
        r = self.rnd.random()
        if r < 0.15:  # round-number spike
            return Decimal(
                self.rnd.choice([1_000, 5_000, 10_000, 25_000, 50_000, 100_000, 250_000, 1_000_000])
            )
        return Decimal(str(round(10 ** self.rnd.uniform(2.7, 6.3), 2)))  # log-uniform 500 … 2M

    def ref(self, a: str, b: str, k: int) -> str:
        return self.rnd.choice([f"IC-{a}-{b}-{k:06d}", f"ICL{k:07d}", f"INV-{k:06d}/{a}", f"JE{k:08d}"])

    # ---- reference noise ----------------------------------------------------------------------------
    def typo(self, ref: str) -> str:
        chars = list(ref)
        idx = [i for i, c in enumerate(chars) if c.upper() in _KEYBOARD]
        if not idx:
            return ref + "X"
        i = self.rnd.choice(idx)
        op = self.rnd.random()
        if op < 0.5:
            chars[i] = _KEYBOARD[chars[i].upper()]
        elif op < 0.8 and i + 1 < len(chars):
            chars[i], chars[i + 1] = chars[i + 1], chars[i]
        else:
            del chars[i]
        return "".join(chars)

    def ocr(self, ref: str) -> str:
        idx = [i for i, c in enumerate(ref) if c in _OCR]
        if not idx:
            return self.typo(ref)
        chars = list(ref)
        for i in self.rnd.sample(idx, k=min(len(idx), self.rnd.randint(1, 2))):
            chars[i] = _OCR[chars[i]]
        return "".join(chars)


def _mirror(
    b: _Builder,
    scenario: str,
    a: str,
    p: str,
    k: int,
    *,
    usd: Decimal | None = None,
    ref_a: str | None = None,
    ref_b: str | None = None,
    lag: int = 0,
    b_usd: Decimal | None = None,
    b_rate_factor: Decimal = Decimal(1),
    desc_b: str | None = None,
) -> tuple[Line, Line]:
    usd = usd if usd is not None else b.amount_usd()
    day = PERIOD_START + timedelta(days=b.rnd.randrange(26))
    kind = b.rnd.choice(KINDS)
    ref = b.ref(a, p, k)
    la = b.line(
        a, p, _usd_to_local(usd, ENTITY_CURRENCY[a], day), day, ref_a if ref_a is not None else ref, kind
    )
    when_b = day + timedelta(days=lag)
    local_b = (
        _usd_to_local(-(b_usd if b_usd is not None else usd), ENTITY_CURRENCY[p], when_b) * b_rate_factor
    )
    lb = b.line(
        p, a, local_b.quantize(CENT), when_b, ref_b if ref_b is not None else ref, kind, description=desc_b
    )
    b.group(scenario, [la, lb])
    return la, lb


def _event(b: _Builder, scenario: str, k: int) -> None:
    rnd = b.rnd
    a, p = rnd.sample(list(ENTITY_CURRENCY), 2)
    match scenario:
        case "clean":
            _mirror(b, scenario, a, p, k)
        case "fx_source_mismatch":  # counterparty converts at a different rate source (±0.1-0.6%)
            f = Decimal(str(1 + rnd.choice([-1, 1]) * rnd.uniform(0.001, 0.006)))
            _mirror(b, scenario, a, p, k, b_rate_factor=f)
        case "fx_rounding":
            la, lb = _mirror(b, scenario, a, p, k)
            # B books in whole units: replace with rounded line (same truth group id via rebuild)
            b.lines.pop()
            b.truth.pop()
            rounded = Decimal(round(lb.amount))
            lb2 = b.line(
                lb.entity,
                lb.counterparty,
                rounded,
                lb.value_date,
                lb.reference,
                "IC",
                description=lb.description,
            )
            b.group(scenario, [la, lb2])
        case "timing_lag":
            _mirror(b, scenario, a, p, k, lag=rnd.randint(1, 6))
        case "period_cutoff":
            _mirror(b, scenario, a, p, k, lag=rnd.randint(3, 12))
        case "bank_fee":  # receiving side short by a fixed fee
            usd = b.amount_usd()
            _mirror(b, scenario, a, p, k, usd=usd, b_usd=usd - Decimal(rnd.choice([10, 15, 25, 35, 50])))
        case "withholding_tax":
            usd = b.amount_usd()
            _mirror(
                b,
                scenario,
                a,
                p,
                k,
                usd=usd,
                b_usd=(usd * Decimal(str(1 - rnd.choice([0.05, 0.1, 0.15])))).quantize(CENT),
            )
        case "split_1m" | "bundle_m1":
            usd = b.amount_usd() + Decimal(1000)
            day = PERIOD_START + timedelta(days=rnd.randrange(22))
            ref, kind, n = b.ref(a, p, k), rnd.choice(KINDS), rnd.randint(2, 4)
            parts = [Decimal(str(rnd.uniform(0.15, 1))) for _ in range(n)]
            shares = [(usd * x / sum(parts)).quantize(CENT) for x in parts]
            shares[-1] = usd - sum(shares[:-1], Decimal(0))
            one, many = (a, p) if scenario == "split_1m" else (p, a)
            sign = Decimal(1) if one == a else Decimal(-1)
            whole = b.line(one, many, _usd_to_local(sign * usd, ENTITY_CURRENCY[one], day), day, ref, kind)
            pieces = [
                b.line(
                    many,
                    one,
                    _usd_to_local(-sign * s, ENTITY_CURRENCY[many], day + timedelta(days=i)),
                    day + timedelta(days=i),
                    ref if rnd.random() < 0.7 else f"{ref}/{i + 1}",
                    kind,
                )
                for i, s in enumerate(shares)
            ]
            b.group(scenario, [whole, *pieces])
        case "netting_mm":  # several invoices on each side settled as one net position
            day = PERIOD_START + timedelta(days=rnd.randrange(20))
            kind, ref = rnd.choice(KINDS), f"NET-{a}-{p}-{k:05d}"
            a_amounts = [b.amount_usd() for _ in range(rnd.randint(2, 3))]
            total = sum(a_amounts, Decimal(0))
            nb = rnd.randint(2, 3)
            cuts = sorted(Decimal(str(rnd.uniform(0.2, 0.8))) for _ in range(nb - 1))
            bounds = [Decimal(0), *cuts, Decimal(1)]
            b_amounts = [(total * (hi - lo)).quantize(CENT) for lo, hi in pairwise(bounds)]
            b_amounts[-1] = total - sum(b_amounts[:-1], Decimal(0))
            side_a = [
                b.line(a, p, _usd_to_local(x, ENTITY_CURRENCY[a], day), day, f"{ref}-A{i}", kind)
                for i, x in enumerate(a_amounts)
            ]
            side_b = [
                b.line(
                    p,
                    a,
                    _usd_to_local(-x, ENTITY_CURRENCY[p], day + timedelta(days=2)),
                    day + timedelta(days=2),
                    ref,
                    kind,
                )
                for x in b_amounts
            ]
            b.group(scenario, [*side_a, *side_b])
        case "ref_typo" | "ref_ocr" | "ref_prefix" | "ref_truncated":
            ref = b.ref(a, p, k)
            noisy = {
                "ref_typo": b.typo,
                "ref_ocr": b.ocr,
                "ref_prefix": lambda r: rnd.choice(["SG-", "INT/", "00"]) + r,
                "ref_truncated": lambda r: r[: max(6, len(r) - rnd.randint(2, 4))],
            }[scenario](ref)
            _mirror(b, scenario, a, p, k, ref_a=ref, ref_b=noisy)
        case "ref_missing":
            _mirror(b, scenario, a, p, k, ref_b="")
        case "ref_in_description":
            ref = b.ref(a, p, k)
            _mirror(b, scenario, a, p, k, ref_a=ref, ref_b="", desc_b=f"Settlement of {ref} per agreement")
        case "duplicate_posting":  # B books the same document twice: one copy matches, the extra must not
            la, lb = _mirror(b, scenario, a, p, k)
            extra = b.line(
                lb.entity,
                lb.counterparty,
                Decimal(str(lb.amount)),
                lb.value_date + timedelta(days=rnd.randint(0, 1)),
                lb.reference,
                "IC",
                description=lb.description,
            )
            same_day = extra.value_date == lb.value_date
            b.group("duplicate_extra", [extra], difficulty=3, twin_of=lb.id if same_day else None)
        case "reversal_repost":  # A posts, reverses, re-posts; reversal pair nets to zero on A's side
            la, lb = _mirror(b, scenario, a, p, k)
            wrong = b.line(
                a,
                p,
                Decimal(str(la.amount)) * Decimal("1.1"),
                la.value_date - timedelta(days=2),
                la.reference,
                "IC",
            )
            rev = b.line(
                a,
                p,
                -Decimal(str(wrong.amount)),
                la.value_date - timedelta(days=1),
                f"REV-{la.reference}",
                "IC",
            )
            b.group("reversal_pair", [wrong, rev], difficulty=3)
        case "orphan":
            usd = b.amount_usd()
            day = PERIOD_START + timedelta(days=rnd.randrange(28))
            o = b.line(
                a, p, _usd_to_local(usd, ENTITY_CURRENCY[a], day), day, b.ref(a, p, k), rnd.choice(KINDS)
            )
            b.group("orphan", [o])
        case (
            "decoy_same_amount"
        ):  # true pair + a look-alike with the same amount and date but another reference
            la, lb = _mirror(b, "clean", a, p, k)
            d = b.line(
                lb.entity,
                lb.counterparty,
                Decimal(str(lb.amount)),
                lb.value_date,
                b.ref(a, p, rnd.randint(600_000, 999_999)),
                "IC",
            )
            b.group("decoy_same_amount", [d])
        case "decoy_same_ref":  # same reference, materially different amount (e.g. next month's charge)
            la, lb = _mirror(b, "clean", a, p, k)
            d = b.line(
                lb.entity,
                lb.counterparty,
                (Decimal(str(lb.amount)) * Decimal("1.37")).quantize(CENT),
                lb.value_date + timedelta(days=3),
                lb.reference,
                "IC",
            )
            b.group("decoy_same_ref", [d])
        case _:
            raise ValueError(f"unknown scenario {scenario}")


def generate(
    size: int, seed: int = 1, name: str = "custom", weights: dict[str, float] | None = None
) -> Dataset:
    """About `size` lines. Deterministic for (size, seed, weights, GENERATOR_VERSION)."""
    b = _Builder(seed)
    names = list(SCENARIOS)
    w = [(weights or {}).get(s, SCENARIOS[s][0]) for s in names]
    k = 0
    while len(b.lines) < size:
        k += 1
        _event(b, b.rnd.choices(names, weights=w)[0], k)
    # Hide generation order: shuffle lines and replace sequential ids with random ones, so no matcher can
    # exploit adjacency or id order (both sides of a pair are generated next to each other).
    order = list(range(len(b.lines)))
    b.rnd.shuffle(order)
    new_ids = {line.id: f"T{b.rnd.getrandbits(48):012x}" for line in b.lines}
    lines = [replace(b.lines[i], id=new_ids[b.lines[i].id]) for i in order]
    truth = [
        replace(
            g,
            line_ids=frozenset(new_ids[i] for i in g.line_ids),
            twin_of=new_ids[g.twin_of] if g.twin_of else None,
        )
        for g in b.truth
    ]
    return Dataset(name=name, lines=lines, truth=truth, seed=seed, version=GENERATOR_VERSION)


GOLDEN: dict[str, tuple[int, int]] = {
    "small": (1_000, 101),
    "medium": (100_000, 202),
    "large": (1_000_000, 303),
}


def golden(name: str) -> Dataset:
    size, seed = GOLDEN[name]
    return generate(size, seed, name=name)


def fingerprint(ds: Dataset) -> str:
    h = hashlib.sha256(ds.version.encode())
    for x in ds.lines:
        h.update(
            f"{x.id}|{x.entity}|{x.counterparty}|{x.amount:.2f}|{x.currency}|{x.value_date}|{x.reference}\n".encode()
        )
    for g in ds.truth:
        h.update(f"{g.id}|{g.scenario}|{','.join(sorted(g.line_ids))}\n".encode())
    return h.hexdigest()


Transform = Callable[[Dataset], Dataset]
