# UFME Platform

**Universal Financial Matching Engine** — a cloud-agnostic platform for 1:1, 1:M, M:1, and M:M reconciliation with deterministic rules, optimization, AI ranking, explainability, and human-in-the-loop review.

This repository is the product monorepo: React frontend, FastAPI services, shared libraries, data assets, and infrastructure.

## What it does

UFME matches financial events across ERP, files, and APIs, then routes residual risk into review, approval, and period close.

- Intercompany, bank, AP/AR, journal, inventory, and payroll reconciliation (MVP starts with intercompany)
- Exact, tolerance, and fuzzy matching plus candidate generation
- Exception cases, SLAs, SOX/audit evidence, and controller sign-off
- AI copilot, explainability, and a continuous learning loop

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
| `apps/web` | Controller dashboard (React + TypeScript + Material UI + Redux Toolkit) |
| `services/api` | Matching API (Python 3.12 + FastAPI) |
| `libraries/` | Shared `ufme_common` (Python) and `@ufme/types` (TypeScript) |
| `UFME_Development_Blueprint.md` | End-to-end product blueprint |
| `UFME_Dashboard_Review_Feedback.md` | Dashboard UX review used for the current UI |

## Dashboard (current)

The web app is a daily working screen for analysts and controllers, not only an executive demo.

- **My Work Queue** — approvals, critical exceptions, SLA breaches, assigned cases
- **Workflow funnel** — Ingested → Candidate → Suggested → Pending Review → Approved → Posted → Closed
- **Risk KPIs** — exposure, exceptions, exposure coverage; AI quality shows confidence, precision/recall, and false-positive rate
- **Exceptions** — sorted by financial impact, with entity, owner, and due date
- **Exposure heatmap** — drill into an entity risk view (trend, aging, root causes)
- **Close, SLA, and controls** — period close completion, breach mix, SOX/policy/overrides
- **Copilot dock** — recommended actions plus conversation
- **Light / dark mode**

Run it:

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:5173/](http://localhost:5173/).

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

