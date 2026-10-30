"""Import every model here so Alembic and Base.metadata see them."""

from app.models.agents import AgentBinding, AgentEvent, AgentModel, AgentRun
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
from app.models.matching import MatchGroup, MatchLabel, MatchMember, MatchRun, ScorerModel
from app.models.tenant import LegalEntity, Tenant
from app.models.workflow import ApprovalRequest, PeriodSignoff

__all__ = [
    "AgentBinding",
    "AgentEvent",
    "AgentModel",
    "AgentRun",
    "AppUser",
    "ApprovalRequest",
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
    "MatchGroup",
    "MatchLabel",
    "MatchMember",
    "MatchRule",
    "MatchRun",
    "PeriodSignoff",
    "Policy",
    "QuarantinedRow",
    "ReconCase",
    "Role",
    "ScorerModel",
    "Snapshot",
    "Tenant",
    "UserRole",
]
