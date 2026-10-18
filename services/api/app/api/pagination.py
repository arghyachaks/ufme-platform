"""Shared list conventions: ?limit=&cursor=&sort=  → {items, next_cursor, total}."""

import base64
import json
from typing import Annotated, Any

from fastapi import Depends, Query
from pydantic import BaseModel

from app.core.config import settings
from app.core.errors import AppError


class PageParams(BaseModel):
    limit: int
    offset: int
    sort: str | None


def encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(json.dumps({"o": offset}).encode()).decode()


def decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        return int(json.loads(base64.urlsafe_b64decode(cursor.encode()))["o"])
    except (ValueError, KeyError, TypeError) as exc:
        raise AppError("Invalid cursor.", code="invalid_cursor") from exc


def page_params(
    limit: Annotated[int, Query(ge=1, le=settings.max_page_size)] = settings.default_page_size,
    cursor: Annotated[str | None, Query()] = None,
    sort: Annotated[str | None, Query(pattern=r"^-?[a-z_]+(,-?[a-z_]+)*$")] = None,
) -> PageParams:
    return PageParams(limit=limit, offset=decode_cursor(cursor), sort=sort)


Pagination = Annotated[PageParams, Depends(page_params)]


class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None
    total: int | None = None


def paginate(items: list[Any], params: PageParams, total: int | None = None) -> dict[str, Any]:
    """For list results already fetched with limit+1 rows."""
    has_more = len(items) > params.limit
    return {
        "items": items[: params.limit],
        "next_cursor": encode_cursor(params.offset + params.limit) if has_more else None,
        "total": total,
    }
