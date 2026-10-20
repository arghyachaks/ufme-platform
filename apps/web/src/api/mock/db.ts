import type {
  AppUser, AuditEvent, CaseItem, ChatMessage, ControlTest, DataSource, ExceptionItem, Explanation, FeatureDef,
  GraphEdge, GraphNode, JobRun, LearningSignal, LegalEntity, LineageStep, MatchRule, ModelVersion, Policy,
  QualityIssue, RoleDef, ServiceHealth, SimulationResult, WorkflowStage,
} from "../types";

const owners = ["Priya Nair", "Daniel Ortiz", "Mei Chen", "Arjun Rao", "Sofia Rossi", "Unassigned"];
const entities = ["US01", "UK02", "DE03", "IN04", "SG05", "BR06"];
const counterparties = ["UK02", "DE03", "US01", "SG05", "IN04", "Acme Supplies", "Globex Bank", "Initech Ltd"];
const types: ExceptionItem["type"][] = ["Unmatched", "Amount variance", "Duplicate", "FX difference", "Timing", "Missing document"];
const causes = ["FX rate mismatch", "Posting period cut-off", "Partial payment", "Missing invoice ref", "Duplicate posting", "Bank fee deducted"];
const sev: ExceptionItem["severity"][] = ["Critical", "High", "Medium", "Low"];
const statuses: ExceptionItem["status"][] = ["New", "Investigating", "Escalated", "Resolved"];

export const exceptions: ExceptionItem[] = Array.from({ length: 24 }, (_, i) => {
  const severity = sev[(i * 7) % 4];
  return {
    id: `EX-${String(4821 + i)}`,
    entity: entities[i % entities.length],
    counterparty: counterparties[(i * 3) % counterparties.length],
    type: types[(i * 5) % types.length],
    amount: Math.round(((i * 7919) % 480000) + 1200 + (severity === "Critical" ? 650000 : 0)),
    currency: ["USD", "GBP", "EUR", "INR", "SGD"][i % 5],
    ageDays: (i * 3) % 34 + 1,
    severity,
    slaHoursLeft: ((i * 11) % 60) - 8,
    owner: owners[i % owners.length],
    rootCause: causes[(i * 2) % causes.length],
    status: statuses[(i * 3) % 4],
  };
});

export const cases: CaseItem[] = [
  { id: "CS-1042", title: "US01 ↔ UK02 intercompany loan variance", exceptionIds: ["EX-4821", "EX-4827"], entity: "US01", exposure: 1284000, priority: "Critical", status: "Escalated", assignee: "Priya Nair", dueIn: "6h", opened: "12 Aug",
    comments: [
      { author: "Priya Nair", at: "12 Aug 09:14", text: "Variance traced to FX revaluation posted on UK02 side only." },
      { author: "Daniel Ortiz", at: "12 Aug 15:40", text: "UK02 treasury confirms reval journal JE-77812. Requesting reversal." },
      { author: "ufme Assist", at: "13 Aug 08:02", text: "Similar pattern resolved in CS-0981 via reval true-up; suggested resolution drafted." },
    ] },
  { id: "CS-1041", title: "DE03 duplicate vendor payments — Acme Supplies", exceptionIds: ["EX-4823"], entity: "DE03", exposure: 312450, priority: "High", status: "In progress", assignee: "Mei Chen", dueIn: "1d", opened: "11 Aug",
    comments: [{ author: "Mei Chen", at: "11 Aug 11:20", text: "Two payments with same invoice ref, 2 days apart. Recall requested." }] },
  { id: "CS-1040", title: "IN04 bank fee deductions unmatched", exceptionIds: ["EX-4824", "EX-4830"], entity: "IN04", exposure: 18420, priority: "Medium", status: "Pending approval", assignee: "Arjun Rao", dueIn: "2d", opened: "10 Aug",
    comments: [{ author: "Arjun Rao", at: "10 Aug 16:05", text: "Proposing write-off to bank charges GL 6120 under materiality." }] },
  { id: "CS-1039", title: "SG05 cut-off timing — July accruals", exceptionIds: ["EX-4826"], entity: "SG05", exposure: 96200, priority: "Medium", status: "Open", assignee: "Unassigned", dueIn: "3d", opened: "10 Aug", comments: [] },
  { id: "CS-1038", title: "BR06 missing remittance documents", exceptionIds: ["EX-4831"], entity: "BR06", exposure: 54100, priority: "Low", status: "Open", assignee: "Sofia Rossi", dueIn: "5d", opened: "09 Aug", comments: [] },
  { id: "CS-1037", title: "UK02 partial settlement Globex Bank", exceptionIds: ["EX-4829"], entity: "UK02", exposure: 140000, priority: "High", status: "Closed", assignee: "Daniel Ortiz", dueIn: "—", opened: "05 Aug",
    comments: [{ author: "Daniel Ortiz", at: "08 Aug 10:00", text: "Matched 1:M against three settlements. Closed." }] },
];

