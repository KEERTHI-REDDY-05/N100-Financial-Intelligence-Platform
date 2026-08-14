import time

from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)

MAX_RESPONSE_TIME = 0.5  # 500 milliseconds


def check_response_time(url):
    start = time.perf_counter()

    response = client.get(url)

    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed < MAX_RESPONSE_TIME, (
        f"{url} took {elapsed * 1000:.2f} ms"
    )


def test_health_performance():
    check_response_time("/api/v1/health")


def test_companies_performance():
    check_response_time("/api/v1/companies")


def test_screener_performance():
    check_response_time("/api/v1/screener")


def test_sectors_performance():
    check_response_time("/api/v1/sectors")


def test_portfolio_clusters_performance():
    check_response_time("/api/v1/portfolio/clusters")


def test_portfolio_stats_performance():
    check_response_time("/api/v1/portfolio/stats")


def test_tcs_ratios_performance():
    check_response_time(
        "/api/v1/companies/TCS/ratios"
    )


def test_tcs_valuation_performance():
    check_response_time(
        "/api/v1/valuation/TCS"
    )