"""Stage 3: matching runs, match groups (proposals), members, and reviewer labels."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPk
from app.models.domain import Money, TenantScoped


class MatchRun(TenantScoped, Base):
    __tablename__ = "match_run"

    status: Mapped[str] = mapped_column(String(16))  # Queued | Running | Completed | Failed
    scope: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    engine_version: Mapped[str] = mapped_column(String(64))
    rules: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list
    )  # rule definitions used (audit replay)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    requested_by: Mapped[str] = mapped_column(String(120), default="system")


class MatchGroup(TenantScoped, Base):
    __tablename__ = "match_group"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_match_group_tenant_code"),
        Index("ix_match_group_tenant_status", "tenant_id", "status"),
        Index("ix_match_group_tenant_run_status", "tenant_id", "run_id", "status"),
    )

    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("match_run.id", ondelete="CASCADE"), index=True)
    match_type: Mapped[str] = mapped_column(String(8))  # 1:1 | 1:M | M:1 | M:M
    decision: Mapped[str] = mapped_column(String(16))  # auto | suggest
    status: Mapped[str] = mapped_column(String(16))  # matched | proposed | accepted | rejected | superseded
    confidence: Mapped[float] = mapped_column(Float)
    exposure_usd: Mapped[Decimal] = mapped_column(Money)
    residual_usd: Mapped[Decimal] = mapped_column(Money)
    entity_pair: Mapped[str] = mapped_column(String(40))
    rule_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    explanation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    decided_by: Mapped[str | None] = mapped_column(String(120))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    members: Mapped[list["MatchMember"]] = relationship(back_populates="group", cascade="all, delete-orphan")


class MatchMember(UUIDPk, Timestamps, Base):
    __tablename__ = "match_member"

    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("match_group.id", ondelete="CASCADE"), index=True)
    txn_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ledger_txn.id", ondelete="CASCADE"), index=True)
    side: Mapped[str] = mapped_column(String(1))

    group: Mapped[MatchGroup] = relationship(back_populates="members")


class MatchLabel(UUIDPk, Timestamps, Base):
    """Reviewer outcome on a proposal — training data for the learning loop (Stage 3f) and an audit record."""

    __tablename__ = "match_label"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), index=True)
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("match_group.id", ondelete="CASCADE"), index=True)
    action: Mapped[str] = mapped_column(String(16))  # accept | reject
    actor: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str | None] = mapped_column(Text)
    model_confidence: Mapped[float] = mapped_column(Float)
    features: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