export const rules: MatchRule[] = [
  { id: "R-001", name: "IC exact: reference + amount + date", kind: "Exact", scope: "Intercompany", conditions: ["ic_reference = ic_reference", "amount = amount", "value_date = value_date"], priority: 1, enabled: true, hitRate: 61.2, precision: 99.8, version: "v14", lastEdited: "02 Aug · Mei Chen" },
  { id: "R-002", name: "IC tolerance: amount ±0.5%, date ±3d", kind: "Tolerance", scope: "Intercompany", conditions: ["counterparty = entity", "|amount Δ| ≤ 0.5%", "|date Δ| ≤ 3 days"], tolerance: "0.5% / 3d", priority: 2, enabled: true, hitRate: 18.4, precision: 98.1, version: "v9", lastEdited: "29 Jul · Priya Nair" },
  { id: "R-003", name: "FX-adjusted amount match", kind: "Tolerance", scope: "Intercompany", conditions: ["amount_usd(rate=ECB) ≈ amount_usd", "|Δ| ≤ 25 USD"], tolerance: "25 USD", priority: 3, enabled: true, hitRate: 6.7, precision: 96.4, version: "v5", lastEdited: "21 Jul · Arjun Rao" },
  { id: "R-004", name: "Fuzzy reference (≤ 1 edit, OCR-canonical)", kind: "Fuzzy", scope: "AP / AR", conditions: ["edit_distance(canonical(reference)) ≤ 1", "|amount Δ| ≤ 0.1%", "|date Δ| ≤ 7 days"], priority: 4, enabled: true, hitRate: 4.1, precision: 93.0, version: "v3", lastEdited: "15 Jul · Mei Chen" },
  { id: "R-005", name: "Settlement aggregation (1:M up to 8)", kind: "Many-to-many", scope: "Bank", conditions: ["Σ amount(B) = amount(A)", "|B| ≤ 8", "window ≤ 10 days"], priority: 5, enabled: true, hitRate: 3.2, precision: 95.6, version: "v4", lastEdited: "10 Jul · Daniel Ortiz" },
  { id: "R-006", name: "Payroll batch net-to-gross", kind: "Many-to-many", scope: "Payroll", conditions: ["Σ net + Σ deductions = gross", "batch_id = batch_id"], priority: 6, enabled: false, hitRate: 0, precision: 0, version: "v1 draft", lastEdited: "08 Aug · Sofia Rossi" },
];

