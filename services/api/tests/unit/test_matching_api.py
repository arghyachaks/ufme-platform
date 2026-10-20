from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import MatchLabel, MatchRun, Tenant
from app.seed import seed_demo
from app.services import audit

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)


@pytest.fixture
def api(
    db: Session, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    seed_demo(db, now=NOW)
    monkeypatch.setattr(settings, "ingest_inline", True)
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    assert client.post("/api/v1/data/sources/SRC-01/sync?rows=3000").status_code == 202  # synthetic IC ledger
    yield client


def run(api: TestClient, **body: str) -> dict:
    r = api.post("/api/v1/recon/runs", json=body or None)
    assert r.status_code == 202, r.text
    return api.get(f"/api/v1/recon/runs/{r.json()['id']}").json()


def test_run_produces_explained_proposals(api: TestClient, db: Session) -> None:
    result = run(api)
    assert result["status"] == "Completed", result["error"]
    m = result["metrics"]
    assert m["lines"] > 2800 and m["auto"] > 0 and m["auto"] + m["suggested"] > 0
    assert [r["id"] for r in result["rules"]] == ["R-001", "R-002", "R-003", "R-004"]

    proposals = api.get(f"/api/v1/recon/proposals?run={result['id']}&limit=5000").json()
    assert len(proposals) == m["auto"] + m["suggested"]
    p = proposals[0]
    assert p["type"] == "1:1" and len(p["lines"]) == 2 and {x["side"] for x in p["lines"]} == {"A", "B"}
    assert p["explanation"]["contributions"] and p["explanation"]["blocking"]
    assert all(x["decision"] != "auto" or x["status"] == "matched" for x in proposals)
    tenant = db.scalar(select(Tenant))
    assert tenant is not None and audit.verify_chain(db, tenant.id)


def test_accept_and_reject_become_labels(api: TestClient, db: Session) -> None:
    result = run(api)
    pending = api.get(f"/api/v1/recon/proposals?run={result['id']}&status=proposed").json()
    assert len(pending) >= 2, (
        "the 3,000-row synthetic pull always yields suggestions (FX gaps, timing, splits)"
    )
    a, b = pending[0]["id"], pending[1]["id"]
    assert (
        api.post(f"/api/v1/recon/proposals/{a}/accept", json={"reason": "confirmed with UK02"}).json()[
            "status"
        ]
        == "accepted"
    )
    assert api.post(f"/api/v1/recon/proposals/{b}/reject").json()["status"] == "rejected"
    again = api.post(f"/api/v1/recon/proposals/{a}/reject")
    assert again.status_code == 409 and again.json()["code"] == "proposal_not_pending"
    assert api.post("/api/v1/recon/proposals/MT-999999/accept").status_code == 404
    assert api.post(f"/api/v1/recon/proposals/{a}/approve").status_code == 422
    assert db.scalar(select(func.count()).select_from(MatchLabel)) == 2


def test_second_run_supersedes_pending_and_skips_matched(api: TestClient) -> None:
    first = run(api)
    matched = {
        x["id"]
        for p in api.get(f"/api/v1/recon/proposals?run={first['id']}&status=matched&limit=5000").json()
        for x in p["lines"]
    }
    second = run(api)
    assert second["metrics"]["lines"] == first["metrics"]["lines"] - len(matched)
    assert not api.get(f"/api/v1/recon/proposals?run={first['id']}&status=proposed").json()
    runs = api.get("/api/v1/recon/runs").json()
    assert [r["id"] for r in runs[:2]] == [second["id"], first["id"]]


def test_disabled_rules_are_not_used(api: TestClient) -> None:
    r = api.patch("/api/v1/rules/R-004", json={"enabled": False})
    assert r.status_code == 200 and r.json()["enabled"] is False
    assert "R-004" not in [x["id"] for x in run(api)["rules"]]
    assert api.patch("/api/v1/rules/NOPE", json={"enabled": True}).status_code == 404


def test_workspace_feeds_real_runs_to_the_ui(api: TestClient) -> None:
    before = api.get("/api/v1/workspace/recon").json()
    assert before["runs"][0]["id"].startswith("IC-")  # demo data until a real run exists
    result = run(api)
    ws = api.get("/api/v1/workspace/recon").json()
    assert ws["runs"][0]["id"] == result["id"]
    assert ws["runs"][0]["transactionsProcessed"] == f"{result['metrics']['lines']:,}"
    if result["metrics"]["suggested"]:
        assert ws["sideA"][0]["id"].startswith("MT-")
        assert ws["suggestedMatch"]["queueSize"] == result["metrics"]["suggested"]
        assert sum(x["weight"] for x in ws["suggestedMatch"]["confidenceBreakdown"]) in range(98, 103)


def test_only_one_run_at_a_time(api: TestClient, db: Session) -> None:
    tenant = db.scalar(select(Tenant))
    assert tenant is not None
    db.add(
        MatchRun(
            tenant_id=tenant.id,
            code="RUN-99999",
            status="Running",
            scope={},
            engine_version="x",
            rules=[],
            metrics={},
        )
    )
    db.flush()
    r = api.post("/api/v1/recon/runs")
    assert r.status_code == 409 and r.json()["code"] == "run_in_progress"
