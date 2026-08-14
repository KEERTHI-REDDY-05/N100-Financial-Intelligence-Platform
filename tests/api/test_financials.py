from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_profit_and_loss():
    response = client.get(
        "/api/v1/companies/TCS/pl"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["ticker"] == "TCS"
    assert data["record_count"] > 0
    assert isinstance(data["history"], list)


def test_profit_and_loss_year_filter():
    response = client.get(
        "/api/v1/companies/TCS/pl",
        params={
            "from_year": "2020",
            "to_year": "2024",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["record_count"] == 5


def test_balance_sheet():
    response = client.get(
        "/api/v1/companies/TCS/bs"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["ticker"] == "TCS"
    assert data["record_count"] > 0


def test_balance_sheet_year_filter():
    response = client.get(
        "/api/v1/companies/TCS/bs",
        params={
            "from_year": "2020",
            "to_year": "2024",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["record_count"] == 6


def test_cashflow():
    response = client.get(
        "/api/v1/companies/TCS/cashflow"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["ticker"] == "TCS"
    assert data["record_count"] == 12


def test_cashflow_year_filter():
    response = client.get(
        "/api/v1/companies/TCS/cashflow",
        params={
            "from_year": "2020",
            "to_year": "2024",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["record_count"] == 5


def test_ratios():
    response = client.get(
        "/api/v1/companies/TCS/ratios"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["ticker"] == "TCS"
    assert data["record_count"] == 12


def test_ratios_year_filter():
    response = client.get(
        "/api/v1/companies/TCS/ratios",
        params={"year": "2024"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["record_count"] == 1
    assert data["ratios"][0]["year"] == "Mar 2024"