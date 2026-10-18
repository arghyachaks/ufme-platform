"""Rule-only baseline matcher — the "typical incumbent": exact reference + amount tolerance, then amount-only.

Deliberately simple. It exists to give the benchmark a floor that every UFME engine version must beat.
"""

from collections import defaultdict
from datetime import date

from app.engines.benchmark.model import Line, Prediction

TOLERANCE = 0.005  # 0.5% in USD
DATE_WINDOW = 3


def _gap(a: Line, b: Line) -> float:
    base = max(abs(a.amount_usd), abs(b.amount_usd), 1.0)
    return abs(a.amount_usd + b.amount_usd) / base


def _content_key(x: Line) -> tuple[float, date, str, str, str, str]:
    """Order by business content, so results don't depend on input order or id naming (id only breaks exact clones)."""
    return (-abs(x.amount_usd), x.value_date, x.reference_norm or "", x.description, x.currency, x.id)


def match(lines: list[Line]) -> list[Prediction]:
    by_pair: dict[tuple[str, str], tuple[list[Line], list[Line]]] = defaultdict(lambda: ([], []))
    for x in lines:
        by_pair[x.pair][0 if x.side == "A" else 1].append(x)

    out: list[Prediction] = []
    for side_a, side_b in by_pair.values():
        used: set[str] = set()
        b_by_ref: dict[str, list[Line]] = defaultdict(list)
        for y in side_b:
            if y.reference_norm:
                b_by_ref[y.reference_norm].append(y)
        # Rule 1: exact normalized reference + amount within tolerance → auto (tight) or suggest.
        for x in sorted(side_a, key=_content_key):
            if not x.reference_norm:
                continue
            best = min(
                (y for y in b_by_ref.get(x.reference_norm, []) if y.id not in used),
                key=lambda y: (_gap(x, y), _content_key(y)),
                default=None,
            )
            if best is not None and _gap(x, best) <= TOLERANCE:
                used.update((x.id, best.id))
                tight = _gap(x, best) <= 0.001 and abs((x.value_date - best.value_date).days) <= 1
                out.append(
                    Prediction(
                        frozenset((x.id, best.id)),
                        0.97 if tight else 0.85,
                        "auto" if tight else "suggest",
                        ["R1 reference + amount"],
                    )
                )
        # Rule 2: amount within tolerance and date window, no reference → suggest.
        rest_b = sorted((y for y in side_b if y.id not in used), key=_content_key)
        for x in sorted((x for x in side_a if x.id not in used), key=_content_key):
            cands = [
                y
                for y in rest_b
                if y.id not in used
                and _gap(x, y) <= TOLERANCE
                and abs((x.value_date - y.value_date).days) <= DATE_WINDOW
            ]
            if cands:
                best = min(
                    cands,
                    key=lambda y: (_gap(x, y), abs((x.value_date - y.value_date).days), _content_key(y)),
                )
                used.update((x.id, best.id))
                out.append(Prediction(frozenset((x.id, best.id)), 0.6, "suggest", ["R2 amount + date"]))
    return out
