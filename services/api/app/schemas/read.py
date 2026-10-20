"""Response models. Field names are camelCase on the wire to match apps/web/src/api/types.ts."""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ExceptionOut(CamelModel):
    id: str
    entity: str
    counterparty: str
    type: str
    amount: int | float
    currency: str
    age_days: int
    severity: str
    sla_hours_left: int
    owner: str
    root_cause: str
    status: str


class CaseCommentOut(CamelModel):
    author: str
    at: str
    text: str


class CaseOut(CamelModel):
    id: str
    title: str
    exception_ids: list[str]
    entity: str
    exposure: int | float
    priority: str
    status: str
    assignee: str
    due_in: str
    opened: str
    comments: list[CaseCommentOut]


class RuleOut(CamelModel):
    id: str
    name: str
    kind: str
    scope: str
    conditions: list[str]
    tolerance: str | None = None
    priority: int
    enabled: bool
    hit_rate: int | float
    precision: int | float
    version: str
    last_edited: str


class Threshold(CamelModel):
    label: str
    value: str


class PolicyOut(CamelModel):
    id: str
    name: str
    category: str
    version: str
    status: str
    owner: str
    effective: str
    summary: str
    thresholds: list[Threshold]


class SourceOut(CamelModel):
    id: str
    name: str
    system: str
    kind: str
    status: str
    last_sync: str
    records_24h: int = Field(alias="records24h")
    latency_min: int
    schedule: str


class QualityIssueOut(CamelModel):
    id: str
    source: str
    check: str
    field: str
    failing: int
    total: int
    severity: str
    auto_fixed: bool


class ControlOut(CamelModel):
    id: str
    name: str
    owner: str
    last_run: str
    result: str
    evidence: int


class AuditEventOut(CamelModel):
    id: str
    at: str
    actor: str
    action: str
    object: str
    entity: str
    control: str


class UserOut(CamelModel):
    name: str
    email: str
    role: str
    entities: list[str]
    status: str
    mfa: bool
    last_login: str


class RoleOut(CamelModel):
    role: str
    users: int
    permissions: list[str]


class EntityOut(CamelModel):
    code: str
    name: str
    country: str
    currency: str
    owner: str


class AdminOut(CamelModel):
    users: list[UserOut]
    roles: list[RoleOut]
    entities: list[EntityOut]


class ScenarioOut(CamelModel):
    key: str
    label: str


class AskIn(CamelModel):
    prompt: str


class AssistIn(CamelModel):
    prompt: str
    history: list[dict[str, str]] = []
    page: str | None = None


class ChatMessageOut(CamelModel):
    role: str
    text: str
    refs: list[str] | None = None


class BatchOut(CamelModel):
    id: str
    source_id: str
    source: str
    file_name: str
    status: str
    rows_total: int
    rows_loaded: int
    rows_quarantined: int
    started_at: str | None
    duration_ms: int | None
    error: str | None


class QuarantineOut(CamelModel):
    line: int
    errors: list[str]
    raw: dict[str, str | None]


class BatchDetailOut(BatchOut):
    quarantined: list[QuarantineOut]
    issues: list[QualityIssueOut]


class TxnOut(CamelModel):
    id: str
    entity: str
    counterparty: str
    account: str | None
    amount: int | float
    currency: str
    amount_usd: int | float | None
    value_date: str
    reference: str | None
    description: str | None
    batch: str
    warnings: list[str]


class TxnPage(CamelModel):
    items: list[TxnOut]
    next_cursor: str | None
    total: int


class FxRateOut(CamelModel):
    date: str
    currency: str
    rate_to_usd: float
    source: str


class RunOut(CamelModel):
    id: str
    status: str
    scope: dict[str, str | None]
    engine_version: str
    rules: list[dict[str, object]]
    started_at: str | None
    duration_ms: int | None
    metrics: dict[str, object]
    error: str | None


class ProposalLineOut(CamelModel):
    id: str
    side: str
    entity: str
    counterparty: str
    amount: int | float
    currency: str
    amount_usd: int | float | None
    value_date: str
    reference: str | None
    description: str | None


class ProposalOut(CamelModel):
    id: str
    run: str
    type: str
    decision: str
    status: str
    confidence: float
    exposure_usd: int | float
    residual_usd: int | float
    entity_pair: str
    rules: list[str]
    explanation: dict[str, object]
    lines: list[ProposalLineOut]


class RunRequest(CamelModel):
    entity: str | None = None


class DecisionIn(CamelModel):
    reason: str | None = None
