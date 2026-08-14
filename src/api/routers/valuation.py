import sqlite3
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException

from src.analytics.valuation import build_valuation_summary


router = APIRouter(
    prefix="/valuation",
    tags=["Valuation"],
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "data" / "n100_financial.db"


def get_connection():
    """Create SQLite database connection."""

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection


@router.get("/{ticker}")
def get_valuation(ticker: str):
    """
    Return valuation history and valuation summary
    for a company.
    """

    ticker = ticker.upper().strip()

    connection = get_connection()
    cursor = connection.cursor()

    # Check whether company exists
    cursor.execute(
        """
        SELECT
            id,
            company_name
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

    # Get historical valuation data
    cursor.execute(
        """
        SELECT
            year,
            market_cap_crore,
            enterprise_value_crore,
            pe_ratio,
            pb_ratio,
            ev_ebitda,
            dividend_yield_pct
        FROM market_cap
        WHERE UPPER(company_id) = ?
        ORDER BY year
        """,
        (ticker,),
    )

    rows = cursor.fetchall()

    connection.close()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Valuation data for '{ticker}' not found",
        )

    valuation_df = pd.DataFrame(
        [dict(row) for row in rows]
    )

    summary = build_valuation_summary(
        valuation_df
    )

    history = (
        valuation_df
        .where(pd.notnull(valuation_df), None)
        .to_dict(orient="records")
    )

    return {
        "ticker": ticker,
        "company_name": company["company_name"],
        "record_count": len(history),
        "summary": summary,
        "history": history,
    }