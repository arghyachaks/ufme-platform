"""Rule DSL: rules are data (stored on match_rule.definition) evaluated against pair features.

A rule is {"all": [{"feature": f, "op": op, "value": v}, ...], "action": "auto"|"suggest", "confidence": p}.
Rules are *fast paths and floors*: when an enabled rule fires, the pair's probability is at least the rule's
confidence and the rule id is recorded in the explanation. They never bypass policy (tolerance/materiality).
"""

from dataclasses import dataclass
from typing import Any

OPS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "lte": lambda a, b: a is not None and a <= b,
    "lt": lambda a, b: a is not None and a < b,
    "gte": lambda a, b: a is not None and a >= b,
    "gt": lambda a, b: a is not None and a > b,
}


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    conditions: tuple[tuple[str, str, Any], ...]
    action: str
    confidence: float
    priority: int = 100
    any_of: tuple[tuple[tuple[str, str, Any], ...], ...] = ()

    @staticmethod
    def from_definition(rule_id: str, name: str, definition: dict[str, Any], priority: int = 100) -> "Rule":
        def conds(items: list[dict[str, Any]]) -> tuple[tuple[str, str, Any], ...]:
            out = []
            for c in items:
                if c["op"] not in OPS:
                    raise ValueError(f"{rule_id}: unknown operator {c['op']!r}")
                out.append((c["feature"], c["op"], c["value"]))
            return tuple(out)

        return Rule(
            id=rule_id,
            name=name,
            conditions=conds(definition.get("all", [])),
            action=definition.get("action", "suggest"),
            confidence=float(definition.get("confidence", 0.9)),
            priority=priority,
            any_of=tuple(conds(group) for group in definition.get("any", [])),
        )

    def matches(self, features: dict[str, Any]) -> bool:
        if not all(OPS[op](features.get(f), v) for f, op, v in self.conditions):
            return False
        return not self.any_of or any(all(OPS[op](features.get(f), v) for f, op, v in g) for g in self.any_of)


# Built-in definitions, mirroring the seeded rules R-001…R-004 (R-005/R-006 are many-to-many).
DEFAULT_DEFINITIONS: dict[str, dict[str, Any]] = {
    "R-001": {
        "all": [
            {"feature": "ref_exact", "op": "eq", "value": True},
            {"feature": "amount_gap", "op": "lte", "value": 0.001},
            {"feature": "date_gap_days", "op": "lte", "value": 3},
        ],
        "action": "auto",
        "confidence": 0.995,
    },
    "R-002": {
        "all": [
            {"feature": "amount_gap", "op": "lte", "value": 0.005},
            {"feature": "date_gap_days", "op": "lte", "value": 3},
        ],
        "any": [
            [{"feature": "ref_exact", "op": "eq", "value": True}],
            [{"feature": "ref_canonical_exact", "op": "eq", "value": True}],
            [{"feature": "ref_affix", "op": "eq", "value": True}],
        ],
        "action": "auto",
        "confidence": 0.985,
    },
    "R-003": {
        "all": [
            {"feature": "amount_gap", "op": "lte", "value": 0.0065},
            {"feature": "ref_strong", "op": "eq", "value": True},
        ],
        "action": "suggest",
        "confidence": 0.93,
    },
    "R-004": {
        "all": [
            {"feature": "ref_edit_distance", "op": "lte", "value": 1},
            {"feature": "ref_strong", "op": "eq", "value": True},
            {"feature": "amount_gap", "op": "lte", "value": 0.001},
            {"feature": "date_gap_days", "op": "lte", "value": 7},
        ],
        "action": "auto",
        "confidence": 0.98,
    },
}
DEFAULT_NAMES = {
    "R-001": "IC exact: reference + amount + date",
    "R-002": "IC tolerance: amount ±0.5%, date ±3d",
    "R-003": "FX-adjusted amount match",
    "R-004": "Fuzzy reference (≤ 1 edit, OCR-canonical)",
}


def default_rules() -> list[Rule]:
    return [
        Rule.from_definition(rid, DEFAULT_NAMES[rid], d, priority=i)
        for i, (rid, d) in enumerate(DEFAULT_DEFINITIONS.items(), 1)
    ]
