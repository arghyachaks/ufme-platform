# ufme

**Open-source intercompany reconciliation.** ufme matches the transactions that a group's entities book with
each other, explains every match, sends the uncertain ones to a reviewer, and keeps an audit trail an external
auditor can verify.

Built and maintained by **[Arghya Chakraborty](https://github.com/arghyachaks)**. Licensed under
[Apache 2.0](LICENSE); please keep the [NOTICE](NOTICE) when you redistribute it.

> Status: feature-complete for a self-hosted pilot. Runs locally in Docker. Cloud deployment, backups and load
> testing (Stage 7) are next, so treat it as pre-production.

---

## What it does

- **Matches at scale.** Exact, fuzzy-reference, FX-aware, timing-tolerant, one-to-many and many-to-many matching
  across every entity pair; 690K ledger lines in about 7 minutes on a laptop.
- **Knows when it is sure.** A learned, monotonic scorer with calibrated probabilities and an auto-match
  threshold that is *proven* (Clopper-Pearson) to keep auto-match errors under 0.5% at 95% confidence.
  Everything else goes to a person, with the reason.
- **Explains itself.** Each suggestion shows its drivers, what would have made it an auto-match, and why the
  amounts differ (withholding tax, bank fee, FX, rounding).
- **Learns from your reviewers.** Accept/reject decisions train a tenant-specific model, which must pass a
  promotion gate and be approved by a Controller before it is used. One-click rollback; drift monitoring.
- **Works the way controllers work.** Review queue, approval matrix by exposure, segregation of duties, dual
  control above 1M, manual matching within tolerance, cases, period sign-off.
- **Audit-ready.** Tamper-evident hash-chained audit trail, signed evidence packages, SOX controls computed
  from data.
- **Secure by default.** OIDC sign-in (Keycloak locally), entity-scoped access, Postgres row-level security
  between tenants.
- **Local AI assistant.** Optional on-premise LLM (Ollama) for questions and reviewer notes; no data leaves
  your machine.

## Results on the benchmark

Measured on a 100,000-line synthetic group ledger with known ground truth (21 real-world scenarios: FX source
differences, withholding tax, bank fees, timing lags, split payments, reference typos, OCR noise, decoys...):

| | |
|---|---|
| Lines auto-matched | **94.97%** |
| Precision of auto-matches | **100%** (0 wrong) |
| Recall | 99.9% |
| Calibration error (ECE) | 0.18% |
| Learning loop: new tenant pattern, 300 reviewer decisions | auto-match 87.1% → **94.2%**, still 0 wrong |

Reproduce: `docker compose -f infra/docker/docker-compose.yml --profile test run --rm api-test python -m app.engines.benchmark --dataset medium --matcher engine`

## Quick start

Requirements: Docker Desktop (8 GB RAM for Docker is comfortable).

```bash
git clone https://github.com/arghyachaks/ufme-platform.git
cd ufme-platform
docker compose -f infra/docker/docker-compose.yml up -d --build
```

Then open **http://localhost:5173** and sign in as one of the demo users listed in
[infra/keycloak/README.md](infra/keycloak/README.md) (local development credentials). A synthetic demo tenant
is seeded on first start; run a reconciliation from **Reconciliation → Runs**.

Optional: install [Ollama](https://ollama.com) and `ollama pull gemma4:e4b-it-qat` to enable ufme Assist.

| Service | URL |
|---|---|
| Web app | http://localhost:5173 |
| API + OpenAPI docs | http://localhost:8000/docs |
| Keycloak (sign-in) | http://localhost:8081 |

## Architecture

```
apps/web            React 19 + MUI (Vite)
services/api        FastAPI, SQLAlchemy 2, Alembic, Celery workers
  app/engines/      matching engine, learned scorer, benchmark, data quality
  app/services/     workflow, learning loop, audit, evidence
infra/docker        Docker Compose: Postgres 16, Redis, Keycloak, API, worker, web
infra/keycloak      local OIDC realm
```

The matching engine is plain Python + NumPy (no ML framework at runtime); the scorer ships as a JSON artifact
and can be retrained from the synthetic corpus (`python -m app.engines.matching.train`).

## Development

```bash
# backend checks: ruff, mypy, pytest on Postgres, benchmark floors
docker compose -f infra/docker/docker-compose.yml --profile test run --rm api-test
# frontend type-check and build
docker compose -f infra/docker/docker-compose.yml --profile test run --rm web-test
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Security issues: see [SECURITY.md](SECURITY.md).

## License

Copyright 2026 Arghya Chakraborty. Licensed under the [Apache License 2.0](LICENSE).

You may use, modify, distribute and sell ufme, including in commercial products. If you redistribute it
(modified or not), you must include the LICENSE and the [NOTICE](NOTICE) file crediting the original author.
"ufme" and its logo are trademarks of Arghya Chakraborty and are not licensed for use in derived products.
