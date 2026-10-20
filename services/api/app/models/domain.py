"""Stage 1 domain tables: exceptions, cases, rules, policies, data sources, DQ issues, controls, snapshots."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPk

Money = Numeric(20, 4)


class TenantScoped(UUIDPk, Timestamps):
    """Business rows carry a tenant and a human-readable code (e.g. EX-4821), unique per tenant."""

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(32))

    @declared_attr.directive
    def __table_args__(cls) -> tuple[Any, ...]:
        return (UniqueConstraint("tenant_id", "code", name=f"uq_{cls.__tablename__}_tenant_code"),)  # type: ignore[attr-defined]


class ExceptionItem(TenantScoped, Base):
    __tablename__ = "exception_item"

    entity_code: Mapped[str] = mapped_column(String(16))
    counterparty: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(32))
    amount: Mapped[Decimal] = mapped_column(Money)
    currency: Mapped[str] = mapped_column(String(3))
    severity: Mapped[str] = mapped_column(String(16))
    owner: Mapped[str] = mapped_column(String(120))
    root_cause: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sla_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReconCase(TenantScoped, Base):
    __tablename__ = "recon_case"

    title: Mapped[str] = mapped_column(String(300))
    entity_code: Mapped[str] = mapped_column(String(16))
    exposure: Mapped[Decimal] = mapped_column(Money)
    priority: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(24))
    assignee: Mapped[str] = mapped_column(String(120))
    exception_codes: Mapped[list[str]] = mapped_column(JSON, default=list)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    comments: Mapped[list["CaseComment"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="CaseComment.posted_at"
    )


class CaseComment(UUIDPk, Timestamps, Base):
    __tablename__ = "case_comment"

    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("recon_case.id", ondelete="CASCADE"), index=True)
    author: Mapped[str] = mapped_column(String(120))
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    body: Mapped[str] = mapped_column(Text)

    case: Mapped[ReconCase] = relationship(back_populates="comments")


class MatchRule(TenantScoped, Base):
    __tablename__ = "match_rule"

    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(24))
    scope: Mapped[str] = mapped_column(String(48))
    conditions: Mapped[list[str]] = mapped_column(JSON, default=list)
    tolerance: Mapped[str | None] = mapped_column(String(64))
    priority: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(default=True)
    hit_rate: Mapped[float] = mapped_column(Float, default=0.0)
    precision: Mapped[float] = mapped_column(Float, default=0.0)
    version: Mapped[str] = mapped_column(String(24))
    edited_on: Mapped[date] = mapped_column(Date)
    edited_by: Mapped[str] = mapped_column(String(120))
    definition: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # engine-executable rule DSL


class Policy(TenantScoped, Base):
    __tablename__ = "policy"

    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(48))
    version: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(16))
    owner: Mapped[str] = mapped_column(String(120))
    effective_on: Mapped[date] = mapped_column(Date)
    summary: Mapped[str] = mapped_column(Text)
    thresholds: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)


class DataSource(TenantScoped, Base):
    __tablename__ = "data_source"

    name: Mapped[str] = mapped_column(String(200))
    system: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    records_24h: Mapped[int] = mapped_column(Integer, default=0)
    latency_min: Mapped[int] = mapped_column(Integer, default=0)
    schedule: Mapped[str] = mapped_column(String(64))


class DqIssue(TenantScoped, Base):
    __tablename__ = "dq_issue"

    source_name: Mapped[str] = mapped_column(String(200))
    check_name: Mapped[str] = mapped_column(String(200))
    field: Mapped[str] = mapped_column(String(64))
    failing: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(16))
    auto_fixed: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(16), default="Open")  # Open | Resolved | Ignored
    batch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ingestion_batch.id", ondelete="SET NULL"))


class ControlTest(TenantScoped, Base):
    __tablename__ = "control_test"

    name: Mapped[str] = mapped_column(String(300))
    owner: Mapped[str] = mapped_column(String(120))
    last_run_on: Mapped[date | None] = mapped_column(Date)
    result: Mapped[str] = mapped_column(String(16))
    evidence: Mapped[int] = mapped_column(Integer, default=0)


class Snapshot(UUIDPk, Timestamps, Base):
    """Read-only reference payloads for screens whose engines arrive in later stages
    (model registry, lineage, feature store, ops metrics, graph, dashboard and recon workspace)."""

    __tablename__ = "snapshot"
    __table_args__ = (UniqueConstraint("tenant_id", "key", name="uq_snapshot_tenant_key"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(64))
    payload: Mapped[Any] = mapped_column(JSON, nullable=True)
