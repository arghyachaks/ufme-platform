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
