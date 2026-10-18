# UFME Platform

**Universal Financial Matching Engine** — a cloud-agnostic platform for 1:1, 1:M, M:1, and M:M reconciliation with deterministic rules, optimization, AI ranking, explainability, and human-in-the-loop review.

This repository is the product monorepo: React frontend, FastAPI services, shared libraries, data assets, and infrastructure.

## What it does

UFME matches financial events across ERP, files, and APIs, then routes residual risk through review, manual match, approval, and period close.

- Intercompany, bank, AP/AR, journal, inventory, and payroll reconciliation (MVP starts with intercompany)
- Exact, tolerance, and fuzzy matching plus ranked candidates
- Exception cases, SLAs, SOX/audit evidence, and controller sign-off
- AI Match Advisor with explainability and a continuous learning loop

## Repository layout

```
ufme-platform
├── apps          user-facing applications (React)
├── services      backend services (FastAPI)
├── libraries     shared Python and TypeScript packages
├── data          samples, fixtures, and synthetic datasets
├── infra         Docker and Kubernetes
├── docs          product and engineering docs
└── tests         cross-service e2e, contract, and performance tests
```

| Path | Purpose |
|------|---------|
| `apps/web` | Controller UI (React + TypeScript + Material UI + Redux Toolkit) |
| `services/api` | Matching API (Python 3.12 + FastAPI) |
| `libraries/` | Shared `ufme_common` (Python) and `@ufme/types` (TypeScript) |

Product design specs stay local (Markdown other than this README is not published).

## Web app (current)

