"""Stage 4 end to end: ingest → run → review → approve (matrix, SoD, dual control) → controls → sign-off."""

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ApprovalRequest, AuditEvent, MatchGroup
from app.seed import seed_demo
from app.services import audit, workflow

ANALYST = {"X-Ufme-User": "priya.nair@example.com"}
MANAGER = {"X-Ufme-User": "arjun.rao@example.com"}
CONTROLLER = {"X-Ufme-User": "daniel.ortiz@example.com"}
DIRECTOR = {"X-Ufme-User": "liam.walsh@example.com"}
AUDITOR = {"X-Ufme-User": "sofia.rossi@example.com"}


@pytest.fixture
def api(
    db: Session, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    seed_demo(db, now=datetime(2026, 10, 18, 12, 0, tzinfo=UTC))
    monkeypatch.setattr(settings, "ingest_inline", True)
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    assert client.post("/api/v1/data/sources/SRC-01/sync?rows=3000").status_code == 202
    run = client.post("/api/v1/recon/runs", headers=ANALYST)
    assert run.status_code == 202
    assert client.get(f"/api/v1/recon/runs/{run.json()['id']}").json()["status"] == "Completed"
    yield client


def _accept_one(api: TestClient, min_usd: float = 0, max_usd: float = 1e18) -> dict:
    pending = api.get("/api/v1/recon/proposals?status=proposed&limit=5000").json()
    p = next(x for x in pending if min_usd <= x["exposureUsd"] <= max_usd)
    r = api.post(
        f"/api/v1/recon/proposals/{p['id']}/accept", headers=ANALYST, json={"reason": "agreed with UK02"}
    )
    assert r.status_code == 200 and r.json()["status"] == "pending_approval", r.text
    return p


def test_acting_user(api: TestClient) -> None:
    assert api.get("/api/v1/me").json()["role"] == "Analyst"  # default demo user
    assert api.get("/api/v1/me", headers=CONTROLLER).json()["name"] == "Daniel Ortiz"
    assert api.get("/api/v1/me", headers={"X-Ufme-User": "nobody@x.com"}).status_code == 403
    assert {u["role"] for u in api.get("/api/v1/users/acting").json()} >= {
        "Analyst",
        "Controller",
        "Finance Director",
    }


def test_review_to_approval_with_segregation_of_duties(api: TestClient, db: Session) -> None:
    p = _accept_one(api, max_usd=999_999)  # single-approver band
    queue = api.get("/api/v1/approvals").json()
    item = next(a for a in queue if a["matchId"] == p["id"])
    assert item["stage"] == workflow.required_role(Decimal(str(p["exposureUsd"])))
    assert item["submittedBy"] == "Priya Nair" and item["status"] == "Pending"

    self_approve = api.post(f"/api/v1/approvals/{item['id']}/approve", headers=ANALYST)
    assert self_approve.status_code == 403 and self_approve.json()["code"] == "sod_self_approval"
    assert (
        db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == "approval.denied"))
        == 1
    )

    ok = api.post(f"/api/v1/approvals/{item['id']}/approve", headers=DIRECTOR, json={"comment": "fine"})
    assert ok.status_code == 200 and ok.json()["status"] == "Approved"
    assert api.get("/api/v1/recon/proposals?status=accepted").json()[0]["id"] == p["id"]
    again = api.post(f"/api/v1/approvals/{item['id']}/reject", headers=CONTROLLER)
    assert again.status_code == 409 and again.json()["code"] == "approval_closed"
    tenant_id = db.scalar(select(MatchGroup.tenant_id).limit(1))
    assert audit.verify_chain(db, tenant_id)


def test_matrix_authority_and_dual_control(api: TestClient, db: Session) -> None:
    p = _accept_one(api)
    req = db.scalar(select(ApprovalRequest).where(ApprovalRequest.match_code == p["id"]))
    assert req is not None
    # Force the top band to exercise the Finance Director + dual-control path deterministically.
    req.exposure_usd, req.required_role, req.approvals_needed = Decimal("2500000"), "Finance Director", 2
    db.flush()
    low = api.post(f"/api/v1/approvals/{req.code}/approve", headers=CONTROLLER)
    assert low.status_code == 403 and low.json()["code"] == "insufficient_authority"
    first = api.post(f"/api/v1/approvals/{req.code}/approve", headers=DIRECTOR).json()
    assert first["status"] == "Pending" and len(first["approvals"]) == 1
    dup = api.post(f"/api/v1/approvals/{req.code}/approve", headers=DIRECTOR)
    assert dup.status_code == 403 and dup.json()["code"] == "duplicate_approver"
    weak = api.post(f"/api/v1/approvals/{req.code}/approve", headers=MANAGER)
    assert weak.status_code == 403 and weak.json()["code"] == "insufficient_authority"
    second = api.post(f"/api/v1/approvals/{req.code}/approve", headers=CONTROLLER).json()
    assert second["status"] == "Approved"
    assert [a["role"] for a in second["approvals"]] == ["Finance Director", "Controller"]
    controls = {
        c["id"]: c["result"] for c in api.post("/api/v1/audit/controls/evaluate", headers=AUDITOR).json()
    }
    assert controls["IC-07"] == "Pass"  # > 1M approved by two different people


def test_reject_and_request_info(api: TestClient) -> None:
    p = _accept_one(api, max_usd=999_999)
    code = next(a["id"] for a in api.get("/api/v1/approvals").json() if a["matchId"] == p["id"])
    info = api.post(f"/api/v1/approvals/{code}/request-info", headers=DIRECTOR, json={"comment": "attach GL"})
    assert info.json()["status"] == "Info requested" and "attach GL" in info.json()["trail"][-1]
    assert api.post(f"/api/v1/approvals/{code}/reject", headers=DIRECTOR).json()["status"] == "Rejected"
    assert any(x["id"] == p["id"] for x in api.get("/api/v1/recon/proposals?status=rejected").json())


