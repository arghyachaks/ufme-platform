"""ufme Assist: streaming contract, grounding, and graceful fallback when the local model is down."""

import json
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.seed import seed_demo
from app.services import assist


@pytest.fixture
def seeded(db: Any, client: TestClient) -> TestClient:
    seed_demo(db)
    return client


def _lines(r: Any) -> list[dict[str, Any]]:
    return [json.loads(x) for x in r.text.splitlines() if x.strip()]


@pytest.fixture
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ollama_url", "http://127.0.0.1:9")  # nothing listens on the discard port


def test_status_offline(offline: None, seeded: TestClient) -> None:
    body = seeded.get("/api/v1/ai/assist/status").json()
    assert body["online"] is False and body["model"] == settings.assist_model


def test_stream_falls_back_when_model_down(offline: None, seeded: TestClient) -> None:
    r = seeded.post("/api/v1/ai/assist/stream", json={"prompt": "Summarize CS-1042", "page": "/dashboard"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/x-ndjson")
    lines = _lines(r)
    assert "CS-1042" in "".join(x.get("delta", "") for x in lines)
    assert lines[-1] == {"done": True, "source": "fallback"}


class _FakeStream:
    def __init__(self, sent: dict[str, Any]) -> None:
        self.sent = sent
        self.status_code = 200

    def __enter__(self) -> "_FakeStream":
        return self

    def __exit__(self, *a: object) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    def iter_lines(self) -> Iterator[str]:
        yield json.dumps({"message": {"content": "EX-8902 is "}})
        yield ""
        yield json.dumps({"message": {"content": "open."}, "done": True})


def test_stream_uses_local_model_with_grounding(monkeypatch: pytest.MonkeyPatch, seeded: TestClient) -> None:
    sent: dict[str, Any] = {}

    def fake_stream(method: str, url: str, json: dict[str, Any], timeout: Any) -> _FakeStream:
        sent.update(json)
        return _FakeStream(sent)

    monkeypatch.setattr(httpx, "stream", fake_stream)
    r = seeded.post(
        "/api/v1/ai/assist/stream",
        json={
            "prompt": "Why is EX-8902 open?",
            "history": [{"role": "user", "content": "hi"}, {"role": "system", "content": "x"}],
        },
    )
    lines = _lines(r)
    assert "".join(x.get("delta", "") for x in lines) == "EX-8902 is open."
    assert lines[-1]["source"] == "local-llm"
    msgs = sent["messages"]
    assert msgs[0]["role"] == "system" and "ufme Assist" in msgs[0]["content"]
    assert [m["role"] for m in msgs[1:]] == [
        "user",
        "user",
    ]  # injected system turns from the client are dropped
    assert sent["model"] == settings.assist_model and sent["stream"] is True


def test_facts_are_grounded_in_tenant_data(db: Any) -> None:
    tenant = seed_demo(db)
    facts = assist._facts(db, tenant, "/recon")
    for expected in ("screen: /recon", "EX-8902", "CS-1042", "Period close completion"):
        assert expected in facts
