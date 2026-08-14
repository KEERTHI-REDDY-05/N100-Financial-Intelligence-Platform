from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_get_all_companies():
    response = client.get("/api/v1/companies")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 92


def test_company_tcs():
    response = client.get("/api/v1/companies/TCS")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == "TCS"
    assert data["company_name"] == "Tata Consultancy Services Ltd"
    assert data["broad_sector"] == "Information Technology"
    assert "latest_kpis" in data


def test_invalid_company():
    response = client.get("/api/v1/companies/INVALID")

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == "Company 'INVALID' not found"


def test_company_sector_filter():
    response = client.get(
        "/api/v1/companies",
        params={"sector": "Energy"},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 14

    for company in data:
        assert company["broad_sector"] == "Energy"


def test_company_market_cap_filter():
    response = client.get(
        "/api/v1/companies",
        params={
            "market_cap_category": "Large Cap"
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) > 0

    for company in data:
        assert (
            company["market_cap_category"]
            == "Large Cap"
        )


def test_company_search():
    response = client.get(
        "/api/v1/companies",
        params={"search": "Tata"},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 5

    names = [
        company["company_name"]
        for company in data
    ]

    assert any(
        "Tata" in name
        for name in names
    )