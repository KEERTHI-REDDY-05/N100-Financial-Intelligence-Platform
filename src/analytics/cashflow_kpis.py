from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# ============================================================
# Project paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

COMPANIES_FILE = DATA_DIR / "companies.xlsx"
SECTORS_FILE = DATA_DIR / "sectors.xlsx"
PROFIT_LOSS_FILE = DATA_DIR / "profitandloss.xlsx"
BALANCE_SHEET_FILE = DATA_DIR / "balancesheet.xlsx"
CASHFLOW_FILE = DATA_DIR / "cashflow.xlsx"

CASHFLOW_OUTPUT = OUTPUT_DIR / "cashflow_intelligence.xlsx"
DISTRESS_OUTPUT = OUTPUT_DIR / "distress_alerts.csv"
CAPITAL_ALLOCATION_OUTPUT = OUTPUT_DIR / "capital_allocation.csv"
DISTRIBUTION_OUTPUT = OUTPUT_DIR / "capital_allocation_distribution.csv"
PATTERN_CHANGES_OUTPUT = OUTPUT_DIR / "pattern_changes.csv"


# ============================================================
# Data-loading helpers
# ============================================================

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names."""
    result = df.copy()
    result.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in result.columns
    ]
    return result


def load_excel(path: Path, header: int) -> pd.DataFrame:
    """Load an Excel file with a specific header row."""
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")

    return clean_columns(pd.read_excel(path, header=header))


def normalize_company_id(value: Any) -> str:
    """Normalize company ticker/company ID."""
    if pd.isna(value):
        return ""

    return str(value).strip().upper()


def extract_year(value: Any) -> float:
    """
    Extract years from values such as:
    Mar-13, Mar 2014, Dec 2025, or 2024.
    """
    if pd.isna(value):
        return np.nan

    text = str(value).strip()

    four_digit = re.search(r"\b(?:19|20)\d{2}\b", text)

    if four_digit:
        return float(four_digit.group())

    two_digit = re.search(
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"[\s\-]*(\d{2})",
        text,
        flags=re.IGNORECASE,
    )

    if two_digit:
        year = int(two_digit.group(1))

        if year <= 50:
            return float(2000 + year)

        return float(1900 + year)

    return np.nan


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize company IDs, years and numeric columns."""
    result = df.copy()

    if "company_id" in result.columns:
        result["company_id"] = result[
            "company_id"
        ].apply(normalize_company_id)

    if "year" in result.columns:
        result["year_number"] = result["year"].apply(extract_year)
        result = result.dropna(subset=["company_id", "year_number"])
        result["year_number"] = result["year_number"].astype(int)

    return result


def load_project_data() -> dict[str, pd.DataFrame]:
    """
    Load the existing project datasets.

    The title-row files use header=1.
    sectors.xlsx uses its normal first row as the header.
    """
    companies = load_excel(COMPANIES_FILE, header=1)
    sectors = load_excel(SECTORS_FILE, header=0)
    profit_loss = load_excel(PROFIT_LOSS_FILE, header=1)
    balance_sheet = load_excel(BALANCE_SHEET_FILE, header=1)
    cashflow = load_excel(CASHFLOW_FILE, header=1)

    if "id" not in companies.columns:
        raise ValueError(
            "companies.xlsx does not contain the required id column."
        )

    companies = companies.rename(columns={"id": "company_id"})

    companies = prepare_dataframe(companies)
    sectors = prepare_dataframe(sectors)
    profit_loss = prepare_dataframe(profit_loss)
    balance_sheet = prepare_dataframe(balance_sheet)
    cashflow = prepare_dataframe(cashflow)

    return {
        "companies": companies,
        "sectors": sectors,
        "profit_loss": profit_loss,
        "balance_sheet": balance_sheet,
        "cashflow": cashflow,
    }


# ============================================================
# General calculation helpers
# ============================================================

