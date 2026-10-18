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
from app.models.ingestion import FxRate, IngestionBatch, LedgerTxn, QuarantinedRow
from app.models.tenant import LegalEntity, Tenant

__all__ = [
    "AppUser",
    "AuditEvent",
    "CaseComment",
    "ControlTest",
    "DataSource",
    "DqIssue",
    "ExceptionItem",
    "FxRate",
    "IngestionBatch",
    "LedgerTxn",
    "LegalEntity",
    "MatchRule",
    "Policy",
    "QuarantinedRow",
    "ReconCase",
    "Role",
    "Snapshot",
    "Tenant",
    "UserRole",
]
