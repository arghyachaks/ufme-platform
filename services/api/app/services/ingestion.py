"""Ingestion pipeline: connector → DQ checks → normalization → FX enrichment → ledger_txn / quarantine.

Blocking DQ failures quarantine the row (never silently dropped); warnings are stored on the loaded row and
aggregated into DQ issues per batch. Rows are bulk-inserted in chunks so 100K-row files load in well under 2 min.
"""

import json
import logging
import time
import uuid
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.engines.augmented_data.fx import FxTable
from app.engines.connectors.base import Connector, CsvFileConnector
from app.engines.data_quality import checks as dq
from app.engines.data_quality.normalize import map_columns
from app.models import (
    DataSource,
    DqIssue,
    FxRate,
    IngestionBatch,
    LedgerTxn,
    LegalEntity,
    QuarantinedRow,
    Tenant,
)
from app.services import audit

logger = logging.getLogger("ufme.ingestion")
CHUNK = 5_000
AUTO_FIXED = {"currency_case", "reference_noise"}
DEGRADED_QUARANTINE_RATIO = 0.05


def upload_dir() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def next_batch_code(db: Session, tenant: Tenant) -> str:
    count = db.scalar(
        select(func.count()).select_from(IngestionBatch).where(IngestionBatch.tenant_id == tenant.id)
    )
    return f"BAT-{(count or 0) + 1:05d}"


def create_batch(db: Session, tenant: Tenant, source: DataSource, file_name: str) -> IngestionBatch:
    batch = IngestionBatch(
        tenant_id=tenant.id,
        code=next_batch_code(db, tenant),
        source_id=source.id,
        file_name=file_name,
        status="Queued",
        rows_total=0,
        rows_loaded=0,
        rows_quarantined=0,
    )
    db.add(batch)
    db.flush()
    batch.storage_path = str(upload_dir() / f"{tenant.slug}-{batch.code}.csv")
    return batch


def bulk_insert(db: Session, model: type[Any], rows: list[dict[str, Any]]) -> None:
    """COPY on Postgres (≈10x faster than INSERT for large loads); executemany elsewhere."""
    if not rows:
        return
    if db.get_bind().dialect.name != "postgresql":
        db.execute(insert(model), rows)
        return
    table = model.__table__
    now = datetime.now(UTC)
    columns = [c.name for c in table.columns]
    json_cols = {c.name for c in table.columns if c.type.__class__.__name__ == "JSON"}
    raw_conn: Any = db.connection().connection.driver_connection
    with raw_conn.cursor() as cur, cur.copy(f"COPY {table.name} ({', '.join(columns)}) FROM STDIN") as copy:
        for r in rows:
            values = []
            for name in columns:
                if name == "id":
                    values.append(r.get("id") or uuid.uuid4())
                elif name in ("created_at", "updated_at"):
                    values.append(r.get(name) or now)
                elif name in json_cols:
                    values.append(json.dumps(r.get(name, [] if name == "warnings" else None)))
                else:
                    values.append(r.get(name))
            copy.write_row(values)


def _fx_table(db: Session, tenant_id: uuid.UUID) -> FxTable:
    rows = db.execute(
        select(FxRate.rate_date, FxRate.currency, FxRate.rate_to_usd).where(FxRate.tenant_id == tenant_id)
    )
    return FxTable([(d, c, r) for d, c, r in rows])


def _already_loaded(db: Session, tenant_id: uuid.UUID, source_id: uuid.UUID, ids: list[str]) -> set[str]:
    found: set[str] = set()
    for i in range(0, len(ids), 1000):
        chunk = ids[i : i + 1000]
        found.update(
            db.scalars(
                select(LedgerTxn.external_id).where(
                    LedgerTxn.tenant_id == tenant_id,
                    LedgerTxn.source_id == source_id,
                    LedgerTxn.external_id.in_(chunk),
                )
            )
        )
    return found


