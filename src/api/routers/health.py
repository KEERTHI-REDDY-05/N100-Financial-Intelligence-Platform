import sqlite3
import time
from pathlib import Path

from fastapi import APIRouter


router = APIRouter(tags=["Health"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "data" / "n100_financial.db"

START_TIME = time.time()


def get_database_counts():
    """
    Return row counts for all available SQLite tables.
    """

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    )

    tables = [row[0] for row in cursor.fetchall()]
    row_counts = {}

    for table in tables:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
            row_counts[table] = cursor.fetchone()[0]
        except sqlite3.Error:
            row_counts[table] = None

    connection.close()
    return row_counts


@router.get("/health")
def health_check():
    """
    Return API health and database row counts.
    """

    uptime_seconds = round(
        time.time() - START_TIME,
        2,
    )

    return {
        "status": "ok",
        "db_row_counts": get_database_counts(),
        "uptime_seconds": uptime_seconds,
        "version": "1.0.0",
    }