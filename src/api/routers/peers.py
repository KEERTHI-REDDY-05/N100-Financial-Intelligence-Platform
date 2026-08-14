import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException


router = APIRouter(
    prefix="/peers",
    tags=["Peers"],
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "data" / "n100_financial.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


@router.get("/{group_name}")
def get_peer_group(group_name: str):
    """
    Return all companies in a peer group
    with percentile ranks for 10 financial metrics.
    """

    connection = get_connection()
    cursor = connection.cursor()

    # Check peer group exists
    cursor.execute(
        """
        SELECT DISTINCT peer_group_name
        FROM peer_groups
        WHERE LOWER(peer_group_name) = LOWER(?)
        """,
        (group_name,),
    )

    group = cursor.fetchone()

    if group is None:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail=f"Peer group '{group_name}' not found",
        )

    actual_group = group["peer_group_name"]

    metrics = [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "free_cash_flow_cr",
        "earnings_per_share",
        "dividend_payout_ratio_pct",
        "cash_from_operations_cr",
    ]

    # Latest ratio row per company
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

    latest_ratios = {
        row["company_id"]: dict(row)
        for row in cursor.fetchall()
    }

    # Companies in peer group
    cursor.execute(
        """
        SELECT
            pg.company_id,
            pg.is_benchmark,
            c.company_name
        FROM peer_groups pg
        LEFT JOIN companies c
            ON pg.company_id = c.id
        WHERE LOWER(pg.peer_group_name) = LOWER(?)
        ORDER BY pg.company_id
        """,
        (actual_group,),
    )

    peer_rows = cursor.fetchall()

    records = []

    for row in peer_rows:

        company_id = row["company_id"]

        ratio = latest_ratios.get(
            company_id,
            {}
        )

        record = {
            "company_id": company_id,
            "company_name": row["company_name"],
            "is_benchmark": row["is_benchmark"],
        }

        for metric in metrics:
            record[metric] = ratio.get(metric)

        records.append(record)

    # Percentile ranks within peer group
    for metric in metrics:

        valid_values = [
            record[metric]
            for record in records
            if record[metric] is not None
        ]

        if not valid_values:
            for record in records:
                record[f"{metric}_percentile"] = None

            continue

        sorted_values = sorted(valid_values)

        for record in records:

            value = record[metric]

            if value is None:
                record[f"{metric}_percentile"] = None
                continue

            less_or_equal = sum(
                1
                for v in sorted_values
                if v <= value
            )

            percentile = (
                less_or_equal
                / len(sorted_values)
            ) * 100

            record[
                f"{metric}_percentile"
            ] = round(
                percentile,
                2,
            )

    connection.close()

    return {
        "peer_group": actual_group,
        "count": len(records),
        "companies": records,
    }