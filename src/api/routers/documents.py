import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "data" / "n100_financial.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@router.get("/{ticker}")
def get_documents(ticker: str):
    """
    Return annual-report document links for a company.
    """

    ticker = ticker.upper().strip()

    connection = get_connection()
    cursor = connection.cursor()

    # Check company exists
    cursor.execute(
        """
        SELECT id, company_name
        FROM companies
        WHERE UPPER(id) = ?
        """,
        (ticker,),
    )

    company = cursor.fetchone()

    if company is None:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail=f"Company '{ticker}' not found",
        )

    cursor.execute(
        """
        SELECT
            id,
            company_id,
            year,
            annual_report
        FROM documents
        WHERE UPPER(company_id) = ?
        ORDER BY
            CAST(
                SUBSTR(year, LENGTH(year) - 3, 4)
                AS INTEGER
            ) DESC,
            id DESC
        """,
        (ticker,),
    )

    rows = cursor.fetchall()

    connection.close()

    return {
        "ticker": ticker,
        "company_name": company["company_name"],
        "count": len(rows),
        "documents": [
            dict(row)
            for row in rows
        ],
    }