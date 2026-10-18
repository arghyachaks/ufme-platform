/**
 * UFME data services. Pages call `api.*` / `workspaceApi.*`; they never know where data comes from.
 * Default: the FastAPI backend at /api/v1 (Vite proxies /api). Set VITE_USE_MOCKS=true to use local mocks.
 */
import * as db from "./mock/db";
import * as reconMock from "./mock/recon";
import * as dashboardMock from "./mock/dashboard";
import type { ChatMessage } from "./types";

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
    headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}), ...init?.headers },
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({}));
    throw new ApiError(response.status, problem);
  }
  return response.json() as Promise<T>;
}
const post = <T,>(path: string, body?: unknown) => http<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

const delay = <T,>(value: T, ms = 250) => new Promise<T>((resolve) => setTimeout(() => resolve(structuredClone(value)), ms));

const mockApi = {
  exceptions: { list: () => delay(db.exceptions) },
  cases: { list: () => delay(db.cases) },
  rules: { list: () => delay(db.rules) },
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
  },
  data: {
    sources: () => delay(db.sources),
    quality: () => delay({ issues: db.qualityIssues, dimensions: db.qualityDimensions }),
    lineage: (txnId: string) => delay(db.lineage[txnId] ?? []),
    lineageIds: () => delay(Object.keys(db.lineage)),
    features: () => delay(db.featureStore),
  },
  audit: { events: () => delay(db.auditEvents), controls: () => delay(db.controlTests) },
  admin: { all: () => delay({ users: db.users, roles: db.roles, entities: db.legalEntities }) },
  ops: { all: () => delay({ services: db.services, jobs: db.jobs }) },
  graph: { get: () => delay({ nodes: db.graphNodes, edges: db.graphEdges }) },
};

type Api = typeof mockApi;
type R<F extends (...args: never[]) => Promise<unknown>> = Awaited<ReturnType<F>>;

const httpApi: Api = {
  exceptions: { list: () => http("/exceptions") },
  cases: { list: () => http("/cases") },
  rules: { list: () => http("/rules") },
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
  },
  audit: { events: () => http("/audit/events"), controls: () => http("/audit/controls") },
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