def safe_float(value: Any) -> float:
    """Convert a value to a finite float or return NaN."""
    try:
        result = float(value)

        if np.isfinite(result):
            return result

        return np.nan
    except (TypeError, ValueError):
        return np.nan


def safe_divide(
    numerator: Any,
    denominator: Any,
) -> float:
    """Safely divide two numbers."""
    numerator_value = safe_float(numerator)
    denominator_value = safe_float(denominator)

    if (
        pd.isna(numerator_value)
        or pd.isna(denominator_value)
        or denominator_value == 0
    ):
        return np.nan

    return numerator_value / denominator_value


def calculate_cagr(
    starting_value: Any,
    ending_value: Any,
    periods: int,
) -> float:
    """
    Calculate CAGR only when starting and ending values are positive.

    CAGR is not mathematically meaningful when FCF starts or ends
    at zero or a negative value.
    """
    start = safe_float(starting_value)
    end = safe_float(ending_value)

    if (
        pd.isna(start)
        or pd.isna(end)
        or start <= 0
        or end <= 0
        or periods <= 0
    ):
        return np.nan

    return ((end / start) ** (1 / periods) - 1) * 100


def latest_record(df: pd.DataFrame) -> pd.Series | None:
    """Return the latest row from a company DataFrame."""
    if df.empty:
        return None

    return df.sort_values("year_number").iloc[-1]


def previous_record(df: pd.DataFrame) -> pd.Series | None:
    """Return the previous-year row."""
    if len(df) < 2:
        return None

    return df.sort_values("year_number").iloc[-2]


def get_company_rows(
    df: pd.DataFrame,
    company_id: str,
) -> pd.DataFrame:
    """Return sorted records belonging to one company."""
    if "company_id" not in df.columns:
        return pd.DataFrame()

    result = df[
        df["company_id"] == company_id
    ].copy()

    if "year_number" in result.columns:
        result = result.sort_values("year_number")

    return result


