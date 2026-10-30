import uuid
from datetime import UTC, datetime

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import IngestionBatch, MatchRun
from app.services import matching
from app.services.ingestion import run_batch
from app.workers.celery_app import celery_app


@celery_app.task(name="ufme.ping")
def ping() -> str:
    """Smoke-test task: `celery -A app.workers.celery_app call ufme.ping`."""
    return "pong"


@celery_app.task(name="ufme.ingest_batch")
def ingest_batch(batch_id: str) -> dict[str, object]:
    with SessionLocal.begin() as db:
        batch = db.get(IngestionBatch, uuid.UUID(batch_id))
        if batch is None:
            return {"error": f"batch {batch_id} not found"}
        run_batch(db, batch)
        return {
            "batch": batch.code,
            "status": batch.status,
            "loaded": batch.rows_loaded,
            "quarantined": batch.rows_quarantined,
        }


@celery_app.task(name="ufme.match_run")
def match_run(run_id: str) -> dict[str, object]:
    with SessionLocal.begin() as db:  # make "Running" visible to the UI before the long transaction starts
        run = db.get(MatchRun, uuid.UUID(run_id))
        if run is None:
            return {"error": f"run {run_id} not found"}
        run.status, run.started_at = "Running", datetime.now(UTC)
    with SessionLocal.begin() as db:
        run = db.get(MatchRun, uuid.UUID(run_id))
        assert run is not None
        matching.execute_run(db, run)
        out: dict[str, object] = {
            "run": run.code,
            "status": run.status,
            **{k: run.metrics.get(k) for k in ("auto", "suggested", "unmatched")},
        }
    if out["status"] == "Completed" and settings.judge_enabled:
        judge_suggestions.delay(run_id)  # advisory; runs after the results are committed and visible
    return out


@celery_app.task(name="ufme.judge_suggestions")
def judge_suggestions(run_id: str) -> dict[str, int]:
    from app.services.judge import judge_run

    with SessionLocal() as db:
        return judge_run(db, uuid.UUID(run_id))


@celery_app.task(name="ufme.train_scorer")
def train_scorer(model_id: str) -> dict[str, object]:
    """3f: train a tenant adapter from reviewer decisions and evaluate its promotion gate (never promotes)."""
    from app.models import ScorerModel
    from app.services import learning

    with SessionLocal.begin() as db:
        model = db.get(ScorerModel, uuid.UUID(model_id))
        if model is None:
            return {"error": f"model {model_id} not found"}
        learning.train(db, model)
        return {"version": model.version, "status": model.status, "gate": (model.gate or {}).get("passed")}
