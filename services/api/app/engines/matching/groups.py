"""Group construction (L4, Stage 3c): 1:M, M:1 and M:M matches, plus same-side reversal pairs.

Runs after the 1:1 assignment on what is still open. Two evidence paths, both reference-led so precision holds:
- Reference families: raw references reduced to a root ("IC/US01/UK02/1023/2" -> "ICUS01UK021023",
  "NET-..-00012-A0" -> "NET..00012"). A family that nets to zero within policy becomes one group; otherwise the
  unique subset that nets is proposed for review.
- Reversals: a line and its "REV-" counterpart on the same side that cancel exactly.
Amount-only subset-sum (no shared reference) is deliberately not auto-matched: it is where false matches live.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

from app.engines.benchmark.model import Line

POLICY_TOLERANCE = 0.005  # 0.5% of the group's exposure …
ABS_CAP_USD = 500.0  # … capped at 500 USD (policy P-01)
MAX_FAMILY = 14  # larger families are left for review: subset search grows as 2^n
MAX_SPAN_DAYS = 31
REVERSAL_DAYS = 10
_SPLIT = re.compile(r"[^A-Z0-9]+")
_SUFFIX = re.compile(r"(?:[A-Z]|PART)?\d{1,2}")  # "/2", "-A0"; never a 2-letter entity code like SG05
_REV = {"REV", "RV", "REVERSAL", "STORNO", "CANCEL"}


def ref_root(raw: str) -> tuple[str | None, bool]:
    """(root, is_reversal). Strips a short trailing split/line suffix and a leading reversal marker."""
    tokens = [t for t in _SPLIT.split((raw or "").upper()) if t]
    rev = bool(tokens) and tokens[0] in _REV
    if rev:
        tokens = tokens[1:]
    if len(tokens) >= 2 and _SUFFIX.fullmatch(tokens[-1]) and len("".join(tokens[:-1])) >= 8:
        tokens = tokens[:-1]
    root = "".join(tokens)
    return (root if len(root) >= 8 else None), rev


def tolerance(exposure: float) -> float:
    return min(POLICY_TOLERANCE * exposure, ABS_CAP_USD)


@dataclass
class GroupResult:
    lines: list[Line]
    match_type: str  # 1:M | M:1 | M:M | reversal
    features: dict[str, Any]
    log_odds: float
    contributions: dict[str, float]
    rules: list[str] = field(default_factory=list)

    @property
    def probability(self) -> float:
        return 1 / (1 + math.exp(-self.log_odds))

    @property
    def a(self) -> Line:
        return next((x for x in self.lines if x.side == "A"), self.lines[0])

    @property
    def b(self) -> Line:
        return next((x for x in self.lines if x.side == "B"), self.lines[-1])

    @property
    def exposure_usd(self) -> float:
        a = sum(abs(x.amount_usd) for x in self.lines if x.side == "A")
        b = sum(abs(x.amount_usd) for x in self.lines if x.side == "B")
        return max(a, b) if a and b else sum(abs(x.amount_usd) for x in self.lines) / 2


def _result(lines: list[Line], kind: str, root: str, whole_family: bool, unique: bool) -> GroupResult:
    net = abs(sum(x.amount_usd for x in lines))
    na = sum(1 for x in lines if x.side == "A")
    nb = len(lines) - na
    mtype = kind if kind == "reversal" else f"{'1' if na == 1 else 'M'}:{'1' if nb == 1 else 'M'}"
    dates = [x.value_date for x in lines]
    span = (max(dates) - min(dates)).days
    g = GroupResult(
        lines=sorted(lines, key=lambda x: (x.side, -abs(x.amount_usd), x.id)),
        match_type=mtype,
        features={},
        log_odds=0.0,
        contributions={},
    )
    exposure = g.exposure_usd
    local_net = abs(sum(x.amount for x in lines)) if kind == "reversal" else net
    c = {"prior": -4.0, "reference": 4.5, "amount": 5.0 if local_net <= 0.01 else 4.0}
    if not whole_family:
        c["family"] = -1.5  # part of the family nets; the rest stays open
    if not unique:
        c["ambiguity"] = -3.0
    if span > 15:
        c["date"] = -1.0
    if len(lines) > 8:
        c["size"] = -1.0
    g.contributions, g.log_odds = c, sum(c.values())
    g.features = {
        "amount_gap": net / max(exposure, 1.0),
        "amount_gap_usd": net,
        "date_gap_days": span,
        "ref_root": root,
        "items_a": na,
        "items_b": nb,
        "whole_family": whole_family,
        "unique": unique,
        "blocking": ["ref_family"],
    }
    g.rules = ["G-REV" if kind == "reversal" else "G-REF-FAMILY"]
    return g


def _nets(lines: list[Line]) -> bool:
    exposure = max(sum(abs(x.amount_usd) for x in lines) / 2, 1.0)
    return abs(sum(x.amount_usd for x in lines)) <= tolerance(exposure)


def _subsets(a: list[Line], b: list[Line]) -> list[list[Line]]:
    """All (A-subset, B-subset) combinations that net within policy, smallest first; capped for safety."""
    sums_b: list[tuple[float, tuple[Line, ...]]] = [
        (sum(x.amount_usd for x in combo), combo)
        for k in range(1, len(b) + 1)
        for combo in combinations(b, k)
    ]
    out: list[list[Line]] = []
    for k in range(1, len(a) + 1):
        for ca in combinations(a, k):
            sa = sum(x.amount_usd for x in ca)
            for sb, cb in sums_b:
                if len(ca) + len(cb) < 3:
                    continue  # 1:1 is the assignment step's job
                exposure = max(abs(sa), abs(sb), 1.0)
                if abs(sa + sb) <= tolerance(exposure):
                    out.append([*ca, *cb])
                    if len(out) > 4:
                        return out
    return out


def build(open_lines: list[Line]) -> list[GroupResult]:
    """Groups for one entity pair's open lines (already excluding auto 1:1 matches)."""
    fam: dict[str, list[tuple[Line, bool]]] = defaultdict(list)
    for x in open_lines:
        root, rev = ref_root(x.reference)
        if root:
            fam[root].append((x, rev))
    used: set[str] = set()
    out: list[GroupResult] = []

    # 1. Reversals: same side, a REV-marked line cancelling an original within days.
    for root, members in sorted(fam.items()):
        revs = [x for x, r in members if r]
        origs = [x for x, r in members if not r]
        for rv in sorted(revs, key=lambda x: x.id):
            hits = [
                o
                for o in origs
                if o.id not in used
                and o.side == rv.side
                and o.entity == rv.entity
                and o.currency == rv.currency
                and abs(o.amount + rv.amount)
                <= 0.005  # exact in booking currency (USD drifts with the FX date)
                and abs((o.value_date - rv.value_date).days) <= REVERSAL_DAYS
            ]
            if rv.id in used or not hits:
                continue
            hit = min(hits, key=lambda o: (abs((o.value_date - rv.value_date).days), o.id))
            out.append(_result([hit, rv], "reversal", root, True, len(hits) == 1))
            used |= {hit.id, rv.id}

    # 2. Cross-side reference families: 1:M, M:1, M:M.
    for root, members in sorted(fam.items()):
        lines = [x for x, r in members if x.id not in used and not r]
        a = [x for x in lines if x.side == "A"]
        b = [x for x in lines if x.side == "B"]
        if not a or not b or len(lines) < 3 or len(lines) > MAX_FAMILY:
            continue
        dates = [x.value_date for x in lines]
        if (max(dates) - min(dates)).days > MAX_SPAN_DAYS:
            continue
        if _nets(lines):
            out.append(_result(lines, "family", root, True, True))
            used |= {x.id for x in lines}
            continue
        found = _subsets(a, b)
        if found:
            best = min(found, key=lambda g: (abs(sum(x.amount_usd for x in g)), len(g)))
            out.append(_result(best, "family", root, False, len(found) == 1))
            used |= {x.id for x in best}
    return out