export const policies: Policy[] = [
  { id: "P-01", name: "Intercompany tolerance policy", category: "Tolerance", version: "3.2", status: "Published", owner: "Group Controller", effective: "01 Jul 2026", summary: "Auto-match allowed within 0.5% variance or 500 USD, whichever is lower.", thresholds: [{ label: "Variance %", value: "0.5%" }, { label: "Absolute cap", value: "500 USD" }, { label: "Date window", value: "±3 days" }] },
  { id: "P-02", name: "Approval matrix", category: "Approval", version: "2.0", status: "Published", owner: "CFO Office", effective: "01 Apr 2026", summary: "Manual matches and overrides route by exposure band.", thresholds: [{ label: "< 50K", value: "Manager" }, { label: "50K – 1M", value: "Controller" }, { label: "> 1M", value: "Finance Director" }] },
  { id: "P-03", name: "Segregation of duties", category: "Segregation of duties", version: "1.4", status: "Published", owner: "Internal Audit", effective: "01 Jan 2026", summary: "Preparer cannot approve own match; signoff requires a separate controller.", thresholds: [{ label: "Self-approval", value: "Blocked" }, { label: "Dual control > 1M", value: "Required" }] },
  { id: "P-04", name: "Materiality thresholds", category: "Materiality", version: "4.0 draft", status: "Draft", owner: "Group Controller", effective: "01 Oct 2026", summary: "Proposed tightening of materiality for APAC entities.", thresholds: [{ label: "Group", value: "250K USD" }, { label: "APAC entities", value: "100K USD" }] },
  { id: "P-05", name: "Evidence retention", category: "Retention", version: "1.1", status: "Published", owner: "Compliance", effective: "01 Jan 2025", summary: "Match evidence and audit logs retained 7 years, immutable.", thresholds: [{ label: "Retention", value: "7 years" }, { label: "Storage", value: "WORM" }] },
];

export const simulationResults: Record<string, SimulationResult> = {
  baseline: { scenario: "Current rules (v14)", dataset: "July 2026 IC actuals", matchRate: 91.4, baselineMatchRate: 91.4, falsePositives: 12, newMatches: 0, lostMatches: 0, exposureCleared: 0 },
  widen: { scenario: "Tolerance 0.5% → 1.0%", dataset: "July 2026 IC actuals", matchRate: 94.1, baselineMatchRate: 91.4, falsePositives: 41, newMatches: 1180, lostMatches: 0, exposureCleared: 2840000 },
  fx: { scenario: "Enable FX-adjusted v6", dataset: "July 2026 IC actuals", matchRate: 93.2, baselineMatchRate: 91.4, falsePositives: 15, newMatches: 760, lostMatches: 22, exposureCleared: 1920000 },
  payroll: { scenario: "Enable payroll net-to-gross", dataset: "Synthetic payroll Q2", matchRate: 88.7, baselineMatchRate: 72.3, falsePositives: 9, newMatches: 4300, lostMatches: 0, exposureCleared: 610000 },
};

export const workflowStages: WorkflowStage[] = [
  { name: "Auto-match", role: "Engine", slaHours: 0, condition: "confidence ≥ 0.97 and within tolerance policy" },
  { name: "Analyst review", role: "Analyst", slaHours: 24, condition: "0.80 ≤ confidence < 0.97", escalateTo: "Manager" },
  { name: "Manager approval", role: "Manager", slaHours: 24, condition: "manual match or exposure < 50K", escalateTo: "Controller" },
  { name: "Controller approval", role: "Controller", slaHours: 48, condition: "exposure 50K–1M or policy exception", escalateTo: "Finance Director" },
  { name: "Director approval", role: "Finance Director", slaHours: 48, condition: "exposure > 1M" },
  { name: "Period signoff", role: "Controller", slaHours: 72, condition: "all controls passed, residual < materiality" },
];

export const models: ModelVersion[] = [
  { name: "match-ranker", version: "2.4.1", stage: "Production", precision: 97.2, recall: 93.8, f1: 95.5, drift: 0.04, trainedOn: "1.8M labelled pairs", deployed: "28 Jul" },
  { name: "match-ranker", version: "2.5.0-rc", stage: "Shadow", precision: 97.9, recall: 94.6, f1: 96.2, drift: 0.02, trainedOn: "2.1M labelled pairs", deployed: "12 Aug" },
  { name: "reference-embedder", version: "1.3.0", stage: "Production", precision: 94.1, recall: 91.0, f1: 92.5, drift: 0.11, trainedOn: "Sentence-T5 fine-tune", deployed: "02 Jun" },
  { name: "anomaly-detector", version: "0.9.2", stage: "Staging", precision: 88.4, recall: 79.5, f1: 83.7, drift: 0.07, trainedOn: "Isolation forest, 6 months", deployed: "—" },
  { name: "match-ranker", version: "2.3.0", stage: "Archived", precision: 96.1, recall: 92.2, f1: 94.1, drift: 0.19, trainedOn: "1.4M labelled pairs", deployed: "03 May" },
];

