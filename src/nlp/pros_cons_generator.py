from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

COMPANIES_FILE = DATA_DIR / "companies.xlsx"
SECTORS_FILE = DATA_DIR / "sectors.xlsx"
PROFIT_LOSS_FILE = DATA_DIR / "profitandloss.xlsx"
BALANCE_SHEET_FILE = DATA_DIR / "balancesheet.xlsx"
RATIOS_FILE = DATA_DIR / "financial_ratios.xlsx"
CASHFLOW_FILE = DATA_DIR / "cashflow.xlsx"

OUTPUT_FILE = OUTPUT_DIR / "pros_cons_generated.csv"
COVERAGE_FILE = OUTPUT_DIR / "pros_cons_coverage.csv"


# ---------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------

MIN_CONFIDENCE = 60

FINANCIAL_SECTOR_KEYWORDS = {
    "bank",
    "banking",
    "financial",
    "finance",
    "insurance",
    "nbfc",
    "asset management",
    "capital markets",
}


# ---------------------------------------------------------------------
# General utility functions
# ---------------------------------------------------------------------

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize column names."""
    cleaned = df.copy()

    cleaned.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in cleaned.columns
    ]

    return cleaned


def load_excel(
    file_path: Path,
    header: int = 0,
) -> pd.DataFrame:
    """Load and clean an Excel file."""
    if not file_path.exists():
        raise FileNotFoundError(f"Required file not found: {file_path}")

    df = pd.read_excel(file_path, header=header)
    return clean_columns(df)


def normalize_company_id(value: Any) -> str:
    if pd.isna(value):
        return ""

    return str(value).strip().upper()


def extract_year(value: Any) -> float:
    """
    Extract a four-digit year from values such as:
    Mar 2025, Mar-25, Dec 2012, 2024.
    """
    if pd.isna(value):
        return np.nan

    text = str(value).strip()

    four_digit_match = re.search(r"\b(19|20)\d{2}\b", text)

    if four_digit_match:
        return float(four_digit_match.group())

    two_digit_match = re.search(
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\s-]*(\d{2})",
        text,
        re.IGNORECASE,
    )

    if two_digit_match:
        two_digit_year = int(two_digit_match.group(1))

        if two_digit_year <= 50:
            return float(2000 + two_digit_year)

        return float(1900 + two_digit_year)

    numeric_match = re.search(r"\b\d{2}\b", text)

    if numeric_match:
        two_digit_year = int(numeric_match.group())

        if two_digit_year <= 50:
            return float(2000 + two_digit_year)

        return float(1900 + two_digit_year)

    return np.nan


def safe_float(value: Any) -> float:
    """Convert a value to float or return NaN."""
    try:
        number = float(value)

        if math.isfinite(number):
            return number

        return np.nan
    except (TypeError, ValueError):
        return np.nan


def valid_number(value: Any) -> bool:
    return pd.notna(value) and np.isfinite(float(value))


def calculate_cagr(
    start_value: Any,
    end_value: Any,
    periods: int,
) -> float:
    """
    Calculate CAGR only when both values are positive.
    """
    start = safe_float(start_value)
    end = safe_float(end_value)

    if (
        not valid_number(start)
        or not valid_number(end)
        or start <= 0
        or end <= 0
        or periods <= 0
    ):
        return np.nan

    return ((end / start) ** (1 / periods) - 1) * 100


def is_increasing(values: list[float], years: int) -> bool:
    """Return True when the latest values increased consecutively."""
    clean_values = [
        float(value)
        for value in values
        if valid_number(value)
    ]

    if len(clean_values) < years:
        return False

    recent = clean_values[-years:]

    return all(
        recent[index] > recent[index - 1]
        for index in range(1, len(recent))
    )


def is_decreasing(values: list[float], years: int) -> bool:
    """Return True when the latest values declined consecutively."""
    clean_values = [
        float(value)
        for value in values
        if valid_number(value)
    ]

    if len(clean_values) < years:
        return False

    recent = clean_values[-years:]

    return all(
        recent[index] < recent[index - 1]
        for index in range(1, len(recent))
    )


def consecutive_positive(values: list[float], years: int) -> bool:
    clean_values = [
        float(value)
        for value in values
        if valid_number(value)
    ]

    if len(clean_values) < years:
        return False

    return all(value > 0 for value in clean_values[-years:])


def consecutive_negative(values: list[float], years: int) -> bool:
    clean_values = [
        float(value)
        for value in values
        if valid_number(value)
    ]

    if len(clean_values) < years:
        return False

    return all(value < 0 for value in clean_values[-years:])


def calculate_confidence(
    base: float,
    strength: float = 0,
    duration: float = 0,
) -> int:
    """
    Produce a deterministic confidence score between 0 and 100.
    """
    confidence = base + strength + duration
    return int(round(max(0, min(100, confidence))))


def is_financial_company(
    broad_sector: str,
    sub_sector: str,
) -> bool:
    combined = f"{broad_sector} {sub_sector}".lower()

    return any(
        keyword in combined
        for keyword in FINANCIAL_SECTOR_KEYWORDS
    )


# ---------------------------------------------------------------------
# Loading project data
# ---------------------------------------------------------------------

def load_project_data() -> dict[str, pd.DataFrame]:
    """
    Load project datasets.

    Some files have a title row, so header=1 is required.
    Other files already have normal headers.
    """
    companies = load_excel(COMPANIES_FILE, header=1)
    sectors = load_excel(SECTORS_FILE, header=0)
    profit_loss = load_excel(PROFIT_LOSS_FILE, header=1)
    balance_sheet = load_excel(BALANCE_SHEET_FILE, header=1)
    ratios = load_excel(RATIOS_FILE, header=0)
    cashflow = load_excel(CASHFLOW_FILE, header=1)

    if "id" not in companies.columns:
        raise ValueError(
            "companies.xlsx does not contain the required id column."
        )

    companies = companies.rename(columns={"id": "company_id"})

    datasets = {
        "companies": companies,
        "sectors": sectors,
        "profit_loss": profit_loss,
        "balance_sheet": balance_sheet,
        "ratios": ratios,
        "cashflow": cashflow,
    }

    for name, dataframe in datasets.items():
        if "company_id" in dataframe.columns:
            dataframe["company_id"] = dataframe[
                "company_id"
            ].apply(normalize_company_id)

        if "year" in dataframe.columns:
            dataframe["year_number"] = dataframe[
                "year"
            ].apply(extract_year)

            dataframe.sort_values(
                ["company_id", "year_number"],
                inplace=True,
            )

    return datasets


# ---------------------------------------------------------------------
# Company-level data preparation
# ---------------------------------------------------------------------

def get_company_rows(
    dataframe: pd.DataFrame,
    company_id: str,
) -> pd.DataFrame:
    if "company_id" not in dataframe.columns:
        return pd.DataFrame()

    result = dataframe[
        dataframe["company_id"] == company_id
    ].copy()

    if "year_number" in result.columns:
        result = result.sort_values("year_number")

    return result


def series_values(
    dataframe: pd.DataFrame,
    column: str,
) -> list[float]:
    if dataframe.empty or column not in dataframe.columns:
        return []

    return (
        pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )
        .dropna()
        .astype(float)
        .tolist()
    )


def latest_value(
    dataframe: pd.DataFrame,
    column: str,
) -> float:
    values = series_values(dataframe, column)

    if not values:
        return np.nan

    return values[-1]


def build_company_features(
    company_id: str,
    datasets: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    companies = datasets["companies"]
    sectors = datasets["sectors"]
    profit_loss = get_company_rows(
        datasets["profit_loss"],
        company_id,
    )
    balance_sheet = get_company_rows(
        datasets["balance_sheet"],
        company_id,
    )
    ratios = get_company_rows(
        datasets["ratios"],
        company_id,
    )
    cashflow = get_company_rows(
        datasets["cashflow"],
        company_id,
    )

    company_row = companies[
        companies["company_id"] == company_id
    ]

    sector_row = sectors[
        sectors["company_id"] == company_id
    ]

    company_name = company_id

    if (
        not company_row.empty
        and "company_name" in company_row.columns
    ):
        company_name = str(
            company_row.iloc[0]["company_name"]
        )

    broad_sector = ""

    if (
        not sector_row.empty
        and "broad_sector" in sector_row.columns
    ):
        broad_sector = str(
            sector_row.iloc[0]["broad_sector"]
        )

    sub_sector = ""

    if (
        not sector_row.empty
        and "sub_sector" in sector_row.columns
    ):
        sub_sector = str(
            sector_row.iloc[0]["sub_sector"]
        )

    sales_history = series_values(
        profit_loss,
        "sales",
    )
    net_profit_history = series_values(
        profit_loss,
        "net_profit",
    )
    eps_history = series_values(
        profit_loss,
        "eps",
    )
    opm_history = series_values(
        profit_loss,
        "opm_percentage",
    )
    dividend_payout_history = series_values(
        profit_loss,
        "dividend_payout",
    )

    roe_history = series_values(
        ratios,
        "return_on_equity_pct",
    )
    debt_equity_history = series_values(
        ratios,
        "debt_to_equity",
    )
    interest_coverage_history = series_values(
        ratios,
        "interest_coverage",
    )
    fcf_history = series_values(
        ratios,
        "free_cash_flow_cr",
    )
    total_debt_history = series_values(
        ratios,
        "total_debt_cr",
    )

    borrowings_history = series_values(
        balance_sheet,
        "borrowings",
    )
    total_assets_history = series_values(
        balance_sheet,
        "total_assets",
    )

    cfo_history = series_values(
        cashflow,
        "operating_activity",
    )

    revenue_cagr_5yr = np.nan
    pat_cagr_5yr = np.nan
    eps_cagr_5yr = np.nan

    if len(sales_history) >= 6:
        revenue_cagr_5yr = calculate_cagr(
            sales_history[-6],
            sales_history[-1],
            5,
        )

    if len(net_profit_history) >= 6:
        pat_cagr_5yr = calculate_cagr(
            net_profit_history[-6],
            net_profit_history[-1],
            5,
        )

    if len(eps_history) >= 6:
        eps_cagr_5yr = calculate_cagr(
            eps_history[-6],
            eps_history[-1],
            5,
        )

    latest_equity = np.nan
    latest_reserves = np.nan

    if not balance_sheet.empty:
        latest_equity = latest_value(
            balance_sheet,
            "equity_capital",
        )
        latest_reserves = latest_value(
            balance_sheet,
            "reserves",
        )

    latest_net_debt = latest_value(
        ratios,
        "total_debt_cr",
    )

    latest_operating_profit = latest_value(
        profit_loss,
        "operating_profit",
    )

    latest_depreciation = latest_value(
        profit_loss,
        "depreciation",
    )

    latest_ebitda = np.nan

    if (
        valid_number(latest_operating_profit)
        and valid_number(latest_depreciation)
    ):
        latest_ebitda = (
            latest_operating_profit
            + latest_depreciation
        )

    return {
        "company_id": company_id,
        "company_name": company_name,
        "broad_sector": broad_sector,
        "sub_sector": sub_sector,
        "is_financial": is_financial_company(
            broad_sector,
            sub_sector,
        ),
        "sales_history": sales_history,
        "net_profit_history": net_profit_history,
        "eps_history": eps_history,
        "opm_history": opm_history,
        "dividend_payout_history": dividend_payout_history,
        "roe_history": roe_history,
        "debt_equity_history": debt_equity_history,
        "interest_coverage_history": interest_coverage_history,
        "fcf_history": fcf_history,
        "total_debt_history": total_debt_history,
        "borrowings_history": borrowings_history,
        "total_assets_history": total_assets_history,
        "cfo_history": cfo_history,
        "revenue_cagr_5yr": revenue_cagr_5yr,
        "pat_cagr_5yr": pat_cagr_5yr,
        "eps_cagr_5yr": eps_cagr_5yr,
        "latest_sales": latest_value(
            profit_loss,
            "sales",
        ),
        "latest_net_profit": latest_value(
            profit_loss,
            "net_profit",
        ),
        "latest_eps": latest_value(
            profit_loss,
            "eps",
        ),
        "latest_opm": latest_value(
            profit_loss,
            "opm_percentage",
        ),
        "latest_dividend_payout": latest_value(
            profit_loss,
            "dividend_payout",
        ),
        "latest_roe": latest_value(
            ratios,
            "return_on_equity_pct",
        ),
        "latest_debt_equity": latest_value(
            ratios,
            "debt_to_equity",
        ),
        "latest_interest_coverage": latest_value(
            ratios,
            "interest_coverage",
        ),
        "latest_fcf": latest_value(
            ratios,
            "free_cash_flow_cr",
        ),
        "latest_total_debt": latest_value(
            ratios,
            "total_debt_cr",
        ),
        "latest_borrowings": latest_value(
            balance_sheet,
            "borrowings",
        ),
        "latest_assets": latest_value(
            balance_sheet,
            "total_assets",
        ),
        "latest_equity": latest_equity,
        "latest_reserves": latest_reserves,
        "latest_net_debt": latest_net_debt,
        "latest_ebitda": latest_ebitda,
    }


# ---------------------------------------------------------------------
# Output record helper
# ---------------------------------------------------------------------

def make_record(
    company_id: str,
    result_type: str,
    rule_id: str,
    text: str,
    confidence: int,
) -> dict[str, Any]:
    return {
        "company_id": company_id,
        "type": result_type,
        "rule_id": rule_id,
        "text": text,
        "confidence_pct": int(confidence),
    }


# ---------------------------------------------------------------------
# Pro rules
# ---------------------------------------------------------------------

def evaluate_pro_rules(
    features: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    company_id = features["company_id"]

    roe_history = features["roe_history"]
    fcf_history = features["fcf_history"]
    debt_equity = features["latest_debt_equity"]
    revenue_cagr = features["revenue_cagr_5yr"]
    latest_opm = features["latest_opm"]
    pat_cagr = features["pat_cagr_5yr"]
    interest_coverage = features["latest_interest_coverage"]
    eps_cagr = features["eps_cagr_5yr"]

    # Pro Rule 1: ROE > 20% sustained for 3+ years
    if len(roe_history) >= 3:
        recent_roe = roe_history[-3:]

        if all(value > 20 for value in recent_roe):
            average_roe = float(np.mean(recent_roe))

            confidence = calculate_confidence(
                base=61,
                strength=min((average_roe - 20) * 1.5, 24),
                duration=min((len(roe_history) - 3) * 2, 10),
            )

            results.append(
                make_record(
                    company_id,
                    "pro",
                    "PRO_01",
                    (
                        "Consistently high return on equity above "
                        "20% demonstrates exceptional capital efficiency."
                    ),
                    confidence,
                )
            )

    # Pro Rule 2: FCF positive for 5+ consecutive years
    if consecutive_positive(fcf_history, 5):
        average_fcf = float(np.mean(fcf_history[-5:]))

        confidence = calculate_confidence(
            base=66,
            strength=min(abs(average_fcf) / 100, 20),
            duration=min((len(fcf_history) - 5) * 2, 10),
        )

        results.append(
            make_record(
                company_id,
                "pro",
                "PRO_02",
                (
                    "Strong free cash flow generation over 5 years "
                    "signals healthy business fundamentals."
                ),
                confidence,
            )
        )

    # Pro Rule 3: D/E = 0 in latest year
    if valid_number(debt_equity) and debt_equity == 0:
        results.append(
            make_record(
                company_id,
                "pro",
                "PRO_03",
                (
                    "Debt-free balance sheet provides financial "
                    "flexibility and eliminates interest burden."
                ),
                88,
            )
        )

    # Pro Rule 4: Revenue CAGR > 15% over 5 years
    if valid_number(revenue_cagr) and revenue_cagr > 15:
        confidence = calculate_confidence(
            base=62,
            strength=min((revenue_cagr - 15) * 2, 30),
        )

        results.append(
            make_record(
                company_id,
                "pro",
                "PRO_04",
                (
                    "Revenue growing at above 15% CAGR over 5 years "
                    "reflects strong business momentum."
                ),
                confidence,
            )
        )

    # Pro Rule 5: OPM > 25% in latest year
    if valid_number(latest_opm) and latest_opm > 25:
        confidence = calculate_confidence(
            base=62,
            strength=min((latest_opm - 25) * 1.5, 30),
        )

        results.append(
            make_record(
                company_id,
                "pro",
                "PRO_05",
                (
                    "Operating profit margin above 25% indicates "
                    "strong pricing power and cost discipline."
                ),
                confidence,
            )
        )

    # Pro Rule 6: PAT CAGR > 20% over 5 years
    if valid_number(pat_cagr) and pat_cagr > 20:
        confidence = calculate_confidence(
            base=62,
            strength=min((pat_cagr - 20) * 1.5, 30),
        )

        results.append(
            make_record(
                company_id,
                "pro",
                "PRO_06",
                (
                    "Net profit compounding at above 20% over 5 "
                    "years creates significant shareholder value."
                ),
                confidence,
            )
        )

    # Pro Rule 7: ICR > 10 or debt free
    debt_free = (
        valid_number(debt_equity)
        and debt_equity == 0
    )

    high_interest_coverage = (
        valid_number(interest_coverage)
        and interest_coverage > 10
    )

    if high_interest_coverage or debt_free:
        if high_interest_coverage:
            confidence = calculate_confidence(
                base=65,
                strength=min(
                    (interest_coverage - 10) * 0.8,
                    28,
                ),
            )
        else:
            confidence = 85

        results.append(
            make_record(
                company_id,
                "pro",
                "PRO_07",
                (
                    "Very high interest coverage or a debt-free "
                    "position reflects negligible financial stress "
                    "from debt servicing."
                ),
                confidence,
            )
        )

    # Pro Rule 8 cannot be evaluated because dividend yield is absent.
    # It is intentionally skipped instead of inventing data.

    # Pro Rule 9: EPS CAGR > 15% over 5 years
    if valid_number(eps_cagr) and eps_cagr > 15:
        confidence = calculate_confidence(
            base=62,
            strength=min((eps_cagr - 15) * 1.5, 30),
        )

        results.append(
            make_record(
                company_id,
                "pro",
                "PRO_09",
                (
                    "Earnings per share growing above 15% CAGR "
                    "indicates strong earnings quality and compounding."
                ),
                confidence,
            )
        )

    # Pro Rule 10: ROE improving for 3 consecutive years
    if is_increasing(roe_history, 3):
        recent = roe_history[-3:]
        total_improvement = recent[-1] - recent[0]

        confidence = calculate_confidence(
            base=63,
            strength=min(total_improvement * 2, 28),
        )

        results.append(
            make_record(
                company_id,
                "pro",
                "PRO_10",
                (
                    "Return on equity improving for 3 consecutive "
                    "years shows strengthening business quality."
                ),
                confidence,
            )
        )

    # Pro Rule 11:
    # Profit CAGR should exceed revenue CAGR for operating leverage.
    if (
        valid_number(revenue_cagr)
        and valid_number(pat_cagr)
        and pat_cagr > revenue_cagr
    ):
        difference = pat_cagr - revenue_cagr

        confidence = calculate_confidence(
            base=62,
            strength=min(difference * 2, 30),
        )

        results.append(
            make_record(
                company_id,
                "pro",
                "PRO_11",
                (
                    "Profits growing faster than revenue demonstrate "
                    "improving operating leverage and scale benefits."
                ),
                confidence,
            )
        )

    # Pro Rule 12: Assets growing while debt declines
    assets = features["total_assets_history"]
    borrowings = features["borrowings_history"]

    if len(assets) >= 2 and len(borrowings) >= 2:
        assets_growing = assets[-1] > assets[-2]
        debt_declining = borrowings[-1] < borrowings[-2]

        if assets_growing and debt_declining:
            asset_growth_pct = (
                (assets[-1] - assets[-2])
                / abs(assets[-2])
                * 100
                if assets[-2] != 0
                else 0
            )

            confidence = calculate_confidence(
                base=65,
                strength=min(max(asset_growth_pct, 0), 25),
            )

            results.append(
                make_record(
                    company_id,
                    "pro",
                    "PRO_12",
                    (
                        "Growing asset base with declining debt "
                        "reflects growth supported by internal accruals."
                    ),
                    confidence,
                )
            )

    return results


# ---------------------------------------------------------------------
# Con rules
# ---------------------------------------------------------------------

def evaluate_con_rules(
    features: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    company_id = features["company_id"]

    debt_equity = features["latest_debt_equity"]
    fcf_history = features["fcf_history"]
    opm_history = features["opm_history"]
    net_profit_history = features["net_profit_history"]
    sales_history = features["sales_history"]
    interest_coverage = features["latest_interest_coverage"]
    dividend_payout = features["latest_dividend_payout"]
    debt_equity_history = features["debt_equity_history"]
    eps_history = features["eps_history"]
    revenue_cagr = features["revenue_cagr_5yr"]

    # Con Rule 1: D/E > 2 for non-financial companies
    if (
        not features["is_financial"]
        and valid_number(debt_equity)
        and debt_equity > 2
    ):
        confidence = calculate_confidence(
            base=65,
            strength=min((debt_equity - 2) * 8, 30),
        )

        results.append(
            make_record(
                company_id,
                "con",
                "CON_01",
                (
                    f"Debt-to-equity ratio of {debt_equity:.2f} is "
                    "elevated for a non-financial company and "
                    "warrants monitoring."
                ),
                confidence,
            )
        )

    # Con Rule 2: FCF negative for 3 consecutive years
    if consecutive_negative(fcf_history, 3):
        average_negative_fcf = abs(
            float(np.mean(fcf_history[-3:]))
        )

        confidence = calculate_confidence(
            base=68,
            strength=min(average_negative_fcf / 100, 25),
        )

        results.append(
            make_record(
                company_id,
                "con",
                "CON_02",
                (
                    "Free cash flow negative for 3 consecutive years "
                    "raises concern about cash generation quality."
                ),
                confidence,
            )
        )

    # Con Rule 3: OPM declining for 3 consecutive years
    if is_decreasing(opm_history, 3):
        recent = opm_history[-3:]
        decline = recent[0] - recent[-1]

        confidence = calculate_confidence(
            base=63,
            strength=min(decline * 3, 30),
        )

        results.append(
            make_record(
                company_id,
                "con",
                "CON_03",
                (
                    "Operating margins declining for 3 consecutive "
                    "years suggest pricing or cost pressure."
                ),
                confidence,
            )
        )

    # Con Rule 4: Latest net profit negative
    latest_net_profit = features["latest_net_profit"]

    if (
        valid_number(latest_net_profit)
        and latest_net_profit < 0
    ):
        confidence = calculate_confidence(
            base=80,
            strength=min(abs(latest_net_profit) / 100, 18),
        )

        results.append(
            make_record(
                company_id,
                "con",
                "CON_04",
                (
                    "The company reported a net loss in the most "
                    "recent financial year."
                ),
                confidence,
            )
        )

    # Con Rule 5: Revenue declining for 2+ years
    if is_decreasing(sales_history, 3):
        recent = sales_history[-3:]

        decline_pct = (
            (recent[0] - recent[-1])
            / abs(recent[0])
            * 100
            if recent[0] != 0
            else 0
        )

        confidence = calculate_confidence(
            base=66,
            strength=min(max(decline_pct, 0), 28),
        )

        results.append(
            make_record(
                company_id,
                "con",
                "CON_05",
                (
                    "Revenue contraction over 2 consecutive years "
                    "indicates demand weakness or market share loss."
                ),
                confidence,
            )
        )

    # Con Rule 6: ICR < 1.5
    if (
        valid_number(interest_coverage)
        and interest_coverage < 1.5
    ):
        confidence = calculate_confidence(
            base=72,
            strength=min(
                (1.5 - interest_coverage) * 12,
                25,
            ),
        )

        results.append(
            make_record(
                company_id,
                "con",
                "CON_06",
                (
                    "Interest coverage ratio below 1.5x indicates "
                    "risk in meeting debt obligations."
                ),
                confidence,
            )
        )

    # Con Rule 7: Dividend payout > 100%
    if (
        valid_number(dividend_payout)
        and dividend_payout > 100
    ):
        confidence = calculate_confidence(
            base=72,
            strength=min(
                (dividend_payout - 100) * 0.4,
                25,
            ),
        )

        results.append(
            make_record(
                company_id,
                "con",
                "CON_07",
                (
                    "Dividend payout ratio above 100% means the "
                    "company may be paying dividends beyond current "
                    "earnings, which can be unsustainable."
                ),
                confidence,
            )
        )

    # Con Rule 8: D/E rising for 3 consecutive years
    if is_increasing(debt_equity_history, 3):
        recent = debt_equity_history[-3:]
        increase = recent[-1] - recent[0]

        confidence = calculate_confidence(
            base=63,
            strength=min(max(increase, 0) * 15, 30),
        )

        results.append(
            make_record(
                company_id,
                "con",
                "CON_08",
                (
                    "Rising debt-to-equity ratio over 3 years "
                    "suggests increasing financial leverage risk."
                ),
                confidence,
            )
        )

    # Con Rule 9: EPS declining for 3 consecutive years
    if is_decreasing(eps_history, 3):
        recent = eps_history[-3:]

        decline_pct = (
            (recent[0] - recent[-1])
            / abs(recent[0])
            * 100
            if recent[0] != 0
            else 0
        )

        confidence = calculate_confidence(
            base=64,
            strength=min(max(decline_pct, 0), 30),
        )

        results.append(
            make_record(
                company_id,
                "con",
                "CON_09",
                (
                    "Earnings per share declining for 3 consecutive "
                    "years reflects deteriorating profitability."
                ),
                confidence,
            )
        )

    # Con Rule 10:
    # ROCE history is unavailable in the current ratios file.
    # Use latest company-level ROCE from companies.xlsx when available.
    # This value is added below in the fallback preparation if present.

    latest_roce = features.get("latest_roce", np.nan)

    if valid_number(latest_roce) and latest_roce < 10:
        confidence = calculate_confidence(
            base=66,
            strength=min((10 - latest_roce) * 3, 28),
        )

        results.append(
            make_record(
                company_id,
                "con",
                "CON_10",
                (
                    "Return on capital employed below 10% suggests "
                    "the business is not generating sufficient "
                    "returns on invested capital."
                ),
                confidence,
            )
        )

    # Con Rule 11: Net debt > 3x EBITDA
    net_debt = features["latest_net_debt"]
    ebitda = features["latest_ebitda"]

    if (
        valid_number(net_debt)
        and valid_number(ebitda)
        and ebitda > 0
        and net_debt / ebitda > 3
    ):
        ratio = net_debt / ebitda

        confidence = calculate_confidence(
            base=70,
            strength=min((ratio - 3) * 8, 26),
        )

        results.append(
            make_record(
                company_id,
                "con",
                "CON_11",
                (
                    f"Net debt of approximately {ratio:.2f} times "
                    "EBITDA represents high leverage and limits "
                    "financial flexibility."
                ),
                confidence,
            )
        )

    # Con Rule 12: Revenue CAGR < 5% over 5 years
    if valid_number(revenue_cagr) and revenue_cagr < 5:
        confidence = calculate_confidence(
            base=63,
            strength=min((5 - revenue_cagr) * 3, 30),
        )

        results.append(
            make_record(
                company_id,
                "con",
                "CON_12",
                (
                    "Revenue growing at below 5% over 5 years lags "
                    "inflation and suggests limited business momentum."
                ),
                confidence,
            )
        )

    return results


# ---------------------------------------------------------------------
# Fallback observations
# ---------------------------------------------------------------------

def create_fallback_pro(
    features: dict[str, Any],
) -> dict[str, Any]:
    company_id = features["company_id"]

    latest_roe = features["latest_roe"]
    latest_opm = features["latest_opm"]
    latest_fcf = features["latest_fcf"]
    latest_net_profit = features["latest_net_profit"]

    candidates: list[tuple[float, str]] = []

    if valid_number(latest_roe):
        candidates.append(
            (
                latest_roe,
                (
                    f"The latest return on equity of "
                    f"{latest_roe:.1f}% is one of the company’s "
                    "stronger observed financial indicators."
                ),
            )
        )

    if valid_number(latest_opm):
        candidates.append(
            (
                latest_opm,
                (
                    f"The latest operating margin of "
                    f"{latest_opm:.1f}% provides a positive signal "
                    "about operating performance."
                ),
            )
        )

    if valid_number(latest_fcf) and latest_fcf > 0:
        candidates.append(
            (
                min(latest_fcf / 100, 30),
                (
                    "The company generated positive free cash flow "
                    "in the latest available financial year."
                ),
            )
        )

    if (
        valid_number(latest_net_profit)
        and latest_net_profit > 0
    ):
        candidates.append(
            (
                min(latest_net_profit / 100, 25),
                (
                    "The company remained profitable in the latest "
                    "available financial year."
                ),
            )
        )

    if candidates:
        _, text = max(candidates, key=lambda item: item[0])
    else:
        text = (
            "The company has available financial history that can "
            "support further trend analysis."
        )

    return make_record(
        company_id,
        "pro",
        "PRO_FALLBACK",
        text,
        61,
    )


def create_fallback_con(
    features: dict[str, Any],
) -> dict[str, Any]:
    company_id = features["company_id"]

    revenue_cagr = features["revenue_cagr_5yr"]
    latest_roe = features["latest_roe"]
    latest_opm = features["latest_opm"]
    latest_debt_equity = features["latest_debt_equity"]

    if (
        valid_number(revenue_cagr)
        and revenue_cagr <= 15
    ):
        text = (
            f"Five-year revenue growth of approximately "
            f"{revenue_cagr:.1f}% remains an area to monitor "
            "relative to higher-growth companies."
        )

    elif valid_number(latest_roe) and latest_roe < 20:
        text = (
            f"Latest return on equity of {latest_roe:.1f}% remains "
            "below the exceptional 20% level and should be monitored."
        )

    elif valid_number(latest_opm) and latest_opm < 25:
        text = (
            f"Latest operating margin of {latest_opm:.1f}% remains "
            "below the strong pricing-power threshold of 25%."
        )

    elif (
        valid_number(latest_debt_equity)
        and latest_debt_equity > 0
    ):
        text = (
            f"Debt-to-equity of {latest_debt_equity:.2f} should be "
            "monitored for any future increase in leverage."
        )

    else:
        text = (
            "The company should be monitored for changes in growth, "
            "profitability and cash-flow consistency."
        )

    return make_record(
        company_id,
        "con",
        "CON_FALLBACK",
        text,
        61,
    )


# ---------------------------------------------------------------------
# Main generation
# ---------------------------------------------------------------------

def add_company_level_roce(
    features: dict[str, Any],
    companies: pd.DataFrame,
) -> None:
    company_id = features["company_id"]

    row = companies[
        companies["company_id"] == company_id
    ]

    if (
        not row.empty
        and "roce_percentage" in row.columns
    ):
        features["latest_roce"] = safe_float(
            row.iloc[0]["roce_percentage"]
        )
    else:
        features["latest_roce"] = np.nan


def generate_pros_cons(
    datasets: dict[str, pd.DataFrame],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    companies = datasets["companies"]

    company_ids = (
        companies["company_id"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .unique()
        .tolist()
    )

    all_records: list[dict[str, Any]] = []
    coverage_records: list[dict[str, Any]] = []

    for company_id in company_ids:
        features = build_company_features(
            company_id,
            datasets,
        )

        add_company_level_roce(
            features,
            companies,
        )

        pro_records = evaluate_pro_rules(features)
        con_records = evaluate_con_rules(features)

        pro_records = [
            record
            for record in pro_records
            if record["confidence_pct"] > MIN_CONFIDENCE
        ]

        con_records = [
            record
            for record in con_records
            if record["confidence_pct"] > MIN_CONFIDENCE
        ]

        if not pro_records:
            pro_records.append(
                create_fallback_pro(features)
            )

        if not con_records:
            con_records.append(
                create_fallback_con(features)
            )

        all_records.extend(pro_records)
        all_records.extend(con_records)

        coverage_records.append(
            {
                "company_id": company_id,
                "company_name": features["company_name"],
                "pro_count": len(pro_records),
                "con_count": len(con_records),
                "coverage_status": (
                    "PASS"
                    if pro_records and con_records
                    else "FAIL"
                ),
            }
        )

    output_df = pd.DataFrame(
        all_records,
        columns=[
            "company_id",
            "type",
            "rule_id",
            "text",
            "confidence_pct",
        ],
    )

    coverage_df = pd.DataFrame(coverage_records)

    output_df.sort_values(
        ["company_id", "type", "confidence_pct"],
        ascending=[True, True, False],
        inplace=True,
    )

    return output_df, coverage_df


def validate_output(
    output_df: pd.DataFrame,
    companies_df: pd.DataFrame,
) -> None:
    expected_companies = set(
        companies_df["company_id"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
    )

    pro_companies = set(
        output_df.loc[
            output_df["type"] == "pro",
            "company_id",
        ]
    )

    con_companies = set(
        output_df.loc[
            output_df["type"] == "con",
            "company_id",
        ]
    )

    missing_pros = expected_companies - pro_companies
    missing_cons = expected_companies - con_companies

    low_confidence = output_df[
        output_df["confidence_pct"] <= MIN_CONFIDENCE
    ]

    if missing_pros:
        raise ValueError(
            f"Companies missing pros: {sorted(missing_pros)}"
        )

    if missing_cons:
        raise ValueError(
            f"Companies missing cons: {sorted(missing_cons)}"
        )

    if not low_confidence.empty:
        raise ValueError(
            "Output contains confidence scores of 60 or below."
        )


def save_outputs(
    output_df: pd.DataFrame,
    coverage_df: pd.DataFrame,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    coverage_df.to_csv(
        COVERAGE_FILE,
        index=False,
        encoding="utf-8-sig",
    )


def main() -> None:
    print("Loading Sprint 5 financial datasets...")

    datasets = load_project_data()

    company_count = datasets["companies"][
        "company_id"
    ].nunique()

    print(f"Companies loaded: {company_count}")
    print("Generating automatic pros and cons...")

    output_df, coverage_df = generate_pros_cons(
        datasets
    )

    validate_output(
        output_df,
        datasets["companies"],
    )

    save_outputs(
        output_df,
        coverage_df,
    )

    print("\nDay 30 pros/cons generation completed.")
    print(f"Total generated records: {len(output_df)}")
    print(
        "Companies with pros:",
        output_df[
            output_df["type"] == "pro"
        ]["company_id"].nunique(),
    )
    print(
        "Companies with cons:",
        output_df[
            output_df["type"] == "con"
        ]["company_id"].nunique(),
    )
    print(f"Created: {OUTPUT_FILE}")
    print(f"Created: {COVERAGE_FILE}")


if __name__ == "__main__":
    main()