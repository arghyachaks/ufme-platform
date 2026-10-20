/**
 * UFME data services. Pages call `api.*` / `workspaceApi.*`; they never know where data comes from.
 * Default: the FastAPI backend at /api/v1 (Vite proxies /api). Set VITE_USE_MOCKS=true to use local mocks.
 */
import * as db from "./mock/db";
import * as reconMock from "./mock/recon";
import * as dashboardMock from "./mock/dashboard";
import type { BatchDetail, ChatMessage, IngestionBatch, MatchProposal, MatchRunInfo, MatchRule } from "./types";

export type ReconData = typeof reconMock;
export type DashboardData = typeof dashboardMock;

export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "true";
const BASE = "/api/v1";

export class ApiError extends Error {
  constructor(public status: number, public problem: { title?: string; detail?: string; code?: string; request_id?: string }) {
    super(problem.detail ?? problem.title ?? `Request failed (${status})`);
  }
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body && !(init.body instanceof FormData) ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({}));
    throw new ApiError(response.status, problem);
  }
  return response.json() as Promise<T>;
}
const post = <T,>(path: string, body?: unknown) => http<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

const delay = <T,>(value: T, ms = 250) => new Promise<T>((resolve) => setTimeout(() => resolve(structuredClone(value)), ms));

const mockBatches: IngestionBatch[] = [];
const mockBatch = (sourceId: string, fileName: string): IngestionBatch => {
  const batch: IngestionBatch = {
    id: `BAT-${String(mockBatches.length + 1).padStart(5, "0")}`, sourceId, source: sourceId, fileName,
    status: "Completed", rowsTotal: 2000, rowsLoaded: 1962, rowsQuarantined: 38, startedAt: "just now",
    durationMs: 900, error: null,
  };
  mockBatches.unshift(batch);
  return batch;
};

const mockRun: MatchRunInfo = {
  id: "RUN-00001", status: "Completed", scope: {}, engineVersion: "mock", rules: [], startedAt: null, durationMs: 0,
  metrics: {}, error: null,
};


export type AssistTurn = { role: "user" | "assistant"; content: string };
export type AssistStatus = { online: boolean; model: string };
type AssistArgs = { prompt: string; history: AssistTurn[]; page?: string; onDelta: (text: string) => void; signal?: AbortSignal };

async function mockAssist({ prompt, onDelta, signal }: AssistArgs): Promise<"fallback"> {
  const words = db.copilotAnswer(prompt).text.split(/(\s+)/);
  for (const w of words) {
    if (signal?.aborted) break;
    await new Promise((r) => setTimeout(r, 18));
    onDelta(w);
  }
  return "fallback";
}

