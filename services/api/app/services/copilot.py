"""Copilot answers. Stage 1: deterministic answers grounded in demo records. Stage 6 replaces this with an LLM
that calls the read APIs as tools, keeping the same request/response contract."""

from app.schemas.read import ChatMessageOut


def answer(prompt: str) -> ChatMessageOut:
    p = prompt.lower()
    if "1042" in p or "summar" in p:
        return ChatMessageOut(
            role="assistant",
            refs=["CS-1042", "JE-77812", "R-002"],
            text=(
                "CS-1042: a 1.28M USD IC loan variance between US01 and UK02. Root cause is an FX revaluation journal "
                "(JE-77812) posted only on UK02. Recommended: reverse JE-77812 or post a matching reval on US01, then "
                "rerun R-002. Expected to clear 2 linked exceptions."
            ),
        )
    if "20918" in p or "why" in p:
        return ChatMessageOut(
            role="assistant",
            refs=["MT-20918", "R-004"],
            text=(
                "MT-20918 scored 0.71, below the 0.80 review threshold. Reference similarity was high (0.93) but the "
                "19-day date gap and a high duplicate-risk score pulled confidence down. It was routed to the "
                "exception queue."
            ),
        )
    if "close" in p or "block" in p:
        return ChatMessageOut(
            role="assistant",
            refs=["UK02", "DE03", "IC-07"],
            text=(
                "UK02 and DE03 are blocking close: UK02 has the 1.28M escalated case and control IC-07 is failing; "
                "DE03 has 312K of duplicate vendor payments pending recall. Close readiness is 87%."
            ),
        )
    if "email" in p or "draft" in p:
        return ChatMessageOut(
            role="assistant",
            refs=["JE-77812"],
            text=(
                "Draft:\n\nHi UK02 Treasury, our August IC reconciliation shows a 1,284,000 USD variance with US01 "
                "caused by revaluation journal JE-77812, which has no counterpart in US01. Could you confirm whether "
                "it should be reversed or mirrored by 18 Aug? Thanks."
            ),
        )
    return ChatMessageOut(
        role="assistant",
        refs=[],
        text=(
            "I can summarize cases, explain match decisions, check close readiness, and draft counterparty emails. "
            "Try one of the suggested prompts."
        ),
    )
