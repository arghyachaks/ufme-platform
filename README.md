# UFME Platform

Monorepo for the Universal Financial Matching Engine.

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

## Apps and services

- `apps/web` — React + TypeScript + Material UI + Redux Toolkit
- `services/api` — Python 3.12 + FastAPI matching API

## Getting started

Frontend:

```bash
cd apps/web
npm install
npm run dev
```

Backend:

```bash
cd services/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