export const modelTrend = { weeks: ["W27", "W28", "W29", "W30", "W31", "W32", "W33"], precision: [96.4, 96.7, 96.9, 97.0, 97.1, 97.3, 97.2], drift: [0.02, 0.02, 0.03, 0.03, 0.03, 0.04, 0.04] };

export const explanations: Explanation[] = [
  { matchId: "MT-20931", confidence: 0.94, decision: "Suggested 1:M — route to analyst review", rulesFired: ["R-002 IC tolerance", "R-005 Settlement aggregation"],
    contributions: [
      { feature: "Amount sum match", value: "Δ 0.12%", weight: 0.31 }, { feature: "Reference similarity", value: "0.96", weight: 0.22 },
      { feature: "Counterparty pairing", value: "US01 ↔ UK02", weight: 0.18 }, { feature: "Date proximity", value: "2 days", weight: 0.11 },
      { feature: "Historical pattern", value: "14 prior", weight: 0.08 }, { feature: "FX rate source mismatch", value: "ECB vs BoE", weight: -0.07 },
    ], counterfactual: "With matching FX source the confidence would rise to 0.98 and auto-match." },
  { matchId: "MT-20918", confidence: 0.71, decision: "Not matched — sent to exception queue", rulesFired: ["R-004 Fuzzy reference"],
    contributions: [
      { feature: "Reference similarity", value: "0.93", weight: 0.24 }, { feature: "Amount match", value: "Exact", weight: 0.2 },
      { feature: "Date proximity", value: "19 days", weight: -0.16 }, { feature: "Duplicate risk", value: "High", weight: -0.21 },
    ], counterfactual: "A posting within 5 days would raise confidence above the 0.80 review threshold." },
];

export const learningSignals: LearningSignal[] = [
  { id: "LS-9921", matchId: "MT-20931", analyst: "Priya Nair", action: "Accepted", modelScore: 0.94, reason: "Settlement split confirmed", at: "10:42" },
  { id: "LS-9920", matchId: "MT-20929", analyst: "Mei Chen", action: "Rejected", modelScore: 0.88, reason: "Different invoice despite same amount", at: "10:31" },
  { id: "LS-9919", matchId: "MT-20925", analyst: "Arjun Rao", action: "Overridden", modelScore: 0.62, reason: "Bank fee netted — manual 1:2", at: "10:12" },
  { id: "LS-9918", matchId: "MT-20922", analyst: "Daniel Ortiz", action: "Accepted", modelScore: 0.91, reason: "—", at: "09:58" },
  { id: "LS-9917", matchId: "MT-20918", analyst: "Sofia Rossi", action: "Rejected", modelScore: 0.71, reason: "Duplicate posting", at: "09:40" },
];

export const learningStats = { labelsThisWeek: 3842, acceptRate: 86.4, overrideRate: 4.9, nextRetrain: "Sun 20 Aug, 02:00 UTC", queuedForActiveLearning: 412 };

export const sources: DataSource[] = [
  { id: "SRC-01", name: "SAP S/4HANA — US/UK", system: "SAP", kind: "ERP", status: "Healthy", lastSync: "4 min ago", records24h: 182340, latencyMin: 4, schedule: "Every 15 min" },
  { id: "SRC-02", name: "Oracle EBS — DE/BR", system: "Oracle", kind: "ERP", status: "Degraded", lastSync: "52 min ago", records24h: 96210, latencyMin: 52, schedule: "Every 30 min" },
  { id: "SRC-03", name: "NetSuite — APAC", system: "NetSuite", kind: "ERP", status: "Healthy", lastSync: "9 min ago", records24h: 41880, latencyMin: 9, schedule: "Every 15 min" },
  { id: "SRC-04", name: "SWIFT MT940 statements", system: "SWIFT", kind: "Bank", status: "Healthy", lastSync: "1 h ago", records24h: 22740, latencyMin: 60, schedule: "Hourly" },
  { id: "SRC-05", name: "Payroll SFTP drop", system: "ADP", kind: "File", status: "Failed", lastSync: "Yesterday 22:00", records24h: 0, latencyMin: 760, schedule: "Daily 22:00" },
  { id: "SRC-06", name: "Treasury FX rates API", system: "ECB / Bloomberg", kind: "API", status: "Healthy", lastSync: "2 min ago", records24h: 1440, latencyMin: 2, schedule: "Every minute" },
  { id: "SRC-07", name: "Concur expenses", system: "SAP Concur", kind: "API", status: "Paused", lastSync: "05 Aug", records24h: 0, latencyMin: 0, schedule: "Paused" },
];

