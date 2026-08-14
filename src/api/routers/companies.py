import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "data" / "n100_financial.db"


def get_connection():
    """Create a SQLite database connection."""

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection


@router.get("")
def get_companies(
    sector: Optional[str] = None,
    market_cap_category: Optional[str] = None,
    search: Optional[str] = None,
):
    """
    Return all companies with optional sector,
    market-cap and company search filters.
    """

    connection = get_connection()
    cursor = connection.cursor()

    query = """
        SELECT
            c.id,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            s.market_cap_category,
            c.roe_percentage AS roe_pct,
            c.roce_percentage AS roce_pct
        FROM companies c
        LEFT JOIN sectors s
            ON c.id = s.company_id
        WHERE 1 = 1
    """

    parameters = []

    if sector:
        query += """
            AND LOWER(s.broad_sector) = LOWER(?)
        """

        parameters.append(sector)

    if market_cap_category:
        query += """
            AND LOWER(s.market_cap_category) = LOWER(?)
        """

        parameters.append(
            market_cap_category
        )

    if search:
        query += """
            AND (
                LOWER(c.company_name)
                    LIKE LOWER(?)
                OR LOWER(CAST(c.id AS TEXT))
                    LIKE LOWER(?)
            )
        """

        search_value = f"%{search}%"

        parameters.extend(
            [
                search_value,
                search_value,
            ]
        )

    query += """
        ORDER BY c.company_name
    """

    cursor.execute(
        query,
        parameters,
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]
@router.get("/{ticker}")
def get_company_profile(ticker: str):
    """
    Return full company profile with sector data
    and latest financial KPIs.
    """

    connection = get_connection()
    cursor = connection.cursor()

    # -----------------------------------------------------
    # Company profile + sector information
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT
            c.*,
            s.broad_sector,
            s.sub_sector,
            s.index_weight_pct,
            s.market_cap_category
        FROM companies c
        LEFT JOIN sectors s
            ON c.id = s.company_id
        WHERE UPPER(c.id) = UPPER(?)
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

    company_data = dict(company)

    # -----------------------------------------------------
    # Latest financial ratios
    # -----------------------------------------------------

    cursor.execute(
        """
        SELECT *
        FROM financial_ratios
        WHERE UPPER(company_id) = UPPER(?)
        ORDER BY
            CAST(
                SUBSTR(year, LENGTH(year) - 3, 4)
                AS INTEGER
            ) DESC
        LIMIT 1
        """,
        (ticker,),
    )

    latest_ratios = cursor.fetchone()

    if latest_ratios:
        company_data["latest_kpis"] = dict(
            latest_ratios
        )
    else:
        company_data["latest_kpis"] = None

    connection.close()

    return company_data
@router.get("/{ticker}/pl")
def get_profit_and_loss(
    ticker: str,
    from_year: Optional[str] = None,
    to_year: Optional[str] = None,
):
    """
    Return profit and loss history for a company
    with optional year filters.
    """

    connection = get_connection()
    cursor = connection.cursor()

    # Check whether company exists
    cursor.execute(
        """
        SELECT id
        FROM companies
        WHERE UPPER(id) = UPPER(?)
        """,
        (ticker,),
    )

    if cursor.fetchone() is None:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail=f"Company '{ticker}' not found",
        )

    query = """
        SELECT
            id,
            company_id,
            year,
            sales,
            expenses,
            operating_profit,
            opm_percentage,
            other_income,
            interest,
            depreciation,
            profit_before_tax,
            tax_percentage,
            net_profit,
            eps,
            dividend_payout
        FROM profitandloss
        WHERE UPPER(company_id) = UPPER(?)
    """

    parameters = [ticker]

    if from_year:
        query += """
            AND CAST(
                SUBSTR(year, LENGTH(year) - 3, 4)
                AS INTEGER
            ) >= ?
        """

        parameters.append(
            int(from_year[-4:])
        )

    if to_year:
        query += """
            AND CAST(
                SUBSTR(year, LENGTH(year) - 3, 4)
                AS INTEGER
            ) <= ?
        """

        parameters.append(
            int(to_year[-4:])
        )

    query += """
        ORDER BY
            CAST(
                SUBSTR(year, LENGTH(year) - 3, 4)
                AS INTEGER
            )
    """

    cursor.execute(
        query,
        parameters,
    )

    rows = cursor.fetchall()

    connection.close()

    return {
        "ticker": ticker.upper(),
        "record_count": len(rows),
        "history": [
            dict(row)
            for row in rows
        ],
    }
