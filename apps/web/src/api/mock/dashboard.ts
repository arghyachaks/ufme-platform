export const kpiGroups = [
  {
    title: "Risk",
    items: [
      { label: "Financial Exposure", value: "$1.24B", hint: "Unmatched risk · MED" },
      { label: "Open Exceptions", value: "842", hint: "14 critical · 312 aging" },
      { label: "Coverage (Exposure)", value: "99.7%", hint: "More material than count match" },
    ],
  },
  {
    title: "Operational",
    items: [
      { label: "Auto Match Rate", value: "98.42%", hint: "Item coverage 98.4%" },
      { label: "Volume (24H)", value: "14.2M", hint: "$84.2B USD" },
      { label: "Avg Resolution", value: "4.2m", hint: "Manual baseline 45m" },
    ],
  },
  {
    title: "Match quality",
    items: [
      { label: "Confidence", value: "99.1%", hint: "Average certainty on suggested matches" },
      { label: "Precision / Recall", value: "98.7% / 97.9%", hint: "Accepted matches that were correct" },
      { label: "False Positive Rate", value: "0.2%", hint: "Incorrect auto-matches" },
    ],
  },
];

export const workQueue = [
  { label: "Awaiting approval", count: 15, to: "/reconciliation/approvals", tone: "warn" as const },
  { label: "Critical exceptions", count: 7, to: "/exceptions", tone: "crit" as const },
  { label: "SLA breaches", count: 3, to: "/exceptions", tone: "crit" as const },
  { label: "Cases assigned to me", count: 12, to: "/exceptions/cases", tone: "ok" as const },
];

export const workflowFunnel = [
  { label: "Ingested", value: "14.2M" },
  { label: "Candidate", value: "13.8M" },
  { label: "Suggested", value: "13.1M" },
  { label: "Pending Review", value: "118k" },
  { label: "Approved", value: "12.9M" },
  { label: "Posted", value: "12.7M" },
  { label: "Closed", value: "12.6M" },
];

export const agents = [
  {
    name: "Duplicate check",
    online: true,
    workload: "0 items",
    precision: "100%",
    status: "Hands off to FX check",
  },
  {
    name: "FX variance check",
    online: true,
    workload: "412 items",
    precision: "97.4%",
    status: "Hands off to intercompany",
  },
  {
    name: "Intercompany matching",
    online: true,
    workload: "2.4M items",
    precision: "99.8%",
    status: "Matching now",
  },
];

export const agentFlow = ["Duplicate Agent", "FX Agent", "Intercompany matching"];

export const exposureTiles = [
  {
    id: "emea-le-04",
    amount: "$400M",
    entity: "EMEA - Legal Entity 04",
    cause: "Unmatched FX Swaps",
    tone: "crit" as const,
  },
  {
    id: "apac-e-09",
    amount: "$210M",
    entity: "APAC - Entity 09",
    cause: "SG- invoice prefix",
    tone: "warn" as const,
  },
  {
    id: "namer-main",
    amount: "$42M",
    entity: "NAMER - Main Entity",
    cause: "Timing differences",
    tone: "ok" as const,
  },
];

export const highRiskExceptions = [
  {
    id: "EX-8902",
    severity: "CRITICAL",
    category: "FX Variance",
    impact: "$48.2M",
    entity: "EMEA LE04",
    owner: "Priya Raman · Group Controller",
    due: "17 Aug",
    age: "48h",
  },
  {
    id: "EX-8911",
    severity: "CRITICAL",
    category: "Duplicate Posting",
    impact: "$21.4M",
    entity: "APAC E09",
    owner: "Ops Team A",
    due: "17 Aug",
    age: "36h",
  },
  {
    id: "EX-9004",
    severity: "WARNING",
    category: "Format Mismatch",
    impact: "$6.1M",
    entity: "APAC E09",
    owner: "Intercompany auto-match",
    due: "18 Aug",
    age: "12h",
  },
];

export const rootCauses = [
  { label: "FX Variance", share: 35 },
  { label: "Reference Mismatch", share: 25 },
  { label: "Timing Difference", share: 20 },
  { label: "Duplicate", share: 10 },
  { label: "Other", share: 10 },
];

