from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

ANALYSIS_FILE = DATA_DIR / "analysis.xlsx"
PARSED_OUTPUT = OUTPUT_DIR / "analysis_parsed.csv"
FAILURE_OUTPUT = OUTPUT_DIR / "parse_failures.csv"

TARGET_COLUMNS = [
    "compounded_sales_growth",
    "compounded_profit_growth",
    "stock_price_cagr",
    "roe",
]

PATTERN = re.compile(
    r"(\d+)\s*Years?\s*:?\s*([\d.]+)\s*%",
    re.IGNORECASE,
)


def load_analysis_data() -> pd.DataFrame:
    """
    Load analysis.xlsx.

    The project file contains a title row above the actual column headers,
    so header=1 is used.
    """
    if not ANALYSIS_FILE.exists():
        raise FileNotFoundError(
            f"analysis.xlsx not found at: {ANALYSIS_FILE}"
        )

    df = pd.read_excel(ANALYSIS_FILE, header=1)

    df.columns = [
        str(column).strip().lower()
        for column in df.columns
    ]

    if "company_id" not in df.columns:
        raise ValueError(
            "The analysis file does not contain a company_id column."
        )

    missing_columns = [
        column
        for column in TARGET_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    return df


def parse_analysis_text(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    parsed_rows: list[dict] = []
    failure_rows: list[dict] = []

    for _, row in df.iterrows():
        company_id = row.get("company_id")

        if pd.isna(company_id):
            continue

        company_id = str(company_id).strip()

        for metric_type in TARGET_COLUMNS:
            raw_value = row.get(metric_type)

            if pd.isna(raw_value):
                continue

            original_text = str(raw_value).strip()

            if not original_text:
                continue

            matches = PATTERN.findall(original_text)

            if not matches:
                failure_rows.append(
                    {
                        "company_id": company_id,
                        "metric_type": metric_type,
                        "original_text": original_text,
                        "failure_reason": "No regex match",
                    }
                )
                continue

            for period_years, value_pct in matches:
                try:
                    parsed_rows.append(
                        {
                            "company_id": company_id,
                            "metric_type": metric_type,
                            "period_years": int(period_years),
                            "value_pct": float(value_pct),
                        }
                    )
                except ValueError:
                    failure_rows.append(
                        {
                            "company_id": company_id,
                            "metric_type": metric_type,
                            "original_text": original_text,
                            "failure_reason": (
                                "Unable to convert period or percentage"
                            ),
                        }
                    )

    parsed_df = pd.DataFrame(
        parsed_rows,
        columns=[
            "company_id",
            "metric_type",
            "period_years",
            "value_pct",
        ],
    )

    failures_df = pd.DataFrame(
        failure_rows,
        columns=[
            "company_id",
            "metric_type",
            "original_text",
            "failure_reason",
        ],
    )

    return parsed_df, failures_df


def save_outputs(
    parsed_df: pd.DataFrame,
    failures_df: pd.DataFrame,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    parsed_df.to_csv(PARSED_OUTPUT, index=False)
    failures_df.to_csv(FAILURE_OUTPUT, index=False)


def main() -> None:
    print("Loading analysis.xlsx...")

    analysis_df = load_analysis_data()

    print(f"Rows loaded: {len(analysis_df)}")

    parsed_df, failures_df = parse_analysis_text(analysis_df)

    save_outputs(parsed_df, failures_df)

    print("\nDay 29 parser completed.")
    print(f"Parsed records: {len(parsed_df)}")
    print(f"Parse failures: {len(failures_df)}")
    print(f"Created: {PARSED_OUTPUT}")
    print(f"Created: {FAILURE_OUTPUT}")


if __name__ == "__main__":
    main()