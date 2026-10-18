"""Demo data seeding from the JSON fixtures exported from the frontend mocks (scripts/export-mocks.mts)."""

import json
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AppUser,
    AuditEvent,
    CaseComment,
    ControlTest,
    DataSource,
    DqIssue,
    ExceptionItem,
    LegalEntity,
    MatchRule,
    Policy,
    ReconCase,
    Role,
    Snapshot,
    Tenant,
    UserRole,
)
from app.services import audit
from app.services import display as fmt

FIXTURES = Path(__file__).parent / "demo"
DEMO_TENANT = "demo"
logger = logging.getLogger("ufme.seed")


def load_fixtures() -> dict[str, Any]:
    return {
        name: json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
        for name in ("core", "recon", "dashboard")
    }


def snapshot_payloads(fx: dict[str, Any]) -> dict[str, Any]:
    core = fx["core"]
    return {
        "workflow.stages": core["workflowStages"],
        "simulation.results": core["simulationResults"],
        "ai.models": {"models": core["models"], "trend": core["modelTrend"]},
        "ai.explanations": core["explanations"],
        "ai.learning": {"signals": core["learningSignals"], "stats": core["learningStats"]},
        "ai.copilot": {"messages": core["copilotSeed"], "prompts": core["copilotPrompts"]},
        "data.quality.dimensions": core["qualityDimensions"],
        "data.lineage": core["lineage"],
        "data.features": core["featureStore"],
        "ops": {"services": core["services"], "jobs": core["jobs"]},
        "graph": {"nodes": core["graphNodes"], "edges": core["graphEdges"]},
        "workspace.recon": fx["recon"],
        "workspace.dashboard": fx["dashboard"],
    }


def seed_demo(db: Session, now: datetime | None = None) -> Tenant:
    """Idempotent: creates the demo tenant and rows once; snapshots are refreshed on every run."""
    now = now or datetime.now(UTC)
    fx = load_fixtures()
    core = fx["core"]
    tenant = db.scalar(select(Tenant).where(Tenant.slug == DEMO_TENANT))
    created = tenant is None
    if tenant is None:
        tenant = Tenant(slug=DEMO_TENANT, name="UFME Demo", region="eu-west")
        db.add(tenant)
        db.flush()
    tid = tenant.id

    existing = {s.key: s for s in db.scalars(select(Snapshot).where(Snapshot.tenant_id == tid))}
    for key, payload in snapshot_payloads(fx).items():
        if key in existing:
            existing[key].payload = payload
        else:
            db.add(Snapshot(tenant_id=tid, key=key, payload=payload))

    if not created and db.scalar(
        select(func.count()).select_from(ExceptionItem).where(ExceptionItem.tenant_id == tid)
    ):
        db.flush()
        return tenant

    for e in core["legalEntities"]:
        db.add(
            LegalEntity(
                tenant_id=tid,
                code=e["code"],
                name=e["name"],
                country=e["country"],
                currency=e["currency"],
                recon_owner=e["owner"],
            )
        )
    roles = {}
    for r in core["roles"]:
        roles[r["role"]] = Role(tenant_id=tid, name=r["role"], permissions=r["permissions"])
        db.add(roles[r["role"]])
    for u in core["users"]:
        user = AppUser(
            tenant_id=tid,
            email=u["email"],
            display_name=u["name"],
            status=u["status"],
            mfa_enabled=u["mfa"],
            last_login_at=fmt.parse_last_login(u["lastLogin"], now),
        )
        user.roles.append(UserRole(role=roles[u["role"]], entity_codes=u["entities"]))
        db.add(user)

    for x in core["exceptions"]:
        db.add(
            ExceptionItem(
                tenant_id=tid,
                code=x["id"],
                entity_code=x["entity"],
                counterparty=x["counterparty"],
                kind=x["type"],
                amount=Decimal(str(x["amount"])),
                currency=x["currency"],
                severity=x["severity"],
                owner=x["owner"],
                root_cause=x["rootCause"],
                status=x["status"],
                opened_at=now - timedelta(days=x["ageDays"]),
                sla_due_at=now + timedelta(hours=x["slaHoursLeft"]),
            )
        )
    for c in core["cases"]:
        case = ReconCase(
            tenant_id=tid,
            code=c["id"],
            title=c["title"],
            entity_code=c["entity"],
            exposure=Decimal(str(c["exposure"])),
            priority=c["priority"],
            status=c["status"],
            assignee=c["assignee"],
            exception_codes=c["exceptionIds"],
            opened_at=datetime.combine(fmt.parse_day(c["opened"]), datetime.min.time(), UTC),
            due_at=fmt.parse_due_in(c["dueIn"], now),
        )
        case.comments = [
            CaseComment(author=m["author"], posted_at=fmt.parse_minute(m["at"]), body=m["text"])
            for m in c["comments"]
        ]
        db.add(case)
    for r in core["rules"]:
        edited_on, _, edited_by = r["lastEdited"].partition(" · ")
        db.add(
            MatchRule(
                tenant_id=tid,
                code=r["id"],
                name=r["name"],
                kind=r["kind"],
                scope=r["scope"],
                conditions=r["conditions"],
                tolerance=r.get("tolerance"),
                priority=r["priority"],
                enabled=r["enabled"],
                hit_rate=r["hitRate"],
                precision=r["precision"],
                version=r["version"],
                edited_on=fmt.parse_day(edited_on),
                edited_by=edited_by,
            )
        )
    for p in core["policies"]:
        db.add(
            Policy(
                tenant_id=tid,
                code=p["id"],
                name=p["name"],
                category=p["category"],
                version=p["version"],
                status=p["status"],
                owner=p["owner"],
                effective_on=fmt.parse_day_year(p["effective"]),
                summary=p["summary"],
                thresholds=p["thresholds"],
            )
        )
    for s in core["sources"]:
        db.add(
            DataSource(
                tenant_id=tid,
                code=s["id"],
                name=s["name"],
                system=s["system"],
                kind=s["kind"],
                status=s["status"],
                last_sync_at=fmt.parse_last_sync(s["lastSync"], now),
                records_24h=s["records24h"],
                latency_min=s["latencyMin"],
                schedule=s["schedule"],
            )
        )
    for q in core["qualityIssues"]:
        db.add(
            DqIssue(
                tenant_id=tid,
                code=q["id"],
                source_name=q["source"],
                check_name=q["check"],
                field=q["field"],
                failing=q["failing"],
                total=q["total"],
                severity=q["severity"],
                auto_fixed=q["autoFixed"],
            )
        )
    for t in core["controlTests"]:
        db.add(
            ControlTest(
                tenant_id=tid,
                code=t["id"],
                name=t["name"],
                owner=t["owner"],
                last_run_on=None if t["lastRun"] == "Pending" else fmt.parse_day(t["lastRun"]),
                result=t["result"],
                evidence=t["evidence"],
            )
        )
    db.flush()
    if not db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.tenant_id == tid)):
        for a in sorted(core["auditEvents"], key=lambda a: fmt.parse_second(a["at"])):
            audit.record(
                db,
                tenant_id=tid,
                actor=a["actor"],
                action=a["action"],
                object_type="demo",
                object_id=a["object"],
                entity_code=a["entity"],
                control=a["control"],
                occurred_at=fmt.parse_second(a["at"]),
            )
        db.flush()
    logger.info("Seeded demo tenant")
    return tenant
