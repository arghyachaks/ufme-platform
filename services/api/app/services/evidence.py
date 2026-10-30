"""Evidence package (Stage 5, control AUD-02): what an auditor takes away, provably unaltered.

A zip with the audit trail and control results as CSV, plus `manifest.json` (tenant, period, who generated it,
the SHA-256 of every file, and the audit chain's verification result and head hash) and `manifest.sig`, an
HMAC-SHA256 of the manifest under the deployment's evidence signing key. Anyone holding the key can re-verify
with `verify_package`; anyone at all can check the files against the manifest hashes.
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import zipfile
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ForbiddenError
from app.models import AuditEvent, ControlTest, Tenant
from app.services import audit
from app.services.workflow import RANK, Actor

DEV_KEY = "ufme-local-development-evidence-key"


def signing_key() -> bytes:
    key = settings.evidence_signing_key
    if not key:
        if settings.environment in ("staging", "prod"):
            raise ForbiddenError(
                "Evidence signing isn't configured on this deployment.", code="no_signing_key"
            )
        key = DEV_KEY  # local/test only: packages say so in their manifest
    return key.encode()


def can_export(actor: Actor) -> bool:
    return actor.role == "Auditor" or actor.rank >= RANK["Controller"]


def _csv(header: list[str], rows: list[list[Any]]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue().encode()


def build(
    db: Session, tenant: Tenant, actor: Actor, start: date | None = None, end: date | None = None
) -> tuple[bytes, dict[str, Any]]:
    if not can_export(actor):
        raise ForbiddenError(
            "Evidence export needs an Auditor or a Controller and above.", code="insufficient_authority"
        )
    q = select(AuditEvent).where(AuditEvent.tenant_id == tenant.id)
    if start:
        q = q.where(AuditEvent.occurred_at >= datetime.combine(start, time.min, UTC))
    if end:
        q = q.where(AuditEvent.occurred_at <= datetime.combine(end, time.max, UTC))
    events = list(db.scalars(q.order_by(AuditEvent.seq)))
    files = {
        "audit_events.csv": _csv(
            [
                "seq",
                "occurred_at",
                "actor",
                "action",
                "object_type",
                "object_id",
                "entity",
                "control",
                "request_id",
                "before",
                "after",
                "prev_hash",
                "hash",
            ],
            [
                [
                    e.seq,
                    e.occurred_at.isoformat(),
                    e.actor,
                    e.action,
                    e.object_type,
                    e.object_id,
                    e.entity_code or "",
                    e.control or "",
                    e.request_id or "",
                    json.dumps(e.before, sort_keys=True, default=str) if e.before else "",
                    json.dumps(e.after, sort_keys=True, default=str) if e.after else "",
                    e.prev_hash or "",
                    e.hash,
                ]
                for e in events
            ],
        ),
        "control_tests.csv": _csv(
            ["control", "name", "owner", "result", "last_run", "evidence_items"],
            [
                [
                    c.code,
                    c.name,
                    c.owner,
                    c.result,
                    c.last_run_on.isoformat() if c.last_run_on else "",
                    c.evidence,
                ]
                for c in db.scalars(
                    select(ControlTest).where(ControlTest.tenant_id == tenant.id).order_by(ControlTest.code)
                )
            ],
        ),
    }
    manifest: dict[str, Any] = {
        "format": "ufme-evidence/1",
        "tenant": tenant.slug,
        "period": {"from": start.isoformat() if start else None, "to": end.isoformat() if end else None},
        "generated_by": actor.email,
        "generated_at": datetime.now(UTC).isoformat(),
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
        "audit_chain": audit.verify_report(db, tenant.id),
        "events_in_package": len(events),
        "signing": "development key (not for external audit)"
        if not settings.evidence_signing_key
        else "deployment key",
    }
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode()
    signature = hmac.new(signing_key(), manifest_bytes, hashlib.sha256).hexdigest()
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
        z.writestr("manifest.json", manifest_bytes)
        z.writestr("manifest.sig", signature + "\n")
    audit.record(
        db,
        tenant_id=tenant.id,
        actor=actor.email,
        action="evidence.exported",
        object_type="evidence_package",
        object_id=signature[:16],
        control="AUD-02",
        after={
            "events": len(events),
            "chain_ok": manifest["audit_chain"]["ok"],
            "period": manifest["period"],
        },
    )
    return out.getvalue(), manifest


def verify_package(data: bytes) -> dict[str, Any]:
    """Signature valid and every file matches its manifest hash."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        manifest_bytes = z.read("manifest.json")
        signature = z.read("manifest.sig").decode().strip()
        manifest = json.loads(manifest_bytes)
        files_ok = {
            name: hashlib.sha256(z.read(name)).hexdigest() == digest
            for name, digest in manifest["files"].items()
        }
    expected = hmac.new(signing_key(), manifest_bytes, hashlib.sha256).hexdigest()
    return {
        "signature_ok": hmac.compare_digest(expected, signature),
        "files_ok": all(files_ok.values()),
        "files": files_ok,
        "audit_chain_ok": manifest["audit_chain"]["ok"],
    }
