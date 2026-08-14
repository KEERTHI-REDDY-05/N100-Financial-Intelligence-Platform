import pandas as pd
import streamlit as st

from src.dashboard.utils.db import (
    get_companies,
    get_sectors,
    get_valuation,
)


st.set_page_config(
    page_title="Financial Screener | Nifty 100 Analytics",
    page_icon="🔍",
    layout="wide",
)


st.title("Financial Screener")

st.caption(
    "Filter Nifty 100 companies using sector, market-cap, "
    "profitability, and valuation criteria."
)


# ---------------------------------------------------------
# Load and prepare data
# ---------------------------------------------------------

try:
    companies = get_companies()
    sectors = get_sectors()

except Exception as error:
    st.error("Unable to load screener data.")
    st.exception(error)
    st.stop()


company_data = companies.merge(
    sectors,
    left_on="id",
    right_on="company_id",
    how="left",
    suffixes=("", "_sector"),
)


latest_valuation_rows = []


for ticker in company_data["id"].dropna().astype(str):
    valuation = get_valuation(ticker)

    if valuation.empty:
        continue

    valuation = valuation.copy()

    valuation["year"] = pd.to_numeric(
        valuation["year"],
        errors="coerce",
    )

    valuation = (
        valuation.dropna(subset=["year"])
        .sort_values("year")
    )

    if valuation.empty:
        continue

    latest_row = valuation.iloc[-1].copy()

    latest_row["id"] = ticker

    latest_valuation_rows.append(latest_row)


if latest_valuation_rows:
    latest_valuation = pd.DataFrame(
        latest_valuation_rows
    )

    valuation_columns = [
        "id",
        "year",
        "market_cap_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "dividend_yield_pct",
    ]

    available_valuation_columns = [
        column
        for column in valuation_columns
        if column in latest_valuation.columns
    ]

    latest_valuation = latest_valuation[
        available_valuation_columns
    ]

    screener_data = company_data.merge(
        latest_valuation,
        on="id",
        how="left",
    )

else:
    screener_data = company_data.copy()


# ---------------------------------------------------------
# Convert numeric fields
# ---------------------------------------------------------

numeric_columns = [
    "roce_percentage",
    "roe_percentage",
    "index_weight_pct",
    "market_cap_crore",
    "pe_ratio",
    "pb_ratio",
    "ev_ebitda",
    "dividend_yield_pct",
]


for column in numeric_columns:
    if column in screener_data.columns:
        screener_data[column] = pd.to_numeric(
            screener_data[column],
            errors="coerce",
        )


# ---------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------

st.sidebar.header("Screener Filters")


