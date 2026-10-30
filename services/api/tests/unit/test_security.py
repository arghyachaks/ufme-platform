"""Security: OIDC token validation, authorization matrix (role x endpoint x entity), tenant isolation (Postgres RLS),
tamper-evident audit chain, signed evidence packages, security headers."""

import io
import time
import uuid
import zipfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.db import tenancy
from app.models import AuditEvent, Tenant
from app.seed import seed_demo
from app.services import audit, evidence

ANALYST = {"X-Ufme-User": "priya.nair@example.com"}  # Analyst, US01 + UK02
ANALYST_DE = {"X-Ufme-User": "mei.chen@example.com"}  # Analyst, DE03
MANAGER = {"X-Ufme-User": "arjun.rao@example.com"}  # Manager, IN04 + SG05
CONTROLLER = {"X-Ufme-User": "daniel.ortiz@example.com"}  # Controller, US01 + UK02 + DE03
AUDITOR = {"X-Ufme-User": "sofia.rossi@example.com"}  # Auditor, All (read-only)
DIRECTOR = {"X-Ufme-User": "liam.walsh@example.com"}  # Finance Director, All

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def api(
    db: Session, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    seed_demo(db, now=datetime(2026, 10, 18, 12, 0, tzinfo=UTC))
    monkeypatch.setattr(settings, "ingest_inline", True)
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    assert client.post("/api/v1/data/sources/SRC-01/sync?rows=3000").status_code == 202
    assert client.post("/api/v1/recon/runs", headers=DIRECTOR).status_code == 202
    yield client


# ---------------------------------------------------------------- OIDC


def _token(key: Any = KEY, **claims: Any) -> str:
    now = int(time.time())
    body = {
        "iss": settings.oidc_issuer,
        "aud": ["ufme-api", "account"],
        "sub": str(uuid.uuid4()),
        "iat": now,
        "exp": now + 600,
        "email": "priya.nair@example.com",
        "ufme_tenant": "demo",
    }
    body.update(claims)
    return jwt.encode(
        {k: v for k, v in body.items() if v is not None}, key, algorithm="RS256", headers={"kid": "k1"}
    )


@pytest.fixture
def oidc(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Key:
        key = KEY.public_key()

    class _Jwks:
        def get_signing_key_from_jwt(self, token: str) -> _Key:
            return _Key()

    monkeypatch.setattr(settings, "auth_mode", "oidc")
    monkeypatch.setattr(security, "_jwks", lambda url: _Jwks())


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_oidc_valid_token_identifies_the_user(api: TestClient, oidc: None) -> None:
    me = api.get("/api/v1/me", headers=_bearer(_token()))
    assert me.status_code == 200 and me.json()["name"] == "Priya Nair" and me.json()["role"] == "Analyst"
    ctl = api.get("/api/v1/me", headers=_bearer(_token(email="Daniel.Ortiz@example.com")))
    assert ctl.json()["role"] == "Controller"  # email matched case-insensitively; role comes from ufme


@pytest.mark.parametrize(
    ("headers", "code"),
    [
        ({}, "not_authenticated"),
        (ANALYST, "not_authenticated"),  # the dev header means nothing once OIDC is on
        ({"Authorization": "Basic abc"}, "not_authenticated"),
        ({"Authorization": "Bearer not-a-jwt"}, "invalid_token"),
    ],
)
def test_oidc_rejects_missing_or_malformed_credentials(
    api: TestClient, oidc: None, headers: dict[str, str], code: str
) -> None:
    r = api.get("/api/v1/me", headers=headers)
    assert r.status_code == 401 and r.json()["code"] == code


@pytest.mark.parametrize(
    ("claims", "key", "status", "code"),
    [
        ({"exp": int(time.time()) - 3600}, KEY, 401, "token_expired"),
        ({"aud": "some-other-app"}, KEY, 401, "invalid_token"),
        ({"iss": "https://evil.example.com/realms/ufme"}, KEY, 401, "invalid_token"),
        ({}, OTHER_KEY, 401, "invalid_token"),  # signed by someone else
        ({"email": None, "preferred_username": "no-email"}, KEY, 401, "no_email_claim"),
        ({"email": "stranger@example.com"}, KEY, 403, "unknown_user"),  # authenticated but not a ufme user
        ({"ufme_tenant": "acme"}, KEY, 403, "unknown_tenant"),
    ],
)
def test_oidc_rejects_bad_tokens(
    api: TestClient, oidc: None, claims: dict[str, Any], key: Any, status: int, code: str
) -> None:
    r = api.get("/api/v1/me", headers=_bearer(_token(key, **claims)))
    assert r.status_code == status and r.json()["code"] == code, r.text


def test_tokens_must_be_signed_with_an_asymmetric_algorithm(api: TestClient, oidc: None) -> None:
    forged = jwt.encode(
        {
            "iss": settings.oidc_issuer,
            "aud": "ufme-api",
            "sub": "x",
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,
            "email": "liam.walsh@example.com",
        },
        "guessable-shared-secret-of-32-bytes!",
        algorithm="HS256",
    )
    assert api.get("/api/v1/me", headers=_bearer(forged)).status_code == 401


def test_dev_login_is_refused_in_production(api: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "environment", "prod")
    r = api.get("/api/v1/me", headers=ANALYST)
    assert r.status_code == 401 and r.json()["code"] == "dev_auth_disabled"


# ---------------------------------------------------------------- authorization matrix


def _proposals(api: TestClient, who: dict[str, str]) -> list[dict[str, Any]]:
    return api.get(
        "/api/v1/recon/proposals?limit=5000", headers=who
    ).json()  # every status, so all pairs show


def test_users_only_see_their_entities(api: TestClient) -> None:
    everything = _proposals(api, DIRECTOR)
    assert {p["entityPair"] for p in everything} > {p["entityPair"] for p in _proposals(api, ANALYST)}
    for who, mine in ((ANALYST, ("US01", "UK02")), (MANAGER, ("IN04", "SG05")), (ANALYST_DE, ("DE03",))):
        seen = _proposals(api, who)
        assert all(any(e in p["entityPair"] for e in mine) for p in seen), who
    assert len(_proposals(api, AUDITOR)) == len(everything)  # auditors see everything, change nothing


def test_out_of_scope_actions_are_refused(api: TestClient) -> None:
    foreign = next(
        p
        for p in _proposals(api, DIRECTOR)
        if "US01" not in p["entityPair"] and "UK02" not in p["entityPair"]
    )
    r = api.post(f"/api/v1/recon/proposals/{foreign['id']}/accept", headers=ANALYST)
    assert r.status_code == 403 and r.json()["code"] == "entity_out_of_scope"
    pair = foreign["entityPair"]
    r = api.get(f"/api/v1/recon/unmatched?pair={pair}", headers=ANALYST)
    assert r.status_code == 403 and r.json()["code"] == "entity_out_of_scope"


ACTIONS = [
    ("post", "/api/v1/recon/proposals/{proposal}/accept", None),
    ("post", "/api/v1/recon/manual-matches", {"txnIds": ["X1", "X2"], "rationale": "test"}),
    ("post", "/api/v1/cases", {"exceptionIds": ["EX-1"]}),
    ("post", "/api/v1/learning/train", None),
]


@pytest.mark.parametrize(("method", "path", "body"), ACTIONS)
def test_auditor_is_read_only(api: TestClient, method: str, path: str, body: Any) -> None:
    proposal = _proposals(api, DIRECTOR)[0]["id"]
    r = getattr(api, method)(path.format(proposal=proposal), headers=AUDITOR, json=body)
    assert r.status_code == 403 and r.json()["code"] == "read_only_role", (path, r.text)


@pytest.mark.parametrize(
    ("who", "status"),
    [(ANALYST, 403), (MANAGER, 403), (CONTROLLER, 200), (AUDITOR, 200), (DIRECTOR, 200)],
)
def test_evidence_export_matrix(api: TestClient, who: dict[str, str], status: int) -> None:
    assert api.get("/api/v1/audit/evidence", headers=who).status_code == status


@pytest.mark.parametrize(
    ("who", "status"),
    [(ANALYST, 403), (MANAGER, 403), (CONTROLLER, 404), (AUDITOR, 403), (DIRECTOR, 404)],
)
def test_model_promotion_matrix(api: TestClient, who: dict[str, str], status: int) -> None:
    # 404 = allowed to promote, but this version doesn't exist; 403 = not allowed to promote at all.
    assert api.post("/api/v1/learning/models/nope/promote", headers=who).status_code == status


# ---------------------------------------------------------------- audit chain + evidence


def test_audit_chain_detects_tampering(api: TestClient, db: Session) -> None:
    ok = api.get("/api/v1/audit/verify", headers=AUDITOR).json()
    assert ok["ok"] and ok["events"] > 0
    tenant = db.scalar(select(Tenant).where(Tenant.slug == "demo"))
    assert tenant is not None
    victim = db.scalar(
        select(AuditEvent).where(AuditEvent.tenant_id == tenant.id).order_by(AuditEvent.seq.desc())
    )
    assert victim is not None
    victim.actor = "someone.else@example.com"  # rewrite history
    db.flush()
    broken = api.get("/api/v1/audit/verify", headers=AUDITOR).json()
    assert not broken["ok"] and broken["brokenAt"] == victim.seq and "changed" in broken["reason"]


def test_evidence_package_is_signed_and_verifiable(api: TestClient) -> None:
    r = api.get("/api/v1/audit/evidence", headers=AUDITOR)
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    assert "attachment" in r.headers["content-disposition"]
    check = evidence.verify_package(r.content)
    assert check["signature_ok"] and check["files_ok"] and check["audit_chain_ok"]

    # Change one byte of the audit CSV: the manifest hash no longer matches.
    src = zipfile.ZipFile(io.BytesIO(r.content))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name in src.namelist():
            data = src.read(name)
            z.writestr(name, data + b"999999,forged,row\n" if name == "audit_events.csv" else data)
    tampered = evidence.verify_package(out.getvalue())
    assert tampered["signature_ok"] and not tampered["files_ok"] and not tampered["files"]["audit_events.csv"]
    actions = [e["action"] for e in api.get("/api/v1/audit/events", headers=AUDITOR).json()]
    assert "evidence.exported" in actions or any("evidence" in a for a in actions)


def test_security_headers(api: TestClient) -> None:
    h = api.get("/api/v1/me", headers=ANALYST).headers
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in h["content-security-policy"] and h["cache-control"] == "no-store"


# ---------------------------------------------------------------- tenant isolation (Postgres RLS)


def test_row_level_security_isolates_tenants(api: TestClient, db: Session) -> None:
    if db.get_bind().dialect.name != "postgresql":
        pytest.skip("row-level security is a Postgres feature (CI and Docker run on Postgres)")
    conn = db.connection()
    policed = {
        r[0]
        for r in conn.execute(text("SELECT tablename FROM pg_policies WHERE policyname = 'tenant_isolation'"))
    }
    assert set(tenancy.tenant_tables(conn)) <= policed, "every table with tenant_id needs the policy"

    tenancy.unpin(db)  # setup as the system (the fixture's requests pinned this test session)
    demo = db.scalar(select(Tenant).where(Tenant.slug == "demo"))
    other = Tenant(slug=f"other-{uuid.uuid4().hex[:6]}", name="Other Co", region="eu-west")
    db.add(other)
    db.flush()
    audit.record(
        db, tenant_id=other.id, actor="x@other.com", action="secret.thing", object_type="t", object_id="1"
    )
    db.flush()
    assert demo is not None
    tenancy.pin_tenant(db, demo.id)  # what every API request does
    visible = db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.tenant_id == other.id))
    assert visible == 0  # even an explicit query for the other tenant's rows returns nothing
    assert db.scalar(select(func.count()).select_from(AuditEvent)) > 0  # own rows still visible
    with pytest.raises(Exception, match="row-level security"), db.begin_nested():
        db.add(
            AuditEvent(
                tenant_id=other.id,
                occurred_at=datetime.now(UTC),
                actor="x",
                action="y",
                object_type="z",
                object_id="1",
                hash="0" * 64,
            )
        )
        db.flush()
