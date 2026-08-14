from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_tcs_documents():
    response = client.get(
        "/api/v1/documents/TCS"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["ticker"] == "TCS"
    assert data["company_name"] == "Tata Consultancy Services Ltd"
    assert data["count"] == 16
    assert len(data["documents"]) == 16


def test_tcs_latest_document():
    response = client.get(
        "/api/v1/documents/TCS"
    )

    data = response.json()

    latest = data["documents"][0]

    assert latest["company_id"] == "TCS"
    assert latest["year"] == 2024
    assert latest["annual_report"] is not None


def test_tcs_document_structure():
    response = client.get(
        "/api/v1/documents/TCS"
    )

    documents = response.json()["documents"]

    for document in documents:
        assert "id" in document
        assert "company_id" in document
        assert "year" in document
        assert "annual_report" in document


def test_invalid_company_documents():
    response = client.get(
        "/api/v1/documents/INVALID"
    )

    assert response.status_code == 404

    data = response.json()

    assert data["detail"] == "Company 'INVALID' not found"