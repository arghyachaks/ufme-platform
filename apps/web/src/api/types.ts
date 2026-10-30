// Domain types shared by the mock API and (later) the real FastAPI backend.
export type Tone = "ok" | "warn" | "crit";
export type Severity = "Critical" | "High" | "Medium" | "Low";

export type Kpi = { label: string; value: string; hint?: string; tone?: Tone };

export type ExceptionItem = {
  id: string;
  entity: string;
  counterparty: string;
  type: "Unmatched" | "Amount variance" | "Duplicate" | "FX difference" | "Timing" | "Missing document";
  amount: number;
  currency: string;
  ageDays: number;
  severity: Severity;
  slaHoursLeft: number;
  owner: string;
  rootCause: string;
  status: "New" | "Investigating" | "Escalated" | "Resolved";
};

export type CaseComment = { author: string; at: string; text: string };
export type CaseItem = {
  id: string;
  title: string;
  exceptionIds: string[];
  entity: string;
  exposure: number;
  priority: Severity;
  status: "Open" | "In progress" | "Pending approval" | "Escalated" | "Closed";
  assignee: string;
  dueIn: string;
  opened: string;
  comments: CaseComment[];
};

export type MatchRule = {
  id: string;
  name: string;
  kind: "Exact" | "Tolerance" | "Fuzzy" | "Many-to-many";
  scope: string;
  conditions: string[];
  tolerance?: string;
  priority: number;
  enabled: boolean;
  hitRate: number;
  precision: number;
  version: string;
  lastEdited: string;
};

export type Policy = {
  id: string;
  name: string;
  category: "Tolerance" | "Approval" | "Segregation of duties" | "Materiality" | "Retention";
  version: string;
  status: "Published" | "Draft" | "Retired";
  owner: string;
  effective: string;
  summary: string;
  thresholds: { label: string; value: string }[];
};

export type SimulationResult = {
  scenario: string;
  dataset: string;
  matchRate: number;
  baselineMatchRate: number;
  falsePositives: number;
  newMatches: number;
  lostMatches: number;
  exposureCleared: number;
};

export type WorkflowStage = { name: string; role: string; slaHours: number; condition: string; escalateTo?: string };

export type ModelVersion = {
  name: string;
  version: string;
  stage: "Production" | "Shadow" | "Staging" | "Archived";
  precision: number;
  recall: number;
  f1: number;
  drift: number;
  trainedOn: string;
  deployed: string;
};

export type FeatureContribution = { feature: string; value: string; weight: number };
export type Explanation = {
  matchId: string;
  confidence: number;
  decision: string;
  rulesFired: string[];
  contributions: FeatureContribution[];
  counterfactual: string;
};

export type LearningSignal = {
  id: string;
  matchId: string;
  analyst: string;
  action: "Accepted" | "Rejected" | "Overridden";
  modelScore: number;
  reason: string;
  at: string;
};

export type DataSource = {
  id: string;
  name: string;
  system: string;
  kind: "ERP" | "Bank" | "File" | "API";
  status: "Healthy" | "Degraded" | "Failed" | "Paused";
  lastSync: string;
  records24h: number;
  latencyMin: number;
  schedule: string;
};

export type QualityIssue = {
  id: string;
  source: string;
  check: string;
  field: string;
  failing: number;
  total: number;
  severity: Severity;
  autoFixed: boolean;
};

export type LineageStep = { stage: string; system: string; at: string; detail: string; status: Tone };

export type FeatureDef = {
  name: string;
  group: string;
  type: string;
  version: string;
  usedBy: string[];
  freshness: string;
  coverage: number;
};

export type AuditEvent = {
  id: string;
  at: string;
  actor: string;
  action: string;
  object: string;
  entity: string;
  control: string;
};

export type ControlTest = { id: string; name: string; owner: string; lastRun: string; result: "Pass" | "Fail" | "Pending"; evidence: number };

export type AppUser = { name: string; email: string; role: string; entities: string[]; status: "Active" | "Invited" | "Disabled"; mfa: boolean; lastLogin: string };
export type RoleDef = { role: string; users: number; permissions: string[] };
export type LegalEntity = { code: string; name: string; country: string; currency: string; owner: string };