export const qualityIssues: QualityIssue[] = [
  { id: "DQ-311", source: "Oracle EBS — DE/BR", check: "Missing counterparty code", field: "ic_partner", failing: 1284, total: 96210, severity: "High", autoFixed: false },
  { id: "DQ-310", source: "SAP S/4HANA — US/UK", check: "Currency not ISO-4217", field: "currency", failing: 42, total: 182340, severity: "Medium", autoFixed: true },
  { id: "DQ-309", source: "SWIFT MT940 statements", check: "Duplicate statement lines", field: "line_ref", failing: 118, total: 22740, severity: "High", autoFixed: true },
  { id: "DQ-308", source: "NetSuite — APAC", check: "Future-dated posting", field: "posting_date", failing: 9, total: 41880, severity: "Low", autoFixed: false },
  { id: "DQ-307", source: "SAP S/4HANA — US/UK", check: "Reference contains whitespace/noise", field: "reference", failing: 6610, total: 182340, severity: "Low", autoFixed: true },
  { id: "DQ-306", source: "Payroll SFTP drop", check: "File schema mismatch", field: "*", failing: 1, total: 1, severity: "Critical", autoFixed: false },
];

export const qualityDimensions = [
  { label: "Completeness", score: 98.6 }, { label: "Validity", score: 97.1 }, { label: "Uniqueness", score: 99.4 },
  { label: "Timeliness", score: 91.8 }, { label: "Consistency", score: 95.2 },
];

export const lineage: Record<string, LineageStep[]> = {
  "TXN-US01-778120": [
    { stage: "Extracted", system: "SAP S/4HANA (BKPF/BSEG)", at: "17 Aug 08:01:12", detail: "Doc 1900077812, company code US01, 1,284,000.00 USD", status: "ok" },
    { stage: "Validated", system: "Data Quality", at: "17 Aug 08:01:14", detail: "12/12 checks passed", status: "ok" },
    { stage: "Normalized", system: "Normalization", at: "17 Aug 08:01:14", detail: "Reference cleaned: 'IC LOAN-UK02 /0817' → 'ICLOANUK020817'", status: "ok" },
    { stage: "Enriched", system: "Augmented Data", at: "17 Aug 08:01:15", detail: "FX → GBP 1,011,211 (ECB), counterparty resolved to UK02", status: "warn" },
    { stage: "Candidates", system: "Candidate Generation", at: "17 Aug 08:01:16", detail: "37 candidates (blocking on counterparty + amount band)", status: "ok" },
    { stage: "Rules", system: "Rule Engine v14", at: "17 Aug 08:01:16", detail: "R-002 tolerance fired on 3 candidates", status: "ok" },
    { stage: "Optimized", system: "OR-Tools solver", at: "17 Aug 08:01:17", detail: "Best 1:3 combination, residual 1,540 USD", status: "ok" },
    { stage: "Ranked", system: "match-ranker 2.4.1", at: "17 Aug 08:01:17", detail: "Confidence 0.94 → analyst review", status: "warn" },
    { stage: "Decision", system: "Workflow", at: "17 Aug 10:42:03", detail: "Accepted by Priya Nair · MT-20931", status: "ok" },
  ],
};

