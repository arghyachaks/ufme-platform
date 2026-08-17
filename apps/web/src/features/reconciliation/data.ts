export const reconContext = {
  period: "Q3 2026",
  entity: "APAC",
  type: "Intercompany",
};

export const runKpis = [
  { label: "Total Transactions", value: "2.41M" },
  { label: "Matched", value: "2.36M" },
  { label: "Pending", value: "28.4k" },
  { label: "Exceptions", value: "18.2k" },
  { label: "Financial Exposure", value: "$210M" },
  { label: "Auto Match Rate", value: "97.4%" },
  { label: "Open Exposure %", value: "2.6%" },
];

export const runTrends = {
  matchRate: [96.1, 96.8, 97.0, 96.4, 97.2, 97.6, 97.4],
  exposure: [280, 265, 240, 255, 230, 218, 210],
  exceptions: [24, 22, 21, 23, 20, 19, 18],
};

export const trendDays = ["11 Aug", "12 Aug", "13 Aug", "14 Aug", "15 Aug", "16 Aug", "17 Aug"];

export const runs = [
  {
    id: "IC-2026-08-17",
    type: "Intercompany",
    entity: "APAC",
    period: "Q3 2026",
    status: "Review Required",
    progress: 100,
    matchRate: "97.4%",
    exposure: "$210M",
    exposureValue: 210,
    materiality: "High",
    start: "08:12",
    duration: "11m",
    ruleVersion: "rules-v3.4",
    modelVersion: "ranker-v4.8",
    dataSource: "SAP ECC APAC + Oracle GL US01",
    transactionsProcessed: "2.41M",
    rulesExecuted: ["INV_REF_EXACT", "AMT_TOL_0.5", "DATE_WIN_3"],
    runtimeBreakdown: [
      { step: "Ingest", time: "2.1m" },
      { step: "Rules", time: "6.4m" },
      { step: "AI rank", time: "2.5m" },
    ],
    exceptionSummary: "18.2k open · $210M exposure",
  },
  {
    id: "IC-2026-08-16",
    type: "Intercompany",
    entity: "EMEA",
    period: "Q3 2026",
    status: "Completed",
    progress: 100,
    matchRate: "98.9%",
    exposure: "$400M",
    exposureValue: 400,
    materiality: "High",
    start: "07:04",
    duration: "9m",
    ruleVersion: "rules-v3.4",
    modelVersion: "ranker-v4.8",
    dataSource: "SAP EMEA + Oracle GL US01",
    transactionsProcessed: "1.12M",
    rulesExecuted: ["INV_REF_EXACT", "AMT_TOL_0.5"],
    runtimeBreakdown: [
      { step: "Ingest", time: "1.8m" },
      { step: "Rules", time: "5.1m" },
      { step: "AI rank", time: "2.1m" },
    ],
    exceptionSummary: "6.4k open · $400M exposure",
  },
  {
    id: "BNK-2026-08-16",
    type: "Bank to GL",
    entity: "NAMER",
    period: "Q3 2026",
    status: "Running",
    progress: 46,
    matchRate: "—",
    exposure: "$88M",
    exposureValue: 88,
    materiality: "Medium",
    start: "08:31",
    duration: "3m",
    ruleVersion: "rules-v3.3",
    modelVersion: "ranker-v4.7",
    dataSource: "JPM bank file + NAMER GL",
    transactionsProcessed: "410k / 890k",
    rulesExecuted: ["STMT_REF", "AMT_EXACT"],
    runtimeBreakdown: [
      { step: "Ingest", time: "1.2m" },
      { step: "Rules", time: "1.4m" },
      { step: "AI rank", time: "in progress" },
    ],
    exceptionSummary: "Pending until run completes",
  },
  {
    id: "IC-2026-08-14",
    type: "Intercompany",
    entity: "APAC",
    period: "Q3 2026",
    status: "Failed",
    progress: 22,
    matchRate: "—",
    exposure: "$12M",
    exposureValue: 12,
    materiality: "Low",
    start: "05:10",
    duration: "2m",
    ruleVersion: "rules-v3.4",
    modelVersion: "ranker-v4.8",
    dataSource: "SAP ECC APAC",
    transactionsProcessed: "88k / 2.4M",
    rulesExecuted: ["INV_REF_EXACT"],
    runtimeBreakdown: [
      { step: "Ingest", time: "1.1m" },
      { step: "Rules", time: "failed" },
      { step: "AI rank", time: "—" },
    ],
    exceptionSummary: "Source file checksum mismatch",
  },
  {
    id: "IC-2026-08-15",
    type: "Intercompany",
    entity: "APAC",
    period: "Q3 2026",
    status: "Completed",
    progress: 100,
    matchRate: "99.1%",
    exposure: "$18M",
    exposureValue: 18,
    materiality: "Low",
    start: "06:50",
    duration: "12m",
    ruleVersion: "rules-v3.3",
    modelVersion: "ranker-v4.7",
    dataSource: "SAP ECC APAC + Oracle GL US01",
    transactionsProcessed: "1.98M",
    rulesExecuted: ["INV_REF_EXACT", "AMT_TOL_0.5", "DATE_WIN_3"],
    runtimeBreakdown: [
      { step: "Ingest", time: "2.4m" },
      { step: "Rules", time: "7.0m" },
      { step: "AI rank", time: "2.6m" },
    ],
    exceptionSummary: "1.1k open · $18M exposure",
  },
];