Run it:

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:5173/](http://localhost:5173/). Active work is on **`develop`**.

### Reconciliation operating workflow

The core loop is **Runs → Review → Manual Match → Approvals → Signoff**.

| Screen | What it covers |
|--------|----------------|
| **Runs** | Job list sorted by exposure, 7-day trends, materiality, rule/model versions, run summary drawer, bulk rerun/export/archive, compare, audit trail |
| **Review** | Suggested matches with amount impact, confidence breakdown, 1:1 / 1:M / M:1 / M:M, candidate scores, queue-scale batch actions, transaction drawer, SLA, convert to exception case |
| **Manual Match** | Build matches from unmatched sides, live totals, 0.5% tolerance policy, AI suggest + why, document preview, create exception |
| **Approvals** | Queue with hierarchy (Analyst → Director), materiality, SLA timers, confidence factors, batch approve/reject/request info |
| **Signoff** | Close readiness score, failed-control drill-down, checklist, exception summary, comments, digital signature evidence |

The right-hand **AI Match Advisor** changes by screen: combinations on Manual Match, approve/reject on Approvals, readiness hold/go on Signoff.

### All modules (demo-ready, mock data)

Every navigation item now has a working screen backed by a typed mock API:

| Area | Screens |
|------|---------|
| Exceptions | Dashboard (aging, root causes, load, bulk actions), Investigations (AI hypotheses, nearest candidates, evidence), Cases (Kanban board / list, case drawer with comments) |
| Rules & Policies | Rules (priority list, condition builder), Policies (versions, thresholds), Simulation (baseline vs scenario), Workflow (stages, SLAs, guardrails) |
| AI Control Hub | Copilot (chat with cited records), Explainability (feature contributions, counterfactual), Models (champion/challenger, drift), Learning (feedback loop) |
| Data Engine | Sources (connector health), Quality (DQ dimensions, issues), Lineage (source-to-decision trace), Features (feature store) |
| Governance | Audit & SOX (trail + control testing), Administration (users, roles, entities, security), Operations (service health, jobs), Knowledge Graph |

### Frontend data layer

Pages never import mock data directly. They call `api.*` in `apps/web/src/api/services.ts` through the `useQuery` hook; types live in `src/api/types.ts` and mock records in `src/api/mock/db.ts`. To connect the backend, replace each service body with a `fetch` to the matching FastAPI endpoint — no page changes needed. The Dashboard, Entity Risk, and Reconciliation screens load through `workspaceApi` (mock payloads in `src/api/mock/dashboard.ts` and `recon.ts`).

### Dashboard

Daily working screen for analysts and controllers.

- Work queue, workflow funnel, exposure/exception KPIs
- Entity risk drill-down, close/SLA/controls
- Light / dark mode

## Local Docker workflow (required before every push)

All development is validated in local Docker before anything reaches GitHub.

```powershell
docker compose -f infra/docker/docker-compose.yml up --build -d   # run everything
```

| Service | URL |
|---------|-----|
| Web app | http://localhost:5173 |
| API docs | http://localhost:8000/docs |
| Postgres / Redis | localhost:5432 / localhost:6379 |

**Gate:** `scripts\docker-check.bat` (or `bash scripts/docker-check.sh`) builds all images, starts the stack, runs ruff, mypy and pytest against Postgres, builds the frontend, and smoke-tests the API, web proxy and worker. A git **pre-push hook** (`.githooks/pre-push`, enabled with `git config core.hooksPath .githooks`) runs the same gate and blocks the push if it fails. Log: `tmp/docker-check.log`.

## Backend API

Python 3.12 + FastAPI, PostgreSQL 16, Redis, Celery. Stage 0 (foundation) is in place: settings, structured logging with request IDs, RFC 7807 errors, cursor pagination, SQLAlchemy 2 + Alembic migrations, tamper-evident audit log, Celery worker, Docker, tests, and CI.

**Quick start (Windows, from the repo root):**

```powershell
.\scripts\dev.ps1 setup     # create services\api\.venv and install dependencies
.\scripts\dev.ps1 test      # run tests (SQLite, no Docker needed)
.\scripts\dev.ps1 deps      # start Postgres + Redis in Docker
.\scripts\dev.ps1 migrate   # apply migrations
.\scripts\dev.ps1 api       # http://127.0.0.1:8000/docs
```

Or run the whole stack (Postgres, Redis, API, worker) with `.\scripts\dev.ps1 stack`. Run `.\scripts\dev.ps1 format` then `lint` before committing.

| Path | Purpose |
|------|---------|
| `app/core` | Settings, logging, request-ID middleware, problem+json errors |
| `app/db` | Declarative base, session, Alembic migrations |
| `app/models` | Tenant, legal entity, user/role, audit event |
| `app/services` | Business logic (audit trail so far) |
| `app/api` | Routers and pagination helpers |
| `app/engines` | Matching pipeline stages (Stage 3+) |
| `app/workers` | Celery app and tasks |

**Stage 1 (read APIs):** every screen reads from the API. On startup in Docker the API migrates and seeds a demo tenant from `app/seed/demo/*.json` (exported from the frontend mocks with `node --experimental-strip-types scripts/export-mocks.mts`). Contract tests assert each endpoint returns exactly what the mocks returned. Set `VITE_USE_MOCKS=true` to run the UI without the backend.

**Stage 2 (ingestion):** `POST /api/v1/data/sources/{id}/upload` (CSV/TSV) and `.../sync` (ERP/bank/API pull; synthetic extract until native connectors land) run the pipeline in the Celery worker: column mapping (SAP/Oracle header aliases) → data-quality checks → normalization → FX to USD → `ledger_txn`, with failing rows quarantined and DQ issues raised per batch. 100K rows load in ~10 s on Postgres (`python -m app.seed.benchmark --rows 100000`). Generate test files with `python -m app.engines.connectors.synthetic --rows 10000 --out ic.csv`.

**Stage 3a (matching benchmark):** `app/engines/benchmark` generates ground-truth intercompany ledgers across 21 scenarios (FX, timing, fees, splits, bundles, netting, reference noise/OCR, duplicates, reversals, orphans, decoys), scores any matcher per scenario (pair, group, exposure-weighted, auto-rate at precision, decoy/orphan false-match rates), and guards against regressions. Golden sets are frozen by fingerprint (`benchmarks/datasets.json`); the Docker gate fails if the 100K benchmark drops below `benchmarks/floor_medium_baseline.json`. Run `python -m app.engines.benchmark --dataset medium`.

Health: `GET /api/v1/health` (liveness), `GET /api/v1/health/ready` (database check). Frontend types can be regenerated from the running API with `npm run gen:api-types` in `apps/web`. The Vite dev server proxies `/api` to the backend.

## Technology stack

| Layer | Choice |
|--------|--------|
| Frontend | React, TypeScript, Vite, Material UI, Redux Toolkit |
| Backend | Python 3.12, FastAPI |
| Data | PostgreSQL, Redis, OpenSearch, S3-compatible object storage |
| Async / messaging | Celery or Temporal, Kafka |
| AI / optimization | PyTorch, LightGBM, Sentence Transformers, OR-Tools |
| Runtime | Docker, Kubernetes (AWS, Azure, GCP, OpenShift, on-prem) |

## Personas

Finance analysts review suggested matches. Controllers approve overrides and sign off. Auditors export evidence. Admins configure tenants and RBAC. Platform operators watch health and scale.

## Development branch

Active development is on **`develop`**.

```bash
git clone https://github.com/arghyachaks/ufme-platform.git
cd ufme-platform
git checkout develop
```

## License

Free for non-commercial use (personal, education, research, and evaluation).
**Commercial use requires a paid license.** See [LICENSE](LICENSE).
