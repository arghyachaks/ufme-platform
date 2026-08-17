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
    start: "08:12",
    duration: "11m",
    ruleVersion: "rules-v3.4",
    modelVersion: "ranker-v4.8",
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
    start: "07:04",
    duration: "9m",
    ruleVersion: "rules-v3.4",
    modelVersion: "ranker-v4.8",
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
    start: "08:31",
    duration: "3m",
    ruleVersion: "rules-v3.3",
    modelVersion: "ranker-v4.7",
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
    start: "05:10",
    duration: "2m",
    ruleVersion: "rules-v3.4",
    modelVersion: "ranker-v4.8",
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
    start: "06:50",
    duration: "12m",
    ruleVersion: "rules-v3.3",
    modelVersion: "ranker-v4.7",
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
    status: "Unmatched",
    attachments: [],
  },
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
};

export const aiRecoCard = {
  title: "Apply SG- prefix strip rule",
  confidence: "98.4%",
  impact: "+$210M auto-match",
  detail: "Vendor X prepended SG- after an ERP patch. One-click execute will re-run APAC intercompany candidates.",
};

export const unmatchedA = [
  { id: "INV-4501", invoice: "SG-4501", amount: 91050, date: "13 Aug", entity: "APAC E09" },
  { id: "INV-4510", invoice: "SG-4510", amount: 22000, date: "13 Aug", entity: "APAC E09" },
  { id: "INV-4522", invoice: "SG-4522", amount: 17800, date: "14 Aug", entity: "APAC E09" },
];

export const unmatchedB = [
  { id: "GL-8902", invoice: "4501-A", amount: 45525, date: "14 Aug", entity: "US01 HQ" },
  { id: "GL-8903", invoice: "4501-B", amount: 45525, date: "14 Aug", entity: "US01 HQ" },
  { id: "GL-8910", invoice: "4510", amount: 22000, date: "14 Aug", entity: "US01 HQ" },
];

export const approvalKpis = [
  { label: "Pending Approval", value: "15" },
  { label: "High Risk", value: "4" },
  { label: "SLA Breached", value: "2" },
  { label: "Exposure Awaiting", value: "$64.2M" },
];

export const approvals = [
  {
    id: "MT-9004",
    submittedBy: "Analyst_APAC",
    entity: "APAC E09",
    exposure: "$6.1M",
    confidence: "92.1%",
    date: "16 Aug",
    rationale: "1:M split invoice after ERP prefix change. Variance within 0.05% FX policy.",
    documents: ["INV SG-4501.pdf", "GL extract 14 Aug.csv"],
    trail: ["16 Aug 09:12 submitted", "16 Aug 09:14 AI policy check passed", "16 Aug 09:20 queued for controller"],
  },
  {
    id: "MT-8902",
    submittedBy: "Agent_FX_04",
    entity: "EMEA LE04",
    exposure: "$48.2M",
    confidence: "81.0%",
    date: "16 Aug",
    rationale: "FX swap residual above standard tolerance; override requested with hedge evidence.",
    documents: ["Hedge ticket H-441.xlsx"],
    trail: ["16 Aug 07:40 AI suggested", "16 Aug 08:02 analyst escalated", "16 Aug 08:15 SLA warning"],
  },
  {
    id: "MT-8830",
    submittedBy: "Analyst_APAC",
    entity: "APAC E09",
    exposure: "$64k",
    confidence: "97.1%",
    date: "15 Aug",
    rationale: "Amount off by $20 due to rounding. Within AMT_TOL_0.5.",
    documents: ["Match packet MT-8830.pdf"],
    trail: ["15 Aug 18:02 submitted"],
  },
];

export const closeReadiness = [
  { label: "Match Rate", value: "97.4%" },
  { label: "Open Exposure", value: "$210M" },
  { label: "Exceptions Remaining", value: "148" },
  { label: "Controls Passed", value: "11 / 12" },
];

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
