"""Shared types for the matching benchmark: lines, ground truth, predictions."""

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Line:
    """A normalized ledger line as the matcher sees it (mirrors ledger_txn)."""

    id: str
    entity: str
    counterparty: str
    amount: float  # local currency, signed
    currency: str
    amount_usd: float  # signed, at the value-date rate (as the ingestion pipeline computes it)
    value_date: date
    posting_date: date
    reference: str  # as booked (raw)
    reference_norm: str | None
    description: str
    account: str

    @property
    def pair(self) -> tuple[str, str]:
        """Unordered entity pair: both sides of an intercompany relationship share it."""
        return (
            (self.entity, self.counterparty)
            if self.entity < self.counterparty
            else (self.counterparty, self.entity)
        )

    @property
    def side(self) -> str:
        return "A" if self.entity < self.counterparty else "B"


@dataclass(frozen=True)
class TruthGroup:
    id: str
    scenario: str
    line_ids: frozenset[str]  # size 1 = must stay unmatched (orphan, decoy, duplicate)
    difficulty: int = 1  # 1 easy … 3 hard
    twin_of: str | None = None  # exact duplicate of this line: either copy may be the one matched


@dataclass
class Prediction:
    line_ids: frozenset[str]
    confidence: float  # calibrated probability that the group is a true match
    decision: str  # "auto" | "suggest"
    reasons: list[str] = field(default_factory=list)


@dataclass
class Dataset:
    name: str
    lines: list[Line]
    truth: list[TruthGroup]
    seed: int
    version: str
