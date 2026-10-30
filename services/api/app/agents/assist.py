"""ufme Assist as a harness agent: it thinks, plans, works through its to-do list with read-only tools (and
parallel sub-agents for broad questions), then answers. Everything it does is streamed and recorded."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from sqlalchemy.orm import Session

from app.agents import harness, registry, tools
from app.core.config import settings
from app.models.tenant import Tenant
from app.services.workflow import Actor

PROMPT = """You are ufme Assist, the analyst agent inside ufme, an intercompany reconciliation platform.
You help controllers, accountants and finance managers understand matches, exceptions and close readiness.

How you work (the user watches every step):
1. Your first action is always a call to the share_thinking tool (a real tool call, never written as text) with
   a one- or two-sentence summary of how you read the question and your plan as 2 to 5 short steps.
2. Work through the plan step by step. If you keep a to-do list with write_todos, mark steps in_progress and
   completed as you go.
3. Use the ufme tools to get facts. Never guess amounts, IDs, people or dates.
4. For broad questions that cover several entities or topics, delegate independent parts to the "researcher"
   sub-agent with the task tool, several at once (at most {max_sub} in parallel), each with a precise brief.
5. Then answer.

Answer rules: lead with the answer, then at most 4 short bullets starting with "• ". Plain business English, no
markdown tables, no LaTeX. Quote IDs exactly (EX-8902, CS-1042). Do not mention tools, models or prompts.
You can explain and recommend but you cannot approve, post or change anything: actions go through the normal
approval flow. Do not use file tools; use only the ufme tools.
{page}"""

RESEARCHER = """You are a ufme research sub-agent. Answer the brief you are given using only the ufme tools.
Return a compact factual finding (at most 6 lines) with exact IDs and amounts. Do not recommend actions."""


def stream(
    db: Session,
    tenant: Tenant,
    actor: Actor,
    prompt: str,
    history: list[dict[str, str]],
    page: str | None,
    legacy: Any,
) -> Iterator[str]:
    rec = harness.Recorder(db, tenant.id, "assist", actor.email, prompt, page)
    read_tools = tools.build(db, tenant, actor)

    def build(spec: registry.ModelSpec) -> Any:
        from deepagents import create_deep_agent

        model = registry.chat_model(spec)
        return create_deep_agent(
            model=model,
            tools=[harness.share_thinking, *read_tools],
            system_prompt=PROMPT.format(
                max_sub=settings.agent_max_subagents,
                page=f"The user is on the ufme screen: {page}" if page else "",
            ),
            subagents=[
                {
                    "name": "researcher",
                    "description": "Looks into one entity, entity pair or topic in ufme and returns the facts.",
                    "system_prompt": RESEARCHER,
                    "tools": list(read_tools),
                    "model": model,
                }
            ],
            name="ufme-assist",
        )

    messages = [m for m in history[-8:] if m.get("role") in ("user", "assistant")]
    messages.append({"role": "user", "content": prompt})
    try:
        yield from harness.run_graph(
            build, registry.candidates("assist"), {"messages": messages}, rec, settings.agent_max_steps
        )
    except Exception as exc:
        text = ""
        for raw in legacy():
            yield raw
            for part in raw.splitlines():
                if '"delta"' in part:
                    text += json.loads(part).get("delta", "")
        rec.emit({"type": "answer", "text": text})
        yield harness.line(rec.finish("fallback", None, None, str(exc)[:500]))
