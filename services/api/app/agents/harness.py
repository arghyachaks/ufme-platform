"""Runs a Deep Agent and turns its graph events into a transparent, replayable stream.

Stream protocol (NDJSON, one object per line). Every event has a `type`:

  run        {id, agent, model, provider, local}             the run started on this model
  thinking   {text}                                          the agent's short summary of its approach
  todos      {items: [{content, status}]}                    the plan / to-do list, re-sent on every change
  task       {id, name, args, agent, status, summary?}       a tool call: status running -> done | error
  subagent   {id, kind, brief, status, summary?}             a sub-agent the supervisor started
  token      {msg, text}                                     live text from the supervisor
  step       {msg}                                           that message turned out to be working, not the answer
  answer     {text}                                          the final answer
  usage      {tokensIn, tokensOut, costUsd, toolCalls, subagents, ms}
  error      {message}
  done       {source}                                        agent | fallback

`delta` lines (the pre-harness protocol) are still emitted alongside answer text for older clients.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.agents.registry import ModelSpec
from app.models.agents import AgentEvent, AgentRun

PUBLIC_TOOLS = {"write_todos", "task", "share_thinking"}


def share_thinking(summary: str, plan: str = "") -> str:
    """Call this tool FIRST, once. summary: one or two plain sentences on how you understand the question and how
    you will answer it. plan: 2 to 5 short steps separated by ' | ', e.g.
    "Read the close overview | Check critical exceptions | Summarise what needs attention"."""
    return "noted. Now carry out the plan with the ufme tools."


def line(obj: dict[str, Any]) -> str:
    return json.dumps(obj, default=str) + "\n"


def _messages(update: Any) -> list[Any]:
    if not isinstance(update, dict):
        return []
    msgs = update.get("messages") or []
    msgs = getattr(msgs, "value", msgs)  # langgraph Overwrite
    return list(msgs) if isinstance(msgs, list | tuple) else []


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return ""


@dataclass
class Mapper:
    """Converts LangGraph `(namespace, mode, data)` stream items into harness events. Pure: easy to test."""

    seen_calls: set[str] = field(default_factory=set)
    done_calls: set[str] = field(default_factory=set)
    seen_msgs: set[str] = field(default_factory=set)
    call_names: dict[str, str] = field(default_factory=dict)
    last_todos: str = ""
    own_todos: bool = False  # the agent maintains its to-do list with write_todos
    plan: list[str] = field(default_factory=list)  # the plan it shared up front
    answer: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    tool_calls: int = 0
    subagents: int = 0

    def feed(self, ns: tuple[str, ...], mode: str, data: Any) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        top = len(ns) == 0
        who = "supervisor" if top else ns[-1].split(":")[0]
        if mode == "messages":
            chunk, _meta = data
            text = _text(getattr(chunk, "content", ""))
            if top and text and getattr(chunk, "type", "") in ("AIMessageChunk", "ai"):
                out.append({"type": "token", "msg": getattr(chunk, "id", None), "text": text})
            return out
        if mode != "updates" or not isinstance(data, dict):
            return out
        for update in data.values():
            if isinstance(update, dict) and "todos" in update:
                out += self._todos(update.get("todos"))
            for m in _messages(update):
                out += self._message(m, top, who)
        return out

    def progress(self, done: int) -> list[dict[str, Any]]:
        """To-do statuses for a plan shared up front (models that don't maintain write_todos themselves):
        the first `done` steps completed, the next one in progress."""
        if self.own_todos or not self.plan:
            return []
        done = min(done, len(self.plan))
        items = [
            {"content": c, "status": "completed" if i < done else "in_progress" if i == done else "pending"}
            for i, c in enumerate(self.plan)
        ]
        return self._todos(items)

    def _todos(self, todos: Any) -> list[dict[str, Any]]:
        items = [
            {"content": t.get("content", ""), "status": t.get("status", "pending")}
            for t in (todos or [])
            if isinstance(t, dict)
        ]
        key = json.dumps(items)
        if not items or key == self.last_todos:
            return []
        self.last_todos = key
        return [{"type": "todos", "items": items}]

    def _message(self, m: Any, top: bool, who: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        kind = getattr(m, "type", "")
        mid = getattr(m, "id", None) or str(id(m))
        if kind == "ai":
            if mid in self.seen_msgs:
                return out
            self.seen_msgs.add(mid)
            usage = getattr(m, "usage_metadata", None) or {}
            self.tokens_in += int(usage.get("input_tokens", 0) or 0)
            self.tokens_out += int(usage.get("output_tokens", 0) or 0)
            calls = getattr(m, "tool_calls", None) or []
            if calls and top:
                out.append({"type": "step", "msg": getattr(m, "id", None)})
            if not calls and top:
                text = _text(m.content).strip()
                if text:
                    self.answer = text
                    out += self.progress(len(self.plan))
            for c in calls:
                cid = c.get("id") or f"{mid}:{len(self.seen_calls)}"
                if cid in self.seen_calls:
                    continue
                self.seen_calls.add(cid)
                name, args = c.get("name", ""), c.get("args") or {}
                self.call_names[cid] = name
                if name == "write_todos":
                    self.own_todos = True
                    out += self._todos(args.get("todos"))
                elif name == "share_thinking":
                    out.append({"type": "thinking", "text": str(args.get("summary", ""))[:600], "agent": who})
                    if top and not self.own_todos and not self.plan:
                        raw = args.get("plan") or []
                        steps = raw if isinstance(raw, list) else re.split(r"\s*(?:\||\n|;)\s*", str(raw))
                        self.plan = [str(x).strip(" -•")[:160] for x in steps if str(x).strip(" -•")][:6]
                        out += self.progress(0)
                elif name == "task":
                    self.subagents += 1
                    out.append(
                        {
                            "type": "subagent",
                            "id": cid,
                            "kind": args.get("subagent_type", "general-purpose"),
                            "brief": str(args.get("description", ""))[:400],
                            "status": "running",
                        }
                    )
                else:
                    self.tool_calls += 1
                    out.append(
                        {
                            "type": "task",
                            "id": cid,
                            "name": name,
                            "args": args,
                            "agent": who,
                            "status": "running",
                        }
                    )
        elif kind == "tool":
            cid = getattr(m, "tool_call_id", None)
            if not cid or cid in self.done_calls or cid not in self.call_names:
                return out
            self.done_calls.add(cid)
            name = self.call_names[cid]
            if name in ("write_todos", "share_thinking"):
                return out
            status = "error" if getattr(m, "status", "success") == "error" else "done"
            if top and self.plan and not self.own_todos:
                finished = sum(
                    1
                    for c in self.done_calls
                    if self.call_names.get(c) not in ("write_todos", "share_thinking")
                )
                out += self.progress(min(finished, len(self.plan) - 1))
            summary = _text(m.content)[:280]
            out.append(
                {
                    "type": "subagent" if name == "task" else "task",
                    "id": cid,
                    "status": status,
                    "summary": summary,
                }
            )
        return out


class Recorder:
    """Persists a run and its events (the evidence behind the Operations dashboard and run replay)."""

    def __init__(
        self, db: Session, tenant_id: uuid.UUID, agent: str, actor: str, question: str, page: str | None
    ):
        self.db = db
        self.events: list[dict[str, Any]] = []
        self.started = time.monotonic()
        self.run = AgentRun(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            agent=agent,
            actor=actor,
            question=question[:4000],
            page=(page or None) and page[:120],
            model="-",
            provider="-",
            status="running",
            started_at=datetime.now(UTC),
            tokens_in=0,
            tokens_out=0,
            cost_usd=Decimal(0),
            tool_calls=0,
            subagents=0,
            egress=False,
            summary={},
        )

    def emit(self, event: dict[str, Any]) -> str:
        if event.get("type") != "token":  # tokens are re-derivable from the answer; keep the log compact
            self.events.append(event)
        return line(event)

    def model(self, spec: ModelSpec) -> None:
        self.run.model, self.run.provider, self.run.egress = spec.name, spec.provider, not spec.local

    def finish(
        self, status: str, mapper: Mapper | None, spec: ModelSpec | None, error: str | None = None
    ) -> dict:
        ms = int((time.monotonic() - self.started) * 1000)
        r = self.run
        r.status, r.error, r.finished_at = status, error, datetime.now(UTC)
        if mapper is not None:
            r.tokens_in, r.tokens_out = mapper.tokens_in, mapper.tokens_out
            r.tool_calls, r.subagents = mapper.tool_calls, mapper.subagents
            if spec is not None:
                r.cost_usd = spec.cost(mapper.tokens_in, mapper.tokens_out)
        r.summary = {"ms": ms, "events": len(self.events)}
        try:
            self.db.add(r)
            self.db.flush()
            now = datetime.now(UTC)
            for i, e in enumerate(self.events):
                self.db.add(
                    AgentEvent(tenant_id=r.tenant_id, run_id=r.id, seq=i, type=e["type"], payload=e, at=now)
                )
            self.db.commit()
        except Exception:  # telemetry must never break an answer
            self.db.rollback()
        return {
            "type": "usage",
            "tokensIn": r.tokens_in,
            "tokensOut": r.tokens_out,
            "costUsd": float(r.cost_usd),
            "toolCalls": r.tool_calls,
            "subagents": r.subagents,
            "ms": ms,
            "model": r.model,
        }


def run_graph(
    build: Callable[[ModelSpec], Any],
    specs: list[ModelSpec],
    inputs: dict[str, Any],
    rec: Recorder,
    max_steps: int,
) -> Iterator[str]:
    """Runs the agent on the first model that answers (fallback order). Yields NDJSON event lines.

    Raises RuntimeError when no model produced anything, so the caller can fall back to a plain answer."""
    last_error = "no approved model is bound to this agent"
    for spec in specs:
        mapper = Mapper()
        started = False
        try:
            agent = build(spec)
            for ns, mode, data in agent.stream(
                inputs, {"recursion_limit": max_steps}, stream_mode=["updates", "messages"], subgraphs=True
            ):
                if not started:
                    started = True
                    rec.model(spec)
                    yield rec.emit(
                        {
                            "type": "run",
                            "id": str(rec.run.id),
                            "agent": rec.run.agent,
                            "model": spec.model,
                            "provider": spec.provider,
                            "local": spec.local,
                        }
                    )
                for ev in mapper.feed(tuple(ns), mode, data):
                    yield rec.emit(ev)
                    if ev["type"] == "token":
                        yield line({"delta": ev["text"]})
            if not mapper.answer:
                raise RuntimeError("the agent finished without an answer")
            if re.match(
                r"^\s*(share_thinking|write_todos|task|close_overview|list_\w+)\s*[:(]", mapper.answer
            ):
                raise RuntimeError("the model wrote a tool call as text instead of calling it")
            yield rec.emit({"type": "answer", "text": mapper.answer})
            yield line(rec.finish("completed", mapper, spec))
            yield line({"type": "done", "source": "agent", "done": True})
            return
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"[:500]
            if started:
                yield rec.emit({"type": "error", "message": "The agent stopped unexpectedly: " + last_error})
                raise RuntimeError(last_error) from exc
    raise RuntimeError(last_error)
