"""Learning loop: reviewer decisions -> tenant model -> gated promotion -> drift."""

from typing import Any

from fastapi import APIRouter, BackgroundTasks

from app.api.deps import CurrentActor, CurrentTenant, DbSession
from app.core.config import settings
from app.services import learning, workflow

router = APIRouter(prefix="/learning")


@router.get("/status")
def status(db: DbSession, tenant: CurrentTenant) -> dict[str, Any]:
    return learning.status(db, tenant)


@router.post("/train", status_code=202)
def train(
    db: DbSession, tenant: CurrentTenant, actor: CurrentActor, background: BackgroundTasks
) -> dict[str, Any]:
    workflow.require_writer(actor)  # Auditors can see the loop but not change the model
    model = learning.request_training(db, tenant, actor.email)
    if settings.ingest_inline:
        learning.train(db, model)
    else:
        db.commit()  # the worker must see the row
        from app.workers.tasks import train_scorer

        background.add_task(train_scorer.delay, str(model.id))
    return learning.model_out(model)


@router.post("/models/{version}/promote")
def promote(version: str, db: DbSession, tenant: CurrentTenant, actor: CurrentActor) -> dict[str, Any]:
    return learning.model_out(learning.promote(db, tenant, version, actor))


@router.post("/rollback")
def rollback(db: DbSession, tenant: CurrentTenant, actor: CurrentActor) -> dict[str, Any]:
    restored = learning.rollback(db, tenant, actor)
    return {"active": restored.version if restored is not None else "shipped"}
