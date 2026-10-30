"""Agent harness: every agent run and every step it took (plan, to-dos, tool calls, sub-agents, usage).

Runs are the evidence behind the Agent Operations dashboard (usage, models, anomalies, InfoSec / QRM views) and
let anyone with access replay exactly what an agent did. Both tables are tenant-scoped (row-level security).
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Timestamps, UUIDPk


class AgentRun(UUIDPk, Timestamps, Base):
    __tablename__ = "agent_run"
    __table_args__ = (Index("ix_agent_run_tenant_started", "tenant_id", "started_at"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), index=True)
    agent: Mapped[str] = mapped_column(String(48))  # e.g. assist
    actor: Mapped[str] = mapped_column(String(120))
    question: Mapped[str] = mapped_column(Text)
    page: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str] = mapped_column(String(120))  # registry name actually used
    provider: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24))  # running | completed | failed | awaiting_approval ...
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal(0))
    tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    subagents: Mapped[int] = mapped_column(Integer, default=0)
    egress: Mapped[bool] = mapped_column(default=False)  # data left the machine (hosted model)
    error: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AgentEvent(UUIDPk, Base):
    __tablename__ = "agent_event"
    __table_args__ = (Index("ix_agent_event_run_seq", "run_id", "seq"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_run.id", ondelete="CASCADE"))
    seq: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(24))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AgentModel(UUIDPk, Timestamps, Base):
    """A model an admin registered for this tenant. Four eyes: proposed by one person, approved by another
    (a Finance Director) before any agent may use it. Blocking is immediate. API keys are never stored: only the
    name of the environment variable / secret that holds the key."""

    __tablename__ = "agent_model"
    __table_args__ = (Index("uq_agent_model_tenant_name", "tenant_id", "name", unique=True),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(120))
    base_url: Mapped[str | None] = mapped_column(String(300))
    api_key_env: Mapped[str | None] = mapped_column(String(80))
    price_in: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal(0))
    price_out: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal(0))
    allows_confidential: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(16))  # pending | approved | blocked
    requested_by: Mapped[str] = mapped_column(String(120))
    approved_by: Mapped[str | None] = mapped_column(String(120))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)


class AgentBinding(UUIDPk, Timestamps, Base):
    """Which models an agent role uses, in fallback order (overrides the configured default for the tenant)."""

    __tablename__ = "agent_binding"
    __table_args__ = (Index("uq_agent_binding_tenant_role", "tenant_id", "role", unique=True),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(48))
    models: Mapped[list[str]] = mapped_column(JSON, default=list)
    updated_by: Mapped[str] = mapped_column(String(120))