export const featureStore: FeatureDef[] = [
  { name: "amount_delta_pct", group: "Amount", type: "float", version: "v3", usedBy: ["Rules", "Smart ranking"], freshness: "Real-time", coverage: 100 },
  { name: "reference_similarity_jw", group: "Text", type: "float", version: "v2", usedBy: ["Rules", "Smart ranking"], freshness: "Real-time", coverage: 99.2 },
  { name: "reference_embedding_768", group: "Text", type: "vector", version: "v1.3", usedBy: ["Smart ranking"], freshness: "Real-time", coverage: 97.8 },
  { name: "date_delta_days", group: "Temporal", type: "int", version: "v1", usedBy: ["Rules", "Optimizer", "Smart ranking"], freshness: "Real-time", coverage: 100 },
  { name: "counterparty_pair_history", group: "Behavioral", type: "int", version: "v2", usedBy: ["Smart ranking"], freshness: "Hourly", coverage: 94.5 },
  { name: "fx_rate_source_mismatch", group: "FX", type: "bool", version: "v1", usedBy: ["Rules", "Smart ranking"], freshness: "Every minute", coverage: 100 },
  { name: "duplicate_risk_score", group: "Risk", type: "float", version: "v1", usedBy: ["Smart ranking", "Exceptions"], freshness: "Hourly", coverage: 98.1 },
];

export const auditEvents: AuditEvent[] = [
  { id: "AU-77120", at: "17 Aug 10:42:03", actor: "Priya Nair", action: "Accepted match", object: "MT-20931", entity: "US01", control: "IC-03" },
  { id: "AU-77119", at: "17 Aug 10:31:44", actor: "Mei Chen", action: "Rejected match", object: "MT-20929", entity: "DE03", control: "IC-03" },
  { id: "AU-77118", at: "17 Aug 10:12:09", actor: "Arjun Rao", action: "Created manual match", object: "MT-20925", entity: "IN04", control: "IC-05" },
  { id: "AU-77117", at: "17 Aug 09:20:51", actor: "System", action: "Published rule", object: "R-001 v14", entity: "All", control: "CHG-01" },
  { id: "AU-77116", at: "17 Aug 08:05:30", actor: "Daniel Ortiz", action: "Approved override", object: "AP-3381", entity: "UK02", control: "IC-07" },
  { id: "AU-77115", at: "16 Aug 18:44:02", actor: "Sofia Rossi", action: "Exported evidence", object: "Q2 SOX pack", entity: "BR06", control: "AUD-02" },
  { id: "AU-77114", at: "16 Aug 17:10:15", actor: "System", action: "Blocked self-approval", object: "AP-3379", entity: "SG05", control: "SOD-01" },
];

export const controlTests: ControlTest[] = [
  { id: "IC-03", name: "All IC matches reviewed or auto-matched within policy", owner: "Group Controller", lastRun: "17 Aug", result: "Pass", evidence: 18420 },
  { id: "IC-05", name: "Manual matches approved per matrix", owner: "Group Controller", lastRun: "17 Aug", result: "Pass", evidence: 342 },
  { id: "IC-07", name: "Overrides > 1M have dual approval", owner: "Internal Audit", lastRun: "17 Aug", result: "Fail", evidence: 12 },
  { id: "SOD-01", name: "No self-approval of matches", owner: "Internal Audit", lastRun: "17 Aug", result: "Pass", evidence: 2930 },
  { id: "CHG-01", name: "Rule changes approved before publish", owner: "IT Controls", lastRun: "16 Aug", result: "Pass", evidence: 14 },
  { id: "AUD-02", name: "Evidence retained immutably", owner: "Compliance", lastRun: "Pending", result: "Pending", evidence: 0 },
];

