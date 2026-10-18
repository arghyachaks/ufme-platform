from fastapi import APIRouter, Query
from fastapi.testclient import TestClient

from app.api.pagination import Pagination, decode_cursor, encode_cursor, paginate
from app.core.errors import NotFoundError
from app.main import app

probe = APIRouter()


@probe.get("/_probe/missing")
def _missing() -> None:
    raise NotFoundError("Case CS-0000 does not exist.", code="case_not_found")


@probe.get("/_probe/boom")
def _boom() -> None:
    raise RuntimeError("secret internals")


@probe.get("/_probe/validate")
def _validate(n: int = Query(ge=1)) -> dict[str, int]:
    return {"n": n}


@probe.get("/_probe/page")
def _page(p: Pagination) -> dict[str, object]:
    rows = list(range(p.offset, min(p.offset + p.limit + 1, 7)))
    return paginate(rows, p, total=7)


app.include_router(probe, prefix="/api/v1")


def test_request_id_is_generated_and_echoed(client: TestClient) -> None:
    generated = client.get("/api/v1/health").headers["X-Request-ID"]
    assert len(generated) == 32
    assert client.get("/api/v1/health", headers={"X-Request-ID": "abc-123"}).headers["X-Request-ID"] == "abc-123"


def test_app_errors_are_problem_json(client: TestClient) -> None:
    r = client.get("/api/v1/_probe/missing", headers={"X-Request-ID": "req-1"})
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["title"] == "Not found"
    assert body["code"] == "case_not_found"
    assert body["request_id"] == "req-1"


def test_unknown_route_is_problem_json(client: TestClient) -> None:
    r = client.get("/api/v1/does-not-exist")
    assert r.status_code == 404
    assert r.json()["status"] == 404


def test_validation_errors_are_listed(client: TestClient) -> None:
    r = client.get("/api/v1/_probe/validate?n=0")
    assert r.status_code == 422
    assert r.json()["errors"][0]["loc"] == ["query", "n"]


def test_unhandled_errors_hide_internals(client: TestClient) -> None:
    r = client.get("/api/v1/_probe/boom")
    assert r.status_code == 500
    assert "secret" not in r.text


def test_cursor_pagination_walks_all_rows(client: TestClient) -> None:
    seen: list[int] = []
    url = "/api/v1/_probe/page?limit=3"
    while url:
        body = client.get(url).json()
        seen += body["items"]
        url = f"/api/v1/_probe/page?limit=3&cursor={body['next_cursor']}" if body["next_cursor"] else ""
    assert seen == list(range(7))


def test_cursor_roundtrip_and_rejects_garbage(client: TestClient) -> None:
    assert decode_cursor(encode_cursor(150)) == 150
    assert client.get("/api/v1/_probe/page?cursor=not-a-cursor").status_code == 400
