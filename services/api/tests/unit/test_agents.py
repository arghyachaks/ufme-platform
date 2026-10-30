"""Agent harness: event mapping (plan, to-dos, tasks, sub-agents), model fallback, recording, operations views."""

import json
from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from sqlalchemy import select

from app.agents import harness, ops, registry, tools
from app.core.config import settings
from app.models import AgentEvent, AgentRun
from app.seed import seed_demo
from app.services.workflow import resolve_actor

ANALYST = {"X-Ufme-User": "priya.nair@example.com"}
DIRECTOR = {"X-Ufme-User": "liam.walsh@example.com"}


def _lines(text: str) -> list[dict[str, Any]]:
    return [json.loads(x) for x in text.splitlines() if x.strip()]


def _script() -> list[tuple[tuple[str, ...], str, Any]]:
    """What a Deep Agent run looks like on the wire: think, plan, two parallel lookups, a sub-agent, answer."""
    plan = AIMessage(
        content="",
        id="m1",
        tool_calls=[
            {
                "id": "c0",
                "name": "share_thinking",
                "args": {"summary": "Check the overview, then exceptions."},
            },
            {
                "id": "c1",
                "name": "write_todos",
                "args": {
                    "todos": [
                        {"content": "Read close overview", "status": "in_progress"},
                        {"content": "List critical exceptions", "status": "pending"},
                    ]
                },
            },
        ],
        usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
    )
    work = AIMessage(
        content="",
        id="m2",
        tool_calls=[
            {"id": "c2", "name": "close_overview", "args": {}},
            {
                "id": "c3",
                "name": "task",
                "args": {"subagent_type": "researcher", "description": "DE03-IN04 breaks"},
            },
        ],
        usage_metadata={"input_tokens": 300, "output_tokens": 30, "total_tokens": 330},
    )
    final = AIMessage(
        content="Close is 72% done.\n• EX-8902 is the largest break.",
        id="m3",
        usage_metadata={"input_tokens": 500, "output_tokens": 40, "total_tokens": 540},
    )
    return [
        ((), "updates", {"model": {"messages": [plan]}}),
        (
            (),
            "updates",
            {
                "tools": {
                    "messages": [ToolMessage("noted", tool_call_id="c0")],
                    "todos": plan.tool_calls[1]["args"]["todos"],
                }
            },
        ),
        ((), "updates", {"model": {"messages": [work]}}),
        (
            ("tools:abc",),
            "updates",
            {
                "model": {
                    "messages": [
                        AIMessage(
                            content="",
                            id="s1",
                            tool_calls=[
                                {"id": "s-c1", "name": "list_exceptions", "args": {"entity": "DE03"}}
                            ],
                        )
                    ]
                }
            },
        ),
        (
            ("tools:abc",),
            "updates",
            {"tools": {"messages": [ToolMessage('{"count":3}', tool_call_id="s-c1")]}},
        ),
        (
            (),
            "updates",
            {
                "tools": {
                    "messages": [
                        ToolMessage('{"closeCompletion":72}', tool_call_id="c2"),
                        ToolMessage("3 open breaks", tool_call_id="c3"),
                    ]
                }
            },
        ),
        ((), "messages", (AIMessageChunk(content="Close is 72% done.", id="m3"), {})),
        ((), "updates", {"model": {"messages": [final]}}),
    ]


def test_mapper_shows_thinking_plan_tasks_and_subagents() -> None:
    m = harness.Mapper()
    events = [e for ns, mode, data in _script() for e in m.feed(ns, mode, data)]
    kinds = [e["type"] for e in events]
    assert kinds[:3] == ["step", "thinking", "todos"]
    assert events[2]["items"][0] == {"content": "Read close overview", "status": "in_progress"}
    assert kinds.count("todos") == 1  # the same list re-sent by the tools node is not repeated
    tasks = [e for e in events if e["type"] == "task"]
    assert [(t["name"] if "name" in t else t["id"], t["status"]) for t in tasks] == [
        ("close_overview", "running"),
        ("list_exceptions", "running"),
        ("s-c1", "done"),
        ("c2", "done"),
    ]
    assert tasks[1]["agent"] == "tools"  # the sub-agent's own lookup is attributed to it
    sub = [e for e in events if e["type"] == "subagent"]
    assert sub[0]["kind"] == "researcher" and sub[0]["status"] == "running" and sub[1]["status"] == "done"
    assert {"type": "token", "msg": "m3", "text": "Close is 72% done."} in events
    assert m.answer.startswith("Close is 72% done.")
    assert (m.tokens_in, m.tokens_out, m.tool_calls, m.subagents) == (900, 90, 2, 1)


