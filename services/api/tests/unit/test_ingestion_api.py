import time
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.engines.connectors.synthetic import write_csv
from app.models import DataSource, Tenant
from app.seed import seed_demo
from app.services import audit, ingestion

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=UTC)
GOOD = """document_id,company_code,trading_partner,gl_account,amount,currency,document_date,reference,text
D1,US01,UK02,1910,1000.00,USD,2026-08-12,IC-1,loan
D2,UK02,US01,2910,-787.40,GBP,2026-08-12, ic 1 ,loan
D3,DE03,US01,1910,500,eur,2026-08-13,IC-2,fee
D4,US01,,1910,100,USD,2026-08-13,IC-3,missing partner
D5,US01,UK02,1910,100,XX,2026-08-13,IC-4,bad currency
D1,US01,UK02,1910,1000.00,USD,2026-08-12,IC-1,duplicate
D6,ZZ99,UK02,1910,100,USD,2026-08-13,IC-5,unknown entity
"""


@pytest.fixture
def api(
    db: Session, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    seed_demo(db, now=NOW)
    monkeypatch.setattr(settings, "ingest_inline", True)
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    yield client


def upload(api: TestClient, content: str, source: str = "SRC-05", name: str = "extract.csv") -> dict:
    r = api.post(
        f"/api/v1/data/sources/{source}/upload", files={"file": (name, content.encode(), "text/csv")}
    )
    assert r.status_code == 202, r.text
    return api.get(f"/api/v1/data/batches/{r.json()['id']}").json()


def test_upload_loads_good_rows_and_quarantines_bad_ones(api: TestClient, db: Session) -> None:
    batch = upload(api, GOOD)
    assert batch["status"] == "Completed"
    assert (batch["rowsTotal"], batch["rowsLoaded"], batch["rowsQuarantined"]) == (7, 3, 4)
    reasons = {e for q in batch["quarantined"] for e in q["errors"]}
    assert reasons == {
        "Missing counterparty code",
        "Currency not ISO-4217",
        "Duplicate line in batch",
        "Unknown legal entity",
    }
    checks = {i["check"]: i for i in batch["issues"]}
    assert checks["Reference contains whitespace/noise"]["autoFixed"] is True
    assert checks["Currency not ISO-4217"]["failing"] == 1

    txns = api.get(f"/api/v1/data/transactions?batch={batch['id']}").json()
    assert txns["total"] == 3
    gbp = next(t for t in txns["items"] if t["currency"] == "GBP")
    assert gbp["reference"] == "IC1" and gbp["amountUsd"] < 0 and gbp["warnings"]
    eur = next(t for t in txns["items"] if t["entity"] == "DE03")
    assert eur["currency"] == "EUR" and eur["amountUsd"] > 500  # EUR is worth more than USD in demo rates

    steps = api.get(f"/api/v1/data/lineage/{gbp['id']}").json()
    assert [s["stage"] for s in steps] == ["Extracted", "Validated", "Normalized", "Enriched", "Candidates"]
    assert gbp["id"] in api.get("/api/v1/data/lineage").json()

    source = next(s for s in api.get("/api/v1/data/sources").json() if s["id"] == "SRC-05")
    assert source["status"] == "Degraded"  # >5% quarantined
    tenant = db.scalar(select(Tenant))
    assert tenant is not None and audit.verify_chain(db, tenant.id)


def test_reupload_is_detected_as_duplicates(api: TestClient) -> None:
    upload(api, GOOD)
    second = upload(api, GOOD)
    assert second["rowsLoaded"] == 0
    assert all(
        "Duplicate line in batch" in q["errors"]
        for q in second["quarantined"]
        if q["raw"]["document_id"] in ("D1", "D2", "D3")
    )


def test_unmappable_file_fails_cleanly(api: TestClient) -> None:
    batch = upload(api, "foo,bar\n1,2\n")
    assert batch["status"] == "Failed"
    assert "Could not map required columns" in batch["error"]
    assert batch["rowsLoaded"] == 0
    assert (
        next(s for s in api.get("/api/v1/data/sources").json() if s["id"] == "SRC-05")["status"] == "Failed"
    )


def test_upload_rejects_non_csv_and_unknown_source(api: TestClient) -> None:
    r = api.post("/api/v1/data/sources/SRC-05/upload", files={"file": ("x.pdf", b"%PDF", "application/pdf")})
    assert r.status_code == 400 and r.json()["code"] == "unsupported_file_type"
    r = api.post("/api/v1/data/sources/NOPE/upload", files={"file": ("x.csv", b"a", "text/csv")})
    assert r.status_code == 404
    r = api.post("/api/v1/data/sources/SRC-07/upload", files={"file": ("x.csv", b"a", "text/csv")})
    assert r.status_code == 409  # paused


def test_sync_pulls_through_the_same_pipeline(api: TestClient) -> None:
    r = api.post("/api/v1/data/sources/SRC-01/sync?rows=500")
    assert r.status_code == 202
    batch = api.get(f"/api/v1/data/batches/{r.json()['id']}").json()
    assert batch["status"] == "Completed" and batch["rowsTotal"] == 500
    assert batch["rowsLoaded"] > 450 and batch["rowsQuarantined"] > 0
    assert api.get("/api/v1/data/batches?source=SRC-01").json()[0]["id"] == batch["id"]
    assert api.post("/api/v1/data/sources/SRC-05/sync").status_code == 409  # file-based source


def test_resolving_and_ignoring_quality_issues(api: TestClient) -> None:
    batch = upload(api, GOOD)
    open_ids = {i["id"] for i in api.get("/api/v1/data/quality").json()["issues"]}
    target = next(i["id"] for i in batch["issues"] if not i["autoFixed"])
    assert target in open_ids
    assert api.post(f"/api/v1/data/quality/{target}/resolve").status_code == 200
    assert api.post("/api/v1/data/quality/DQ-311/ignore").status_code == 200
    remaining = {i["id"] for i in api.get("/api/v1/data/quality").json()["issues"]}
    assert target not in remaining and "DQ-311" not in remaining
    assert api.post("/api/v1/data/quality/NOPE/resolve").status_code == 404
    assert api.post(f"/api/v1/data/quality/{target}/explode").status_code == 404


def test_fx_rates(api: TestClient) -> None:
    rates = api.get("/api/v1/data/fx-rates?on=2026-08-12").json()
    assert {r["currency"] for r in rates} == {"GBP", "EUR", "INR", "SGD", "BRL"}
    assert all(r["date"] == "2026-08-12" and r["source"] == "synthetic-demo" for r in rates)


def test_throughput(db: Session, tmp_path: Path) -> None:
    """20K synthetic rows must load at >= 1,000 rows/s (100K rows in under 100 s)."""
    tenant = seed_demo(db, now=NOW)
    source = db.scalar(select(DataSource).where(DataSource.code == "SRC-01"))
    assert source is not None
    settings_dir = settings.upload_dir
    settings.upload_dir = str(tmp_path)
    try:
        batch = ingestion.create_batch(db, tenant, source, "perf.csv")
        write_csv(Path(batch.storage_path or ""), 20_000)
        started = time.perf_counter()
        ingestion.run_batch(db, batch)
        elapsed = time.perf_counter() - started
    finally:
        settings.upload_dir = settings_dir
    assert batch.status == "Completed" and batch.rows_total == 20_000
    assert 20_000 / elapsed >= 1_000, f"{20_000 / elapsed:.0f} rows/s"
