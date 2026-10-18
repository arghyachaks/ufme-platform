"""Read models for every screen. Typed tables are formatted here; later-stage screens read snapshots."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError
from app.models import (
    AppUser,
    AuditEvent,
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
from app.schemas import read as s
from app.services import display as fmt


def snapshot(db: Session, tenant: Tenant, key: str) -> Any:
    row = db.scalar(select(Snapshot).where(Snapshot.tenant_id == tenant.id, Snapshot.key == key))
    if row is None:
        raise NotFoundError(f"No data for '{key}'.", code="snapshot_not_found")
    return row.payload


def exceptions(db: Session, tenant: Tenant, now: datetime | None = None) -> list[s.ExceptionOut]:
    now = now or datetime.now(UTC)
    rows = db.scalars(
        select(ExceptionItem).where(ExceptionItem.tenant_id == tenant.id).order_by(ExceptionItem.code)
    )
    return [
        s.ExceptionOut(
            id=x.code,
            entity=x.entity_code,
            counterparty=x.counterparty,
            type=x.kind,
            amount=fmt.number(x.amount),
            currency=x.currency,
            age_days=fmt.age_days(x.opened_at, now),
            severity=x.severity,
            sla_hours_left=fmt.hours_left(x.sla_due_at, now),
            owner=x.owner,
            root_cause=x.root_cause,
            status=x.status,
        )
        for x in rows
    ]


def cases(db: Session, tenant: Tenant, now: datetime | None = None) -> list[s.CaseOut]:
    now = now or datetime.now(UTC)
    rows = db.scalars(
        select(ReconCase)
        .where(ReconCase.tenant_id == tenant.id)
        .options(selectinload(ReconCase.comments))
        .order_by(ReconCase.code.desc())
    )
    return [
        s.CaseOut(
            id=c.code,
            title=c.title,
            exception_ids=c.exception_codes,
            entity=c.entity_code,
            exposure=fmt.number(c.exposure),
            priority=c.priority,
            status=c.status,
            assignee=c.assignee,
            due_in=fmt.due_in(c.due_at, now, closed=c.status == "Closed"),
            opened=fmt.day(c.opened_at.date()),
            comments=[
                s.CaseCommentOut(author=m.author, at=fmt.minute(m.posted_at), text=m.body) for m in c.comments
            ],
        )
        for c in rows
    ]


def rules(db: Session, tenant: Tenant) -> list[s.RuleOut]:
    rows = db.scalars(select(MatchRule).where(MatchRule.tenant_id == tenant.id).order_by(MatchRule.priority))
    return [
        s.RuleOut(
            id=r.code,
            name=r.name,
            kind=r.kind,
            scope=r.scope,
            conditions=r.conditions,
            tolerance=r.tolerance,
            priority=r.priority,
            enabled=r.enabled,
            hit_rate=fmt.number(r.hit_rate),
            precision=fmt.number(r.precision),
            version=r.version,
            last_edited=f"{fmt.day(r.edited_on)} · {r.edited_by}",
        )
        for r in rows
    ]


def policies(db: Session, tenant: Tenant) -> list[s.PolicyOut]:
    rows = db.scalars(select(Policy).where(Policy.tenant_id == tenant.id).order_by(Policy.code))
    return [
        s.PolicyOut(
            id=p.code,
            name=p.name,
            category=p.category,
            version=p.version,
            status=p.status,
            owner=p.owner,
            effective=fmt.day_year(p.effective_on),
            summary=p.summary,
            thresholds=[s.Threshold(**t) for t in p.thresholds],
        )
        for p in rows
    ]


def sources(db: Session, tenant: Tenant, now: datetime | None = None) -> list[s.SourceOut]:
    now = now or datetime.now(UTC)
    rows = db.scalars(select(DataSource).where(DataSource.tenant_id == tenant.id).order_by(DataSource.code))
    return [
        s.SourceOut(
            id=d.code,
            name=d.name,
            system=d.system,
            kind=d.kind,
            status=d.status,
            last_sync=fmt.last_sync(d.last_sync_at, now),
            records_24h=d.records_24h,
            latency_min=d.latency_min,
            schedule=d.schedule,
        )
        for d in rows
    ]


def quality_issues(db: Session, tenant: Tenant) -> list[s.QualityIssueOut]:
    """Open issues: ingestion batches first (newest first), then baseline issues."""
    rows = db.scalars(
        select(DqIssue)
        .where(DqIssue.tenant_id == tenant.id, DqIssue.status == "Open")
        .order_by(DqIssue.batch_id.is_(None), DqIssue.code.desc())
    )
    return [
        s.QualityIssueOut(
            id=q.code,
            source=q.source_name,
            check=q.check_name,
            field=q.field,
            failing=q.failing,
            total=q.total,
            severity=q.severity,
            auto_fixed=q.auto_fixed,
        )
        for q in rows
    ]


def controls(db: Session, tenant: Tenant) -> list[s.ControlOut]:
    rows = db.scalars(
        select(ControlTest).where(ControlTest.tenant_id == tenant.id).order_by(ControlTest.created_at)
    )
    return [
        s.ControlOut(
            id=t.code,
            name=t.name,
            owner=t.owner,
            last_run=fmt.day(t.last_run_on) if t.last_run_on else "Pending",
            result=t.result,
            evidence=t.evidence,
        )
        for t in rows
    ]


def audit_events(db: Session, tenant: Tenant, limit: int = 200) -> list[s.AuditEventOut]:
    rows = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.tenant_id == tenant.id)
        .order_by(AuditEvent.seq.desc())
        .limit(limit)
    )
    return [
        s.AuditEventOut(
            id=f"AU-{a.seq}",
            at=fmt.second(a.occurred_at),
            actor=a.actor,
            action=a.action,
            object=a.object_id,
            entity=a.entity_code or "—",
            control=a.control or "—",
        )
        for a in rows
    ]


def admin(db: Session, tenant: Tenant, now: datetime | None = None) -> s.AdminOut:
    now = now or datetime.now(UTC)
    users = db.scalars(
        select(AppUser)
        .where(AppUser.tenant_id == tenant.id)
        .options(selectinload(AppUser.roles).selectinload(UserRole.role))
        .order_by(AppUser.created_at)
    ).all()
    counts: dict[str, int] = {
        name: n
        for name, n in db.execute(
            select(Role.name, func.count(UserRole.id))
            .join(UserRole, UserRole.role_id == Role.id, isouter=True)
            .where(Role.tenant_id == tenant.id)
            .group_by(Role.name)
        ).all()
    }
    roles = db.scalars(select(Role).where(Role.tenant_id == tenant.id).order_by(Role.created_at))
    entities = db.scalars(
        select(LegalEntity).where(LegalEntity.tenant_id == tenant.id).order_by(LegalEntity.code)
    )
    return s.AdminOut(
        users=[
            s.UserOut(
                name=u.display_name,
                email=u.email,
                role=u.roles[0].role.name if u.roles else "—",
                entities=u.roles[0].entity_codes if u.roles else [],
                status=u.status,
                mfa=u.mfa_enabled,
                last_login=fmt.last_login(u.last_login_at, now),
            )
            for u in users
        ],
        roles=[s.RoleOut(role=r.name, users=counts.get(r.name, 0), permissions=r.permissions) for r in roles],
        entities=[
            s.EntityOut(
                code=e.code, name=e.name, country=e.country, currency=e.currency, owner=e.recon_owner or "—"
            )
            for e in entities
        ],
    )
