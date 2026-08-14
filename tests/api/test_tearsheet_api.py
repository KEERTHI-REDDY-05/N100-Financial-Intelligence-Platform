from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_tcs_tearsheet():
    response = client.get(
        "/api/v1/companies/TCS/tearsheet"
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 0


def test_tcs_tearsheet_is_pdf():
    response = client.get(
        "/api/v1/companies/TCS/tearsheet"
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_invalid_company_tearsheet():
    response = client.get(
        "/api/v1/companies/INVALID/tearsheet"
    )

    assert response.status_code == 404