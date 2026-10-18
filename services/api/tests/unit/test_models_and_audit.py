from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AppUser, AuditEvent, LegalEntity, Role, Tenant, UserRole
from app.services import audit


def _tenant(db: Session) -> Tenant:
    tenant = Tenant(slug="demo", name="UFME Demo", region="eu-west")
    db.add(tenant)
    db.flush()
    return tenant


def test_tenant_entity_user_role_graph(db: Session) -> None:
    tenant = _tenant(db)
    db.add(LegalEntity(tenant_id=tenant.id, code="US01", name="Demo Inc", country="US", currency="USD"))
    role = Role(tenant_id=tenant.id, name="Controller", permissions=["approve:<=1M", "signoff"])
    user = AppUser(tenant_id=tenant.id, email="d.ortiz@example.com", display_name="Daniel Ortiz", status="Active")
    user.roles.append(UserRole(role=role, entity_codes=["US01", "UK02"]))
    db.add_all([role, user])
    db.flush()

    loaded = db.scalar(select(AppUser).where(AppUser.email == "d.ortiz@example.com"))
    assert loaded is not None
    assert loaded.roles[0].role.name == "Controller"
    assert loaded.roles[0].entity_codes == ["US01", "UK02"]
    assert loaded.created_at is not None


def test_audit_events_form_a_verifiable_chain(db: Session) -> None:
    tenant = _tenant(db)
    first = audit.record(db, tenant_id=tenant.id, actor="system", action="tenant.created",
                         object_type="tenant", object_id=str(tenant.id), after={"slug": "demo"})
    second = audit.record(db, tenant_id=tenant.id, actor="priya@example.com", action="match.accepted",
                          object_type="match", object_id="MT-20931", entity_code="US01", control="IC-03")
    assert first.prev_hash is None
    assert second.prev_hash == first.hash
    assert audit.verify_chain(db, tenant.id)


def test_audit_chain_detects_tampering(db: Session) -> None:
    tenant = _tenant(db)
    audit.record(db, tenant_id=tenant.id, actor="a", action="x", object_type="t", object_id="1")
    event = audit.record(db, tenant_id=tenant.id, actor="b", action="y", object_type="t", object_id="2")
    event.actor = "mallory"  # simulate an edit outside the app (Postgres trigger blocks this in production)
    assert not audit.verify_chain(db, tenant.id)
    assert db.scalar(select(AuditEvent).where(AuditEvent.actor == "mallory")) is not None
