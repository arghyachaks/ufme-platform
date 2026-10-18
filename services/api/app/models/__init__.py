"""Import every model here so Alembic and Base.metadata see them."""

from app.models.audit import AuditEvent
from app.models.identity import AppUser, Role, UserRole
from app.models.tenant import LegalEntity, Tenant

__all__ = ["AppUser", "AuditEvent", "LegalEntity", "Role", "Tenant", "UserRole"]