export const users: AppUser[] = [
  { name: "Priya Nair", email: "priya.nair@example.com", role: "Analyst", entities: ["US01", "UK02"], status: "Active", mfa: true, lastLogin: "Today 08:40" },
  { name: "Mei Chen", email: "mei.chen@example.com", role: "Analyst", entities: ["DE03"], status: "Active", mfa: true, lastLogin: "Today 09:02" },
  { name: "Daniel Ortiz", email: "daniel.ortiz@example.com", role: "Controller", entities: ["US01", "UK02", "DE03"], status: "Active", mfa: true, lastLogin: "Today 07:55" },
  { name: "Arjun Rao", email: "arjun.rao@example.com", role: "Manager", entities: ["IN04", "SG05"], status: "Active", mfa: true, lastLogin: "Yesterday" },
  { name: "Sofia Rossi", email: "sofia.rossi@example.com", role: "Auditor", entities: ["All"], status: "Active", mfa: false, lastLogin: "3 days ago" },
  { name: "Liam Walsh", email: "liam.walsh@example.com", role: "Finance Director", entities: ["All"], status: "Invited", mfa: false, lastLogin: "—" },
  { name: "Tom Becker", email: "tom.becker@example.com", role: "Analyst", entities: ["DE03"], status: "Disabled", mfa: true, lastLogin: "02 Jun" },
];

export const roles: RoleDef[] = [
  { role: "Analyst", users: 18, permissions: ["Review matches", "Create manual match", "Open cases"] },
  { role: "Manager", users: 6, permissions: ["Approve < 50K", "Assign cases", "Review matches"] },
  { role: "Controller", users: 4, permissions: ["Approve ≤ 1M", "Publish rules", "Sign off period"] },
  { role: "Finance Director", users: 2, permissions: ["Approve all", "Final signoff"] },
  { role: "Auditor", users: 3, permissions: ["Read all", "Export evidence"] },
  { role: "Admin", users: 2, permissions: ["Manage users", "Configure tenant", "Manage connectors"] },
];

export const legalEntities: LegalEntity[] = [
  { code: "US01", name: "UFME Demo Holdings Inc.", country: "United States", currency: "USD", owner: "Daniel Ortiz" },
  { code: "UK02", name: "UFME Demo UK Ltd", country: "United Kingdom", currency: "GBP", owner: "Daniel Ortiz" },
  { code: "DE03", name: "UFME Demo GmbH", country: "Germany", currency: "EUR", owner: "Mei Chen" },
  { code: "IN04", name: "UFME Demo India Pvt Ltd", country: "India", currency: "INR", owner: "Arjun Rao" },
  { code: "SG05", name: "UFME Demo Asia Pte Ltd", country: "Singapore", currency: "SGD", owner: "Arjun Rao" },
  { code: "BR06", name: "UFME Demo Brasil Ltda", country: "Brazil", currency: "BRL", owner: "Sofia Rossi" },
];

export const services: ServiceHealth[] = [
  { name: "api-gateway", status: "ok", latencyMs: 38, cpu: 41, memory: 52, replicas: "4/4", uptime: "99.99%" },
  { name: "matching-engine", status: "ok", latencyMs: 212, cpu: 73, memory: 68, replicas: "8/8", uptime: "99.97%" },
  { name: "optimizer (OR-Tools)", status: "warn", latencyMs: 1840, cpu: 91, memory: 77, replicas: "3/4", uptime: "99.82%" },
  { name: "ranker-inference", status: "ok", latencyMs: 64, cpu: 55, memory: 61, replicas: "4/4", uptime: "99.98%" },
  { name: "connector-workers", status: "warn", latencyMs: 0, cpu: 38, memory: 44, replicas: "6/6", uptime: "99.90%" },
  { name: "postgres-primary", status: "ok", latencyMs: 4, cpu: 47, memory: 71, replicas: "1+2", uptime: "100%" },
  { name: "kafka", status: "ok", latencyMs: 6, cpu: 33, memory: 58, replicas: "3/3", uptime: "100%" },
];

export const jobs: JobRun[] = [
  { id: "JOB-88412", job: "IC match run · US01↔UK02", status: "Running", started: "10:58", duration: "6m", records: 184000 },
  { id: "JOB-88411", job: "Oracle EBS ingest", status: "Succeeded", started: "10:30", duration: "21m", records: 96210 },
  { id: "JOB-88410", job: "Payroll SFTP ingest", status: "Failed", started: "22:00 yest.", duration: "1m", records: 0 },
  { id: "JOB-88409", job: "Feature store refresh", status: "Succeeded", started: "10:00", duration: "4m", records: 412000 },
  { id: "JOB-88408", job: "Nightly evidence archive", status: "Queued", started: "—", duration: "—", records: 0 },
];

