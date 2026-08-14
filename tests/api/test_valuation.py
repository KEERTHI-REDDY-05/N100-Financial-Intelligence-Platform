from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_tcs_valuation():
    response = client.get(
        "/api/v1/valuation/TCS"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["ticker"] == "TCS"
    assert data["company_name"] == "Tata Consultancy Services Ltd"
    assert data["record_count"] == 6


def test_tcs_valuation_summary():
    response = client.get(
        "/api/v1/valuation/TCS"
    )

    data = response.json()
    summary = data["summary"]

    assert "latest" in summary
    assert "historical_averages" in summary
    assert "signals" in summary
    assert "market_cap_growth_pct" in summary
    assert "valuation_score" in summary
    assert "valuation_category" in summary


def test_tcs_latest_valuation():
    response = client.get(
        "/api/v1/valuation/TCS"
    )

    data = response.json()
    latest = data["summary"]["latest"]

    assert int(latest["year"]) == 2024
    assert latest["pe_ratio"] == 78.69
    assert latest["pb_ratio"] == 6.08
    assert latest["ev_ebitda"] == 29.94


def test_tcs_valuation_signals():
    response = client.get(
        "/api/v1/valuation/TCS"
    )

    signals = response.json()["summary"]["signals"]

    assert signals["pe_signal"] == "Overvalued"
    assert signals["pb_signal"] == "Undervalued"
    assert signals["ev_ebitda_signal"] == "Overvalued"
    assert signals["dividend_yield_signal"] == "Neutral"


def test_tcs_valuation_score():
    response = client.get(
        "/api/v1/valuation/TCS"
    )

    summary = response.json()["summary"]

    assert summary["valuation_score"] == 40
    assert (
        summary["valuation_category"]
        == "Expensive Relative Valuation"
    )


def test_invalid_company_valuation():
    response = client.get(
        "/api/v1/valuation/INVALID"
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == "Company 'INVALID' not found"