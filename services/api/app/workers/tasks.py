import uuid
from datetime import UTC, datetime

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
        return {
            "run": run.code,
            "status": run.status,
            **{k: run.metrics.get(k) for k in ("auto", "suggested", "unmatched")},
        }