sector_options = sorted(
    screener_data["broad_sector"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)


selected_sectors = st.sidebar.multiselect(
    label="Sector",
    options=sector_options,
)


market_cap_options = sorted(
    screener_data["market_cap_category"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)


selected_market_caps = st.sidebar.multiselect(
    label="Market-cap Category",
    options=market_cap_options,
)


minimum_roce = st.sidebar.number_input(
    label="Minimum ROCE (%)",
    min_value=0.0,
    max_value=200.0,
    value=0.0,
    step=1.0,
)


minimum_roe = st.sidebar.number_input(
    label="Minimum ROE (%)",
    min_value=0.0,
    max_value=200.0,
    value=0.0,
    step=1.0,
)


maximum_pe = st.sidebar.number_input(
    label="Maximum P/E Ratio",
    min_value=0.0,
    max_value=1000.0,
    value=1000.0,
    step=5.0,
)


minimum_dividend_yield = st.sidebar.number_input(
    label="Minimum Dividend Yield (%)",
    min_value=0.0,
    max_value=50.0,
    value=0.0,
    step=0.1,
)


search_text = st.sidebar.text_input(
    label="Search Company or Ticker",
    placeholder="Example: ABB or Reliance",
)


# ---------------------------------------------------------
# Apply filters
# ---------------------------------------------------------

filtered_data = screener_data.copy()


if selected_sectors:
    filtered_data = filtered_data[
        filtered_data["broad_sector"].isin(
            selected_sectors
        )
    ]


if selected_market_caps:
    filtered_data = filtered_data[
        filtered_data["market_cap_category"].isin(
            selected_market_caps
        )
    ]


if "roce_percentage" in filtered_data.columns:
    filtered_data = filtered_data[
        filtered_data["roce_percentage"].fillna(-1)
        >= minimum_roce
    ]


if "roe_percentage" in filtered_data.columns:
    filtered_data = filtered_data[
        filtered_data["roe_percentage"].fillna(-1)
        >= minimum_roe
    ]


if "pe_ratio" in filtered_data.columns:
    filtered_data = filtered_data[
        filtered_data["pe_ratio"].fillna(float("inf"))
        <= maximum_pe
    ]


if "dividend_yield_pct" in filtered_data.columns:
    filtered_data = filtered_data[
        filtered_data["dividend_yield_pct"].fillna(-1)
        >= minimum_dividend_yield
    ]


if search_text.strip():
    search_value = search_text.strip().lower()

    company_match = (
        filtered_data["company_name"]
        .astype(str)
        .str.lower()
        .str.contains(
            search_value,
            na=False,
        )
    )

    ticker_match = (
        filtered_data["id"]
        .astype(str)
        .str.lower()
        .str.contains(
            search_value,
            na=False,
        )
    )

    filtered_data = filtered_data[
        company_match | ticker_match
    ]


# ---------------------------------------------------------
# Screener summary
# ---------------------------------------------------------

st.subheader("Screener Results")


summary1, summary2, summary3, summary4 = st.columns(4)


summary1.metric(
    label="Matching Companies",
    value=len(filtered_data),
)


average_roce = (
    filtered_data["roce_percentage"].mean()
    if "roce_percentage" in filtered_data.columns
    else None
)


average_roe = (
    filtered_data["roe_percentage"].mean()
    if "roe_percentage" in filtered_data.columns
    else None
)


average_pe = (
    filtered_data["pe_ratio"].mean()
    if "pe_ratio" in filtered_data.columns
    else None
)


summary2.metric(
    label="Average ROCE",
    value=(
        f"{average_roce:.2f}%"
        if pd.notna(average_roce)
        else "N/A"
    ),
)


summary3.metric(
    label="Average ROE",
    value=(
        f"{average_roe:.2f}%"
        if pd.notna(average_roe)
        else "N/A"
    ),
)


summary4.metric(
    label="Average P/E",
    value=(
        f"{average_pe:.2f}"
        if pd.notna(average_pe)
        else "N/A"
    ),
)


# ---------------------------------------------------------
# Display table
# ---------------------------------------------------------

display_columns = [
    "id",
    "company_name",
    "broad_sector",
    "sub_sector",
    "market_cap_category",
    "roce_percentage",
    "roe_percentage",
    "market_cap_crore",
    "pe_ratio",
    "pb_ratio",
    "ev_ebitda",
    "dividend_yield_pct",
]


available_columns = [
    column
    for column in display_columns
    if column in filtered_data.columns
]


result_table = filtered_data[
    available_columns
].copy()


result_table = result_table.rename(
    columns={
        "id": "Ticker",
        "company_name": "Company",
        "broad_sector": "Sector",
        "sub_sector": "Sub-sector",
        "market_cap_category": "Market-cap Category",
        "roce_percentage": "ROCE (%)",
        "roe_percentage": "ROE (%)",
        "market_cap_crore": "Market Cap (₹ Cr)",
        "pe_ratio": "P/E Ratio",
        "pb_ratio": "P/B Ratio",
        "ev_ebitda": "EV/EBITDA",
        "dividend_yield_pct": "Dividend Yield (%)",
    }
)


result_table = result_table.sort_values(
    by="Market Cap (₹ Cr)",
    ascending=False,
    na_position="last",
)


st.dataframe(
    result_table,
    use_container_width=True,
    hide_index=True,
)


# ---------------------------------------------------------
# CSV download
# ---------------------------------------------------------

csv_data = result_table.to_csv(
    index=False
).encode("utf-8")


st.download_button(
    label="Download Screener Results as CSV",
    data=csv_data,
    file_name="nifty100_screener_results.csv",
    mime="text/csv",
)