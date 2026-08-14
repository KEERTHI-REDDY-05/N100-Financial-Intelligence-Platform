import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter


router = APIRouter(
    prefix="/screener",
    tags=["Screener"],
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "data" / "n100_financial.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@router.get("")
def get_screener(
    min_roe: Optional[float] = None,
    max_de: Optional[float] = None,
    min_fcf: Optional[float] = None,
    sector: Optional[str] = None,
    min_rev_cagr_5yr: Optional[float] = None,
    min_pat_cagr_5yr: Optional[float] = None,
    max_pe: Optional[float] = None,
):
    """
    Screen companies using financial and valuation filters.
    """

    connection = get_connection()
    cursor = connection.cursor()

    # Latest financial ratio year available per company
    query = """
        WITH latest_ratios AS (
    SELECT *
    FROM (
        SELECT
            fr.*,
            ROW_NUMBER() OVER (
                PARTITION BY fr.company_id
                ORDER BY
                    CAST(
                        SUBSTR(fr.year, LENGTH(fr.year) - 3, 4)
                        AS INTEGER
                    ) DESC,
                    fr.id DESC
            ) AS rn
        FROM financial_ratios fr
    )
    WHERE rn = 1
),

latest_market AS (
            SELECT mc.*
            FROM market_cap mc
            INNER JOIN (
                SELECT
                    company_id,
                    MAX(
                        CAST(
                            SUBSTR(year, LENGTH(year) - 3, 4)
                            AS INTEGER
                        )
                    ) AS latest_year
                FROM market_cap
                GROUP BY company_id
            ) x
                ON mc.company_id = x.company_id
                AND CAST(
                    SUBSTR(mc.year, LENGTH(mc.year) - 3, 4)
                    AS INTEGER
                ) = x.latest_year
        ),

        annual_pl AS (
            SELECT
                company_id,
                CAST(
                    SUBSTR(year, LENGTH(year) - 3, 4)
                    AS INTEGER
                ) AS financial_year,
                sales,
                net_profit
            FROM profitandloss
            WHERE year LIKE '%____'
        ),

        pl_ranked AS (
            SELECT
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY company_id
                    ORDER BY financial_year DESC
                ) AS rn
            FROM annual_pl
        ),

        growth AS (
            SELECT
                latest.company_id,

                CASE
                    WHEN old.sales > 0
                    AND latest.sales > 0
                    THEN (
                        POWER(
                            latest.sales * 1.0 / old.sales,
                            1.0 / 5.0
                        ) - 1
                    ) * 100
                END AS rev_cagr_5yr,

                CASE
                    WHEN old.net_profit > 0
                    AND latest.net_profit > 0
                    THEN (
                        POWER(
                            latest.net_profit * 1.0 / old.net_profit,
                            1.0 / 5.0
                        ) - 1
                    ) * 100
                END AS pat_cagr_5yr

            FROM pl_ranked latest

            LEFT JOIN pl_ranked old
                ON latest.company_id = old.company_id
                AND old.rn = 6

            WHERE latest.rn = 1
        )

        SELECT DISTINCT
            c.id AS ticker,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            s.market_cap_category,

            lr.return_on_equity_pct AS roe_pct,
            lr.debt_to_equity,
            lr.free_cash_flow_cr,

            lm.pe_ratio,

            g.rev_cagr_5yr,
            g.pat_cagr_5yr

        FROM companies c

        LEFT JOIN sectors s
            ON c.id = s.company_id

        LEFT JOIN latest_ratios lr
            ON c.id = lr.company_id

        LEFT JOIN latest_market lm
            ON c.id = lm.company_id

        LEFT JOIN growth g
            ON c.id = g.company_id

        WHERE 1 = 1
    """

    parameters = []

    if min_roe is not None:
        query += " AND lr.return_on_equity_pct >= ?"
        parameters.append(min_roe)

    if max_de is not None:
        query += " AND lr.debt_to_equity <= ?"
        parameters.append(max_de)

    if min_fcf is not None:
        query += " AND lr.free_cash_flow_cr >= ?"
        parameters.append(min_fcf)

    if sector:
        query += " AND LOWER(s.broad_sector) = LOWER(?)"
        parameters.append(sector)

    if min_rev_cagr_5yr is not None:
        query += " AND g.rev_cagr_5yr >= ?"
        parameters.append(min_rev_cagr_5yr)

    if min_pat_cagr_5yr is not None:
        query += " AND g.pat_cagr_5yr >= ?"
        parameters.append(min_pat_cagr_5yr)

    if max_pe is not None:
        query += " AND lm.pe_ratio <= ?"
        parameters.append(max_pe)

    query += " ORDER BY c.company_name"

    cursor.execute(query, parameters)

    rows = cursor.fetchall()

    connection.close()

    return {
        "count": len(rows),
        "results": [
            dict(row)
            for row in rows
        ],
    }