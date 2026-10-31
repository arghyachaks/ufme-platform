"""Agent harness: event mapping (plan, to-dos, tasks, sub-agents), model fallback, recording, operations views."""

import json
from collections.abc import Iterator
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from sqlalchemy import func, select

from app.agents import harness, ops, registry, tools
from app.core.config import settings
from app.models import AgentEvent, AgentRun, AuditEvent
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
    registry.configured.cache_clear()
    try:
        assert [s.name for s in registry.candidates("assist")] == ["gpt", "local-default"]
        assert [s.name for s in registry.candidates("other")] == ["local-default"]
        pub = json.dumps([m.public() for m in registry.models().values()])
        assert "secret-value" not in pub and '"keyConfigured": true' in pub
    finally:
        registry.configured.cache_clear()


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
    registry.configured.cache_clear()
    try:
        r = client.post("/api/v1/ai/assist/stream", json={"prompt": "Summarize CS-1042"}, headers=ANALYST)
        lines = _lines(r.text)
        assert "CS-1042" in "".join(x.get("delta", "") for x in lines)
        assert {"done": True, "source": "fallback"} in lines and lines[-1]["type"] == "usage"
        client.post("/api/v1/ai/assist/stream", json={"prompt": "hello"}, headers=DIRECTOR)
    finally:
        registry.configured.cache_clear()

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


CONTROLLER = {"X-Ufme-User": "daniel.ortiz@example.com"}
MANAGER = {"X-Ufme-User": "arjun.rao@example.com"}


def test_model_admin_four_eyes_and_bindings(db: Any, client: TestClient) -> None:
    seed_demo(db)
    new = {
        "name": "claude-sonnet",
        "provider": "anthropic",
        "model": "claude-x",
        "apiKeyEnv": "ANTHROPIC_API_KEY",
        "priceIn": 0.003,
        "priceOut": 0.015,
        "note": "stronger planning",
    }
    assert client.post("/api/v1/agents/models", json=new, headers=MANAGER).status_code == 403
    bad = client.post("/api/v1/agents/models", json=new | {"apiKeyEnv": "sk-live-123"}, headers=CONTROLLER)
    assert bad.status_code == 422 or bad.json()["code"] == "bad_key_ref"
    r = client.post("/api/v1/agents/models", json=new, headers=CONTROLLER)
    assert r.status_code == 201 and r.json()["status"] == "pending" and r.json()["local"] is False
    # not usable until approved
    put = client.put("/api/v1/agents/bindings/assist", json={"models": ["claude-sonnet"]}, headers=CONTROLLER)
    assert put.status_code >= 400
    assert client.post("/api/v1/agents/models/claude-sonnet/approve", headers=CONTROLLER).status_code == 403
    ok = client.post("/api/v1/agents/models/claude-sonnet/approve", headers=DIRECTOR)
    assert ok.status_code == 200 and ok.json()["approvedBy"] == "liam.walsh@example.com"
    b = client.put(
        "/api/v1/agents/bindings/assist",
        json={"models": ["claude-sonnet", "local-default"]},
        headers=CONTROLLER,
    ).json()
    assert b["assist"] == ["claude-sonnet", "local-default"]
    listing = client.get("/api/v1/agents/models", headers=ANALYST).json()
    assert {m["name"] for m in listing["models"]} >= {"local-default", "claude-sonnet"}
    assert "sk-" not in json.dumps(listing)
    client.post("/api/v1/agents/models/claude-sonnet/block", headers=CONTROLLER)
    tenant = seed_demo(db)
    assert [s.name for s in registry.candidates("assist", db, tenant.id)] == ["local-default"]
    acts = {e.action for e in db.scalars(select(AuditEvent).where(AuditEvent.object_type.like("agent_%")))}
    assert {
        "agent_model.proposed",
        "agent_model.approved",
        "agent_binding.changed",
        "agent_model.blocked",
    } <= acts


def test_requester_cannot_approve_own_model(db: Any, client: TestClient) -> None:
    seed_demo(db)
    m = {"name": "gpt-mini", "provider": "openai", "model": "gpt-x", "apiKeyEnv": "OPENAI_API_KEY"}
    assert client.post("/api/v1/agents/models", json=m, headers=DIRECTOR).status_code == 201
    r = client.post("/api/v1/agents/models/gpt-mini/approve", headers=DIRECTOR)
    assert r.status_code == 403 and r.json()["code"] == "sod_violation"


