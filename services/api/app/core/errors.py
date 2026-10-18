"""RFC 7807 problem+json errors for every failure path."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_JSON = "application/problem+json"
logger = logging.getLogger("ufme.errors")


class AppError(Exception):
    """Raise from services for expected business failures."""

    status_code = 400
    title = "Bad request"

    def __init__(self, detail: str, *, code: str | None = None, extra: dict[str, Any] | None = None):
        super().__init__(detail)
        self.detail = detail
        self.code = code
        self.extra = extra or {}


class NotFoundError(AppError):
    status_code = 404
    title = "Not found"


class ConflictError(AppError):
    status_code = 409
    title = "Conflict"


class ForbiddenError(AppError):
    status_code = 403
    title = "Forbidden"


def problem(
    request: Request, status: int, title: str, detail: str | None = None, **extra: Any
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "instance": request.url.path,
        "request_id": getattr(request.state, "request_id", None),
    }
    if detail:
        body["detail"] = detail
    body.update({k: v for k, v in extra.items() if v is not None})
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return problem(request, exc.status_code, exc.title, exc.detail, code=exc.code, **exc.extra)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        title = {404: "Not found", 405: "Method not allowed", 401: "Unauthorized", 403: "Forbidden"}.get(
            exc.status_code, "HTTP error"
        )
        return problem(request, exc.status_code, title, str(exc.detail) if exc.detail else None)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"loc": list(err.get("loc", [])), "msg": err.get("msg"), "type": err.get("type")}
            for err in exc.errors()
        ]
        return problem(request, 422, "Validation failed", "One or more fields are invalid.", errors=errors)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error")
        return problem(request, 500, "Internal server error", "An unexpected error occurred.")
