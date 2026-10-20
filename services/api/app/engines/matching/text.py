"""String similarity. Uses RapidFuzz (C++) when installed; identical pure-Python fallback otherwise."""

import re

try:  # pragma: no cover - exercised implicitly in Docker/CI
    from rapidfuzz.distance import JaroWinkler as _JW

    def jaro_winkler(a: str, b: str) -> float:
        return float(_JW.similarity(a, b))

except ImportError:  # pragma: no cover - fallback for minimal environments

    def jaro_winkler(a: str, b: str) -> float:
        if a == b:
            return 1.0
        la, lb = len(a), len(b)
        if not la or not lb:
            return 0.0
        window = max(la, lb) // 2 - 1
        ma, mb = [False] * la, [False] * lb
        matches = 0
        for i, ch in enumerate(a):
            lo, hi = max(0, i - window), min(i + window + 1, lb)
            for j in range(lo, hi):
                if not mb[j] and b[j] == ch:
                    ma[i] = mb[j] = True
                    matches += 1
                    break
        if not matches:
            return 0.0
        t, k = 0, 0
        for i in range(la):
            if ma[i]:
                while not mb[k]:
                    k += 1
                if a[i] != b[k]:
                    t += 1
                k += 1
        jaro = (matches / la + matches / lb + (matches - t / 2) / matches) / 3
        prefix = 0
        for x, y in zip(a[:4], b[:4], strict=False):
            if x != y:
                break
            prefix += 1
        return jaro + prefix * 0.1 * (1 - jaro)


try:  # pragma: no cover
    from rapidfuzz.distance import OSA as _OSA

    def edit_distance(a: str, b: str) -> int:
        """Optimal-string-alignment distance: substitutions, insertions, deletions, adjacent transpositions."""
        return int(_OSA.distance(a, b))

except ImportError:  # pragma: no cover

    def edit_distance(a: str, b: str) -> int:
        la, lb = len(a), len(b)
        d = [[0] * (lb + 1) for _ in range(la + 1)]
        for i in range(la + 1):
            d[i][0] = i
        for j in range(lb + 1):
            d[0][j] = j
        for i in range(1, la + 1):
            for j in range(1, lb + 1):
                cost = 0 if a[i - 1] == b[j - 1] else 1
                d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + cost)
                if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                    d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
        return d[la][lb]


_OCR_CANON = str.maketrans({"O": "0", "I": "1", "L": "1", "S": "5", "B": "8", "Z": "2"})


def canonical(ref: str | None) -> str:
    """OCR-canonical form: characters commonly confused by OCR/typing map to one glyph (applied to both sides)."""
    return (ref or "").translate(_OCR_CANON)


def affix(a: str, b: str, max_extra: int = 4) -> bool:
    """One reference is the other plus a short prefix/suffix (ERP-added 'SG-', split '/2', truncated field)."""
    if not a or not b or a == b:
        return False
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return (
        len(short) >= 6
        and len(long_) - len(short) <= max_extra
        and (long_.startswith(short) or long_.endswith(short))
    )


_DIGITS = re.compile(r"\d+")
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-/._]{4,}")
_NOISE = re.compile(r"[^A-Z0-9]")


def digit_core(ref: str | None) -> str | None:
    """Longest digit run without leading zeros (≥ 3 digits): survives prefixes, separators and most typos."""
    if not ref:
        return None
    runs = [r.lstrip("0") for r in _DIGITS.findall(ref)]
    best = max(runs, key=len, default="")
    return best if len(best) >= 3 else None


def reference_tokens(text: str) -> set[str]:
    """Reference-like tokens inside free text (descriptions), normalized like references."""
    return {_NOISE.sub("", t.upper()) for t in _TOKEN.findall(text or "")} - {""}


def grams(text: str, n: int = 3) -> set[str]:
    return {text[i : i + n] for i in range(len(text) - n + 1)} if len(text) >= n else {text}