def test_plan_first_reminds_only_on_the_first_turn() -> None:
    from langchain_core.messages import HumanMessage

    seen: list[Any] = []

    class Req:
        def __init__(self, messages: list[Any]) -> None:
            self.messages = messages

        def override(self, messages: list[Any]) -> "Req":
            return Req(messages)

    mw = harness.plan_first()
    mw.wrap_model_call(Req([HumanMessage("Why is EX-1 open?")]), lambda r: seen.append(r.messages))
    assert seen[0][-1].content.endswith(harness.PLAN_NUDGE)
    planned = [
        HumanMessage("q"),
        AIMessage(content="", tool_calls=[{"id": "a", "name": "share_thinking", "args": {}}]),
    ]
    mw.wrap_model_call(Req(planned), lambda r: seen.append(r.messages))
    assert seen[1] == planned


def test_subagent_cap_trims_parallel_fan_out() -> None:
    cap = harness.subagent_cap(2)
    calls = [{"id": f"t{i}", "name": "task", "args": {}} for i in range(4)] + [
        {"id": "x", "name": "close_overview", "args": {}}
    ]
    out = cap.after_model({"messages": [AIMessage(content="", id="m", tool_calls=calls)]}, None)
    assert [c["id"] for c in out["messages"][0].tool_calls] == ["t0", "t1", "x"]
    assert out["messages"][0].id == "m"  # replaces the model's message instead of adding one
    assert cap.after_model({"messages": [AIMessage(content="hi", id="n")]}, None) is None


def test_stop_records_a_cancelled_run(db: Any) -> None:
    tenant = seed_demo(db)
    rec = harness.Recorder(db, tenant.id, "assist", "a@b", "q", None)
    spec = registry.ModelSpec(name="local-default", provider="ollama", model="x")
    gen = harness.run_graph(lambda s: _Agent(_script()), [spec], {}, rec, 20)
    next(gen)
    next(gen)
    gen.close()  # what Starlette does when the browser disconnects
    assert db.scalar(select(AgentRun)).status == "cancelled"


def test_memory_threads_are_namespaced_per_tenant_and_person() -> None:
    import uuid

    from app.agents import memory

    t = uuid.uuid4()
    tid = memory.thread_id(t, "a@b", "8c5b6a3e-2f7e-4f43-9e1c-1d2a3b4c5d6e")
    assert tid == f"{t}:a@b:8c5b6a3e-2f7e-4f43-9e1c-1d2a3b4c5d6e"
    assert memory.thread_id(t, "a@b", "../other") is None and memory.thread_id(t, "a@b", None) is None


# ---------------------------------------------------------------- Recon Investigator: pause, decide, resume


def _scripted(script: list[AIMessage]) -> Any:
    """A chat model that replays a script (drives the real Deep Agents graph without an LLM)."""
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.outputs import ChatGeneration, ChatResult

    class Scripted(BaseChatModel):
        @property
        def _llm_type(self) -> str:
            return "scripted"

        def bind_tools(self, tools: Any, **kw: Any) -> Any:
            return self

        def _generate(
            self, messages: Any, stop: Any = None, run_manager: Any = None, **kw: Any
        ) -> ChatResult:
            msg = script.pop(0) if script else AIMessage(content="Done.")
            return ChatResult(generations=[ChatGeneration(message=msg)])

    return Scripted()


def _investigation(items: list[str]) -> list[AIMessage]:
    return [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "i0",
                    "name": "share_thinking",
                    "args": {
                        "summary": "Look at the open items, then propose what agrees.",
                        "plan": "Read items | Propose | Summarise",
                    },
                }
            ],
        ),
        AIMessage(content="", tool_calls=[{"id": "i1", "name": "unmatched_items", "args": {"limit": 5}}]),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "i2",
                    "name": "propose_match",
                    "args": {"item_ids": items, "rationale": "Same reference and amount"},
                }
            ],
        ),
    ]