def test_manual_match_policy(api: TestClient) -> None:
    lines = api.get("/api/v1/data/transactions?limit=200").json()
    rows = lines["items"] if isinstance(lines, dict) else lines
    bad = api.post("/api/v1/recon/manual-matches", headers=ANALYST, json={"txnIds": [rows[0]["id"]]})
    assert bad.status_code == 422
    unknown = api.post("/api/v1/recon/manual-matches", headers=ANALYST, json={"txnIds": ["NOPE-1", "NOPE-2"]})
    assert unknown.status_code == 404
    # A suggestion's two lines form a valid 1:1 manual match if the variance is within policy, else a 422.
    p = api.get("/api/v1/recon/proposals?status=proposed&limit=5000").json()
    within = next((x for x in p if x["residualUsd"] <= min(500, 0.005 * x["exposureUsd"])), None)
    outside = next((x for x in p if x["residualUsd"] > min(500, 0.005 * x["exposureUsd"])), None)
    if outside:
        r = api.post(
            "/api/v1/recon/manual-matches",
            headers=ANALYST,
            json={"txnIds": [x["id"] for x in outside["lines"]]},
        )
        assert r.status_code == 422 and r.json()["code"] == "tolerance_exceeded"
    if within:
        api.post(f"/api/v1/recon/proposals/{within['id']}/reject", headers=ANALYST)
        r = api.post(
            "/api/v1/recon/manual-matches",
            headers=ANALYST,
            json={"txnIds": [x["id"] for x in within["lines"]], "rationale": "same invoice"},
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["type"] == "1:1" and body["approvalId"].startswith("AP-")
        dupe = api.post(
            "/api/v1/recon/manual-matches",
            headers=ANALYST,
            json={"txnIds": [x["id"] for x in within["lines"]]},
        )
        assert dupe.status_code == 409 and dupe.json()["code"] == "already_matched"


def test_signoff_blocked_then_signed(api: TestClient) -> None:
    us01 = next(s for s in api.get("/api/v1/signoff").json() if s["entity"] == "US01")
    assert not us01["ready"] and us01["blockers"]
    blocked = api.post("/api/v1/signoff/US01/sign", headers=CONTROLLER)
    assert blocked.status_code == 409 and blocked.json()["code"] == "signoff_blocked"

    # Controls are computed from data: no approvals violate the matrix, so IC-07 now passes.
    controls = {
        c["id"]: c["result"] for c in api.post("/api/v1/audit/controls/evaluate", headers=AUDITOR).json()
    }
    assert controls["IC-07"] == "Pass" and controls["SOD-01"] == "Pass"
    for ex in api.get("/api/v1/exceptions").json():
        if ex["entity"] == "US01" and ex["severity"] == "Critical" and ex["status"] != "Resolved":
            r = api.post(
                f"/api/v1/exceptions/{ex['id']}/status", headers=CONTROLLER, json={"status": "Resolved"}
            )
            assert r.status_code == 200
    for a in api.get("/api/v1/approvals").json():
        if "US01" in a["entity"]:
            api.post(f"/api/v1/approvals/{a['id']}/reject", headers=DIRECTOR)
    remaining = api.get("/api/v1/signoff").json()
    us01 = next(s for s in remaining if s["entity"] == "US01")
    assert us01["ready"], us01["blockers"]

    analyst = api.post("/api/v1/signoff/US01/sign", headers=ANALYST)
    assert analyst.status_code == 403
    signed = api.post("/api/v1/signoff/US01/sign", headers=CONTROLLER).json()
    assert signed["status"] == "Controller signed" and signed["nextSigner"] == "Finance Director"
    final = api.post("/api/v1/signoff/US01/sign", headers=DIRECTOR).json()
    assert final["status"] == "Signed off"
    assert api.post("/api/v1/signoff/US01/sign", headers=DIRECTOR).json()["code"] == "already_signed"


def test_cases_lifecycle(api: TestClient) -> None:
    ex = api.get("/api/v1/exceptions").json()
    open_ex = [e["id"] for e in ex if e["status"] == "New"][:2]
    case = api.post("/api/v1/cases", headers=ANALYST, json={"exceptionIds": open_ex})
    assert case.status_code == 201
    code = case.json()["id"]
    assert case.json()["assignee"] == "Priya Nair" and case.json()["status"] == "Open"
    upd = api.patch(
        f"/api/v1/cases/{code}", headers=CONTROLLER, json={"status": "Escalated", "assignee": "Daniel Ortiz"}
    )
    assert upd.json()["priority"] == "Critical" and upd.json()["assignee"] == "Daniel Ortiz"
    c = api.post(
        f"/api/v1/cases/{code}/comments", headers=CONTROLLER, json={"text": "Treasury to reverse JE"}
    )
    assert c.json()["comments"][-1]["author"] == "Daniel Ortiz"
    assert (
        api.post(f"/api/v1/cases/{code}/comments", headers=CONTROLLER, json={"text": "  "}).status_code == 422
    )
    closed = api.patch(f"/api/v1/cases/{code}", headers=CONTROLLER, json={"status": "Closed"}).json()
    assert closed["status"] == "Closed"
    statuses = {e["id"]: e["status"] for e in api.get("/api/v1/exceptions").json()}
    assert all(statuses[e] == "Resolved" for e in open_ex)
    assert api.post("/api/v1/cases", headers=ANALYST, json={"exceptionIds": []}).status_code == 422
    assert api.patch("/api/v1/cases/CS-0", headers=ANALYST, json={"status": "Open"}).status_code == 404