export const graphNodes: GraphNode[] = [
  { id: "US01", label: "US01", kind: "Entity", x: 300, y: 180, risk: "warn" },
  { id: "UK02", label: "UK02", kind: "Entity", x: 520, y: 110, risk: "crit" },
  { id: "DE03", label: "DE03", kind: "Entity", x: 540, y: 290, risk: "ok" },
  { id: "IN04", label: "IN04", kind: "Entity", x: 120, y: 300, risk: "ok" },
  { id: "ACME", label: "Acme Supplies", kind: "Counterparty", x: 720, y: 330, risk: "warn" },
  { id: "GLOBEX", label: "Globex Bank", kind: "Counterparty", x: 110, y: 90, risk: "ok" },
  { id: "ACC-1910", label: "IC Receivable 1910", kind: "Account", x: 310, y: 40, risk: "ok" },
  { id: "TXN-1", label: "TXN 1.28M", kind: "Transaction", x: 420, y: 230, risk: "warn" },
  { id: "CS-1042", label: "CS-1042", kind: "Case", x: 700, y: 170, risk: "crit" },
];
export const graphEdges: GraphEdge[] = [
  { from: "US01", to: "UK02", label: "IC loan" }, { from: "US01", to: "DE03", label: "IC service" }, { from: "US01", to: "IN04", label: "IC royalty" },
  { from: "DE03", to: "ACME", label: "vendor" }, { from: "US01", to: "GLOBEX", label: "bank" }, { from: "US01", to: "ACC-1910", label: "posts to" },
  { from: "US01", to: "TXN-1", label: "originates" }, { from: "TXN-1", to: "UK02", label: "settles" }, { from: "UK02", to: "CS-1042", label: "exception" },
];

export const copilotSeed: ChatMessage[] = [
  { role: "assistant", text: "Morning! 412 open exceptions, 6 breaching SLA today. Largest exposure is CS-1042 (US01 ↔ UK02, 1.28M USD). Want a summary or a suggested resolution?" },
];

export const copilotPrompts = [
  "Summarize CS-1042",
  "Why didn't MT-20918 auto-match?",
  "Which entities are blocking close?",
  "Draft an email to UK02 treasury",
];

export function copilotAnswer(prompt: string): ChatMessage {
  const p = prompt.toLowerCase();
  if (p.includes("1042") || p.includes("summar"))
    return { role: "assistant", text: "CS-1042: a 1.28M USD IC loan variance between US01 and UK02. Root cause is an FX revaluation journal (JE-77812) posted only on UK02. Recommended: reverse JE-77812 or post a matching reval on US01, then rerun R-002. Expected to clear 2 linked exceptions.", refs: ["CS-1042", "JE-77812", "R-002"] };
  if (p.includes("20918") || p.includes("why"))
    return { role: "assistant", text: "MT-20918 scored 0.71, below the 0.80 review threshold. Reference similarity was high (0.93) but the 19-day date gap and a high duplicate-risk score pulled confidence down. It was routed to the exception queue.", refs: ["MT-20918", "R-004"] };
  if (p.includes("close") || p.includes("block"))
    return { role: "assistant", text: "UK02 and DE03 are blocking close: UK02 has the 1.28M escalated case and control IC-07 is failing; DE03 has 312K of duplicate vendor payments pending recall. Close readiness is 87%.", refs: ["UK02", "DE03", "IC-07"] };
  if (p.includes("email") || p.includes("draft"))
    return { role: "assistant", text: "Draft:\n\nHi UK02 Treasury, our August IC reconciliation shows a 1,284,000 USD variance with US01 caused by revaluation journal JE-77812, which has no counterpart in US01. Could you confirm whether it should be reversed or mirrored by 18 Aug? Thanks.", refs: ["JE-77812"] };
  return { role: "assistant", text: "I can summarize cases, explain match decisions, check close readiness, and draft counterparty emails. Try one of the suggested prompts.", refs: [] };
}
