from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_get_sectors():
    response = client.get("/api/v1/sectors")

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 10
    assert len(data["sectors"]) == 10


def test_energy_sector_companies():
    response = client.get(
        "/api/v1/sectors/Energy/companies"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["sector"] == "Energy"
    assert data["count"] == 14

    for company in data["companies"]:
        assert company["broad_sector"] == "Energy"


def test_invalid_sector():
    response = client.get(
        "/api/v1/sectors/INVALID/companies"
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == "Sector 'INVALID' not found"