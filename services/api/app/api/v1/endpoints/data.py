import shutil
from datetime import date
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, File, Query, Response, UploadFile
from sqlalchemy import select

from app.api.deps import CurrentActor, CurrentTenant, DbSession
from app.api.pagination import Pagination
from app.core.config import settings
from app.core.errors import AppError, ConflictError, NotFoundError
from app.engines.connectors.synthetic import write_csv
from app.models import DataSource, DqIssue, IngestionBatch, Tenant
from app.schemas.read import (
    BatchDetailOut,
    BatchOut,
    ControlOut,
    FxRateOut,
    QualityIssueOut,
    SourceOut,
    TxnPage,
)
from app.services import audit, evidence, ingestion, ingestion_read, read

router = APIRouter()


def _source(db: DbSession, tenant: Tenant, code: str) -> DataSource:
    source = db.scalar(select(DataSource).where(DataSource.tenant_id == tenant.id, DataSource.code == code))
    if source is None:
        raise NotFoundError(f"Data source '{code}' not found.", code="source_not_found")
    return source


def _dispatch(db: DbSession, batch: IngestionBatch, background: BackgroundTasks) -> None:
    if settings.ingest_inline:
        ingestion.run_batch(db, batch)
    else:
        from app.workers.tasks import ingest_batch

        background.add_task(ingest_batch.delay, str(batch.id))  # runs after the request transaction commits


@router.get("/data/sources", response_model=list[SourceOut])
def data_sources(db: DbSession, tenant: CurrentTenant) -> list[SourceOut]:
    return read.sources(db, tenant)


@router.post("/data/sources/{code}/upload", response_model=BatchOut, status_code=202)
def upload(
    code: str,
    db: DbSession,
    tenant: CurrentTenant,
    background: BackgroundTasks,
    file: Annotated[UploadFile, File()],
) -> BatchOut:
    """Upload a CSV extract for a source. Processing is asynchronous; poll GET /data/batches/{id}."""
    source = _source(db, tenant, code)
    if source.status == "Paused":
        raise ConflictError(f"{source.name} is paused.", code="source_paused")
    name = file.filename or "upload.csv"
    if not name.lower().endswith((".csv", ".txt", ".tsv")):
        raise AppError("Only CSV/TSV files are supported.", code="unsupported_file_type")
    batch = ingestion.create_batch(db, tenant, source, name)
    limit = settings.max_upload_mb * 1024 * 1024
    with open(batch.storage_path or "", "wb") as out:
        shutil.copyfileobj(file.file, out, length=1024 * 1024)
        if out.tell() > limit:
            raise AppError(f"File exceeds {settings.max_upload_mb} MB.", code="file_too_large")
    audit.record(
        db,
        tenant_id=tenant.id,
        actor="api",
        action="ingestion.uploaded",
        object_type="ingestion_batch",
        object_id=batch.code,
        after={"file": name, "source": source.code},
    )
    _dispatch(db, batch, background)
    return ingestion_read.batch_out(batch, source)


@router.post("/data/sources/{code}/sync", response_model=BatchOut, status_code=202)
def sync(
    code: str,
    db: DbSession,
    tenant: CurrentTenant,
    background: BackgroundTasks,
    rows: Annotated[int, Query(ge=1, le=200_000)] = 2_000,
) -> BatchOut:
    """Pull from an ERP/bank/API source. Native connectors arrive with the pilot; until then this pulls a
    synthetic intercompany extract through the same pipeline."""
    source = _source(db, tenant, code)
    if source.kind == "File":
        raise ConflictError(f"{source.name} is file-based; upload a file instead.", code="source_is_file")
    if source.status == "Paused":
        raise ConflictError(f"{source.name} is paused.", code="source_paused")
    batch = ingestion.create_batch(db, tenant, source, f"{source.system} pull ({rows} rows)")
    write_csv(Path(batch.storage_path or ""), rows, seed=int(batch.code[4:]))
    _dispatch(db, batch, background)
    return ingestion_read.batch_out(batch, source)


@router.get("/data/batches", response_model=list[BatchOut])
def batches(db: DbSession, tenant: CurrentTenant, source: str | None = None) -> list[BatchOut]:
    return ingestion_read.batches(db, tenant, source)


