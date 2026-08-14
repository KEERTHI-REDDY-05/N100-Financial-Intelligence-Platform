from pathlib import Path

import pandas as pd
import streamlit as st


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

# db.py is located at:
# src/dashboard/utils/db.py
#
# parents[3] points to the main project folder:
# N100-Financial-Intelligence-Platform
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Folder containing all Excel files
DATA_DIR = PROJECT_ROOT / "data"


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def clean_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Standardise DataFrame column names.

    Examples:
    'Company Name' -> 'company_name'
    'ROE %' -> 'roe_pct'
    """

    dataframe = dataframe.copy()

    dataframe.columns = (
        dataframe.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("/", "_", regex=False)
        .str.replace("-", "_", regex=False)
        .str.replace("%", "pct", regex=False)
        .str.replace("(", "", regex=False)
        .str.replace(")", "", regex=False)
    )

    return dataframe


def clean_ticker(ticker: str) -> str:
    """
    Standardise a ticker entered by the user.

    Example:
    ' abb ' -> 'ABB'
    """

    return str(ticker).strip().upper()


@st.cache_data(ttl=600)
def load_excel_file(
    file_name: str,
    sheet_name: str | int = 0,
    skiprows: int = 0,
) -> pd.DataFrame:
    """
    Read an Excel file from the data folder.

    The result is cached for 600 seconds, which is 10 minutes.
    """

    file_path = DATA_DIR / file_name

    if not file_path.exists():
        raise FileNotFoundError(
            f"Data file not found: {file_path}"
        )

    try:
        dataframe = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            skiprows=skiprows,
            engine="openpyxl",
        )

    except ValueError as error:
        raise ValueError(
            f"Unable to read sheet '{sheet_name}' "
            f"from file '{file_name}'."
        ) from error

    return clean_columns(dataframe)


def filter_by_ticker(
    dataframe: pd.DataFrame,
    ticker: str,
) -> pd.DataFrame:
    """
    Filter a DataFrame using the company_id column.
    """

    if dataframe.empty:
        return dataframe.copy()

    if "company_id" not in dataframe.columns:
        raise KeyError(
            "Expected column 'company_id' was not found. "
            f"Available columns: {dataframe.columns.tolist()}"
        )

    cleaned_ticker = clean_ticker(ticker)

    result = dataframe[
        dataframe["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
        == cleaned_ticker
    ].copy()

    return result


# ---------------------------------------------------------
# Required dashboard data functions
# ---------------------------------------------------------

@st.cache_data(ttl=600)
def get_companies() -> pd.DataFrame:
    """
    Return the master list of all companies.
    """

    companies = load_excel_file(
        file_name="companies.xlsx",
        sheet_name="Companies",
        skiprows=1,
    )

    return companies


@st.cache_data(ttl=600)
def get_company(ticker: str) -> pd.DataFrame:
    """
    Return the company master record for one ticker.
    """

    companies = get_companies()

    if "id" not in companies.columns:
        raise KeyError(
            "Expected column 'id' was not found in companies.xlsx."
        )

    cleaned_ticker = clean_ticker(ticker)

    return companies[
        companies["id"]
        .astype(str)
        .str.strip()
        .str.upper()
        == cleaned_ticker
    ].copy()


@st.cache_data(ttl=600)
def get_ratios(
    ticker: str,
    year: int | str | None = None,
) -> pd.DataFrame:
    """
    Return financial ratios for a company.

    If year is supplied, only matching rows are returned.
    """

    ratios = load_excel_file(
        file_name="financial_ratios.xlsx"
    )

    company_ratios = filter_by_ticker(
        ratios,
        ticker,
    )

    if year is not None and "year" in company_ratios.columns:
        year_text = str(year).strip()

        company_ratios = company_ratios[
            company_ratios["year"]
            .astype(str)
            .str.contains(
                year_text,
                case=False,
                na=False,
            )
        ].copy()

    return company_ratios


@st.cache_data(ttl=600)
def get_pl(ticker: str) -> pd.DataFrame:
    """
    Return profit-and-loss data for one company.
    """

    profit_and_loss = load_excel_file(
        file_name="profitandloss.xlsx",
        skiprows=1,
    )

    return filter_by_ticker(
        profit_and_loss,
        ticker,
    )


@st.cache_data(ttl=600)
def get_bs(ticker: str) -> pd.DataFrame:
    """
    Return balance-sheet data for one company.
    """

    balance_sheet = load_excel_file(
        file_name="balancesheet.xlsx",
        skiprows=1,
    )

    return filter_by_ticker(
        balance_sheet,
        ticker,
    )


@st.cache_data(ttl=600)
def get_cf(ticker: str) -> pd.DataFrame:
    """
    Return cash-flow data for one company.
    """

    cash_flow = load_excel_file(
        file_name="cashflow.xlsx",
        skiprows=1,
    )

    return filter_by_ticker(
        cash_flow,
        ticker,
    )


@st.cache_data(ttl=600)
def get_sectors() -> pd.DataFrame:
    """
    Return sector data for all companies.
    """

    sectors = load_excel_file(
        file_name="sectors.xlsx"
    )

    return sectors


@st.cache_data(ttl=600)
def get_company_sector(ticker: str) -> pd.DataFrame:
    """
    Return sector information for one company.
    """

    sectors = get_sectors()

    return filter_by_ticker(
        sectors,
        ticker,
    )


@st.cache_data(ttl=600)
def get_peer_groups() -> pd.DataFrame:
    """
    Return all peer-group records.
    """

    peers = load_excel_file(
        file_name="peer_groups.xlsx"
    )

    return peers


@st.cache_data(ttl=600)
def get_peers(group_name: str) -> pd.DataFrame:
    """
    Return companies belonging to a peer group.

    The peer-group Excel file uses the column:
    peer_group_name
    """

    peers = get_peer_groups()

    if "peer_group_name" not in peers.columns:
        raise KeyError(
            "Expected column 'peer_group_name' was not found. "
            f"Available columns: {peers.columns.tolist()}"
        )

    cleaned_group_name = str(
        group_name
    ).strip().lower()

    return peers[
        peers["peer_group_name"]
        .astype(str)
        .str.strip()
        .str.lower()
        == cleaned_group_name
    ].copy()


@st.cache_data(ttl=600)
def get_peer_group_names() -> list[str]:
    """
    Return a sorted list of unique peer-group names.
    """

    peers = get_peer_groups()

    if "peer_group_name" not in peers.columns:
        return []

    group_names = (
        peers["peer_group_name"]
        .dropna()
        .astype(str)
        .str.strip()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    return group_names


@st.cache_data(ttl=600)
def get_valuation(
    ticker: str,
    year: int | str | None = None,
) -> pd.DataFrame:
    """
    Return valuation and market-cap data for one company.

    If year is supplied, only that year is returned.
    """

    valuation = load_excel_file(
        file_name="market_cap.xlsx"
    )

    company_valuation = filter_by_ticker(
        valuation,
        ticker,
    )

    if year is not None and "year" in company_valuation.columns:
        company_valuation = company_valuation[
            company_valuation["year"]
            .astype(str)
            .str.strip()
            == str(year).strip()
        ].copy()

    return company_valuation


# ---------------------------------------------------------
# Additional useful data functions
# ---------------------------------------------------------

@st.cache_data(ttl=600)
def get_documents(ticker: str) -> pd.DataFrame:
    """
    Return annual-report and document links for one company.
    """

    documents = load_excel_file(
        file_name="documents.xlsx",
        skiprows=1,
    )

    return filter_by_ticker(
        documents,
        ticker,
    )


@st.cache_data(ttl=600)
def get_pros_and_cons(ticker: str) -> pd.DataFrame:
    """
    Return pros and cons for one company.
    """

    pros_and_cons = load_excel_file(
        file_name="prosandcons.xlsx",
        skiprows=1,
    )

    return filter_by_ticker(
        pros_and_cons,
        ticker,
    )


@st.cache_data(ttl=600)
def get_stock_prices(ticker: str) -> pd.DataFrame:
    """
    Return historical stock-price data for one company.
    """

    stock_prices = load_excel_file(
        file_name="stock_prices.xlsx"
    )

    return filter_by_ticker(
        stock_prices,
        ticker,
    )


@st.cache_data(ttl=600)
def get_analysis(ticker: str) -> pd.DataFrame:
    """
    Return analysis data for one company.
    """

    analysis = load_excel_file(
        file_name="analysis.xlsx",
        skiprows=1,
    )

    return filter_by_ticker(
        analysis,
        ticker,
    )


# ---------------------------------------------------------
# Formatting helper
# ---------------------------------------------------------

def format_metric(
    value,
    suffix: str = "",
    decimals: int = 2,
) -> str:
    """
    Format a financial metric safely.

    Missing values are displayed as N/A.
    """

    if value is None or pd.isna(value):
        return "N/A"

    try:
        numeric_value = float(value)

        return (
            f"{numeric_value:,.{decimals}f}"
            f"{suffix}"
        )

    except (TypeError, ValueError):
        return str(value)