"""Matching engine v1 (Stage 3b): candidates → pair features → rules + interpretable scorer → global 1:1 assignment.

Scoring is an explicit log-odds model so every point of confidence is explainable. Stage 3d replaces the
hand-set weights with a calibrated, monotonic GBDT trained on labels; the interface stays the same.
"""

import math
import multiprocessing as mp
import os
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from app.engines.benchmark.model import Line, Prediction
from app.engines.matching import candidates as cand
from app.engines.matching import groups as grp
from app.engines.matching import learned, residual
from app.engines.matching.assignment import max_weight_assignment
from app.engines.matching.rules import Rule, default_rules
from app.engines.matching.text import affix, edit_distance, jaccard, jaro_winkler

ENGINE_VERSION = "engine-1.3"  # + scorer version via version_label(); stored in a 64-char column
POLICY_TOLERANCE = 0.005  # auto-match only within the 0.5% tolerance policy
AUTO_THRESHOLD = 0.985
SUGGEST_THRESHOLD = 0.5
PARALLEL_MIN = 50_000  # lines; below this, process start-up costs more than it saves
MAX_WORKERS = int(os.environ.get("UFME_MATCH_WORKERS", "4"))  # memory: each process holds one entity pair
MAX_RESIDUAL_GAP = 0.2  # ref-strong pairs up to 20% apart are proposed with a residual (fees, withholding)


@dataclass
class PairResult:
    a: Line
    b: Line
    features: dict[str, Any]
    log_odds: float
    contributions: dict[str, float]
    rules: list[str] = field(default_factory=list)
    explain: dict[str, Any] | None = None  # model drivers + counterfactuals for suggestions (3d)
    index: int | None = None  # this pair's row in the entity pair's feature matrix, for explanations

    @property
    def probability(self) -> float:
        return 1 / (1 + math.exp(-self.log_odds))


@dataclass
class EngineResult:
    predictions: list[Prediction]
    candidate_pairs: set[frozenset[str]]
    details: dict[frozenset[str], "PairResult | grp.GroupResult"]
    alternatives: dict[frozenset[str], list[tuple[str, float]]]
    candidate_count: int = 0  # always set; candidate_pairs itself is only kept when asked (benchmarks)


def pair_features(
    a: cand.Prepared,
    b: cand.Prepared,
    sources: set[str],
    ambiguity: int,
    desc_similarity: float = 0.0,
    text_ambiguity: int = 1,
) -> dict[str, Any]:
    la, lb = a.line, b.line
    base = max(abs(la.amount_usd), abs(lb.amount_usd), 1.0)
    gap = abs(la.amount_usd + lb.amount_usd) / base
    ra, rb = la.reference_norm or "", lb.reference_norm or ""
    ca, cb = a.canon, b.canon
    both = bool(ra and rb)
    exact = both and ra == rb
    canon_exact = both and not exact and ca == cb
    if exact or canon_exact:
        edits = 0
    elif both and abs(len(ca) - len(cb)) <= 3:
        edits = edit_distance(ca, cb)
    else:
        edits = 99
    is_affix = both and affix(ca, cb)
    in_desc = (bool(ra) and (ra in b.desc_tokens or ca in b.desc_tokens)) or (
        bool(rb) and (rb in a.desc_tokens or cb in a.desc_tokens)
    )
    digits_equal = bool(a.core and a.core == b.core)
    typo = both and edits == 1 and min(len(ca), len(cb)) >= 8
    strong = exact or canon_exact or is_affix or in_desc or typo
    return {
        "amount_gap": gap,
        "amount_gap_usd": abs(la.amount_usd + lb.amount_usd),
        "date_gap_days": abs((la.value_date - lb.value_date).days),
        "ref_exact": exact,
        "ref_canonical_exact": canon_exact,
        "ref_edit_distance": edits,
        "ref_affix": is_affix,
        "digits_equal": digits_equal,
        "ref_similarity": jaro_winkler(ca, cb) if both else 0.0,
        "ref_in_description": in_desc,
        "ref_strong": strong,
        "ref_conflict": both and not strong and not digits_equal and edits > 2,
        "ref_missing": not both,
        "ambiguity": ambiguity,
        "desc_similarity": round(desc_similarity, 4),  # 3e: same kind of transaction, entities mirrored
        "text_ambiguity": text_ambiguity,  # look-alike amounts whose description also matches
        "blocking": sorted(sources),
    }