@router.get("/data/batches/{code}", response_model=BatchDetailOut)
def batch_detail(code: str, db: DbSession, tenant: CurrentTenant) -> BatchDetailOut:
    return ingestion_read.batch_detail(db, tenant, code)


@router.get("/data/transactions", response_model=TxnPage)
def transactions(
    db: DbSession,
    tenant: CurrentTenant,
    page: Pagination,
    entity: str | None = None,
    counterparty: str | None = None,
    batch: str | None = None,
) -> TxnPage:
    return ingestion_read.transactions(db, tenant, page, entity, counterparty, batch)


@router.get("/data/quality")
def data_quality(db: DbSession, tenant: CurrentTenant) -> dict[str, Any]:
    issues: list[QualityIssueOut] = read.quality_issues(db, tenant)
    return {
        "issues": [i.model_dump(by_alias=True) for i in issues],
        "dimensions": read.snapshot(db, tenant, "data.quality.dimensions"),
    }


@router.post("/data/quality/{code}/{action}", response_model=QualityIssueOut)
def resolve_issue(code: str, action: str, db: DbSession, tenant: CurrentTenant) -> QualityIssueOut:
    if action not in ("resolve", "ignore"):
        raise NotFoundError(f"Unknown action '{action}'.", code="unknown_action")
    issue = db.scalar(select(DqIssue).where(DqIssue.tenant_id == tenant.id, DqIssue.code == code))
    if issue is None:
        raise NotFoundError(f"Quality issue '{code}' not found.", code="issue_not_found")
    before = issue.status
    issue.status = "Resolved" if action == "resolve" else "Ignored"
    audit.record(
        db,
        tenant_id=tenant.id,
        actor="api",
        action=f"dq_issue.{action}d",
        object_type="dq_issue",
        object_id=code,
        before={"status": before},
        after={"status": issue.status},
    )
    return QualityIssueOut(
        id=issue.code,
        source=issue.source_name,
        check=issue.check_name,
        field=issue.field,
        failing=issue.failing,
        total=issue.total,
        severity=issue.severity,
        auto_fixed=issue.auto_fixed,
    )


@router.get("/data/fx-rates", response_model=list[FxRateOut])
def fx_rates(db: DbSession, tenant: CurrentTenant, on: date | None = None) -> list[FxRateOut]:
    return ingestion_read.fx_rates(db, tenant, on)


@router.get("/data/lineage")
def lineage_ids(db: DbSession, tenant: CurrentTenant) -> list[str]:
    return list(read.snapshot(db, tenant, "data.lineage").keys()) + ingestion_read.recent_txn_codes(
        db, tenant
    )


@router.get("/data/lineage/{txn_id}")
def lineage(txn_id: str, db: DbSession, tenant: CurrentTenant) -> Any:
    steps = read.snapshot(db, tenant, "data.lineage").get(txn_id)
    return steps if steps is not None else ingestion_read.lineage(db, tenant, txn_id)


@router.get("/data/features")
def features(db: DbSession, tenant: CurrentTenant) -> Any:
    return read.snapshot(db, tenant, "data.features")


@router.get("/audit/events")
def audit_events(db: DbSession, tenant: CurrentTenant) -> list[dict[str, Any]]:
    return [e.model_dump(by_alias=True) for e in read.audit_events(db, tenant)]


@router.get("/audit/verify")
def audit_verify(db: DbSession, tenant: CurrentTenant, actor: CurrentActor) -> dict[str, Any]:
    """Recompute the tenant's audit hash chain (tamper evidence)."""
    return audit.verify_report(db, tenant.id)


@router.get("/audit/evidence")
def audit_evidence(
    db: DbSession,
    tenant: CurrentTenant,
    actor: CurrentActor,
    start: date | None = Query(None, alias="from"),
    end: date | None = Query(None, alias="to"),
) -> Response:
    """Evidence package: audit trail + control results as CSV, a hashed manifest, and its HMAC signature."""
    data, manifest = evidence.build(db, tenant, actor, start, end)
    name = f"ufme-evidence-{tenant.slug}-{manifest['generated_at'][:10]}.zip"
    return Response(
        data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get("/audit/controls", response_model=list[ControlOut])
def audit_controls(db: DbSession, tenant: CurrentTenant) -> list[ControlOut]:
    return read.controls(db, tenant)