/** Streams ufme Assist's answer (NDJSON from the API, which proxies the local model). Resolves with the source. */
async function httpAssist({ prompt, history, page, onDelta, signal }: AssistArgs): Promise<string> {
  const res = await fetch(`${BASE}/ai/assist/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, history, page }),
    signal,
  });
  if (!res.ok || !res.body) throw new ApiError(res.status, { title: "Assist unavailable" });
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let source = "local-llm";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let nl: number;
    while ((nl = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, nl).trim();
      buf = buf.slice(nl + 1);
      if (!line) continue;
      const msg = JSON.parse(line) as { delta?: string; done?: boolean; source?: string };
      if (msg.delta) onDelta(msg.delta);
      if (msg.done && msg.source) source = msg.source;
    }
  }
  return source;
}

const mockApi = {
  exceptions: { list: () => delay(db.exceptions) },
  cases: { list: () => delay(db.cases) },
  rules: {
    list: () => delay(db.rules),
    setEnabled: (code: string, enabled: boolean): Promise<MatchRule> =>
      delay({ ...(db.rules.find((r) => r.id === code) ?? db.rules[0]), enabled }),
  },
  policies: { list: () => delay(db.policies) },
  simulation: {
    scenarios: () => delay(Object.entries(db.simulationResults).map(([key, value]) => ({ key, label: value.scenario }))),
    run: (key: string) => delay(db.simulationResults[key], 900),
  },
  workflow: { stages: () => delay(db.workflowStages) },
  ai: {
    models: () => delay({ models: db.models, trend: db.modelTrend }),
    explanations: () => delay(db.explanations),
    learning: () => delay({ signals: db.learningSignals, stats: db.learningStats }),
    copilotSeed: () => delay({ messages: db.copilotSeed, prompts: db.copilotPrompts }),
    ask: (prompt: string): Promise<ChatMessage> => delay(db.copilotAnswer(prompt), 700),
    assist: (args: AssistArgs): Promise<string> => mockAssist(args),
    assistStatus: (): Promise<AssistStatus> => delay({ online: false, model: "demo" }),
  },
  data: {
    sources: () => delay(db.sources),
    quality: () => delay({ issues: db.qualityIssues, dimensions: db.qualityDimensions }),
    lineage: (txnId: string) => delay(db.lineage[txnId] ?? []),
    lineageIds: () => delay(Object.keys(db.lineage)),
    features: () => delay(db.featureStore),
    batches: (_source?: string) => delay(mockBatches),
    batch: (code: string): Promise<BatchDetail> =>
      delay({ ...(mockBatches.find((b) => b.id === code) ?? mockBatches[0]), quarantined: [], issues: [] }),
    sync: (code: string): Promise<IngestionBatch> => delay(mockBatch(code, "Synthetic pull"), 600),
    upload: (code: string, file: File): Promise<IngestionBatch> => delay(mockBatch(code, file.name), 600),
    resolveIssue: (code: string, _action: "resolve" | "ignore") =>
      delay(db.qualityIssues.find((i) => i.id === code) ?? db.qualityIssues[0]),
  },
  audit: { events: () => delay(db.auditEvents), controls: () => delay(db.controlTests) },
  recon: {
    startRun: (_entity?: string): Promise<MatchRunInfo> => delay(mockRun, 400),
    run: (_code: string): Promise<MatchRunInfo> => delay(mockRun),
    runs: (): Promise<MatchRunInfo[]> => delay([mockRun]),
    proposals: (_params?: { run?: string; status?: string }): Promise<MatchProposal[]> => delay([]),
    decide: (code: string, action: "accept" | "reject"): Promise<MatchProposal> =>
      delay({ id: code, status: action === "accept" ? "accepted" : "rejected" } as MatchProposal),
  },
  admin: { all: () => delay({ users: db.users, roles: db.roles, entities: db.legalEntities }) },
  ops: { all: () => delay({ services: db.services, jobs: db.jobs }) },
  graph: { get: () => delay({ nodes: db.graphNodes, edges: db.graphEdges }) },
};

type Api = typeof mockApi;
type R<F extends (...args: never[]) => Promise<unknown>> = Awaited<ReturnType<F>>;

const httpApi: Api = {
  exceptions: { list: () => http("/exceptions") },
  cases: { list: () => http("/cases") },
  rules: {
    list: () => http("/rules"),
    setEnabled: (code: string, enabled: boolean) =>
      http<MatchRule>(`/rules/${encodeURIComponent(code)}`, { method: "PATCH", body: JSON.stringify({ enabled }) }),
  },
  policies: { list: () => http("/policies") },
  simulation: {
    scenarios: () => http("/rules/simulations"),
    run: (key: string) => post(`/rules/simulations/${encodeURIComponent(key)}/run`),
  },
  workflow: { stages: () => http("/workflow/stages") },
  ai: {
    models: () => http("/ai/models"),
    explanations: () => http("/ai/explanations"),
    learning: () => http("/ai/learning"),
    copilotSeed: () => http("/ai/copilot"),
    ask: (prompt: string) => post<ChatMessage>("/ai/copilot/ask", { prompt }),
    assist: httpAssist,
    assistStatus: () => http<AssistStatus>("/ai/assist/status"),
  },
  data: {
    sources: () => http("/data/sources"),
    quality: () => http("/data/quality"),
    lineage: (txnId: string) =>
      http<R<Api["data"]["lineage"]>>(`/data/lineage/${encodeURIComponent(txnId)}`).catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404) return [];
        throw err;
      }),
    lineageIds: () => http("/data/lineage"),
    features: () => http("/data/features"),
    batches: (source?: string) => http(`/data/batches${source ? `?source=${encodeURIComponent(source)}` : ""}`),
    batch: (code: string) => http(`/data/batches/${encodeURIComponent(code)}`),
    sync: (code: string) => post(`/data/sources/${encodeURIComponent(code)}/sync`),
    upload: (code: string, file: File) => {
      const form = new FormData();
      form.append("file", file);
      return http<IngestionBatch>(`/data/sources/${encodeURIComponent(code)}/upload`, { method: "POST", body: form });
    },
    resolveIssue: (code: string, action: "resolve" | "ignore") =>
      post(`/data/quality/${encodeURIComponent(code)}/${action}`),
  },
  audit: { events: () => http("/audit/events"), controls: () => http("/audit/controls") },
  recon: {
    startRun: (entity?: string) => post<MatchRunInfo>("/recon/runs", entity ? { entity } : undefined),
    run: (code: string) => http<MatchRunInfo>(`/recon/runs/${encodeURIComponent(code)}`),
    runs: () => http<MatchRunInfo[]>("/recon/runs"),
    proposals: (params?: { run?: string; status?: string }) =>
      http<MatchProposal[]>(`/recon/proposals?${new URLSearchParams(Object.entries(params ?? {}).filter(([, v]) => v) as [string, string][])}`),
    decide: (code: string, action: "accept" | "reject") =>
      post<MatchProposal>(`/recon/proposals/${encodeURIComponent(code)}/${action}`),
  },
  admin: { all: () => http("/admin") },
  ops: { all: () => http("/ops") },
  graph: { get: () => http("/graph") },
};

export const api: Api = USE_MOCKS ? mockApi : httpApi;

// Dashboard and Reconciliation screens (one payload each until Stage 3-4 split them per endpoint).
export const workspaceApi = USE_MOCKS
  ? {
      recon: () => delay({ ...reconMock } as ReconData, 150),
      dashboard: () => delay({ ...dashboardMock } as DashboardData, 150),
    }
  : {
      recon: () => http<ReconData>("/workspace/recon"),
      dashboard: () => http<DashboardData>("/workspace/dashboard"),
    };
