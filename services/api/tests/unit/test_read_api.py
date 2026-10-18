"""Contract tests: with the demo seed and a frozen clock, every endpoint returns exactly the data the frontend mocks
returned (apps/web/src/api/mock/*.ts → app/seed/demo/*.json)."""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed import load_fixtures, seed_demo
from app.services import audit
from app.services import read as read_service

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
FX = load_fixtures()
CORE = FX["core"]


@pytest.fixture
def seeded(db: Session, client: TestClient, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    tenant = seed_demo(db, now=NOW)
    # Freeze "now" for relative labels (age, SLA, due-in, last sync, last login).
    for name in ("exceptions", "cases", "sources", "admin"):
        original = getattr(read_service, name)
        monkeypatch.setattr(read_service, name, lambda d, t, _o=original: _o(d, t, now=NOW))
    assert audit.verify_chain(db, tenant.id)
    yield client


def unordered(items: list[Any]) -> list[str]:
    return sorted(json.dumps(i, sort_keys=True) for i in items)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/exceptions", CORE["exceptions"]),
        ("/cases", CORE["cases"]),
        ("/rules", CORE["rules"]),
        ("/policies", CORE["policies"]),
        ("/data/sources", CORE["sources"]),
        ("/audit/controls", CORE["controlTests"]),
        ("/workflow/stages", CORE["workflowStages"]),
        ("/ai/models", {"models": CORE["models"], "trend": CORE["modelTrend"]}),
        ("/ai/explanations", CORE["explanations"]),
        ("/ai/learning", {"signals": CORE["learningSignals"], "stats": CORE["learningStats"]}),
        ("/ai/copilot", {"messages": CORE["copilotSeed"], "prompts": CORE["copilotPrompts"]}),
        ("/data/quality", {"issues": CORE["qualityIssues"], "dimensions": CORE["qualityDimensions"]}),
        ("/data/lineage", list(CORE["lineage"].keys())),
        ("/data/lineage/TXN-US01-778120", CORE["lineage"]["TXN-US01-778120"]),
        ("/data/features", CORE["featureStore"]),
        ("/ops", {"services": CORE["services"], "jobs": CORE["jobs"]}),
        ("/graph", {"nodes": CORE["graphNodes"], "edges": CORE["graphEdges"]}),
        ("/workspace/recon", FX["recon"]),
        ("/workspace/dashboard", FX["dashboard"]),
    ],
)
def test_endpoint_matches_frontend_mock(seeded: TestClient, path: str, expected: Any) -> None:
    response = seeded.get(f"/api/v1{path}")
    assert response.status_code == 200, response.text
    body = response.json()
    if isinstance(expected, list) and expected and isinstance(expected[0], dict):
        assert unordered(body) == unordered(expected)
    else:
        assert body == expected


def test_simulations(seeded: TestClient) -> None:
    scenarios = seeded.get("/api/v1/rules/simulations").json()
    assert scenarios == [{"key": k, "label": v["scenario"]} for k, v in CORE["simulationResults"].items()]
    run = seeded.post("/api/v1/rules/simulations/widen/run")
    assert run.json() == CORE["simulationResults"]["widen"]
    assert seeded.post("/api/v1/rules/simulations/nope/run").status_code == 404


def test_admin_uses_real_role_counts(seeded: TestClient, db: Session) -> None:
    tenant = seed_demo(db, now=NOW)
    read_service.admin(db, tenant)  # surfaces service errors directly instead of as a 500
    response = seeded.get("/api/v1/admin")
    assert response.status_code == 200, response.text
    body = response.json()
    assert unordered(body["users"]) == unordered(CORE["users"])
    assert unordered(body["entities"]) == unordered(CORE["legalEntities"])
    counts = {r["role"]: r["users"] for r in body["roles"]}
    assert counts["Analyst"] == sum(u["role"] == "Analyst" for u in CORE["users"])
    assert {r["role"]: r["permissions"] for r in body["roles"]} == {
        r["role"]: r["permissions"] for r in CORE["roles"]
    }


def test_audit_events_newest_first_and_chained(seeded: TestClient) -> None:
    body = seeded.get("/api/v1/audit/events").json()
    strip = [{k: v for k, v in e.items() if k != "id"} for e in body]
    assert strip == [{k: v for k, v in e.items() if k != "id"} for e in CORE["auditEvents"]]
    assert all(e["id"].startswith("AU-") for e in body)


def test_copilot_ask(seeded: TestClient) -> None:
    r = seeded.post("/api/v1/ai/copilot/ask", json={"prompt": "Summarize CS-1042"})
    assert r.status_code == 200
    assert "CS-1042" in r.json()["refs"]
    assert seeded.post("/api/v1/ai/copilot/ask", json={}).status_code == 422


def test_seed_is_idempotent(db: Session) -> None:
    first = seed_demo(db, now=NOW)
    second = seed_demo(db, now=NOW)
    assert first.id == second.id
    assert len(read_service.exceptions(db, second, now=NOW)) == len(CORE["exceptions"])


def test_unseeded_tenant_is_a_clear_404(client: TestClient) -> None:
    r = client.get("/api/v1/exceptions")
    assert r.status_code == 404
    assert r.json()["code"] == "tenant_not_found"