export const sideA = [
  {
    id: "INV-4412",
    invoice: "SG-4412",
    reference: "PO-8891",
    amount: 128400,
    currency: "USD",
    date: "12 Aug",
    entity: "APAC E09",
    counterparty: "US01 HQ",
    businessUnit: "Intercompany AR",
    description: "Intercompany AR invoice after ERP SG- prefix patch",
    slaRemaining: "12h remaining",
    status: "Suggested",
    attachments: ["SG-4412.pdf"],
  },
  {
    id: "INV-4418",
    invoice: "SG-4418",
    reference: "PO-8898",
    amount: 64200,
    currency: "USD",
    date: "12 Aug",
    entity: "APAC E09",
    counterparty: "US01 HQ",
    businessUnit: "Intercompany AR",
    description: "Related invoice in same APAC batch",
    slaRemaining: "12h remaining",
    status: "Suggested",
    attachments: ["SG-4418.pdf"],
  },
  {
    id: "INV-4501",
    invoice: "SG-4501",
    reference: "PO-9011",
    amount: 91050,
    currency: "USD",
    date: "13 Aug",
    entity: "APAC E09",
    counterparty: "US01 HQ",
    businessUnit: "Intercompany AR",
    description: "Likely 1:M split against GL-8902 / GL-8903",
    slaRemaining: "6h remaining",
    status: "Unmatched",
    attachments: ["SG-4501.pdf"],
  },
  {
    id: "INV-4510",
    invoice: "SG-4510",
    reference: "PO-9020",
    amount: 22000,
    currency: "USD",
    date: "13 Aug",
    entity: "APAC E09",
    counterparty: "US01 HQ",
    businessUnit: "Intercompany AR",
    description: "Low-value residual",
    slaRemaining: "18h remaining",
    status: "Unmatched",
    attachments: [],
  },
  ...Array.from({ length: 12 }, (_, index) => ({
    id: `INV-${4600 + index}`,
    invoice: `SG-${4600 + index}`,
    reference: `PO-${9100 + index}`,
    amount: 15000 + index * 1250,
    currency: "USD",
    date: "14 Aug",
    entity: "APAC E09",
    counterparty: "US01 HQ",
    businessUnit: "Intercompany AR",
    description: "Queued suggested match from overnight ranker",
    slaRemaining: "20h remaining",
    status: "Suggested",
    attachments: [`SG-${4600 + index}.pdf`],
  })),
];

export const sideB = [
  { id: "GL-8821", invoice: "4412", amount: 128400, date: "12 Aug", entity: "US01 HQ", score: 99.4, status: "Candidate" },
  { id: "GL-8830", invoice: "4418", amount: 64180, date: "13 Aug", entity: "US01 HQ", score: 97.1, status: "Candidate" },
  { id: "GL-8902", invoice: "4501-A", amount: 45525, date: "14 Aug", entity: "US01 HQ", score: 88.2, status: "Candidate" },
  { id: "GL-8903", invoice: "4501-B", amount: 45525, date: "14 Aug", entity: "US01 HQ", score: 88.0, status: "Candidate" },
];