def deduplicate_years(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Keep one record for each company and financial year.

    Some financial datasets may contain duplicate company-year rows.
    """
    if df.empty:
        return df

    return (
        df.sort_values(["company_id", "year_number"])
        .drop_duplicates(
            subset=["company_id", "year_number"],
            keep="last",
        )
        .reset_index(drop=True)
    )


# ============================================================
# Classification helpers
# ============================================================

def classify_cfo_quality(score: float) -> str:
    if pd.isna(score):
        return "Insufficient Data"

    if score > 1.0:
        return "High Quality"

    if score >= 0.5:
        return "Moderate"

    return "Accrual Risk"


def classify_capex_intensity(value: float) -> str:
    if pd.isna(value):
        return "Insufficient Data"

    if value < 3:
        return "Asset Light"

    if value <= 8:
        return "Moderate"

    return "Capital Intensive"


def classify_capital_allocation(
    cfo: float,
    cfi: float,
    cff: float,
    borrowings_declining: bool,
) -> str:
    """
    Classify a company into one of eight capital-allocation patterns.
    """
    if any(pd.isna(value) for value in [cfo, cfi, cff]):
        return "Insufficient Data"

    if cfo < 0 and cff > 0:
        return "Distress Signal"

    if cfo > 0 and cff < 0 and borrowings_declining:
        return "Deleverager"

    if cfo > 0 and cfi < 0 and cff <= 0:
        return "Self-Funded Reinvestor"

    if cfo > 0 and cfi < 0 and cff > 0:
        return "Externally Funded Expansion"

    if cfo > 0 and cfi >= 0 and cff < 0:
        return "Cash Distributor"

    if cfo > 0 and cfi >= 0 and cff >= 0:
        return "Cash Accumulator"

    if cfo < 0 and cff <= 0:
        return "Cash Burn"

    return "Balanced Allocator"


# ============================================================
# Company-level calculations
# ============================================================

def merge_company_financials(
    cashflow_rows: pd.DataFrame,
    profit_rows: pd.DataFrame,
    balance_rows: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge cash-flow, profit and balance-sheet information by year.
    """
    cash_columns = [
        "company_id",
        "year_number",
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ]

    profit_columns = [
        "company_id",
        "year_number",
        "sales",
        "net_profit",
    ]

    balance_columns = [
        "company_id",
        "year_number",
        "borrowings",
    ]

    cash_subset = cashflow_rows[
        [
            column
            for column in cash_columns
            if column in cashflow_rows.columns
        ]
    ].copy()

    profit_subset = profit_rows[
        [
            column
            for column in profit_columns
            if column in profit_rows.columns
        ]
    ].copy()

    balance_subset = balance_rows[
        [
            column
            for column in balance_columns
            if column in balance_rows.columns
        ]
    ].copy()

    merged = cash_subset.merge(
        profit_subset,
        on=["company_id", "year_number"],
        how="left",
    )

    merged = merged.merge(
        balance_subset,
        on=["company_id", "year_number"],
        how="left",
    )

    for column in [
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
        "sales",
        "net_profit",
        "borrowings",
    ]:
        if column in merged.columns:
            merged[column] = pd.to_numeric(
                merged[column],
                errors="coerce",
            )

    merged["free_cash_flow"] = (
        merged["operating_activity"]
        + merged["investing_activity"]
    )

    merged["cfo_pat_ratio"] = merged.apply(
        lambda row: safe_divide(
            row["operating_activity"],
            row["net_profit"],
        )
        if pd.notna(row.get("net_profit"))
        and row.get("net_profit") > 0
        else np.nan,
        axis=1,
    )

    merged["capex_intensity_pct"] = merged.apply(
        lambda row: (
            abs(
                safe_float(row["investing_activity"])
            )
            / safe_float(row["sales"])
            * 100
        )
        if (
            pd.notna(row.get("sales"))
            and safe_float(row.get("sales")) > 0
            and pd.notna(row.get("investing_activity"))
        )
        else np.nan,
        axis=1,
    )

    merged = merged.sort_values("year_number")

    merged["previous_borrowings"] = merged[
        "borrowings"
    ].shift(1)

    merged["borrowings_declining"] = (
        merged["borrowings"]
        < merged["previous_borrowings"]
    )

    merged["distress_flag"] = (
        (merged["operating_activity"] < 0)
        & (merged["financing_activity"] > 0)
    )

    merged["deleveraging_flag"] = (
        (merged["financing_activity"] < 0)
        & merged["borrowings_declining"].fillna(False)
    )

    merged["capital_allocation_label"] = merged.apply(
        lambda row: classify_capital_allocation(
            safe_float(row["operating_activity"]),
            safe_float(row["investing_activity"]),
            safe_float(row["financing_activity"]),
            bool(row["borrowings_declining"]),
        ),
        axis=1,
    )

    return merged


def calculate_company_intelligence(
    company_id: str,
    sector: str,
    merged: pd.DataFrame,
) -> dict[str, Any]:
    """Calculate the final cash-flow intelligence row."""
    if merged.empty:
        return {
            "company_id": company_id,
            "sector": sector,
            "cfo_quality_score": np.nan,
            "cfo_quality_label": "Insufficient Data",
            "capex_intensity_pct": np.nan,
            "capex_label": "Insufficient Data",
            "fcf_cagr_5yr": np.nan,
            "fcf_conversion_pct": np.nan,
            "distress_flag": False,
            "deleveraging_flag": False,
            "capital_allocation_label": "Insufficient Data",
            "latest_year": np.nan,
            "latest_cfo": np.nan,
            "latest_cfi": np.nan,
            "latest_cff": np.nan,
            "latest_net_profit": np.nan,
            "cfo_quality_years_used": 0,
        }

    merged = merged.sort_values("year_number")
    latest = merged.iloc[-1]

    latest_five = merged.tail(5).copy()

    valid_ratios = latest_five[
        "cfo_pat_ratio"
    ].dropna()

    if valid_ratios.empty:
        cfo_quality_score = np.nan
    else:
        cfo_quality_score = float(
            valid_ratios.mean()
        )

    capex_intensity = safe_float(
        latest["capex_intensity_pct"]
    )

    fcf_cagr = np.nan

    if len(latest_five) >= 2:
        first_fcf = latest_five.iloc[0][
            "free_cash_flow"
        ]
        last_fcf = latest_five.iloc[-1][
            "free_cash_flow"
        ]

        period_count = (
            int(latest_five.iloc[-1]["year_number"])
            - int(latest_five.iloc[0]["year_number"])
        )

        fcf_cagr = calculate_cagr(
            first_fcf,
            last_fcf,
            period_count,
        )

    positive_pat_rows = latest_five[
        latest_five["net_profit"] > 0
    ]

    if positive_pat_rows.empty:
        fcf_conversion = np.nan
    else:
        average_fcf = positive_pat_rows[
            "free_cash_flow"
        ].mean()

        average_pat = positive_pat_rows[
            "net_profit"
        ].mean()

        conversion_ratio = safe_divide(
            average_fcf,
            average_pat,
        )

        if pd.isna(conversion_ratio):
            fcf_conversion = np.nan
        else:
            fcf_conversion = conversion_ratio * 100

    return {
        "company_id": company_id,
        "sector": sector,
        "cfo_quality_score": round(
            cfo_quality_score,
            4,
        )
        if pd.notna(cfo_quality_score)
        else np.nan,
        "cfo_quality_label": classify_cfo_quality(
            cfo_quality_score
        ),
        "capex_intensity_pct": round(
            capex_intensity,
            2,
        )
        if pd.notna(capex_intensity)
        else np.nan,
        "capex_label": classify_capex_intensity(
            capex_intensity
        ),
        "fcf_cagr_5yr": round(
            fcf_cagr,
            2,
        )
        if pd.notna(fcf_cagr)
        else np.nan,
        "fcf_conversion_pct": round(
            fcf_conversion,
            2,
        )
        if pd.notna(fcf_conversion)
        else np.nan,
        "distress_flag": bool(
            latest["distress_flag"]
        ),
        "deleveraging_flag": bool(
            latest["deleveraging_flag"]
        ),
        "capital_allocation_label": latest[
            "capital_allocation_label"
        ],
        "latest_year": int(
            latest["year_number"]
        ),
        "latest_cfo": safe_float(
            latest["operating_activity"]
        ),
        "latest_cfi": safe_float(
            latest["investing_activity"]
        ),
        "latest_cff": safe_float(
            latest["financing_activity"]
        ),
        "latest_net_profit": safe_float(
            latest["net_profit"]
        ),
        "cfo_quality_years_used": int(
            len(valid_ratios)
        ),
    }


# ============================================================
# Full report generation
# ============================================================

def generate_outputs(
    datasets: dict[str, pd.DataFrame],
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    companies = datasets["companies"]
    sectors = datasets["sectors"]

    cashflow = deduplicate_years(
        datasets["cashflow"]
    )
    profit_loss = deduplicate_years(
        datasets["profit_loss"]
    )
    balance_sheet = deduplicate_years(
        datasets["balance_sheet"]
    )

    intelligence_rows: list[dict[str, Any]] = []
    distress_rows: list[dict[str, Any]] = []
    allocation_rows: list[dict[str, Any]] = []

    company_ids = (
        companies["company_id"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .unique()
        .tolist()
    )

    for company_id in company_ids:
        sector_match = sectors[
            sectors["company_id"] == company_id
        ]

        if (
            not sector_match.empty
            and "broad_sector" in sector_match.columns
        ):
            sector = str(
                sector_match.iloc[0]["broad_sector"]
            )
        else:
            sector = "Unknown"

        cashflow_rows = get_company_rows(
            cashflow,
            company_id,
        )
        profit_rows = get_company_rows(
            profit_loss,
            company_id,
        )
        balance_rows = get_company_rows(
            balance_sheet,
            company_id,
        )

        merged = merge_company_financials(
            cashflow_rows,
            profit_rows,
            balance_rows,
        )

        intelligence_row = (
            calculate_company_intelligence(
                company_id,
                sector,
                merged,
            )
        )

        intelligence_rows.append(
            intelligence_row
        )

        if not merged.empty:
            for _, row in merged.iterrows():
                allocation_rows.append(
                    {
                        "company_id": company_id,
                        "sector": sector,
                        "year": int(
                            row["year_number"]
                        ),
                        "operating_activity": (
                            safe_float(
                                row["operating_activity"]
                            )
                        ),
                        "investing_activity": (
                            safe_float(
                                row["investing_activity"]
                            )
                        ),
                        "financing_activity": (
                            safe_float(
                                row["financing_activity"]
                            )
                        ),
                        "borrowings": safe_float(
                            row["borrowings"]
                        ),
                        "capital_allocation_pattern": (
                            row[
                                "capital_allocation_label"
                            ]
                        ),
                    }
                )

        if intelligence_row["distress_flag"]:
            distress_rows.append(
                {
                    "company_id": company_id,
                    "sector": sector,
                    "year": intelligence_row[
                        "latest_year"
                    ],
                    "cfo_value": intelligence_row[
                        "latest_cfo"
                    ],
                    "cff_value": intelligence_row[
                        "latest_cff"
                    ],
                    "latest_net_profit": (
                        intelligence_row[
                            "latest_net_profit"
                        ]
                    ),
                }
            )

    intelligence_df = pd.DataFrame(
        intelligence_rows
    )

    distress_df = pd.DataFrame(
        distress_rows,
        columns=[
            "company_id",
            "sector",
            "year",
            "cfo_value",
            "cff_value",
            "latest_net_profit",
        ],
    )

    allocation_df = pd.DataFrame(
        allocation_rows
    )

    distribution_df = (
        generate_distribution(allocation_df)
    )

    pattern_changes_df = (
        generate_pattern_changes(allocation_df)
    )

    return (
        intelligence_df,
        distress_df,
        allocation_df,
        distribution_df,
        pattern_changes_df,
    )


def generate_distribution(
    allocation_df: pd.DataFrame,
) -> pd.DataFrame:
    """Count latest-year capital-allocation patterns."""
    if allocation_df.empty:
        return pd.DataFrame(
            columns=[
                "capital_allocation_pattern",
                "company_count",
                "percentage_of_companies",
            ]
        )

    latest = (
        allocation_df
        .sort_values(["company_id", "year"])
        .groupby("company_id", as_index=False)
        .tail(1)
    )

    distribution = (
        latest[
            "capital_allocation_pattern"
        ]
        .value_counts(dropna=False)
        .rename_axis(
            "capital_allocation_pattern"
        )
        .reset_index(name="company_count")
    )

    total = distribution[
        "company_count"
    ].sum()

    distribution[
        "percentage_of_companies"
    ] = (
        distribution["company_count"]
        / total
        * 100
    ).round(2)

    return distribution


def generate_pattern_changes(
    allocation_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate company year-over-year pattern changes."""
    if allocation_df.empty:
        return pd.DataFrame(
            columns=[
                "company_id",
                "sector",
                "previous_year",
                "current_year",
                "previous_pattern",
                "current_pattern",
                "change_description",
            ]
        )

    result = allocation_df.sort_values(
        ["company_id", "year"]
    ).copy()

    result["previous_pattern"] = (
        result.groupby("company_id")[
            "capital_allocation_pattern"
        ].shift(1)
    )

    result["previous_year"] = (
        result.groupby("company_id")[
            "year"
        ].shift(1)
    )

    changes = result[
        result["previous_pattern"].notna()
        & (
            result["capital_allocation_pattern"]
            != result["previous_pattern"]
        )
    ].copy()

    changes["change_description"] = (
        changes["company_id"]
        + " changed from "
        + changes["previous_pattern"]
        + " to "
        + changes["capital_allocation_pattern"]
    )

    changes = changes.rename(
        columns={
            "year": "current_year",
            "capital_allocation_pattern": (
                "current_pattern"
            ),
        }
    )

    return changes[
        [
            "company_id",
            "sector",
            "previous_year",
            "current_year",
            "previous_pattern",
            "current_pattern",
            "change_description",
        ]
    ]


# ============================================================
# Validation and saving
# ============================================================

def validate_results(
    intelligence_df: pd.DataFrame,
    companies_df: pd.DataFrame,
) -> None:
    required_columns = [
        "company_id",
        "sector",
        "cfo_quality_score",
        "cfo_quality_label",
        "capex_intensity_pct",
        "capex_label",
        "fcf_cagr_5yr",
        "fcf_conversion_pct",
        "distress_flag",
        "deleveraging_flag",
        "capital_allocation_label",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in intelligence_df.columns
    ]

    if missing_columns:
        raise ValueError(
            "Cash-flow output is missing columns: "
            f"{missing_columns}"
        )

    expected_count = companies_df[
        "company_id"
    ].nunique()

    actual_count = intelligence_df[
        "company_id"
    ].nunique()

    if actual_count != expected_count:
        raise ValueError(
            f"Expected {expected_count} companies, "
            f"but output contains {actual_count}."
        )


def save_outputs(
    intelligence_df: pd.DataFrame,
    distress_df: pd.DataFrame,
    allocation_df: pd.DataFrame,
    distribution_df: pd.DataFrame,
    pattern_changes_df: pd.DataFrame,
) -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    intelligence_df.to_excel(
        CASHFLOW_OUTPUT,
        index=False,
        engine="openpyxl",
    )

    distress_df.to_csv(
        DISTRESS_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    allocation_df.to_csv(
        CAPITAL_ALLOCATION_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    distribution_df.to_csv(
        DISTRIBUTION_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )

    pattern_changes_df.to_csv(
        PATTERN_CHANGES_OUTPUT,
        index=False,
        encoding="utf-8-sig",
    )


# ============================================================
# Main runner
# ============================================================

def main() -> None:
    print("Loading cash-flow intelligence datasets...")

    datasets = load_project_data()

    company_count = datasets[
        "companies"
    ]["company_id"].nunique()

    print(f"Companies loaded: {company_count}")
    print("Calculating cash-flow intelligence...")

    (
        intelligence_df,
        distress_df,
        allocation_df,
        distribution_df,
        pattern_changes_df,
    ) = generate_outputs(datasets)

    validate_results(
        intelligence_df,
        datasets["companies"],
    )

    save_outputs(
        intelligence_df,
        distress_df,
        allocation_df,
        distribution_df,
        pattern_changes_df,
    )

    print("\nDay 31 and Day 32 processing completed.")
    print(
        f"Cash-flow intelligence rows: "
        f"{len(intelligence_df)}"
    )
    print(
        f"Distress alerts found: "
        f"{len(distress_df)}"
    )
    print(
        f"Capital-allocation records: "
        f"{len(allocation_df)}"
    )
    print(
        f"Pattern changes found: "
        f"{len(pattern_changes_df)}"
    )

    print(f"\nCreated: {CASHFLOW_OUTPUT}")
    print(f"Created: {DISTRESS_OUTPUT}")
    print(
        f"Created: {CAPITAL_ALLOCATION_OUTPUT}"
    )
    print(f"Created: {DISTRIBUTION_OUTPUT}")
    print(f"Created: {PATTERN_CHANGES_OUTPUT}")


if __name__ == "__main__":
    main()