@pytest.fixture
def ledger(db: Any, client: TestClient, tmp_path: Any, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from datetime import UTC, datetime

    seed_demo(db, now=datetime(2026, 10, 18, 12, 0, tzinfo=UTC))
    monkeypatch.setattr(settings, "ingest_inline", True)
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    monkeypatch.setattr(settings, "agent_memory", False)  # in-process checkpointer for the pause/resume
    assert client.post("/api/v1/data/sources/SRC-01/sync?rows=3000").status_code == 202
    assert client.post("/api/v1/recon/runs", headers=ANALYST).status_code == 202
    return client


def _pair_items(client: TestClient) -> tuple[str, list[str]]:
    assert client.get("/api/v1/agents/investigator/pairs", headers=DIRECTOR).json()
    data = client.get("/api/v1/recon/unmatched", headers=DIRECTOR).json()
    assert data["pair"] and data["sideA"] and data["sideB"]
    return data["pair"], [data["sideA"][0]["id"], data["sideB"][0]["id"]]


def test_investigator_pauses_for_a_person_and_resumes_on_their_decision(
    db: Any, ledger: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.models import ApprovalRequest

    client = ledger
    pair, items = _pair_items(client)
    scripts = [_investigation(items), [AIMessage(content="I proposed one match for review.")]]
    monkeypatch.setattr(registry, "chat_model", lambda spec: _scripted(scripts.pop(0)))
    before = db.scalar(select(func.count()).select_from(ApprovalRequest))

    analyst = client.post("/api/v1/agents/investigator/runs", json={"pair": "IN04-DE03"}, headers=ANALYST)
    assert analyst.status_code == 403  # out of the analyst's entity scope

    r = client.post("/api/v1/agents/investigator/runs", json={"pair": pair}, headers=DIRECTOR)
    ev = _lines(r.text)
    kinds = [e.get("type") for e in ev]
    assert "todos" in kinds and "approval" in kinds and ev[-1]["type"] == "paused"
    assert kinds.count("approval") == 1  # the second proposal in the same turn was held back
    appr = next(e for e in ev if e.get("type") == "approval")
    assert appr["name"] == "propose_match" and appr["args"]["item_ids"] == items
    assert db.scalar(select(func.count()).select_from(ApprovalRequest)) == before  # nothing happened yet
    run_id = ev[-1]["run"]
    listed = client.get("/api/v1/agents/investigator/runs", headers=DIRECTOR).json()
    assert listed[0]["status"] == "awaiting_approval" and listed[0]["pending"]["name"] == "propose_match"

    d = client.post(f"/api/v1/agents/runs/{run_id}/decide", json={"decision": "approve"}, headers=DIRECTOR)
    out = _lines(d.text)
    assert out[0] == {"type": "decision", "decision": "approve", "by": "liam.walsh@example.com"}
    done = [e for e in out if e.get("type") == "task" and e.get("status") in ("done", "error")]
    assert done and ("Submitted" in done[0]["summary"] or "Not submitted" in done[0]["summary"])
    assert {"type": "answer", "text": "I proposed one match for review."} in out
    again = client.post(
        f"/api/v1/agents/runs/{run_id}/decide", json={"decision": "approve"}, headers=DIRECTOR
    )
    assert again.status_code == 409
    detail = client.get(f"/api/v1/agents/runs/{run_id}", headers=DIRECTOR).json()
    assert detail["status"] == "completed"
    assert [e["type"] for e in detail["events"]].count("approval") == 1
    assert any(e["type"] == "decision" for e in detail["events"])


def test_investigator_reject_means_the_tool_never_runs(
    db: Any, ledger: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.models import ApprovalRequest

    client = ledger
    pair, items = _pair_items(client)
    scripts = [_investigation(items), [AIMessage(content="Understood, no match proposed.")]]
    monkeypatch.setattr(registry, "chat_model", lambda spec: _scripted(scripts.pop(0)))
    before = db.scalar(select(func.count()).select_from(ApprovalRequest))
    ev = _lines(client.post("/api/v1/agents/investigator/runs", json={"pair": pair}, headers=DIRECTOR).text)
    d = client.post(
        f"/api/v1/agents/runs/{ev[-1]['run']}/decide",
        json={"decision": "reject", "comment": "Different invoices"},
        headers=DIRECTOR,
    )
    assert {"type": "answer", "text": "Understood, no match proposed."} in _lines(d.text)
    assert db.scalar(select(func.count()).select_from(ApprovalRequest)) == before


@pytest.mark.parametrize(
    ("provider", "model", "base_url", "cls"),
    [
        ("openai", "gpt-4o", None, "ChatOpenAI"),
        ("azure_openai", "my-deployment", "https://r.openai.azure.com/", "AzureChatOpenAI"),
        ("anthropic", "claude-x", None, "ChatAnthropic"),
        ("google_genai", "gemini-2.5-flash", None, "ChatGoogleGenerativeAI"),
        ("openai-compatible-local", "local", "http://host.docker.internal:1234/v1", "ChatOpenAI"),
        ("ollama", "qwen3:8b", "http://host.docker.internal:11434", "ChatOllama"),
    ],
)
def test_hosted_providers_build_without_network(
    provider: str, model: str, base_url: str | None, cls: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("UFME_TEST_KEY", "test-key-not-real")
    key = None if provider in ("ollama", "openai-compatible-local") else "UFME_TEST_KEY"
    spec = registry.ModelSpec(name="x", provider=provider, model=model, base_url=base_url, api_key_env=key)
    assert type(registry.chat_model(spec)).__name__ == cls


def test_missing_key_is_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("UFME_NOPE", raising=False)
    spec = registry.ModelSpec(name="x", provider="openai", model="gpt-4o", api_key_env="UFME_NOPE")
    with pytest.raises(RuntimeError, match="UFME_NOPE is not configured"):
        registry.chat_model(spec)