def score(f: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """Interpretable log-odds. Each term is reported as a contribution in the explanation."""
    c: dict[str, float] = {"prior": -4.0}
    gap = f["amount_gap"]
    c["amount"] = (
        5.0
        if gap <= 0.0005
        else 4.2
        if gap <= 0.002
        else 3.0
        if gap <= 0.005
        else 1.5
        if gap <= 0.0065
        else -1.0
        if gap <= 0.01
        else -3.0
        if gap <= MAX_RESIDUAL_GAP
        else -8.0
    )
    if f["ref_exact"]:
        c["reference"] = 4.5
    elif f["ref_canonical_exact"]:
        c["reference"] = 4.0  # OCR-style confusion only
    elif f["ref_in_description"] or f["ref_affix"]:
        c["reference"] = 3.5
    elif f["ref_edit_distance"] == 1 and f["ref_strong"]:
        c["reference"] = 3.0  # single typo in a long reference
    elif f["digits_equal"]:
        c["reference"] = 2.0
    elif f["ref_edit_distance"] == 2:
        c["reference"] = 0.5
    elif f["ref_conflict"]:
        c["reference"] = -4.0  # both sides carry references that genuinely differ: strong decoy signal
    else:
        c["reference"] = 0.0
    d = f["date_gap_days"]
    c["date"] = 0.5 if d == 0 else 0.0 if d <= 3 else -0.5 if d <= 7 else -1.2 if d <= 15 else -3.0
    if not f["ref_strong"] and f["ambiguity"] > 1:  # amount-only evidence with competing look-alikes
        c["ambiguity"] = -1.5 * min(f["ambiguity"] - 1, 4)
    if f["ref_strong"] and gap > 0.01:  # residual (fee/withholding) candidate: plausible but never auto
        c["residual"] = 2.5 if gap <= MAX_RESIDUAL_GAP else 0.0
    return sum(c.values()), c


def match(lines: list[Line], rules: list[Rule] | None = None, explain: bool = False) -> list[Prediction]:
    return run(lines, rules).predictions


def run(
    lines: list[Line],
    rules: list[Rule] | None = None,
    workers: int | None = None,
    keep_candidates: bool = True,
) -> EngineResult:
    """Entity pairs are independent, so large runs fan out across processes; results are merged in pair
    order, so output is identical to a serial run."""
    rules = sorted(rules if rules is not None else default_rules(), key=lambda r: r.priority)
    by_pair: dict[tuple[str, str], tuple[list[Line], list[Line]]] = defaultdict(lambda: ([], []))
    for line in lines:
        by_pair[line.pair][0 if line.side == "A" else 1].append(line)
    jobs = [(by_pair[k][0], by_pair[k][1], rules, keep_candidates) for k in sorted(by_pair)]
    if workers is None:
        workers = min(len(jobs), os.cpu_count() or 1, MAX_WORKERS) if len(lines) >= PARALLEL_MIN else 1
    if workers > 1:
        # "spawn", never fork: the caller may be multi-threaded (Celery thread pool, uvicorn) and a forked child
        # can inherit a lock held by another thread and hang forever. Spawned children also start without the
        # parent's ORM objects, so memory stays proportional to one entity pair.
        # Spawned children copy the parent's sys.path. Under Celery the project root is only reachable via a
        # relative entry, so pin the absolute root first or children can't import `app`.
        root = str(Path(__file__).resolve().parents[3])
        if root not in sys.path:
            sys.path.insert(0, root)
        biggest_first = sorted(range(len(jobs)), key=lambda i: -(len(jobs[i][0]) + len(jobs[i][1])))
        with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn")) as pool:
            futures = {i: pool.submit(_run_pair_job, jobs[i]) for i in biggest_first}
            parts = [futures[i].result() for i in range(len(jobs))]
    else:
        parts = [_run_pair_job(j) for j in jobs]
    out = EngineResult([], set(), {}, {})
    for part in parts:
        out.predictions.extend(part.predictions)
        out.candidate_pairs |= part.candidate_pairs
        out.candidate_count += part.candidate_count
        out.details.update(part.details)
        out.alternatives.update(part.alternatives)
    return out


def _run_pair_job(job: tuple[list[Line], list[Line], list[Rule], bool]) -> EngineResult:
    a, b, rules, keep_candidates = job
    out = _run_pair([cand.prepare(x) for x in a], [cand.prepare(x) for x in b], rules)
    if not keep_candidates:  # ~8.6M frozensets at full scale: never ship them back unless a benchmark asks
        out.candidate_pairs = set()
    return out


def candidates_with_features(
    side_a: list[cand.Prepared], side_b: list[cand.Prepared]
) -> tuple[
    dict[str, cand.Prepared],
    dict[tuple[str, str], set[str]],
    list[tuple[cand.Prepared, cand.Prepared, dict[str, Any]]],
]:
    """Candidate pairs for one entity pair with their features: the single path shared by scoring and training."""
    prep = {p.line.id: p for p in (*side_a, *side_b)}
    blocks = cand.generate(side_a, side_b)
    # Ambiguity: how many tolerance-close counterparts each line has (both directions).
    close_a: dict[str, int] = defaultdict(int)
    close_b: dict[str, int] = defaultdict(int)
    text_a: dict[str, int] = defaultdict(int)  # ... of which the description also matches
    text_b: dict[str, int] = defaultdict(int)
    sim: dict[tuple[str, str], float] = {}
    for ai, bi in blocks:
        la, lb = prep[ai].line, prep[bi].line
        sim[(ai, bi)] = s_ = jaccard(prep[ai].words, prep[bi].words)
        if (
            abs(la.amount_usd + lb.amount_usd) / max(abs(la.amount_usd), abs(lb.amount_usd), 1.0)
            <= POLICY_TOLERANCE
        ):
            close_a[ai] += 1
            close_b[bi] += 1
            if s_ >= 0.99:
                text_a[ai] += 1
                text_b[bi] += 1
    entries = [
        (
            prep[ai],
            prep[bi],
            pair_features(
                prep[ai],
                prep[bi],
                sources,
                max(close_a[ai], close_b[bi]),
                sim[(ai, bi)],
                max(text_a[ai], text_b[bi], 1),
            ),
        )
        for (ai, bi), sources in blocks.items()
    ]
    return prep, blocks, entries


def _run_pair(side_a: list[cand.Prepared], side_b: list[cand.Prepared], rules: list[Rule]) -> EngineResult:
    predictions: list[Prediction] = []
    candidate_pairs: set[frozenset[str]] = set()
    details: dict[frozenset[str], PairResult | grp.GroupResult] = {}
    alternatives: dict[frozenset[str], list[tuple[str, float]]] = {}
    pair_start = 0
    prep, blocks, entries = candidates_with_features(side_a, side_b)
    candidate_pairs.update(frozenset(k) for k in blocks)
    n_candidates = len(blocks)
    del blocks
    model = learned.load()
    # One float64 matrix per entity pair (~140 B/pair) instead of Python lists (~1 KB/pair): at 8.6M candidate
    # pairs across parallel workers that is the difference between fitting in memory and an OOM kill.
    features_x: np.ndarray | None = None
    probs = None
    if model is not None and entries:
        features_x = np.empty((len(entries), len(learned.FEATURE_NAMES)), dtype=np.float64)
        for i, (a, b, f) in enumerate(entries):
            features_x[i] = learned_row(a, b, f)
        probs = model.proba(features_x)
    auto_threshold = model.auto_threshold if model is not None else AUTO_THRESHOLD

    scored: list[PairResult] = []
    for i, (a, b, f) in enumerate(entries):
        lo, contrib = score(f)
        if probs is not None:  # learned, calibrated confidence; hand terms stay as the readable rationale
            p_model = min(max(float(probs[i]), 1e-6), 1 - 1e-6)
            learned_lo = math.log(p_model / (1 - p_model))
            contrib["learned"] = learned_lo - lo
            lo = learned_lo
        fired = [r for r in rules if r.matches(f)]
        if fired:
            floor = max(r.confidence for r in fired)
            floor_lo = math.log(floor / (1 - floor))
            if floor_lo > lo:
                contrib["rule"] = floor_lo - lo
                lo = floor_lo
        pr = PairResult(a.line, b.line, f, lo, contrib, [r.id for r in fired], index=i)
        if pr.probability >= SUGGEST_THRESHOLD:
            scored.append(pr)
    del entries  # candidate features below the suggest threshold are no longer needed: free them now

    # Global 1:1 assignment per connected component, maximizing total log-odds.
    adj: dict[str, list[PairResult]] = defaultdict(list)
    for pr in scored:
        adj[pr.a.id].append(pr)
        adj[pr.b.id].append(pr)
    seen: set[str] = set()
    for start in sorted(adj):
        if start in seen:
            continue
        stack: list[str] = [start]
        comp_a: set[str] = set()
        comp_b: set[str] = set()
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            (comp_a if prep[node].line.side == "A" else comp_b).add(node)
            for pr in adj[node]:
                stack.extend(x for x in (pr.a.id, pr.b.id) if x not in seen)
        rows, cols = (
            sorted(comp_a, key=lambda i: cand_key(prep[i].line)),
            sorted(comp_b, key=lambda i: cand_key(prep[i].line)),
        )
        ri, ci = {x: n for n, x in enumerate(rows)}, {x: n for n, x in enumerate(cols)}
        weights = [[0.0] * len(cols) for _ in rows]
        edge: dict[tuple[int, int], PairResult] = {}
        for x in rows:
            for pr in adj[x]:
                i, j = ri[pr.a.id], ci[pr.b.id]
                weights[i][j] = pr.log_odds + 1e-9  # positive: p ≥ 0.5
                edge[(i, j)] = pr
        for i, j in max_weight_assignment(weights):
            pr = edge[(i, j)]
            key = frozenset((pr.a.id, pr.b.id))
            p = pr.probability
            within_policy = pr.features["amount_gap"] <= POLICY_TOLERANCE
            decision = "auto" if p >= auto_threshold and within_policy else "suggest"
            runner_up = sorted(
                (o for o in adj[pr.a.id] + adj[pr.b.id] if o is not pr), key=lambda o: -o.log_odds
            )
            # 3e: a competitor that is an exact twin of the chosen counterpart (duplicate posting) is not real
            # ambiguity: either copy is the same match. Match one, report the other as a duplicate.
            twins = [o for o in runner_up if _twin_of(o, pr) is not None]
            real = [o for o in runner_up if _twin_of(o, pr) is None]
            margin_ok = not real or pr.log_odds - real[0].log_odds >= 1.0
            if decision == "auto" and not margin_ok:
                decision = "suggest"  # a close competitor exists: a human should confirm
            if (
                decision == "suggest"
                and model is not None
                and features_x is not None
                and pr.index is not None
            ):
                row = features_x[pr.index].tolist()
                pr.explain = learned.explain(model, row, auto_threshold, within_policy, margin_ok)
            reasons = [*pr.rules, *(f"{k} {v:+.1f}" for k, v in pr.contributions.items() if k != "prior")]
            if decision == "suggest" and not within_policy:  # 3e: name the residual for the reviewer
                rc = residual.classify(pr.a, pr.b)
                pr.features["residual"] = {"cause": rc.cause, "label": rc.label, "detail": rc.detail}
                reasons.append(rc.label)
            if twins:
                dup_ids = sorted(d for d in {_twin_of(o, pr) for o in twins} if d)
                pr.features["duplicate_postings"] = dup_ids
                reasons.append(f"duplicate posting x{len(dup_ids)}")
            predictions.append(Prediction(key, round(p, 6), decision, reasons))
            details[key] = pr
            alternatives[key] = [
                (o.b.id if o.a.id == pr.a.id else o.a.id, round(o.probability, 4)) for o in runner_up[:3]
            ]

    # Stage 3c: groups (1:M, M:1, M:M, reversals) over everything not auto-matched 1:1.
    auto_ids = {i for p in predictions[pair_start:] if p.decision == "auto" for i in p.line_ids}
    open_lines = [x.line for x in (*side_a, *side_b) if x.line.id not in auto_ids]
    built = grp.build(open_lines)
    if built:
        in_groups = {x.id for g in built for x in g.lines}
        # A clean group beats a residual 1:1 suggestion over the same lines.
        kept = [x for x in predictions[pair_start:] if x.decision == "auto" or not (x.line_ids & in_groups)]
        kept_ids = {id(x) for x in kept}  # identity, not equality: O(n), not O(n^2)
        for dropped in predictions[pair_start:]:
            if id(dropped) not in kept_ids:
                details.pop(dropped.line_ids, None)
                alternatives.pop(dropped.line_ids, None)
        del predictions[pair_start:]
        predictions.extend(kept)
        for g in built:
            key = frozenset(x.id for x in g.lines)
            gp = g.probability
            within_policy = g.features["amount_gap_usd"] <= grp.tolerance(g.exposure_usd)
            decision = (
                "auto" if gp >= AUTO_THRESHOLD and within_policy and g.features["unique"] else "suggest"
            )
            reasons = [
                *g.rules,
                g.match_type,
                *(f"{k} {v:+.1f}" for k, v in g.contributions.items() if k != "prior"),
            ]
            predictions.append(Prediction(key, round(gp, 6), decision, reasons))
            details[key] = g
            alternatives[key] = []
    return EngineResult(predictions, candidate_pairs, details, alternatives, n_candidates)


def _same_posting(x: Line, y: Line) -> bool:
    """Two bookings indistinguishable as evidence: same entity, counterparty, amount, reference, description,
    value date within a day."""
    return (
        x.id != y.id
        and x.entity == y.entity
        and x.counterparty == y.counterparty
        and x.currency == y.currency
        and abs(x.amount - y.amount) < 0.005
        and (x.reference_norm or "") == (y.reference_norm or "")
        and x.description == y.description
        and abs((x.value_date - y.value_date).days) <= 1
    )


def _twin_of(other: "PairResult", chosen: "PairResult") -> str | None:
    """If `other` competes with `chosen` only through an exact duplicate of chosen's counterpart, return the
    duplicate's id."""
    if other.a.id == chosen.a.id and _same_posting(other.b, chosen.b):
        return other.b.id
    if other.b.id == chosen.b.id and _same_posting(other.a, chosen.a):
        return other.a.id
    return None


def version_label() -> str:
    """What scored a run, for the audit record: engine version + learned model (or the hand-set fallback)."""
    model = learned.load()
    scorer = model.meta.get("version", "scorer") if model is not None else "hand-scorer"
    return f"{ENGINE_VERSION} ({scorer} + 3c groups)"[:64]


def learned_row(a: cand.Prepared, b: cand.Prepared, f: dict[str, Any]) -> list[float]:
    return learned.vectorize(f, a.line.amount_usd, bool(a.line.account) and a.line.account == b.line.account)


def cand_key(line: Line) -> tuple[float, str, str, str]:
    """Content-based ordering so results never depend on input order (ids only break exact clones)."""
    return (-abs(line.amount_usd), line.value_date.isoformat(), line.reference_norm or "", line.id)