export type ServiceHealth = { name: string; status: Tone; latencyMs: number; cpu: number; memory: number; replicas: string; uptime: string };
export type JobRun = { id: string; job: string; status: "Running" | "Succeeded" | "Failed" | "Queued"; started: string; duration: string; records: number };

export type GraphNode = { id: string; label: string; kind: "Entity" | "Counterparty" | "Account" | "Transaction" | "Case"; x: number; y: number; risk?: Tone };
export type GraphEdge = { from: string; to: string; label: string };

export type ChatMessage = { role: "user" | "assistant"; text: string; refs?: string[] };

export type IngestionBatch = {
  id: string;
  sourceId: string;
  source: string;
  fileName: string;
  status: "Queued" | "Processing" | "Completed" | "Failed";
  rowsTotal: number;
  rowsLoaded: number;
  rowsQuarantined: number;
  startedAt: string | null;
  durationMs: number | null;
  error: string | null;
};

export type BatchDetail = IngestionBatch & {
  quarantined: { line: number; errors: string[]; raw: Record<string, string | null> }[];
  issues: QualityIssue[];
};

export type MatchRunInfo = {
  id: string;
  status: "Queued" | "Running" | "Completed" | "Failed";
  scope: Record<string, string | null>;
  engineVersion: string;
  rules: { id: string; name: string; priority: number }[];
  startedAt: string | null;
  durationMs: number | null;
  metrics: Record<string, unknown>;
  error: string | null;
};

export type MatchProposal = {
  id: string;
  run: string;
  type: string;
  decision: "auto" | "suggest";
  status: "matched" | "proposed" | "accepted" | "rejected" | "superseded";
  confidence: number;
  exposureUsd: number;
  residualUsd: number;
  entityPair: string;
  rules: string[];
  explanation: Record<string, unknown>;
  lines: { id: string; side: "A" | "B"; entity: string; counterparty: string; amount: number; currency: string; amountUsd: number | null; valueDate: string; reference: string | null; description: string | null }[];
};

// ---------------------------------------------------------------- Stage 4 workflow

export type Actor = { email: string; name: string; role: string; entities: string[] };

export type Approval = {
  id: string;
  matchId: string;
  kind: "review" | "manual";
  submittedBy: string;
  entity: string;
  exposure: string;
  exposureUsd: number;
  materiality: "High" | "Medium" | "Low";
  confidence: string;
  date: string;
  stage: string;
  sla: string;
  slaOverdue: boolean;
  exceptionOpen: boolean;
  rationale: string;
  documents: string[];
  trail: string[];
  confidenceFactors: { label: string; weight: number }[];
  status: "Pending" | "Info requested" | "Approved" | "Rejected";
  approvals: { name: string; role: string; at: string }[];
  approvalsNeeded: number;
};

export type ManualMatchResult = { matchId: string; approvalId: string; type: string; varianceUsd: number; stage: string };

export type SignoffState = {
  entity: string;
  period: string;
  status: string;
  signatures: { actor: string; name: string; role: string; step: string; at: string }[];
  openExceptions: number;
  criticalExceptions: number;
  pendingApprovals: number;
  failingControls: string[];
  checklist: { label: string; done: boolean }[];
  readiness: number;
  blockers: string[];
  ready: boolean;
  nextSigner: string | null;
};

export type UnmatchedTxn = {
  id: string;
  invoice: string;
  amount: number;
  date: string;
  entity: string;
  attachments: string[];
  exceptionRisk?: string;
  currency?: string;
  originalAmount?: number;
  originalCurrency?: string;
  description?: string;
};
export type UnmatchedSet = { pair: string | null; sideA: UnmatchedTxn[]; sideB: UnmatchedTxn[] };

/* ---------------- Stage 3f: learning loop ---------------- */

