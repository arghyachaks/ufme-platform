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
from app.engines.matching import learned
from app.engines.matching.assignment import max_weight_assignment
from app.engines.matching.rules import Rule, default_rules
from app.engines.matching.text import affix, edit_distance, jaro_winkler

ENGINE_VERSION = "engine-1.2 (3c groups + 1:1 assignment)"  # stored in a 64-char column
POLICY_TOLERANCE = 0.005  # auto-match only within the 0.5% tolerance policy
AUTO_THRESHOLD = 0.985
SUGGEST_THRESHOLD = 0.5
PARALLEL_MIN = 50_000  # lines; below this, process start-up costs more than it saves
MAX_WORKERS = 8  # memory: each process holds one entity pair
MAX_RESIDUAL_GAP = 0.2  # ref-strong pairs up to 20% apart are proposed with a residual (fees, withholding)


@dataclass
class PairResult:
    a: Line
    b: Line
    features: dict[str, Any]
    log_odds: float
    contributions: dict[str, float]
    rules: list[str] = field(default_factory=list)
    row: list[float] | None = None  # learned-model feature vector (3d), kept for explanations
    explain: dict[str, Any] | None = None  # model drivers + counterfactuals for suggestions

    @property
    def probability(self) -> float:
        return 1 / (1 + math.exp(-self.log_odds))


@dataclass
class EngineResult:
    predictions: list[Prediction]
    candidate_pairs: set[frozenset[str]]
    details: dict[frozenset[str], "PairResult | grp.GroupResult"]
    alternatives: dict[frozenset[str], list[tuple[str, float]]]


def pair_features(a: cand.Prepared, b: cand.Prepared, sources: set[str], ambiguity: int) -> dict[str, Any]:
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


def run(lines: list[Line], rules: list[Rule] | None = None, workers: int | None = None) -> EngineResult:
    """Entity pairs are independent, so large runs fan out across processes; results are merged in pair
    order, so output is identical to a serial run."""
    rules = sorted(rules if rules is not None else default_rules(), key=lambda r: r.priority)
    by_pair: dict[tuple[str, str], tuple[list[Line], list[Line]]] = defaultdict(lambda: ([], []))
    for line in lines:
        by_pair[line.pair][0 if line.side == "A" else 1].append(line)
    jobs = [(by_pair[k][0], by_pair[k][1], rules) for k in sorted(by_pair)]
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
        out.details.update(part.details)
        out.alternatives.update(part.alternatives)
    return out


def _run_pair_job(job: tuple[list[Line], list[Line], list[Rule]]) -> EngineResult:
    a, b, rules = job
    return _run_pair([cand.prepare(x) for x in a], [cand.prepare(x) for x in b], rules)


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
    for ai, bi in blocks:
        la, lb = prep[ai].line, prep[bi].line
        if (
            abs(la.amount_usd + lb.amount_usd) / max(abs(la.amount_usd), abs(lb.amount_usd), 1.0)
            <= POLICY_TOLERANCE
        ):
            close_a[ai] += 1
            close_b[bi] += 1
    entries = [
        (prep[ai], prep[bi], pair_features(prep[ai], prep[bi], sources, max(close_a[ai], close_b[bi])))
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
    model = learned.load()
    feature_rows = [learned_row(a, b, f) for a, b, f in entries] if model is not None else []
    probs = (
        model.proba(np.asarray(feature_rows, dtype=np.float64))
        if model is not None and feature_rows
        else None
    )
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
        pr = PairResult(
            a.line, b.line, f, lo, contrib, [r.id for r in fired], feature_rows[i] if feature_rows else None
        )
        if pr.probability >= SUGGEST_THRESHOLD:
            scored.append(pr)

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
            margin_ok = not runner_up or pr.log_odds - runner_up[0].log_odds >= 1.0
            if decision == "auto" and not margin_ok:
                decision = "suggest"  # a close competitor exists: a human should confirm
            if decision == "suggest" and model is not None and pr.row is not None:
                pr.explain = learned.explain(model, pr.row, auto_threshold, within_policy, margin_ok)
            reasons = [*pr.rules, *(f"{k} {v:+.1f}" for k, v in pr.contributions.items() if k != "prior")]
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
    return EngineResult(predictions, candidate_pairs, details, alternatives)


def learned_row(a: cand.Prepared, b: cand.Prepared, f: dict[str, Any]) -> list[float]:
    return learned.vectorize(f, a.line.amount_usd, bool(a.line.account) and a.line.account == b.line.account)


def cand_key(line: Line) -> tuple[float, str, str, str]:
    """Content-based ordering so results never depend on input order (ids only break exact clones)."""
    return (-abs(line.amount_usd), line.value_date.isoformat(), line.reference_norm or "", line.id)
