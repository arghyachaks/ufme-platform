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

### Dashboard

Daily working screen for analysts and controllers.

- Work queue, workflow funnel, exposure/exception KPIs
- Entity risk drill-down, close/SLA/controls
- Light / dark mode

## Backend API

```bash
cd services/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

The Vite dev server proxies `/api` to that backend.

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
