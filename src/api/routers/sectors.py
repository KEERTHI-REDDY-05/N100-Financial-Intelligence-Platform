import sqlite3
from pathlib import Path
from statistics import median

from fastapi import APIRouter, HTTPException


router = APIRouter(
    prefix="/sectors",
    tags=["Sectors"],
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "data" / "n100_financial.db"


def get_connection():
    """Create SQLite connection."""

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def get_latest_ratio_rows(connection):
    """Return exactly one latest ratio row per company."""

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM (
            SELECT
                fr.*,
                ROW_NUMBER() OVER (
                    PARTITION BY fr.company_id
                    ORDER BY
                        CAST(
                            SUBSTR(
                                fr.year,
                                LENGTH(fr.year) - 3,
                                4
                            ) AS INTEGER
                        ) DESC,
                        fr.id DESC
                ) AS rn
            FROM financial_ratios fr
        )
        WHERE rn = 1
        """
    )

    return {
        row["company_id"]: dict(row)
        for row in cursor.fetchall()
    }


def get_latest_market_rows(connection):
    """Return exactly one latest market-cap row per company."""

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM (
            SELECT
                mc.*,
                ROW_NUMBER() OVER (
                    PARTITION BY mc.company_id
                    ORDER BY
                        CAST(
                            SUBSTR(
                                mc.year,
                                LENGTH(mc.year) - 3,
                                4
                            ) AS INTEGER
                        ) DESC,
                        mc.id DESC
                ) AS rn
            FROM market_cap mc
        )
        WHERE rn = 1
        """
    )

    return {
        row["company_id"]: dict(row)
        for row in cursor.fetchall()
    }


@router.get("")
def get_sectors():
    """
    Return all sectors with company count
    and median ROE, P/E and D/E.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            company_id,
            broad_sector
        FROM sectors
        WHERE broad_sector IS NOT NULL
        ORDER BY broad_sector
        """
    )

    sector_rows = cursor.fetchall()

    latest_ratios = get_latest_ratio_rows(connection)
    latest_market = get_latest_market_rows(connection)

    grouped = {}

    for row in sector_rows:

        company_id = row["company_id"]
        sector = row["broad_sector"]

        if sector not in grouped:
            grouped[sector] = {
                "company_ids": [],
                "roe": [],
                "de": [],
                "pe": [],
            }

        grouped[sector]["company_ids"].append(
            company_id
        )

        ratio = latest_ratios.get(company_id)

        if ratio:

            roe = ratio.get(
                "return_on_equity_pct"
            )

            de = ratio.get(
                "debt_to_equity"
            )

            if roe is not None:
                grouped[sector]["roe"].append(
                    roe
                )

            if de is not None:
                grouped[sector]["de"].append(
                    de
                )

        market = latest_market.get(company_id)

        if market:

            pe = market.get("pe_ratio")

            if pe is not None:
                grouped[sector]["pe"].append(
                    pe
                )

    results = []

    for sector, values in sorted(
        grouped.items()
    ):

        results.append(
            {
                "sector": sector,
                "company_count": len(
                    values["company_ids"]
                ),
                "median_roe": round(
                    median(values["roe"]),
                    2,
                )
                if values["roe"]
                else None,
                "median_pe": round(
                    median(values["pe"]),
                    2,
                )
                if values["pe"]
                else None,
                "median_de": round(
                    median(values["de"]),
                    4,
                )
                if values["de"]
                else None,
            }
        )

    connection.close()

    return {
        "count": len(results),
        "sectors": results,
    }


@router.get("/{sector}/companies")
def get_sector_companies(sector: str):
    """
    Return all companies in a sector
    with latest financial KPIs.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT DISTINCT broad_sector
        FROM sectors
        WHERE LOWER(broad_sector) = LOWER(?)
        """,
        (sector,),
    )

    sector_match = cursor.fetchone()

    if sector_match is None:

        connection.close()

        raise HTTPException(
            status_code=404,
            detail=f"Sector '{sector}' not found",
        )

    actual_sector = sector_match[
        "broad_sector"
    ]

    latest_ratios = get_latest_ratio_rows(
        connection
    )

    latest_market = get_latest_market_rows(
        connection
    )

    cursor.execute(
        """
        SELECT
            c.id,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            s.market_cap_category
        FROM companies c

        INNER JOIN sectors s
            ON c.id = s.company_id

        WHERE LOWER(s.broad_sector)
            = LOWER(?)

        ORDER BY c.company_name
        """,
        (actual_sector,),
    )

    rows = cursor.fetchall()

    results = []

    for row in rows:

        company = dict(row)

        ratio = latest_ratios.get(
            company["id"]
        )

        market = latest_market.get(
            company["id"]
        )

        company["roe_pct"] = (
            ratio.get(
                "return_on_equity_pct"
            )
            if ratio
            else None
        )

        company["debt_to_equity"] = (
            ratio.get("debt_to_equity")
            if ratio
            else None
        )

        company["free_cash_flow_cr"] = (
            ratio.get("free_cash_flow_cr")
            if ratio
            else None
        )

        company["pe_ratio"] = (
            market.get("pe_ratio")
            if market
            else None
        )

        results.append(company)

    connection.close()

    return {
        "sector": actual_sector,
        "count": len(results),
        "companies": results,
    }