def run_batch(
    db: Session, batch: IngestionBatch, connector: Connector | None = None, today: date | None = None
) -> IngestionBatch:
    """Process one batch inside the caller's transaction. Marks the batch Failed (and re-raises nothing) on error."""
    started = time.perf_counter()
    now = datetime.now(UTC)
    today = today or now.date()
    source = db.get(DataSource, batch.source_id)
    assert source is not None
    batch.status, batch.started_at = "Processing", now
    db.flush()
    try:
        with db.begin_nested():  # a failed batch leaves no partial rows behind
            connector = connector or CsvFileConnector(Path(batch.storage_path or ""))
            headers, rows = connector.read()
            mapping = map_columns(headers)
            missing_cols = [
                f for f in ("entity", "counterparty", "amount", "currency", "value_date") if f not in mapping
            ]
            if missing_cols:
                raise ValueError(
                    f"Could not map required columns: {', '.join(missing_cols)}. Found: {', '.join(headers)}"
                )
            entities = set(
                db.scalars(select(LegalEntity.code).where(LegalEntity.tenant_id == batch.tenant_id))
            )
            fx = _fx_table(db, batch.tenant_id)
            seen: set[tuple[object, ...]] = set()
            counts: Counter[str] = Counter()
            loaded: list[dict[str, Any]] = []
            quarantined: list[dict[str, Any]] = []
            total = n_loaded = n_quarantined = 0

            def flush() -> None:
                nonlocal loaded, quarantined, n_loaded, n_quarantined
                if loaded:
                    dupes = _already_loaded(
                        db, batch.tenant_id, source.id, [r["external_id"] for r in loaded if r["external_id"]]
                    )
                    if dupes:
                        keep = []
                        for r in loaded:
                            if r["external_id"] in dupes:
                                counts["duplicate_line"] += 1
                                quarantined.append(
                                    {
                                        "tenant_id": batch.tenant_id,
                                        "batch_id": batch.id,
                                        "line_no": r["line_no"],
                                        "raw": r["raw"],
                                        "errors": ["duplicate_line"],
                                    }
                                )
                            else:
                                keep.append(r)
                        loaded = keep
                    if loaded:
                        bulk_insert(db, LedgerTxn, loaded)
                        n_loaded += len(loaded)
                if quarantined:
                    bulk_insert(db, QuarantinedRow, quarantined)
                    n_quarantined += len(quarantined)
                loaded, quarantined = [], []

            for line_no, raw in enumerate(rows, start=2):  # line 1 is the header
                total += 1
                row = dq.check_row(line_no, raw, mapping, known_entities=entities, today=today, seen=seen)
                if row.ok:
                    assert row.amount is not None and row.value_date is not None
                    amount_usd, rate = fx.to_usd(row.amount, row.currency, row.value_date)
                    if rate is None:
                        row.warnings.append("missing_fx_rate")
                    counts.update(row.warnings)
                    loaded.append(
                        {
                            "tenant_id": batch.tenant_id,
                            "code": f"{batch.code}-{line_no:06d}",
                            "batch_id": batch.id,
                            "source_id": source.id,
                            "external_id": row.external_id,
                            "line_no": line_no,
                            "entity_code": row.entity,
                            "counterparty_code": row.counterparty,
                            "account": row.account,
                            "amount": row.amount,
                            "currency": row.currency,
                            "amount_usd": amount_usd,
                            "fx_rate": rate,
                            "value_date": row.value_date,
                            "posting_date": row.posting_date,
                            "reference_raw": row.reference_raw,
                            "reference_norm": row.reference_norm,
                            "description": row.description,
                            "warnings": row.warnings,
                            "raw": raw,
                        }
                    )
                else:
                    counts.update(row.errors)
                    quarantined.append(
                        {
                            "tenant_id": batch.tenant_id,
                            "batch_id": batch.id,
                            "line_no": line_no,
                            "raw": raw,
                            "errors": row.errors,
                        }
                    )
                if len(loaded) + len(quarantined) >= CHUNK:
                    flush()
            flush()

            batch.rows_total, batch.rows_loaded, batch.rows_quarantined = total, n_loaded, n_quarantined
            batch.status = "Completed"
            _record_issues(db, batch, source, counts, total)
            ratio = n_quarantined / total if total else 0
            source.status = "Degraded" if ratio > DEGRADED_QUARANTINE_RATIO else "Healthy"
            source.records_24h = (source.records_24h or 0) + n_loaded
    except Exception as exc:  # the batch records the failure; the caller's transaction still commits it
        logger.exception("Ingestion failed for %s", batch.code)
        batch.status, batch.error = "Failed", str(exc)[:2000]
        source.status = "Failed"
    batch.finished_at = datetime.now(UTC)
    source.last_sync_at = batch.finished_at
    source.latency_min = 0
    audit.record(
        db,
        tenant_id=batch.tenant_id,
        actor="system",
        action=f"ingestion.{batch.status.lower()}",
        object_type="ingestion_batch",
        object_id=batch.code,
        control="DATA-01",
        after={"loaded": batch.rows_loaded, "quarantined": batch.rows_quarantined, "error": batch.error},
    )
    db.flush()
    logger.info(
        "%s %s: %d rows, %d loaded, %d quarantined in %.1fs",
        batch.code,
        batch.status,
        batch.rows_total,
        batch.rows_loaded,
        batch.rows_quarantined,
        time.perf_counter() - started,
    )
    return batch


def _record_issues(
    db: Session, batch: IngestionBatch, source: DataSource, counts: Counter[str], total: int
) -> None:
    for i, (check, failing) in enumerate(sorted(counts.items(), key=lambda kv: -kv[1]), start=1):
        label, field, severity, _blocking = dq.CHECKS[check]
        db.add(
            DqIssue(
                tenant_id=batch.tenant_id,
                code=f"DQ-{batch.code[4:]}-{i:02d}",
                source_name=source.name,
                check_name=label,
                field=field,
                failing=failing,
                total=total,
                severity=severity,
                auto_fixed=check in AUTO_FIXED,
                status="Open",
                batch_id=batch.id,
            )
        )
