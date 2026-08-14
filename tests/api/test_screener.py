from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_screener_base():
    response = client.get("/api/v1/screener")

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 92
    assert isinstance(data["results"], list)


def test_screener_min_roe():
    response = client.get(
        "/api/v1/screener",
        params={"min_roe": 20},
    )

    assert response.status_code == 200

    data = response.json()

    for company in data["results"]:
        assert company["roe_pct"] >= 20


def test_screener_max_de():
    response = client.get(
        "/api/v1/screener",
        params={"max_de": 0.5},
    )

    assert response.status_code == 200

    data = response.json()

    for company in data["results"]:
        assert company["debt_to_equity"] <= 0.5


def test_screener_min_fcf():
    response = client.get(
        "/api/v1/screener",
        params={"min_fcf": 10000},
    )

    assert response.status_code == 200

    data = response.json()

    for company in data["results"]:
        assert company["free_cash_flow_cr"] >= 10000


def test_screener_sector():
    response = client.get(
        "/api/v1/screener",
        params={"sector": "Energy"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 14

    for company in data["results"]:
        assert company["broad_sector"] == "Energy"


def test_screener_max_pe():
    response = client.get(
        "/api/v1/screener",
        params={"max_pe": 30},
    )

    assert response.status_code == 200

    data = response.json()

    for company in data["results"]:
        assert company["pe_ratio"] <= 30


def test_screener_rev_cagr():
    response = client.get(
        "/api/v1/screener",
        params={"min_rev_cagr_5yr": 15},
    )

    assert response.status_code == 200

    data = response.json()

    for company in data["results"]:
        assert company["rev_cagr_5yr"] >= 15


def test_screener_pat_cagr():
    response = client.get(
        "/api/v1/screener",
        params={"min_pat_cagr_5yr": 20},
    )

    assert response.status_code == 200

    data = response.json()

    for company in data["results"]:
        assert company["pat_cagr_5yr"] >= 20


def test_screener_invalid_parameter():
    response = client.get(
        "/api/v1/screener",
        params={"min_roe": "abc"},
    )

    assert response.status_code == 400

    data = response.json()

    assert data["detail"] == "Invalid request parameter"