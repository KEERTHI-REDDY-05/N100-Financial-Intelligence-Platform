from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_portfolio_clusters():
    response = client.get(
        "/api/v1/portfolio/clusters"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 5
    assert data["total_companies"] == 92
    assert len(data["clusters"]) == 5


def test_cluster_company_total():
    response = client.get(
        "/api/v1/portfolio/clusters"
    )

    data = response.json()

    total = sum(
        cluster["company_count"]
        for cluster in data["clusters"]
    )

    assert total == 92


def test_cluster_structure():
    response = client.get(
        "/api/v1/portfolio/clusters"
    )

    clusters = response.json()["clusters"]

    for cluster in clusters:
        assert "cluster_id" in cluster
        assert "cluster_name" in cluster
        assert "company_count" in cluster
        assert "companies" in cluster


def test_portfolio_stats():
    response = client.get(
        "/api/v1/portfolio/stats"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 10
    assert len(data["statistics"]) == 10


def test_portfolio_stats_structure():
    response = client.get(
        "/api/v1/portfolio/stats"
    )

    statistics = response.json()["statistics"]

    required_fields = {
        "kpi",
        "P10",
        "P25",
        "P50",
        "P75",
        "P90",
        "Mean",
        "Std",
    }

    for item in statistics:
        assert required_fields.issubset(
            item.keys()
        )