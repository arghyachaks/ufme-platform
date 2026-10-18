"""Import every model here so Alembic and Base.metadata see them."""

from app.models.audit import AuditEvent
from app.models.domain import (
    CaseComment,
    ControlTest,
    DataSource,
    DqIssue,
    ExceptionItem,
    MatchRule,
    Policy,
    ReconCase,
    Snapshot,
)
from app.models.identity import AppUser, Role, UserRole
from app.models.tenant import LegalEntity, Tenant

__all__ = [
    "AppUser",
    "AuditEvent",
    "CaseComment",
    "ControlTest",
    "DataSource",
    "DqIssue",
    "ExceptionItem",
    "LegalEntity",
    "MatchRule",
    "Policy",
    "ReconCase",
    "Role",
    "Snapshot",
    "Tenant",
    "UserRole",
]
