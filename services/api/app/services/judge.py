"""Local LLM judge (3e): a second opinion on suggestions, from the on-premise model behind ufme Assist.

The judge never auto-matches on its own. It reads the same facts a reviewer sees (both lines, the residual
arithmetic, the deterministic residual classifier's label) and returns a structured verdict: does it agree with
the cause, and a one-sentence note for the reviewer. Its accuracy is measured against ground truth
(`python -m app.engines.benchmark.judge_eval`); what it is allowed to do is decided by that measurement.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings
from app.engines.benchmark.model import Line
from app.engines.matching.residual import Residual

CAUSES = [
    "withholding_tax",
    "bank_fee",
    "fx_rate_difference",
    "rounding",
    "timing",
    "partial_payment",
    "unexplained",
]

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "cause": {"type": "string", "enum": CAUSES},
        "same_transaction": {"type": "boolean"},
        "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
        "note": {"type": "string"},
    },
    "required": ["cause", "same_transaction", "confidence", "note"],
}

SYSTEM = """You are a senior intercompany accountant reviewing a proposed match between two ledger lines.
Decide (1) whether both lines record the same intercompany transaction and (2) what explains any residual.
Causes: withholding_tax (a statutory % of gross withheld by the payer), bank_fee (a small fixed transfer fee),
fx_rate_difference (each side converted at a different FX rate source), rounding, timing, partial_payment,
unexplained. Use only the facts given. Reply as JSON. The note is one plain sentence a reviewer can act on;
no jargon, do not repeat the numbers verbatim unless they matter."""


@dataclass
class Verdict:
    cause: str
    same_transaction: bool
    confidence: int
    note: str
    seconds: float
    model: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "cause": self.cause,
            "same_transaction": self.same_transaction,
            "confidence": self.confidence,
            "note": self.note,
            "model": self.model,
            "seconds": round(self.seconds, 2),
        }


def facts(a: Line, b: Line, residual: Residual) -> str:
    def side(x: Line) -> str:
        return (
            f"{x.entity} books {x.amount:,.2f} {x.currency} (USD {x.amount_usd:,.2f}) with {x.counterparty} on "
            f"{x.value_date}, reference '{x.reference or '-'}', description '{x.description or '-'}'"
        )

    return (
        f"Line A: {side(a)}\nLine B: {side(b)}\n"
        f"Net residual: USD {residual.residual_usd:,.2f} ({100 * residual.residual_pct:.3f}% of gross)\n"
        f"Rule-based classifier says: {residual.label}. {residual.detail}"
    )


def judge(a: Line, b: Line, residual: Residual, timeout: float = 60.0) -> Verdict | None:
    """One verdict from the local model, or None if it is unavailable (callers must not depend on it)."""
    body = {
        "model": settings.assist_model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": facts(a, b, residual)},
        ],
        "stream": False,
        "think": False,
        "format": SCHEMA,
        "keep_alive": "30m",
        "options": {"temperature": 0, "num_ctx": 2048},
    }
    started = time.perf_counter()
    try:
        r = httpx.post(
            f"{settings.ollama_url}/api/chat", json=body, timeout=httpx.Timeout(timeout, connect=3)
        )
        r.raise_for_status()
        data = json.loads(r.json()["message"]["content"])
        cause = data.get("cause") if data.get("cause") in CAUSES else "unexplained"
        return Verdict(
            cause=cause,
            same_transaction=bool(data.get("same_transaction")),
            confidence=int(max(0, min(100, int(data.get("confidence", 0))))),
            note=str(data.get("note", ""))[:400],
            seconds=time.perf_counter() - started,
            model=settings.assist_model,
        )
    except Exception:  # model down, timeout, malformed JSON: the judge is optional
        return None


def judge_run(db: Any, run_id: Any, limit: int | None = None) -> dict[str, int]:
    """Advisory second opinion on a run's open suggestions, largest exposure first. Stores the verdict on each
    proposal's explanation; never changes a decision. Stops early if the local model is unavailable."""
    from sqlalchemy import select

    from app.engines.matching.residual import classify
    from app.models import LedgerTxn, MatchGroup, MatchMember

    limit = settings.judge_max if limit is None else limit
    groups = list(
        db.scalars(
            select(MatchGroup)
            .where(
                MatchGroup.run_id == run_id, MatchGroup.status == "proposed", MatchGroup.match_type == "1:1"
            )
            .order_by(MatchGroup.exposure_usd.desc(), MatchGroup.code)
            .limit(limit)
        )
    )
    done = failed = 0
    for g in groups:
        rows = db.execute(
            select(MatchMember.side, LedgerTxn)
            .join(LedgerTxn, LedgerTxn.id == MatchMember.txn_id)
            .where(MatchMember.group_id == g.id)
        ).all()
        lines = [
            Line(
                id=t.code,
                entity=t.entity_code,
                counterparty=t.counterparty_code,
                amount=float(t.amount),
                currency=t.currency,
                amount_usd=float(t.amount_usd or 0),
                value_date=t.value_date,
                posting_date=t.posting_date or t.value_date,
                reference=t.reference_raw or "",
                reference_norm=t.reference_norm,
                description=t.description or "",
                account=t.account or "",
            )
            for _, t in sorted(rows, key=lambda r: str(r[0]))
        ]
        if len(lines) != 2:
            continue
        verdict = judge(lines[0], lines[1], classify(lines[0], lines[1]))
        if verdict is None:
            failed += 1
            if failed >= 3 and done == 0:
                break  # model not running: don't spend minutes timing out
            continue
        g.explanation = {**(g.explanation or {}), "judge": verdict.as_dict()}
        done += 1
        if done % 20 == 0:
            db.commit()  # make progress visible to reviewers while the judge works
    db.commit()
    return {"judged": done, "failed": failed, "candidates": len(groups)}
