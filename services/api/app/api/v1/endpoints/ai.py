from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentTenant, DbSession
from app.schemas.read import AskIn, AssistIn, ChatMessageOut
from app.services import assist, copilot, read

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


@router.get("/assist/status")
def assist_status() -> dict[str, Any]:
    return assist.status()


@router.post("/assist/stream")
def assist_stream(body: AssistIn, db: DbSession, tenant: CurrentTenant) -> StreamingResponse:
    return StreamingResponse(
        assist.stream(db, tenant, body.prompt, body.history, body.page),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
