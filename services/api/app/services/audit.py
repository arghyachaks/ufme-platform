import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import request_id_var
from app.db.base import utcnow
from app.models.audit import AuditEvent


def record(
    db: Session,
    *,
    actor: str,
    action: str,
    object_type: str,
    object_id: str,
    tenant_id: uuid.UUID | None = None,
    entity_code: str | None = None,
    control: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditEvent:
    """Append an audit event chained to the tenant's previous event. Call inside the business transaction."""
    prev = db.scalar(
        select(AuditEvent.hash)
        .where(AuditEvent.tenant_id == tenant_id)
        .order_by(AuditEvent.seq.desc())
        .limit(1)
    )
    event = AuditEvent(
        tenant_id=tenant_id,
        occurred_at=utcnow(),
        actor=actor,
        action=action,
        object_type=object_type,
        object_id=object_id,
        entity_code=entity_code,
        control=control,
        request_id=request_id_var.get(),
        before=before,
        after=after,
        prev_hash=prev,
    )
    event.hash = event.compute_hash()
    db.add(event)
    db.flush()
    return event


def verify_chain(db: Session, tenant_id: uuid.UUID | None) -> bool:
    prev: str | None = None
    for event in db.scalars(
        select(AuditEvent).where(AuditEvent.tenant_id == tenant_id).order_by(AuditEvent.seq)
    ):
        if event.prev_hash != prev or event.compute_hash() != event.hash:
            return False
        prev = event.hash
    return True