export const trendSeries = {
  "7D": [96.8, 97.1, 97.4, 96.9, 97.8, 98.1, 98.4],
  "30D": [95.2, 96.1, 96.8, 97.2, 97.5, 97.9, 98.4],
  Quarter: [93.4, 94.8, 96.2, 97.1, 97.6, 98.0, 98.4],
};

export const forecast = {
  exceptions: "790",
  exposure: "$1.05B",
  matchRate: "98.6%",
};

export const closeDays = [
  { label: "Day 1", done: true },
  { label: "Day 2", done: true },
  { label: "Day 3", done: true },
  { label: "Day 4", done: false },
];

export const closeCompletion = 87;

export const sla = [
  { label: "Breached", count: 3, tone: "crit" as const },
  { label: "Near breach", count: 18, tone: "warn" as const },
  { label: "On track", count: 821, tone: "ok" as const },
];

export const controlsAtRisk = [
  { label: "SOX violations", count: 0, tone: "ok" as const },
  { label: "Policy breaches", count: 2, tone: "warn" as const },
  { label: "Manual overrides", count: 11, tone: "warn" as const },
];

export const learning = [
  { label: "Rules proposed", value: "24" },
  { label: "Rules accepted", value: "18" },
  { label: "Auto-match lift", value: "+1.8 pts" },
  { label: "Reviewer overrides", value: "42" },
];

export const copilotActions = [
  { label: "1. Apply SG Prefix Rule", to: "/rules" },
  { label: "2. Simulate Result", to: "/rules/simulation" },
  { label: "3. Submit Approval", to: "/reconciliation/approvals" },
  { label: "4. Deploy Rule", to: "/rules" },
];

export const copilotThread = [
  { role: "user" as const, text: "Why did Singapore's (Legal Entity 09) auto-match rate decrease today?" },
  {
    role: "ai" as const,
    text: "The 12% drop is caused by 4,200 unmatched intercompany invoices from Sub-Entity B. An ERP patch prepended “SG-” to invoice references. A transformation rule is ready to strip the prefix.",
  },
  { role: "user" as const, text: "Yes, run simulation and show exposure reduction." },
  {
    role: "ai" as const,
    text: "Simulation complete: 4,188 of 4,200 items matched instantly. Exposure reduced by $210M USD. Zero control violations detected.",
  },
];

export const tickerItems = [
  "13:18  14,200 intercompany items matched automatically · 99.9% confidence",
  "13:17  SOX control check passed for Q3 close",
  "13:15  EX-8902 escalated to Group Controller · FX variance above $10M",
  "13:12  Matching model 4.8 approved and live for EMEA",
];

export const entityRisk = {
  "emea-le-04": {
    name: "EMEA - Legal Entity 04",
    exposure: "$400M",
    matchRate: "91.2%",
    aging: [
      { bucket: "0-8h", count: 12 },
      { bucket: "8-24h", count: 28 },
      { bucket: "24-48h", count: 41 },
      { bucket: ">48h", count: 19 },
    ],
    causes: [
      { label: "Unmatched FX Swaps", share: 62 },
      { label: "Timing Difference", share: 21 },
      { label: "Reference Mismatch", share: 17 },
    ],
    trend: [94.1, 93.4, 92.8, 92.1, 91.6, 91.4, 91.2],
  },
  "apac-e-09": {
    name: "APAC - Entity 09",
    exposure: "$210M",
    matchRate: "86.4%",
    aging: [
      { bucket: "0-8h", count: 40 },
      { bucket: "8-24h", count: 55 },
      { bucket: "24-48h", count: 22 },
      { bucket: ">48h", count: 8 },
    ],
    causes: [
      { label: "SG- invoice prefix", share: 71 },
      { label: "PO format change", share: 18 },
      { label: "Other", share: 11 },
    ],
    trend: [98.1, 97.6, 96.2, 92.4, 88.1, 86.9, 86.4],
  },
  "namer-main": {
    name: "NAMER - Main Entity",
    exposure: "$42M",
    matchRate: "99.1%",
    aging: [
      { bucket: "0-8h", count: 9 },
      { bucket: "8-24h", count: 6 },
      { bucket: "24-48h", count: 2 },
      { bucket: ">48h", count: 1 },
    ],
    causes: [
      { label: "Timing Difference", share: 54 },
      { label: "FX Variance", share: 28 },
      { label: "Other", share: 18 },
    ],
    trend: [98.6, 98.8, 98.9, 99.0, 99.0, 99.1, 99.1],
  },
};