class _Agent:
    def __init__(self, items: list[Any]) -> None:
        self.items = items

    def stream(self, inputs: Any, config: Any, **kw: Any) -> Iterator[Any]:
        assert kw == {"stream_mode": ["updates", "messages"], "subgraphs": True}
        yield from self.items


def test_plan_shared_up_front_becomes_a_live_todo_list() -> None:
    """Small models often skip write_todos; the plan they share with share_thinking is tracked instead."""
    m = harness.Mapper()
    think = AIMessage(
        content="",
        id="a1",
        tool_calls=[
            {
                "id": "k0",
                "name": "share_thinking",
                "args": {
                    "summary": "Look, then answer.",
                    "plan": ["Read overview", "Check exceptions", "Summarise"],
                },
            }
        ],
    )
    look = AIMessage(content="", id="a2", tool_calls=[{"id": "k1", "name": "close_overview", "args": {}}])
    final = AIMessage(content="Done.", id="a3")
    ev = m.feed((), "updates", {"model": {"messages": [think]}})
    assert ev[-1] == {
        "type": "todos",
        "items": [
            {"content": "Read overview", "status": "in_progress"},
            {"content": "Check exceptions", "status": "pending"},
            {"content": "Summarise", "status": "pending"},
        ],
    }
    m.feed((), "updates", {"tools": {"messages": [ToolMessage("noted", tool_call_id="k0")]}})
    m.feed((), "updates", {"model": {"messages": [look]}})
    ev = m.feed((), "updates", {"tools": {"messages": [ToolMessage("{}", tool_call_id="k1")]}})
    assert [i["status"] for i in ev[0]["items"]] == ["completed", "in_progress", "pending"]
    ev = m.feed((), "updates", {"model": {"messages": [final]}})
    assert [i["status"] for i in ev[0]["items"]] == ["completed"] * 3


def test_run_graph_records_the_run_and_falls_back_across_models(db: Any) -> None:
    tenant = seed_demo(db)
    down = registry.ModelSpec(name="down", provider="ollama", model="x")
    hosted = registry.ModelSpec(
        name="hosted", provider="anthropic", model="y", price_in=Decimal("0.003"), price_out=Decimal("0.015")
    )

    def build(spec: registry.ModelSpec) -> Any:
        if spec.name == "down":
            raise ConnectionError("refused")
        return _Agent(_script())

    rec = harness.Recorder(
        db, tenant.id, "assist", "liam.walsh@example.com", "How is the close?", "/dashboard"
    )
    out = _lines("".join(harness.run_graph(build, [down, hosted], {"messages": []}, rec, 20)))
    assert out[0]["type"] == "run" and out[0]["model"] == "y" and out[0]["local"] is False
    assert {"type": "answer", "text": "Close is 72% done.\n• EX-8902 is the largest break."} in out
    assert any(x.get("delta") == "Close is 72% done." for x in out)  # older clients still get text
    usage = next(x for x in out if x.get("type") == "usage")
    assert usage["tokensIn"] == 900 and usage["costUsd"] == pytest.approx(0.0027 + 0.00135)
    assert out[-1]["type"] == "done" and out[-1]["source"] == "agent"
    run = db.scalar(select(AgentRun))
    assert run.status == "completed" and run.egress is True and run.model == "hosted"
    stored = list(db.scalars(select(AgentEvent).where(AgentEvent.run_id == run.id)))
    assert {e.type for e in stored} >= {"run", "thinking", "todos", "task", "subagent", "answer"}
    assert "token" not in {e.type for e in stored}


def test_run_graph_raises_when_no_model_runs(db: Any) -> None:
    tenant = seed_demo(db)
    rec = harness.Recorder(db, tenant.id, "assist", "a@b", "q", None)

    def build(spec: registry.ModelSpec) -> Any:
        raise ConnectionError("refused")

    with pytest.raises(RuntimeError, match="refused"):
        list(
            harness.run_graph(build, [registry.ModelSpec(name="a", provider="ollama", model="x")], {}, rec, 5)
        )


