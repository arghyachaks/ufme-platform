/**
 * UFME data services. Every page calls these async functions; today they resolve mock data,
 * later each body becomes a fetch to the FastAPI backend (e.g. GET /api/v1/cases).
 */
import * as db from "./mock/db";
import type { ChatMessage } from "./types";

const delay = <T,>(value: T, ms = 250) => new Promise<T>((resolve) => setTimeout(() => resolve(structuredClone(value)), ms));

export const api = {
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

// Existing Dashboard and Reconciliation screens (one payload each; split per endpoint when wiring the backend).
import * as reconMock from "./mock/recon";
import * as dashboardMock from "./mock/dashboard";
export type ReconData = typeof reconMock;
export type DashboardData = typeof dashboardMock;
export const workspaceApi = {
  recon: () => delay({ ...reconMock } as ReconData, 150),
  dashboard: () => delay({ ...dashboardMock } as DashboardData, 150),
};
