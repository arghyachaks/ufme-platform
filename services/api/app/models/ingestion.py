"""Ingestion batches, ledger transactions, quarantined rows and FX rates."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPk
from app.models.domain import Money, TenantScoped


class FxRate(UUIDPk, Timestamps, Base):
    __tablename__ = "fx_rate"
    __table_args__ = (
        UniqueConstraint("tenant_id", "rate_date", "currency", name="uq_fx_rate_tenant_date_ccy"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), index=True)
    rate_date: Mapped[date] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3))
    rate_to_usd: Mapped[Decimal] = mapped_column(Numeric(20, 10))
    source: Mapped[str] = mapped_column(String(64))


class IngestionBatch(TenantScoped, Base):
    __tablename__ = "ingestion_batch"

    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_source.id", ondelete="CASCADE"), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16))  # Queued | Processing | Completed | Failed
    rows_total: Mapped[int] = mapped_column(Integer, default=0)
    rows_loaded: Mapped[int] = mapped_column(Integer, default=0)
    rows_quarantined: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    storage_path: Mapped[str | None] = mapped_column(String(500))


class LedgerTxn(UUIDPk, Timestamps, Base):
    """A normalized ledger line. Immutable once loaded; matching references it."""

    __tablename__ = "ledger_txn"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_ledger_txn_tenant_code"),
        Index("ix_ledger_txn_pair", "tenant_id", "entity_code", "counterparty_code", "value_date"),
        Index("ix_ledger_txn_reference", "tenant_id", "reference_norm"),
        Index("ix_ledger_txn_external", "tenant_id", "source_id", "external_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(64))
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingestion_batch.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_source.id", ondelete="CASCADE"))
    external_id: Mapped[str | None] = mapped_column(String(128))
    line_no: Mapped[int] = mapped_column(Integer)
    entity_code: Mapped[str] = mapped_column(String(16))
    counterparty_code: Mapped[str] = mapped_column(String(120))
    account: Mapped[str | None] = mapped_column(String(64))
    amount: Mapped[Decimal] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(3))
    amount_usd: Mapped[Decimal | None] = mapped_column(Money)
    fx_rate: Mapped[Decimal | None] = mapped_column(Numeric(20, 10))
    value_date: Mapped[date] = mapped_column(Date)
    posting_date: Mapped[date | None] = mapped_column(Date)
    reference_raw: Mapped[str | None] = mapped_column(String(255))
    reference_norm: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(String(500))
    warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    raw: Mapped[dict[str, Any]] = mapped_column(JSON)


class QuarantinedRow(UUIDPk, Timestamps, Base):
    __tablename__ = "quarantined_row"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), index=True)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ingestion_batch.id", ondelete="CASCADE"), index=True
    )
    line_no: Mapped[int] = mapped_column(Integer)
    raw: Mapped[dict[str, Any]] = mapped_column(JSON)
    errors: Mapped[list[str]] = mapped_column(JSON)
