"""Candidate generation (L2): several independent blocking strategies, unioned. Optimized for recall."""

import bisect
from collections import Counter, defaultdict
from dataclasses import dataclass

from app.engines.benchmark.model import Line
from app.engines.matching.text import canonical, description_words, digit_core, grams, reference_tokens

AMOUNT_WINDOW = 0.01  # 1% …
AMOUNT_FLOOR_USD = 60.0  # … or $60 (bank fees), whichever is larger
DATE_WINDOW_DAYS = 15
MAX_AMOUNT_CANDIDATES = 25
GRAM_MIN_JACCARD = 0.5
GRAM_MAX_DOC_FREQ = 0.02  # ignore 3-grams shared by > 2% of a pair's references (e.g. "US0", "IC-")
MAX_GRAM_CANDIDATES = 10


@dataclass
class Prepared:
    line: Line
    canon: str
    core: str | None
    desc_tokens: set[str]
    grams: set[str]
    words: frozenset[str] = frozenset()  # description content words (3e text evidence)


def prepare(line: Line) -> Prepared:
    ref = line.reference_norm or ""
    canon = canonical(ref)
    return Prepared(
        line,
        canon,
        digit_core(canon),
        reference_tokens(line.description),
        grams(canon) if len(canon) >= 6 else set(),
        description_words(line.description),
    )


def generate(side_a: list[Prepared], side_b: list[Prepared]) -> dict[tuple[str, str], set[str]]:
    """Return {(a_id, b_id): {blocking sources}} for one entity pair."""
    out: dict[tuple[str, str], set[str]] = defaultdict(set)

    def add(a: Prepared, b: Prepared, source: str) -> None:
        out[(a.line.id, b.line.id)].add(source)

    by_ref: dict[str, list[Prepared]] = defaultdict(list)
    by_core: dict[str, list[Prepared]] = defaultdict(list)
    by_canon: dict[str, list[Prepared]] = defaultdict(list)
    for b in side_b:
        if b.canon:
            by_canon[b.canon].append(b)
        if b.line.reference_norm:
            by_ref[b.line.reference_norm].append(b)
        if b.core:
            by_core[b.core].append(b)
    a_by_ref: dict[str, list[Prepared]] = defaultdict(list)
    for a in side_a:
        if a.line.reference_norm:
            a_by_ref[a.line.reference_norm].append(a)

    for a in side_a:
        for b in by_ref.get(a.line.reference_norm or "", []):  # 1. exact reference
            add(a, b, "ref")
        for b in by_canon.get(a.canon, []) if a.canon else []:  # 1b. OCR-canonical reference
            add(a, b, "ref_canonical")
        if a.core:
            for b in by_core.get(a.core, []):  # 2. digit core (prefix/separator/zero-padding robust)
                add(a, b, "digits")
        for token in a.desc_tokens:  # 5. reference quoted in description (both directions)
            for b in by_ref.get(token, []):
                add(a, b, "description")
    for b in side_b:
        for token in b.desc_tokens:
            for a in a_by_ref.get(token, []):
                add(a, b, "description")

    # 6. reference extended/truncated by a few characters (split "INV-1/2", trimmed fields), both directions.
    for b in side_b:
        ref = b.line.reference_norm or ""
        for k in (1, 2, 3):
            if len(ref) - k >= 6:
                for a in a_by_ref.get(ref[:-k], []):
                    add(a, b, "affix")
    for a in side_a:
        ref = a.line.reference_norm or ""
        for k in (1, 2, 3):
            if len(ref) - k >= 6:
                for b in by_ref.get(ref[:-k], []):
                    add(a, b, "affix")

    # 3. amount window (USD, mirrored sign) combined with a date window.
    ordered = sorted(side_b, key=lambda p: -p.line.amount_usd)
    keys = [-p.line.amount_usd for p in ordered]
    for a in side_a:
        target = a.line.amount_usd  # B books the mirror: -b.amount_usd ≈ a.amount_usd
        width = max(abs(target) * AMOUNT_WINDOW, AMOUNT_FLOOR_USD)
        lo, hi = bisect.bisect_left(keys, target - width), bisect.bisect_right(keys, target + width)
        window = [
            b for b in ordered[lo:hi] if abs((a.line.value_date - b.line.value_date).days) <= DATE_WINDOW_DAYS
        ]
        window.sort(key=lambda b: (abs(target + b.line.amount_usd), b.line.id))
        for b in window[:MAX_AMOUNT_CANDIDATES]:
            add(a, b, "amount")

    # 4. rare 3-gram overlap on references (typos, OCR, truncation).
    df: Counter[str] = Counter()
    for p in (*side_a, *side_b):
        df.update(p.grams)
    limit = max(3, int(GRAM_MAX_DOC_FREQ * (len(side_a) + len(side_b))))
    rare = {g for g, n in df.items() if n <= limit}
    index: dict[str, list[Prepared]] = defaultdict(list)
    for b in side_b:
        for g in b.grams & rare:
            index[g].append(b)
    for a in side_a:
        mine = a.grams & rare
        if len(mine) < 2:
            continue
        hits: Counter[str] = Counter()
        by_id: dict[str, Prepared] = {}
        for g in mine:
            for b in index.get(g, []):
                hits[b.line.id] += 1
                by_id[b.line.id] = b
        scored = []
        for bid, shared in hits.items():
            theirs = by_id[bid].grams & rare
            jaccard = shared / len(mine | theirs)
            if jaccard >= GRAM_MIN_JACCARD:
                scored.append((-jaccard, bid))
        for _, bid in sorted(scored)[:MAX_GRAM_CANDIDATES]:
            add(a, by_id[bid], "grams")
    return out
