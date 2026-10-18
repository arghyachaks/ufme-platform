from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentTenant, DbSession
from app.schemas.read import AskIn, ChatMessageOut
from app.services import copilot, read

router = APIRouter(prefix="/ai")


@router.get("/models")
def models(db: DbSession, tenant: CurrentTenant) -> Any:
    return read.snapshot(db, tenant, "ai.models")


@router.get("/explanations")
def explanations(db: DbSession, tenant: CurrentTenant) -> Any:
    return read.snapshot(db, tenant, "ai.explanations")


@router.get("/learning")
def learning(db: DbSession, tenant: CurrentTenant) -> Any:
    return read.snapshot(db, tenant, "ai.learning")


@router.get("/copilot")
def copilot_seed(db: DbSession, tenant: CurrentTenant) -> Any:
    return read.snapshot(db, tenant, "ai.copilot")


@router.post("/copilot/ask", response_model=ChatMessageOut, response_model_exclude_none=True)
def copilot_ask(body: AskIn, tenant: CurrentTenant) -> ChatMessageOut:
    return copilot.answer(body.prompt)