@router.get("/{ticker}/bs")
def get_balance_sheet(
    ticker: str,
    from_year: Optional[str] = None,
    to_year: Optional[str] = None,
):
    """
    Return balance sheet history for a company
    with optional year filters.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM companies
        WHERE UPPER(id) = UPPER(?)
        """,
        (ticker,),
    )

    if cursor.fetchone() is None:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail=f"Company '{ticker}' not found",
        )

    query = """
        SELECT
            id,
            company_id,
            year,
            equity_capital,
            reserves,
            borrowings,
            other_liabilities,
            total_liabilities,
            fixed_assets,
            cwip,
            investments,
            other_asset,
            total_assets
        FROM balancesheet
        WHERE UPPER(company_id) = UPPER(?)
    """

    parameters = [ticker]

    if from_year:
        query += """
            AND CAST(
                SUBSTR(year, LENGTH(year) - 3, 4)
                AS INTEGER
            ) >= ?
        """

        parameters.append(
            int(from_year[-4:])
        )

    if to_year:
        query += """
            AND CAST(
                SUBSTR(year, LENGTH(year) - 3, 4)
                AS INTEGER
            ) <= ?
        """

        parameters.append(
            int(to_year[-4:])
        )

    query += """
        ORDER BY
            CAST(
                SUBSTR(year, LENGTH(year) - 3, 4)
                AS INTEGER
            )
    """

    cursor.execute(
        query,
        parameters,
    )

    rows = cursor.fetchall()

    connection.close()

    return {
        "ticker": ticker.upper(),
        "record_count": len(rows),
        "history": [
            dict(row)
            for row in rows
        ],
    }
@router.get("/{ticker}/cashflow")
def get_cashflow(
    ticker: str,
    from_year: Optional[str] = None,
    to_year: Optional[str] = None,
):
    """
    Return deduplicated cash-flow history for a company
    with optional year filters.
    """

    connection = get_connection()
    cursor = connection.cursor()

    # Check company exists
    cursor.execute(
        """
        SELECT id
        FROM companies
        WHERE UPPER(id) = UPPER(?)
        """,
        (ticker,),
    )

    if cursor.fetchone() is None:
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
            operating_activity,
            investing_activity,
            financing_activity,
            net_cash_flow
        FROM cashflow
        WHERE UPPER(company_id) = UPPER(?)
        """,
        (ticker,),
    )

    rows = cursor.fetchall()
    connection.close()

    # -----------------------------------------------------
    # Normalize year formats such as:
    # Mar-20  -> 2020
    # Mar 2020 -> 2020
    # -----------------------------------------------------

    def extract_year(year_value):
        text = str(year_value).strip()

        # Format: Mar 2020
        if len(text) >= 4 and text[-4:].isdigit():
            value = int(text[-4:])

            if value >= 1900:
                return value

        # Format: Mar-20
        if len(text) >= 2 and text[-2:].isdigit():
            value = int(text[-2:])

            if value <= 50:
                return 2000 + value

            return 1900 + value

        return None

    # -----------------------------------------------------
    # Deduplicate by financial year
    # Prefer the full four-digit year record
    # -----------------------------------------------------

    records_by_year = {}

    for row in rows:

        record = dict(row)
        numeric_year = extract_year(
            record["year"]
        )

        if numeric_year is None:
            continue

        # Apply optional filters
        if from_year is not None:
            if numeric_year < int(from_year[-4:]):
                continue

        if to_year is not None:
            if numeric_year > int(to_year[-4:]):
                continue

        existing = records_by_year.get(
            numeric_year
        )

        if existing is None:
            records_by_year[numeric_year] = record

        else:
            # Prefer format like "Mar 2024"
            # instead of abbreviated "Mar-24"
            existing_year = str(
                existing["year"]
            )

            current_year = str(
                record["year"]
            )

            if (
                len(current_year) > len(existing_year)
            ):
                records_by_year[
                    numeric_year
                ] = record

    # Sort chronologically
    sorted_years = sorted(
        records_by_year.keys()
    )

    history = [
        records_by_year[year]
        for year in sorted_years
    ]

    return {
        "ticker": ticker.upper(),
        "record_count": len(history),
        "history": history,
    }
@router.get("/{ticker}/ratios")
def get_ratios(
    ticker: str,
    year: Optional[str] = None,
):
    """
    Return computed financial ratios for a company.
    Optionally filter by year.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM companies
        WHERE UPPER(id) = UPPER(?)
        """,
        (ticker,),
    )

    if cursor.fetchone() is None:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail=f"Company '{ticker}' not found",
        )

    query = """
        SELECT *
        FROM financial_ratios
        WHERE UPPER(company_id) = UPPER(?)
    """

    parameters = [ticker]

    if year:
        numeric_year = int(year[-4:])

        query += """
            AND CAST(
                SUBSTR(year, LENGTH(year) - 3, 4)
                AS INTEGER
            ) = ?
        """

        parameters.append(numeric_year)

    query += """
        ORDER BY
            CAST(
                SUBSTR(year, LENGTH(year) - 3, 4)
                AS INTEGER
            )
    """

    cursor.execute(
        query,
        parameters,
    )

    rows = cursor.fetchall()

    connection.close()

    return {
        "ticker": ticker.upper(),
        "record_count": len(rows),
        "ratios": [
            dict(row)
            for row in rows
        ],
    }
@router.get("/{ticker}/tearsheet")
def get_tearsheet(ticker: str):
    """
    Return the pre-generated company tearsheet PDF.
    """

    tearsheet_dir = (
        PROJECT_ROOT
        / "reports"
        / "tearsheets"
    )

    pdf_path = (
        tearsheet_dir
        / f"{ticker.upper()}_tearsheet.pdf"
    )

    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Tearsheet for '{ticker}' not found",
        )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{ticker.upper()}_tearsheet.pdf",
    )