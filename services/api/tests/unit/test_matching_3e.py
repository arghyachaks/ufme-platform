"""Text evidence, duplicate-twin resolution, residual causes, and the advisory local LLM judge."""

import json
from datetime import date
from typing import Any

import httpx
import pytest

from app.core.config import settings
from app.engines.benchmark.model import Line
from app.engines.data_quality.normalize import normalize_reference
from app.engines.matching import engine, residual
from app.engines.matching.text import description_words, jaccard
from app.services import judge


def ln(
    i: str, entity: str, cp: str, usd: float, ref: str = "", desc: str = "", d: int = 10, ccy: str = "USD"
) -> Line:
    return Line(
        i,
        entity,
        cp,
        usd,
        ccy,
        usd,
        date(2026, 8, d),
        date(2026, 8, d),
        ref,
        normalize_reference(ref),
        desc,
        "1910",
    )


def test_description_words_ignore_mirrored_entity_codes() -> None:
    a, b = description_words("IC dividend DE03->SG05"), description_words("IC dividend SG05->DE03")
    assert a == b == frozenset({"dividend"})
    assert jaccard(description_words("IC royalty US01->UK02"), b) == 0.0


def test_matching_description_breaks_a_round_amount_tie() -> None:
    # No references, same round amount and day: only the description says which is the dividend.
    lines = [
        ln("a", "DE03", "SG05", -250000.0, desc="IC dividend DE03->SG05"),
        ln("b1", "SG05", "DE03", 250000.0, desc="IC royalty SG05->DE03"),
        ln("b2", "SG05", "DE03", 250000.0, desc="IC dividend SG05->DE03"),
    ]
    res = engine.run(lines)
    chosen = [p for p in res.predictions if "a" in p.line_ids]
    assert chosen and chosen[0].line_ids == {"a", "b2"}
    f = res.details[chosen[0].line_ids].features
    assert f["desc_similarity"] == 1.0 and f["text_ambiguity"] == 1


def test_exact_duplicate_is_not_a_rival() -> None:
    # B booked the same document twice: either copy is the match, so no human choice is needed.
    lines = [
        ln("a", "UK02", "US01", 48210.55, "INV-88123", "IC recharge UK02->US01"),
        ln("b", "US01", "UK02", -48210.55, "INV-88123", "IC recharge US01->UK02"),
        ln("b_dup", "US01", "UK02", -48210.55, "INV-88123", "IC recharge US01->UK02"),
    ]
    res = engine.run(lines)
    [p] = [p for p in res.predictions if len(p.line_ids) == 2]
    assert p.decision == "auto" and any("duplicate posting" in r for r in p.reasons)
    assert res.details[p.line_ids].features["duplicate_postings"] in (["b_dup"], ["b"])


@pytest.mark.parametrize(
    ("a_usd", "b_usd", "a_ccy", "b_ccy", "cause"),
    [
        (100000.0, -90000.0, "USD", "INR", "withholding_tax"),  # 10% withheld
        (8000.0, -7975.0, "USD", "USD", "bank_fee"),  # $25 fee, same currency
        (20000.0, -19930.0, "USD", "EUR", "fx_rate_difference"),  # 0.35%, no fee pattern
        (10000.0, -9975.0, "USD", "EUR", "fee_or_fx"),  # $25 = 0.25%: both fit, flagged
        (10000.0, -8000.0, "USD", "USD", "withholding_tax"),  # 20% is a statutory rate too
    ],
)
def test_residual_causes(a_usd: float, b_usd: float, a_ccy: str, b_ccy: str, cause: str) -> None:
    r = residual.classify(
        ln("a", "US01", "IN04", a_usd, ccy=a_ccy), ln("b", "IN04", "US01", b_usd, ccy=b_ccy)
    )
    assert r.cause == cause and r.detail and r.label


def test_residual_unexplained_and_rounding() -> None:
    odd = residual.classify(ln("a", "US01", "IN04", 10000.0), ln("b", "IN04", "US01", -9123.0))
    assert odd.cause == "unexplained" and "investigate" in odd.detail
    tiny = residual.classify(ln("a", "US01", "IN04", 10000.0), ln("b", "IN04", "US01", -9999.6))
    assert tiny.cause == "rounding"


def test_policy_blocked_suggestions_carry_their_residual() -> None:
    lines = [
        ln("a", "US01", "IN04", 100000.0, "ROY-2026-0912", "IC royalty US01->IN04"),
        ln("b", "IN04", "US01", -90000.0, "ROY-2026-0912", "IC royalty IN04->US01", ccy="INR"),
    ]
    [p] = engine.run(lines).predictions
    assert p.decision == "suggest" and "Withholding tax 10%" in p.reasons


class _Resp:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {"message": {"content": json.dumps(self.payload)}}


def test_judge_parses_structured_verdict(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: dict[str, Any] = {}

    def fake_post(url: str, json: dict[str, Any], timeout: Any) -> _Resp:
        sent.update(json)
        return _Resp(
            {"cause": "withholding_tax", "same_transaction": True, "confidence": 93, "note": "Book 10% WHT."}
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    a, b = ln("a", "US01", "IN04", 100000.0), ln("b", "IN04", "US01", -90000.0)
    v = judge.judge(a, b, residual.classify(a, b))
    assert v is not None and v.cause == "withholding_tax" and v.confidence == 93 and v.same_transaction
    assert sent["format"] == judge.SCHEMA and sent["options"]["temperature"] == 0 and sent["think"] is False
    assert sent["model"] == settings.assist_model
    assert "Withholding tax 10%" in sent["messages"][1]["content"]  # the rule label is given as a fact


def test_judge_is_optional_when_model_is_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ollama_url", "http://127.0.0.1:9")
    a, b = ln("a", "US01", "IN04", 100000.0), ln("b", "IN04", "US01", -90000.0)
    assert judge.judge(a, b, residual.classify(a, b), timeout=2) is None


def test_judge_rejects_unknown_cause(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        httpx,
        "post",
        lambda *a, **k: _Resp({"cause": "magic", "same_transaction": True, "confidence": 500, "note": "x"}),
    )
    a, b = ln("a", "US01", "IN04", 100000.0), ln("b", "IN04", "US01", -90000.0)
    v = judge.judge(a, b, residual.classify(a, b))
    assert v is not None and v.cause == "unexplained" and v.confidence == 100
