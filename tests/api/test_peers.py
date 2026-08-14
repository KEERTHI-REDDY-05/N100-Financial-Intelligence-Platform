from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_it_services_peer_group():
    response = client.get(
        "/api/v1/peers/IT%20Services"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["peer_group"] == "IT Services"
    assert data["count"] == 5
    assert len(data["companies"]) == 5


def test_peer_group_benchmark():
    response = client.get(
        "/api/v1/peers/IT%20Services"
    )

    data = response.json()

    benchmarks = [
        company
        for company in data["companies"]
        if company["is_benchmark"] == 1
    ]

    assert len(benchmarks) == 1
    assert benchmarks[0]["company_id"] == "TCS"


def test_peer_percentiles_present():
    response = client.get(
        "/api/v1/peers/IT%20Services"
    )

    data = response.json()

    company = data["companies"][0]

    assert "net_profit_margin_pct_percentile" in company
    assert "return_on_equity_pct_percentile" in company
    assert "free_cash_flow_cr_percentile" in company


def test_invalid_peer_group():
    response = client.get(
        "/api/v1/peers/INVALID"
    )

    assert response.status_code == 404

    data = response.json()

    assert (
        data["detail"]
        == "Peer group 'INVALID' not found"
    )