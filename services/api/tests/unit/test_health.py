from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_checks_database(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["checks"]["database"] == "ok"


def test_openapi_is_served(client: TestClient) -> None:
    assert client.get("/api/v1/openapi.json").status_code == 200