export type GateCheck = { name: string; ok: boolean; detail: string };
export type HoldoutMetrics = {
  labels: number;
  positives?: number;
  log_loss?: number;
  accuracy?: number;
  would_auto_correct?: number;
  would_auto_wrong?: number;
};
export type GoldenDelta = {
  before: { auto_rate: number; precision: number; ece: number | null };
  after: { auto_rate: number; precision: number; ece: number | null };
};
export type ScorerModelInfo = {
  version: string;
  status: "training" | "candidate" | "active" | "retired" | "rejected" | "failed" | "rolled_back";
  base: string;
  labels: number;
  trainedBy: string;
  trainedAt: string | null;
  promotedBy: string | null;
  promotedAt: string | null;
  autoThreshold: number | null;
  seconds: number | null;
  holdout: HoldoutMetrics | null;
  gate: {
    passed?: boolean;
    checks?: GateCheck[];
    holdout?: { candidate: HoldoutMetrics; active: HoldoutMetrics | null };
    golden?: Record<string, GoldenDelta>;
    shadow?: { run: string | null; suggestions?: number; would_auto_match?: number; would_auto_match_active?: number };
  };
  error: string | null;
};
export type DriftReport = {
  status: "ok" | "watch" | "alert" | "unknown";
  max_psi?: number;
  feature?: string;
  top?: Record<string, number>;
  pairs?: number;
  reason?: string;
};
export type OutcomeDrift = {
  status: "ok" | "watch" | "alert" | "unknown";
  decisions: number;
  expected_accept_rate?: number;
  actual_accept_rate?: number;
  gap?: number;
};
export type LearningDecision = {
  at: string | null;
  match: string;
  actor: string;
  outcome: "Accepted" | "Rejected";
  source: string | null;
  modelScore: number;
  reason: string | null;
};
export type LearningStatus = {
  active: string;
  activeIsShipped: boolean;
  labels: {
    total: number;
    usable: number;
    accepted: number;
    rejected: number;
    bySource: Record<string, number>;
    sinceActive: number;
    minimum: number;
  };
  canTrain: boolean;
  models: ScorerModelInfo[];
  recent: LearningDecision[];
  drift: { run: string | null; features: DriftReport | null; outcomes: OutcomeDrift };
};

// ---- Agent harness (ufme Assist and future agents): the live event stream and the operations views
export type AgentTodo = { content: string; status: "pending" | "in_progress" | "completed" };
export type AgentEvent =
  | { type: "run"; id: string; agent: string; model: string; provider: string; local: boolean }
  | { type: "thinking"; text: string; agent?: string }
  | { type: "todos"; items: AgentTodo[] }
  | { type: "task"; id: string; name?: string; args?: Record<string, unknown>; agent?: string; status: "running" | "done" | "error"; summary?: string }
  | { type: "subagent"; id: string; kind?: string; brief?: string; status: "running" | "done" | "error"; summary?: string }
  | { type: "token"; msg: string | null; text: string }
  | { type: "step"; msg: string | null }
  | { type: "answer"; text: string }
  | { type: "usage"; tokensIn: number; tokensOut: number; costUsd: number; toolCalls: number; subagents: number; ms: number; model: string }
  | { type: "error"; message: string }
  | { type: "done"; source: string };

export type AgentRunRow = {
  id: string; agent: string; actor: string; question: string; model: string; provider: string;
  status: "running" | "completed" | "failed" | "fallback" | "cancelled"; startedAt: string; ms: number | null;
  tokensIn: number; tokensOut: number; costUsd: number; toolCalls: number; subagents: number; egress: boolean; error: string | null;
};
export type AgentModel = {
  name: string; provider: string; model: string; status: string; local: boolean; priceIn: number; priceOut: number;
  allowsConfidential: boolean; keyConfigured: boolean | null; bindings?: string[];
};
export type AgentAnomaly = { kind: string; severity: "High" | "Medium" | "Low"; detail: string; run?: string };
export type AgentOverview = {
  scope: "tenant" | "mine";
  days: number;
  totals: { runs: number; completed: number; fallback: number; failed: number; tokensIn: number; tokensOut: number; costUsd: number; toolCalls: number; subagents: number; avgMs: number | null; egressRuns: number };
  byModel: { model: string; provider: string; runs: number; tokens: number; costUsd: number }[];
  byUser: { actor: string; runs: number; tokens: number; costUsd: number }[];
  byDay: { day: string; runs: number; tokens: number }[];
  anomalies: AgentAnomaly[];
  infosec: { egressByProvider: Record<string, number>; localOnly: boolean; hostedModelsApproved: string[]; writeTools: number; autonomousActions: number };
  models: AgentModel[];
  recent: AgentRunRow[];
};
export type AgentRunDetail = AgentRunRow & { events: AgentEvent[] };