export const suggestedMatch = {
  type: "1:1",
  confidence: "98.4%",
  amountImpact: "$128,400",
  materiality: "Medium",
  risk: "Low",
  rule: "INV_REF_EXACT + AMT_TOL_0.5",
  ruleVersion: "rules-v3.4",
  decision: "Approve",
  exposureReduction: "$128,400",
  similarCases: ["IC-2026-08-12 / SG-3301", "IC-2026-08-11 / SG-3188", "IC-2026-08-09 / SG-3012"],
  history: ["12 Aug auto-suggested", "12 Aug similar case approved by Analyst_APAC", "Rule v3.4 accepted 1,842 times this quarter"],
  comments: ["Need to confirm SG- prefix policy with APAC lead."],
  why: [
    "Amount similarity 100%",
    "Reference similarity 96% after SG- prefix strip",
    "Date variance 0 days",
    "Entity relationship: APAC E09 ↔ US01 HQ (intercompany)",
    "Rule history: accepted 1,842 times this quarter",
  ],
  historical: "14 similar APAC invoices auto-matched this week at 99.1% precision",
  slaRemaining: "12h remaining",
  queueSize: 148,
  confidenceBreakdown: [
    { label: "Amount", weight: 35 },
    { label: "Reference", weight: 30 },
    { label: "Date", weight: 15 },
    { label: "History", weight: 10 },
    { label: "Rule", weight: 10 },
  ],
  similarAnalytics: [
    { label: "Approved", value: 11 },
    { label: "Rejected", value: 2 },
    { label: "Escalated", value: 1 },
  ],
  approvalRateTrend: [94, 95, 96, 95, 97, 98, 99],
};

export const advisorMetrics = {
  exposureReduction: "$128,400",
  matchImprovement: "+1.2 pts",
  autoMatchGain: "+$210M",
};

export const aiRecoCard = {
  title: "Apply SG- prefix strip rule",
  confidence: "98.4%",
  impact: "+$210M auto-match",
  executionTime: "18 sec",
  detail: "Vendor X prepended SG- after an ERP patch. One-click execute will re-run APAC intercompany candidates.",
};

export const unmatchedA = [
  { id: "INV-4501", invoice: "SG-4501", amount: 91050, date: "13 Aug", entity: "APAC E09", attachments: ["SG-4501.pdf", "PO-9011.pdf"], exceptionRisk: "High" },
  { id: "INV-4510", invoice: "SG-4510", amount: 22000, date: "13 Aug", entity: "APAC E09", attachments: ["SG-4510.pdf"], exceptionRisk: "Low" },
  { id: "INV-4522", invoice: "SG-4522", amount: 17800, date: "14 Aug", entity: "APAC E09", attachments: ["SG-4522.pdf", "Journal J-882.pdf"], exceptionRisk: "Medium" },
];

export const unmatchedB = [
  { id: "GL-8902", invoice: "4501-A", amount: 45525, date: "14 Aug", entity: "US01 HQ", attachments: ["GL extract 14 Aug.csv"], exceptionRisk: "High" },
  { id: "GL-8903", invoice: "4501-B", amount: 45525, date: "14 Aug", entity: "US01 HQ", attachments: ["GL extract 14 Aug.csv"], exceptionRisk: "High" },
  { id: "GL-8910", invoice: "4510", amount: 22000, date: "14 Aug", entity: "US01 HQ", attachments: ["GL extract 14 Aug.csv"], exceptionRisk: "Low" },
];

export const manualSuggestWhy = [
  "Amount similarity 100% after 1:M split of $91,050",
  "Reference similarity 94% after SG- prefix strip",
  "Historical pattern: 14 APAC split invoices approved this week",
];

export const matchTolerancePolicy = 0.005;

export const approvalKpis = [
  { label: "Pending Approval", value: "15" },
  { label: "High Risk", value: "4" },
  { label: "SLA Breached", value: "2" },
  { label: "Exposure Awaiting", value: "$64.2M" },
];

export const approvalHierarchy = ["Analyst", "Manager", "Controller", "Director"];

