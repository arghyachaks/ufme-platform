"""Score predictions against ground truth: pair, group and exposure-weighted metrics, per scenario."""

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from itertools import product

from app.engines.benchmark.model import Dataset, Line, Prediction, TruthGroup


@dataclass
class Counts:
    tp: float = 0
    fp: float = 0
    fn: float = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 1.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0

    def as_dict(self) -> dict[str, float]:
        return {
            "precision": round(self.precision, 5),
            "recall": round(self.recall, 5),
            "f1": round(self.f1, 5),
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
        }


@dataclass
class Report:
    dataset: str
    matcher: str
    lines: int
    pair: dict[str, float]
    group: dict[str, float]
    exposure: dict[str, float]
    auto: dict[str, float]
    decoy_false_match_rate: float
    orphan_false_match_rate: float
    by_scenario: dict[str, dict[str, float]] = field(default_factory=dict)
    seconds: float = 0.0

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _cross_pairs(ids: frozenset[str], lines: dict[str, Line]) -> set[frozenset[str]]:
    """Matchable pairs inside a group: one line from each side (entity) of the relationship.
    Same-side groups (e.g. a reversal pair) pair within the side."""
    a = [i for i in ids if lines[i].side == "A"]
    b = [i for i in ids if lines[i].side == "B"]
    if a and b:
        return {frozenset(p) for p in product(a, b)}
    members = sorted(ids)
    return {frozenset((x, y)) for i, x in enumerate(members) for y in members[i + 1 :]}


def _canonical(ds: Dataset, predictions: list[Prediction]) -> list[Prediction]:
    """Exact duplicate postings are indistinguishable: if a prediction uses the extra copy instead of its twin,
    score it as if it had used the twin (and vice versa), so metrics reward judgement, not tie-breaking."""
    twins = {g.twin_of: next(iter(g.line_ids)) for g in ds.truth if g.twin_of}
    swap = {**twins, **{v: k for k, v in twins.items()}}
    used = {i for p in predictions for i in p.line_ids}
    out = []
    for p in predictions:
        ids = set(p.line_ids)
        for i in list(ids):
            j = swap.get(i)
            if j is not None and j not in used and i in twins.values():  # extra used, original free → swap
                ids.discard(i)
                ids.add(j)
        out.append(Prediction(frozenset(ids), p.confidence, p.decision, p.reasons))
    return out


def evaluate(ds: Dataset, predictions: list[Prediction], matcher: str = "?", seconds: float = 0.0) -> Report:
    lines = {x.id: x for x in ds.lines}
    predictions = _canonical(ds, predictions)
    group_of: dict[str, TruthGroup] = {i: g for g in ds.truth for i in g.line_ids}

    true_pairs: set[frozenset[str]] = set()
    pair_scenario: dict[frozenset[str], str] = {}
    for g in ds.truth:
        if len(g.line_ids) > 1:
            for p in _cross_pairs(g.line_ids, lines):
                true_pairs.add(p)
                pair_scenario[p] = g.scenario

    pred_pairs: dict[frozenset[str], Prediction] = {}
    for pred in predictions:
        for p in _cross_pairs(pred.line_ids, lines):
            pred_pairs[p] = pred

    pair = Counts()
    scen: dict[str, Counts] = defaultdict(Counts)
    for p in pred_pairs:
        if p in true_pairs:
            pair.tp += 1
            scen[pair_scenario[p]].tp += 1
        else:
            pair.fp += 1
            # attribute a false pair to the scenario of its (first) member's truth group
            scen[group_of[next(iter(p))].scenario].fp += 1
    for p in true_pairs - pred_pairs.keys():
        pair.fn += 1
        scen[pair_scenario[p]].fn += 1

    # Group-level exact match and exposure (USD) weighting.
    truth_sets = {g.line_ids: g for g in ds.truth if len(g.line_ids) > 1}
    group, exposure = Counts(), Counts()

    def usd(ids: frozenset[str]) -> float:
        return sum(abs(lines[i].amount_usd) for i in ids) / 2

    pred_sets = {pr.line_ids for pr in predictions}
    for ids in pred_sets:
        if ids in truth_sets:
            group.tp += 1
            exposure.tp += usd(ids)
        else:
            group.fp += 1
            exposure.fp += usd(ids)
    for ids in truth_sets.keys() - pred_sets:
        group.fn += 1
        exposure.fn += usd(ids)

    # Auto-match bucket: precision of auto pairs and share of matchable lines auto-matched correctly.
    auto_pairs = {p for p, pr in pred_pairs.items() if pr.decision == "auto"}
    auto = Counts(tp=len(auto_pairs & true_pairs), fp=len(auto_pairs - true_pairs))
    matchable = sum(len(g.line_ids) for g in ds.truth if len(g.line_ids) > 1)
    auto_correct_lines = sum(
        len(pr.line_ids) for pr in predictions if pr.decision == "auto" and pr.line_ids in truth_sets
    )
    auto_lines = sum(len(pr.line_ids) for pr in predictions if pr.decision == "auto")

    matched_ids = {i for pr in predictions for i in pr.line_ids}
    singles = [g for g in ds.truth if len(g.line_ids) == 1]
    decoys = [g for g in singles if g.scenario.startswith("decoy") or g.scenario == "duplicate_extra"]
    orphans = [g for g in singles if g.scenario == "orphan"]

    def rate(groups: list[TruthGroup]) -> float:
        return round(sum(1 for g in groups if g.line_ids & matched_ids) / len(groups), 5) if groups else 0.0

    by_scenario = {name: c.as_dict() for name, c in sorted(scen.items())}
    for g in singles:  # singleton scenarios: report how often they were wrongly matched
        entry = by_scenario.setdefault(g.scenario, {"wrongly_matched": 0, "total": 0})
        entry["total"] = entry.get("total", 0) + 1
        entry["wrongly_matched"] = entry.get("wrongly_matched", 0) + (1 if g.line_ids & matched_ids else 0)

    return Report(
        dataset=ds.name,
        matcher=matcher,
        lines=len(ds.lines),
        pair=pair.as_dict(),
        group=group.as_dict(),
        exposure={k: v for k, v in exposure.as_dict().items() if k in ("precision", "recall", "f1")},
        auto={
            "precision": round(auto.precision, 5),
            "rate": round(auto_correct_lines / matchable, 5) if matchable else 0.0,
            "lines": auto_lines,
        },
        decoy_false_match_rate=rate(decoys),
        orphan_false_match_rate=rate(orphans),
        by_scenario=by_scenario,
        seconds=round(seconds, 3),
    )
