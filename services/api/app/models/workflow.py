"""Human-in-the-loop workflow — approval requests and period sign-off."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.domain import Money, TenantScoped


class ApprovalRequest(TenantScoped, Base):
    """A match (reviewed suggestion or manual match) waiting for sign-off under the approval matrix."""

    __tablename__ = "approval_request"

    kind: Mapped[str] = mapped_column(String(16))  # review | manual
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("match_group.id", ondelete="CASCADE"), index=True
    )
    match_code: Mapped[str] = mapped_column(String(32))
    entity_code: Mapped[str] = mapped_column(String(40))
    exposure_usd: Mapped[Decimal] = mapped_column(Money)
    materiality: Mapped[str] = mapped_column(String(8))  # High | Medium | Low
    confidence: Mapped[float] = mapped_column(Float)
    required_role: Mapped[str] = mapped_column(String(32))  # Manager | Controller | Finance Director
    approvals_needed: Mapped[int] = mapped_column(Integer, default=1)  # 2 = dual control (> 1M)
    approvals: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)  # [{actor, role, at}]
    status: Mapped[str] = mapped_column(
        String(16), index=True
    )  # Pending | Approved | Rejected | Info requested
    submitted_by: Mapped[str] = mapped_column(String(320))  # email
    submitted_by_name: Mapped[str] = mapped_column(String(200))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sla_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rationale: Mapped[str] = mapped_column(Text, default="")
    documents: Mapped[list[str]] = mapped_column(JSON, default=list)
    factors: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    trail: Mapped[list[str]] = mapped_column(JSON, default=list)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PeriodSignoff(TenantScoped, Base):
    """One row per entity and period; code = '<ENTITY>-<YYYY-MM>'. Signatures climb Manager → Controller → FD."""

    __tablename__ = "period_signoff"

    entity_code: Mapped[str] = mapped_column(String(16))
    period: Mapped[str] = mapped_column(String(7))
    status: Mapped[str] = mapped_column(String(24))  # Open | Manager signed | Controller signed | Signed off
    signatures: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
