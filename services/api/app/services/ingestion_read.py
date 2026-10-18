"""Read models for ingestion: batches, transactions, lineage of real transactions, FX rates."""

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.pagination import PageParams, encode_cursor
from app.core.errors import NotFoundError
from app.engines.data_quality.checks import CHECKS
from app.models import DataSource, DqIssue, FxRate, IngestionBatch, LedgerTxn, QuarantinedRow, Tenant
from app.schemas import read as s
from app.services import display as fmt


def batch_out(batch: IngestionBatch, source: DataSource) -> s.BatchOut:
    duration = (
        int((batch.finished_at - batch.started_at).total_seconds() * 1000)
        if batch.started_at and batch.finished_at
        else None
    )
    return s.BatchOut(
        id=batch.code,
        source_id=source.code,
        source=source.name,
        file_name=batch.file_name,
        status=batch.status,
        rows_total=batch.rows_total,
        rows_loaded=batch.rows_loaded,
        rows_quarantined=batch.rows_quarantined,
        started_at=fmt.second(batch.started_at) if batch.started_at else None,
        duration_ms=duration,
        error=batch.error,
    )


def batches(db: Session, tenant: Tenant, source_code: str | None = None, limit: int = 50) -> list[s.BatchOut]:
    q = (
        select(IngestionBatch, DataSource)
        .join(DataSource, DataSource.id == IngestionBatch.source_id)
        .where(IngestionBatch.tenant_id == tenant.id)
    )
    if source_code:
        q = q.where(DataSource.code == source_code)
    rows = db.execute(q.order_by(IngestionBatch.code.desc()).limit(limit)).all()
    return [batch_out(b, src) for b, src in rows]


def get_batch(db: Session, tenant: Tenant, code: str) -> IngestionBatch:
    batch = db.scalar(
        select(IngestionBatch).where(IngestionBatch.tenant_id == tenant.id, IngestionBatch.code == code)
    )
    if batch is None:
        raise NotFoundError(f"Batch '{code}' not found.", code="batch_not_found")
    return batch


def batch_detail(db: Session, tenant: Tenant, code: str, sample: int = 50) -> s.BatchDetailOut:
    batch = get_batch(db, tenant, code)
    source = db.get(DataSource, batch.source_id)
    assert source is not None
    q_rows = db.scalars(
        select(QuarantinedRow)
        .where(QuarantinedRow.batch_id == batch.id)
        .order_by(QuarantinedRow.line_no)
        .limit(sample)
    )
    issues = db.scalars(select(DqIssue).where(DqIssue.batch_id == batch.id).order_by(DqIssue.code))
    return s.BatchDetailOut(
        **batch_out(batch, source).model_dump(),
        quarantined=[
            s.QuarantineOut(line=r.line_no, errors=[CHECKS[e][0] for e in r.errors], raw=r.raw)
            for r in q_rows
        ],
        issues=[
            s.QualityIssueOut(
                id=i.code,
                source=i.source_name,
                check=i.check_name,
                field=i.field,
                failing=i.failing,
                total=i.total,
                severity=i.severity,
                auto_fixed=i.auto_fixed,
            )
            for i in issues
        ],
    )


def _txn_out(t: LedgerTxn, batch_code: str) -> s.TxnOut:
    return s.TxnOut(
        id=t.code,
        entity=t.entity_code,
        counterparty=t.counterparty_code,
        account=t.account,
        amount=fmt.number(t.amount),
        currency=t.currency,
        amount_usd=fmt.number(t.amount_usd) if t.amount_usd is not None else None,
        value_date=t.value_date.isoformat(),
        reference=t.reference_norm,
        description=t.description,
        batch=batch_code,
        warnings=[CHECKS[w][0] for w in t.warnings],
    )


