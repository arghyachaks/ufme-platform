import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Identity, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utcnow


class AuditEvent(Base):
    """Append-only audit trail. Each row hashes its content plus the previous row's hash (tamper evidence)."""

    __tablename__ = "audit_event"
    __table_args__ = (Index("ix_audit_event_tenant_object", "tenant_id", "object_type", "object_id"),)

    seq: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), Identity(), primary_key=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenant.id"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(320))
    action: Mapped[str] = mapped_column(String(64))
    object_type: Mapped[str] = mapped_column(String(64))
    object_id: Mapped[str] = mapped_column(String(128))
    entity_code: Mapped[str | None] = mapped_column(String(16))
    control: Mapped[str | None] = mapped_column(String(32))
    request_id: Mapped[str | None] = mapped_column(String(128))
    before: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    prev_hash: Mapped[str | None] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))

    def compute_hash(self) -> str:
        ts = self.occurred_at
        if ts is not None and ts.tzinfo is not None:  # normalise so hashes match across DB drivers
            ts = ts.astimezone(UTC).replace(tzinfo=None)
        body = {
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "occurred_at": ts.isoformat() if ts else None,
            "actor": self.actor,
            "action": self.action,
            "object_type": self.object_type,
            "object_id": self.object_id,
            "before": self.before,
            "after": self.after,
            "prev_hash": self.prev_hash,
        }
        return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()
