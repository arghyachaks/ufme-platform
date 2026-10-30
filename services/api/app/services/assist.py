"""ufme Assist: a grounded finance assistant running on a local Ollama model (default Gemma 4 E4B).

The model never touches the database. We build a compact, read-only fact sheet from the tenant's current data,
put it in the system prompt, and stream the model's answer back. If Ollama is unreachable the deterministic
Stage 1 answers are used, so demos never break.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.matching import MatchRun
from app.models.tenant import Tenant
from app.services import copilot, read
from app.services.workflow import Actor

SYSTEM = """You are ufme Assist, the assistant inside ufme, an intercompany and financial reconciliation platform.
You help controllers, accountants and finance managers understand matches, exceptions and close readiness.

Rules:
- Answer only from the FACTS below and the conversation. If the facts don't cover it, say so plainly and suggest
  where in ufme to look. Never invent amounts, IDs, people or dates.
- Write in clear business English for finance professionals. No technical jargon, no mention of models,
  prompts, tokens or "facts provided".
- Be concise: lead with the answer, then at most 3 short bullets starting with "• ". Plain text only:
  no markdown, no LaTeX, no tables. Quote IDs exactly (e.g. EX-8902, CS-1042).
- You can explain and recommend, but you cannot approve, post or change anything. Say that actions go through
  the normal approval flow.
"""


def _facts(db: Session, tenant: Tenant, page: str | None) -> str:
    lines: list[str] = []
    try:
        d: dict[str, Any] = read.snapshot(db, tenant, "workspace.dashboard")
        lines.append(f"Period close completion: {d.get('closeCompletion')}%")
        for g in d.get("kpiGroups", []):
            items = "; ".join(f"{i['label']} {i['value']} ({i.get('hint', '')})" for i in g.get("items", []))
            lines.append(f"{g['title']}: {items}")
        wq = "; ".join(f"{w['label']} {w['count']}" for w in d.get("workQueue", []))
        lines.append(f"Work queue: {wq}")
        for x in d.get("highRiskExceptions", []):
            lines.append(
                f"High-risk exception {x['id']}: {x['severity']} {x['category']}, impact {x['impact']}, "
                f"entity {x['entity']}, owner {x['owner']}, due {x['due']}, age {x['age']}"
            )
        rc = "; ".join(f"{r['label']} {r['share']}%" for r in d.get("rootCauses", []))
        lines.append(f"Root causes of open breaks: {rc}")
    except Exception:
        pass
    try:
        for e in read.exceptions(db, tenant)[:12]:
            lines.append(f"Exception {e.model_dump_json(by_alias=True, exclude_none=True)}")
    except Exception:
        pass
    try:
        for c in read.cases(db, tenant)[:12]:
            lines.append(f"Case {c.model_dump_json(by_alias=True, exclude_none=True)}")
    except Exception:
        pass
    run = db.scalar(select(MatchRun).where(MatchRun.tenant_id == tenant.id).order_by(MatchRun.code.desc()))
    if run is not None:
        lines.append(
            f"Latest matching run {run.code}: status {run.status}, metrics {json.dumps(run.metrics or {})}"
        )
    if page:
        lines.append(f"The user is currently on the ufme screen: {page}")
    return "\n".join(lines)


def status() -> dict[str, Any]:
    try:
        r = httpx.get(f"{settings.ollama_url}/api/tags", timeout=3)
        names = [m["name"] for m in r.json().get("models", [])]
        return {"online": settings.assist_model in names, "model": settings.assist_model, "available": names}
    except Exception:
        return {"online": False, "model": settings.assist_model, "available": []}


def stream(
    db: Session,
    tenant: Tenant,
    prompt: str,
    history: list[dict[str, str]],
    page: str | None,
    actor: Actor | None = None,
    thread: str | None = None,
) -> Iterator[str]:
    """The harness agent when enabled (plan, to-dos, tools, sub-agents; see app/agents/harness.py for the
    protocol); otherwise, or when no model can run it, a single grounded model call."""
    if settings.agent_harness and actor is not None:
        from app.agents import assist as agent

        return agent.stream(
            db,
            tenant,
            actor,
            prompt,
            history,
            page,
            lambda: simple_stream(db, tenant, prompt, history, page),
            thread,
        )
    return simple_stream(db, tenant, prompt, history, page)


def simple_stream(
    db: Session, tenant: Tenant, prompt: str, history: list[dict[str, str]], page: str | None
) -> Iterator[str]:
    """Yields NDJSON lines: {"delta": "..."} chunks, then {"done": true, "source": "local-llm" | "fallback"}."""
    messages = [{"role": "system", "content": f"{SYSTEM}\nFACTS:\n{_facts(db, tenant, page)}"}]
    messages += [m for m in history[-8:] if m.get("role") in ("user", "assistant")]
    messages.append({"role": "user", "content": prompt})
    body = {
        "model": settings.assist_model,
        "messages": messages,
        "stream": True,
        "think": False,  # skip silent reasoning: faster first words for fact-sheet Q&A
        "keep_alive": "30m",
        "options": {"temperature": 0.2, "num_ctx": 8192},
    }
    try:
        with httpx.stream(
            "POST", f"{settings.ollama_url}/api/chat", json=body, timeout=httpx.Timeout(120, connect=3)
        ) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                text = chunk.get("message", {}).get("content", "")
                if text:
                    yield json.dumps({"delta": text}) + "\n"
                if chunk.get("done"):
                    break
        yield json.dumps({"done": True, "source": "local-llm"}) + "\n"
    except Exception:
        msg = copilot.answer(prompt)
        yield json.dumps({"delta": msg.text}) + "\n"
        yield json.dumps({"done": True, "source": "fallback"}) + "\n"