def transactions(
    db: Session,
    tenant: Tenant,
    page: PageParams,
    entity: str | None = None,
    counterparty: str | None = None,
    batch_code: str | None = None,
) -> s.TxnPage:
    q = (
        select(LedgerTxn, IngestionBatch.code)
        .join(IngestionBatch, IngestionBatch.id == LedgerTxn.batch_id)
        .where(LedgerTxn.tenant_id == tenant.id)
    )
    if entity:
        q = q.where(LedgerTxn.entity_code == entity.upper())
    if counterparty:
        q = q.where(LedgerTxn.counterparty_code == counterparty.upper())
    if batch_code:
        q = q.where(IngestionBatch.code == batch_code)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.execute(q.order_by(LedgerTxn.code.desc()).offset(page.offset).limit(page.limit + 1)).all()
    items = [_txn_out(t, code) for t, code in rows[: page.limit]]
    has_more = len(rows) > page.limit
    return s.TxnPage(
        items=items, next_cursor=encode_cursor(page.offset + page.limit) if has_more else None, total=total
    )


def recent_txn_codes(db: Session, tenant: Tenant, limit: int = 10) -> list[str]:
    return list(
        db.scalars(
            select(LedgerTxn.code)
            .where(LedgerTxn.tenant_id == tenant.id)
            .order_by(LedgerTxn.code.desc())
            .limit(limit)
        )
    )


def lineage(db: Session, tenant: Tenant, code: str) -> list[dict[str, Any]]:
    t = db.scalar(select(LedgerTxn).where(LedgerTxn.tenant_id == tenant.id, LedgerTxn.code == code))
    if t is None:
        raise NotFoundError(f"No lineage for transaction '{code}'.", code="lineage_not_found")
    batch = db.get(IngestionBatch, t.batch_id)
    source = db.get(DataSource, t.source_id)
    assert batch is not None and source is not None
    at = fmt.second(batch.started_at) if batch.started_at else "—"
    done = fmt.second(batch.finished_at) if batch.finished_at else at
    warnings = [CHECKS[w][0] for w in t.warnings]
    blocking = [c for c, meta in CHECKS.items() if meta[3]]
    fx_ok = t.amount_usd is not None
    return [
        {
            "stage": "Extracted",
            "system": f"{source.name} ({source.system})",
            "at": at,
            "detail": f"{batch.file_name} line {t.line_no}: {t.entity_code} → {t.counterparty_code}, "
            f"{fmt.number(t.amount):,} {t.currency}" + (f", doc {t.external_id}" if t.external_id else ""),
            "status": "ok",
        },
        {
            "stage": "Validated",
            "system": "Data Quality",
            "at": done,
            "detail": f"{len(blocking)}/{len(blocking)} blocking checks passed"
            + (f"; warnings: {', '.join(warnings)}" if warnings else ""),
            "status": "warn" if warnings else "ok",
        },
        {
            "stage": "Normalized",
            "system": "Normalization",
            "at": done,
            "detail": f"Reference '{t.reference_raw or '—'}' → '{t.reference_norm or '—'}'; counterparty {t.counterparty_code}",
            "status": "ok",
        },
        {
            "stage": "Enriched",
            "system": "Augmented Data (FX)",
            "at": done,
            "detail": f"{fmt.number(t.amount_usd):,} USD @ {float(t.fx_rate):.6f}"
            if t.amount_usd is not None and t.fx_rate is not None
            else f"No FX rate for {t.currency} on {t.value_date.isoformat()}",
            "status": "ok" if fx_ok else "warn",
        },
        {
            "stage": "Candidates",
            "system": "Candidate Generation",
            "at": "—",
            "detail": "Awaiting the first matching run (Stage 3)",
            "status": "warn",
        },
    ]


def fx_rates(db: Session, tenant: Tenant, on: date | None = None) -> list[s.FxRateOut]:
    latest = select(func.max(FxRate.rate_date)).where(FxRate.tenant_id == tenant.id)
    if on:
        latest = latest.where(FxRate.rate_date <= on)
    day = db.scalar(latest)
    if day is None:
        return []
    rows = db.scalars(
        select(FxRate).where(FxRate.tenant_id == tenant.id, FxRate.rate_date == day).order_by(FxRate.currency)
    )
    return [
        s.FxRateOut(
            date=r.rate_date.isoformat(),
            currency=r.currency,
            rate_to_usd=float(r.rate_to_usd),
            source=r.source,
        )
        for r in rows
    ]
