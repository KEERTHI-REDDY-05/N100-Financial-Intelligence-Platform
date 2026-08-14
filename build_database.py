from pathlib import Path
import sqlite3
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "n100_financial.db"


FILES = {
    "companies": ("companies.xlsx", 1),
    "profitandloss": ("profitandloss.xlsx", 1),
    "balancesheet": ("balancesheet.xlsx", 1),
    "cashflow": ("cashflow.xlsx", 1),
    "financial_ratios": ("financial_ratios.xlsx", 0),
    "sectors": ("sectors.xlsx", 0),
    "peer_groups": ("peer_groups.xlsx", 0),
    "market_cap": ("market_cap.xlsx", 0),
    "documents": ("documents.xlsx", 1),
    "prosandcons": ("prosandcons.xlsx", 1),
}


def clean_columns(df):
    """
    Standardise column names before loading into SQLite.
    """

    df = df.copy()

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("/", "_", regex=False)
        .str.replace("-", "_", regex=False)
        .str.replace("%", "pct", regex=False)
        .str.replace("(", "", regex=False)
        .str.replace(")", "", regex=False)
    )

    return df


def build_database():
    """
    Load the 10 core Excel datasets into SQLite.
    """

    connection = sqlite3.connect(DB_PATH)

    print(f"Database: {DB_PATH}")
    print()

    for table_name, (file_name, skiprows) in FILES.items():

        file_path = DATA_DIR / file_name

        if not file_path.exists():
            print(f"SKIPPED: {file_name} not found")
            continue

        df = pd.read_excel(
            file_path,
            skiprows=skiprows,
            engine="openpyxl",
        )

        df = clean_columns(df)

        df.to_sql(
            table_name,
            connection,
            if_exists="replace",
            index=False,
        )

        print(
            f"{table_name:<20} "
            f"{len(df):>6} rows"
        )

    connection.commit()

    print()
    print("DATABASE TABLE COUNTS")
    print("=" * 50)

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

    tables = [
        row[0]
        for row in cursor.fetchall()
    ]

    for table in tables:
        cursor.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        )

        count = cursor.fetchone()[0]

        print(
            f"{table:<20} "
            f"{count:>6}"
        )

    print()
    print(
        f"Total tables created: {len(tables)}"
    )

    connection.close()


if __name__ == "__main__":
    build_database()