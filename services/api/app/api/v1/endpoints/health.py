from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness: the process is up."""
    return {"status": "ok"}


@router.get("/health/ready", response_model=None)
def ready(db: Session = Depends(get_db)) -> dict[str, object] | JSONResponse:
    """Readiness: dependencies are reachable."""
    checks: dict[str, str] = {}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc.__class__.__name__}"
    ok = all(v == "ok" for v in checks.values())
    body: dict[str, object] = {
        "status": "ok" if ok else "degraded",
        "environment": settings.environment,
        "checks": checks,
    }
    return body if ok else JSONResponse(body, status_code=503)