def test_registry_blocks_unapproved_models_and_never_exposes_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        settings,
        "agent_models",
        json.dumps(
            [
                {
                    "name": "claude",
                    "provider": "anthropic",
                    "model": "claude-x",
                    "status": "blocked",
                    "api_key_env": "UFME_TEST_KEY",
                    "price_in": 0.003,
                },
                {"name": "gpt", "provider": "openai", "model": "gpt-x", "api_key_env": "UFME_TEST_KEY"},
            ]
        ),
    )
    monkeypatch.setattr(
        settings, "agent_bindings", json.dumps({"assist": ["claude", "gpt", "local-default"]})
    )
    monkeypatch.setenv("UFME_TEST_KEY", "secret-value")
    registry.models.cache_clear()
    try:
        assert [s.name for s in registry.candidates("assist")] == ["gpt", "local-default"]
        assert [s.name for s in registry.candidates("other")] == ["local-default"]
        pub = json.dumps([m.public() for m in registry.models().values()])
        assert "secret-value" not in pub and '"keyConfigured": true' in pub
    finally:
        registry.models.cache_clear()


def test_tools_are_read_only_and_entity_scoped(db: Any) -> None:
    tenant = seed_demo(db)
    analyst = resolve_actor(db, tenant, "priya.nair@example.com")
    fns = {f.__name__: f for f in tools.build(db, tenant, analyst)}
    assert not any(n.startswith(("approve", "decide", "post", "update", "delete", "create")) for n in fns)
    items = json.loads(fns["list_exceptions"](limit=25))["items"]
    assert items and all(analyst.covers(i["entity"]) for i in items)
    assert "access" in fns["close_readiness"](entity="IN04")
    assert "closeCompletion" in fns["close_overview"]()
    for name in ("list_cases", "latest_matching_run", "review_queue", "open_approvals"):
        assert json.loads(fns[name]())  # each returns JSON


def test_assist_endpoint_falls_back_and_operations_views(
    db: Any, client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_demo(db)
    monkeypatch.setattr(settings, "ollama_url", "http://127.0.0.1:9")
    registry.models.cache_clear()
    try:
        r = client.post("/api/v1/ai/assist/stream", json={"prompt": "Summarize CS-1042"}, headers=ANALYST)
        lines = _lines(r.text)
        assert "CS-1042" in "".join(x.get("delta", "") for x in lines)
        assert {"done": True, "source": "fallback"} in lines and lines[-1]["type"] == "usage"
        client.post("/api/v1/ai/assist/stream", json={"prompt": "hello"}, headers=DIRECTOR)
    finally:
        registry.models.cache_clear()

    mine = client.get("/api/v1/agents/overview", headers=ANALYST).json()
    assert mine["scope"] == "mine" and mine["totals"]["runs"] == 1 and mine["totals"]["fallback"] == 1
    assert mine["infosec"]["autonomousActions"] == 0 and mine["infosec"]["localOnly"] is True
    allruns = client.get("/api/v1/agents/overview", headers=DIRECTOR).json()
    assert allruns["scope"] == "tenant" and allruns["totals"]["runs"] == 2
    assert any(m["name"] == "local-default" for m in allruns["models"])
    rid = allruns["recent"][-1]["id"]
    detail = client.get(f"/api/v1/agents/runs/{rid}", headers=DIRECTOR).json()
    assert detail["status"] == "fallback" and detail["events"][-1]["type"] == "answer"
    other = next(x["id"] for x in allruns["recent"] if x["actor"] != "priya.nair@example.com")
    assert client.get(f"/api/v1/agents/runs/{other}", headers=ANALYST).status_code == 404
    assert client.get("/api/v1/agents/runs/not-a-uuid", headers=ANALYST).status_code == 404
    assert client.get("/api/v1/agents/models", headers=ANALYST).status_code == 200


def test_anomalies_flag_failures_egress_and_unknown_models() -> None:
    from datetime import UTC, datetime

    now = datetime(2026, 10, 30, 10, tzinfo=UTC)
    runs = [
        AgentRun(
            model="local-default",
            provider="ollama",
            status="fallback",
            started_at=now,
            tokens_in=10,
            tokens_out=1,
            egress=False,
            subagents=0,
            actor="a",
            agent="assist",
            summary={},
        )
        for _ in range(4)
    ] + [
        AgentRun(
            model="rogue",
            provider="openai",
            status="completed",
            started_at=now,
            tokens_in=1,
            tokens_out=1,
            egress=True,
            subagents=0,
            actor="b",
            agent="assist",
            summary={},
        )
    ]
    kinds = {a["kind"] for a in ops.anomalies(runs, now)}
    assert {"Failure rate", "Unregistered model", "Data egress"} <= kinds
