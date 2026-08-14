from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "N100 Financial Intelligence API"
    assert data["version"] == "1.0.0"
    assert data["docs"] == "/docs"


def test_health_endpoint():
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert "db_row_counts" in data
    assert "uptime_seconds" in data


def test_health_companies_count():
    response = client.get("/api/v1/health")

    data = response.json()

    assert data["db_row_counts"]["companies"] == 92


def test_health_table_count():
    response = client.get("/api/v1/health")

    data = response.json()

    assert len(data["db_row_counts"]) == 10