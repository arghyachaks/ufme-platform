import uuid

from app.db.session import SessionLocal
from app.models import IngestionBatch
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