export const approvals = [
  {
    id: "MT-9004",
    submittedBy: "Analyst_APAC",
    entity: "APAC E09",
    exposure: "$6.1M",
    materiality: "Medium",
    confidence: "92.1%",
    date: "16 Aug",
    stage: "Controller",
    sla: "4h remaining",
    slaOverdue: false,
    exceptionOpen: true,
    rationale: "1:M split invoice after ERP prefix change. Variance within 0.05% FX policy.",
    documents: ["INV SG-4501.pdf", "GL extract 14 Aug.csv"],
    trail: ["16 Aug 09:12 submitted", "16 Aug 09:14 AI policy check passed", "16 Aug 09:20 queued for controller"],
    confidenceFactors: [
      { label: "Amount", weight: 40 },
      { label: "Reference", weight: 30 },
      { label: "History", weight: 20 },
      { label: "Policy", weight: 10 },
    ],
  },
  {
    id: "MT-8902",
    submittedBy: "Agent_FX_04",
    entity: "EMEA LE04",
    exposure: "$48.2M",
    materiality: "High",
    confidence: "81.0%",
    date: "16 Aug",
    stage: "Manager",
    sla: "2 days overdue",
    slaOverdue: true,
    exceptionOpen: true,
    rationale: "FX swap residual above standard tolerance; override requested with hedge evidence.",
    documents: ["Hedge ticket H-441.xlsx"],
    trail: ["16 Aug 07:40 AI suggested", "16 Aug 08:02 analyst escalated", "16 Aug 08:15 SLA warning"],
    confidenceFactors: [
      { label: "Amount", weight: 20 },
      { label: "FX residual", weight: 35 },
      { label: "Hedge evidence", weight: 25 },
      { label: "History", weight: 20 },
    ],
  },
  {
    id: "MT-8830",
    submittedBy: "Analyst_APAC",
    entity: "APAC E09",
    exposure: "$64k",
    materiality: "Low",
    confidence: "97.1%",
    date: "15 Aug",
    stage: "Director",
    sla: "18h remaining",
    slaOverdue: false,
    exceptionOpen: false,
    rationale: "Amount off by $20 due to rounding. Within AMT_TOL_0.5.",
    documents: ["Match packet MT-8830.pdf"],
    trail: ["15 Aug 18:02 submitted"],
    confidenceFactors: [
      { label: "Amount", weight: 50 },
      { label: "Reference", weight: 30 },
      { label: "Rounding policy", weight: 20 },
    ],
  },
];

export const closeReadiness = [
  { label: "Match Rate", value: "97.4%" },
  { label: "Open Exposure", value: "$210M" },
  { label: "Exceptions Remaining", value: "148" },
  { label: "Controls Passed", value: "11 / 12" },
];

export const failedControls = [
  { id: "CTL-IC-09", name: "Intercompany aging > 45 days", owner: "FinController_Global", impact: "$18.4M" },
];

export const signoffChecklist = [
  { label: "Reconciliation complete", done: true },
  { label: "Approvals complete", done: false },
  { label: "Controls passed", done: false },
  { label: "Exceptions reviewed", done: true },
  { label: "Exposure accepted", done: false },
];

export const signoffExceptionSummary = [
  { label: "Open critical exceptions", value: 4 },
  { label: "Open high risk exceptions", value: 18 },
  { label: "Open aging exceptions", value: 27 },
];

export const signoffEvidence = {
  signedBy: "FD_Global",
  signedDate: "15 Aug 2026 18:04 UTC",
  approvalHash: "sha256:7c9ae21f4b88",
  auditRecordId: "AUD-SOX-2026-0815-044",
};

export const signoffEntities = [
  { entity: "APAC E09", status: "Pending controller", exposure: "$210M", exceptions: 62, owner: "FinController_Global", date: "—" },
  { entity: "EMEA LE04", status: "Manager signed", exposure: "$400M", exceptions: 88, owner: "Mgr_EMEA", date: "16 Aug" },
  { entity: "NAMER Main", status: "Signed off", exposure: "$42M", exceptions: 6, owner: "FD_Global", date: "15 Aug" },
];

export const signoffFlow = ["Analyst", "Manager", "Controller", "Finance Director"];

export const reconActivity = [
  { time: "08:31", actor: "User", text: "Opened run IC-2026-08-17" },
  { time: "08:22", actor: "AI", text: "Suggested 1:1 for SG-4412 (conf 98.4%)" },
  { time: "08:18", actor: "Rule", text: "INV_REF_EXACT applied to 1.9M items" },
  { time: "08:12", actor: "User", text: "Started Intercompany run for APAC" },
];

export const reconRecos = [
  { action: "Apply SG- prefix strip rule", confidence: "98.4%", impact: "+$210M auto-match" },
  { action: "Submit MT-9004 for approval", confidence: "92.1%", impact: "Clears 1:M split invoice" },
];
