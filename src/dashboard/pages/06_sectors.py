import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import (
    get_companies,
    get_sectors,
    get_valuation,
)


st.set_page_config(
    page_title="Sector Analysis | Nifty 100 Analytics",
    page_icon="🏭",
    layout="wide",
)


st.title("Sector Analysis")

st.caption(
    "Compare Nifty 100 sectors using company count, index weight, "
    "profitability, and market capitalisation."
)


# ---------------------------------------------------------
# Load datasets
# ---------------------------------------------------------

try:
    companies = get_companies()
    sectors = get_sectors()

except Exception as error:
    st.error("Unable to load sector-analysis data.")
    st.exception(error)
    st.stop()


sector_data = companies.merge(
    sectors,
    left_on="id",
    right_on="company_id",
    how="left",
    suffixes=("", "_sector"),
)


# ---------------------------------------------------------
# Add latest valuation data
# ---------------------------------------------------------

latest_valuation_rows = []


for ticker in sector_data["id"].dropna().astype(str):
    valuation = get_valuation(ticker)

    if valuation.empty:
        continue

    valuation = valuation.copy()

    valuation["year_numeric"] = pd.to_numeric(
        valuation["year"],
        errors="coerce",
    )

    valuation = (
        valuation.dropna(subset=["year_numeric"])
        .sort_values("year_numeric")
    )

    if valuation.empty:
        continue

    latest_row = valuation.iloc[-1]

    latest_valuation_rows.append(
        {
            "id": ticker,
            "valuation_year": latest_row.get("year"),
            "market_cap_crore": latest_row.get(
                "market_cap_crore"
            ),
            "pe_ratio": latest_row.get("pe_ratio"),
            "pb_ratio": latest_row.get("pb_ratio"),
            "dividend_yield_pct": latest_row.get(
                "dividend_yield_pct"
            ),
        }
    )


if latest_valuation_rows:
    latest_valuation = pd.DataFrame(
        latest_valuation_rows
    )

    sector_data = sector_data.merge(
        latest_valuation,
        on="id",
        how="left",
    )


# ---------------------------------------------------------
# Convert numeric columns
# ---------------------------------------------------------

numeric_columns = [
    "roce_percentage",
    "roe_percentage",
    "index_weight_pct",
    "market_cap_crore",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield_pct",
]


for column in numeric_columns:
    if column in sector_data.columns:
        sector_data[column] = pd.to_numeric(
            sector_data[column],
            errors="coerce",
        )


# ---------------------------------------------------------
# Sector filter
# ---------------------------------------------------------

sector_options = sorted(
    sector_data["broad_sector"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)


selected_sectors = st.multiselect(
    label="Select sectors",
    options=sector_options,
    default=sector_options,
)


filtered_data = sector_data.copy()


if selected_sectors:
    filtered_data = filtered_data[
        filtered_data["broad_sector"].isin(
            selected_sectors
        )
    ]


if filtered_data.empty:
    st.warning("No companies match the selected sectors.")
    st.stop()


# ---------------------------------------------------------
# Sector summary
# ---------------------------------------------------------

sector_summary = (
    filtered_data.groupby(
        "broad_sector",
        dropna=False,
    )
    .agg(
        company_count=("id", "count"),
        total_index_weight=("index_weight_pct", "sum"),
        total_market_cap=("market_cap_crore", "sum"),
        average_market_cap=("market_cap_crore", "mean"),
        average_roce=("roce_percentage", "mean"),
        average_roe=("roe_percentage", "mean"),
        average_pe=("pe_ratio", "mean"),
        average_pb=("pb_ratio", "mean"),
        average_dividend_yield=(
            "dividend_yield_pct",
            "mean",
        ),
    )
    .reset_index()
)


# ---------------------------------------------------------
# Top-level metrics
# ---------------------------------------------------------

st.subheader("Sector Overview")


metric1, metric2, metric3, metric4 = st.columns(4)


metric1.metric(
    label="Selected Sectors",
    value=len(sector_summary),
)


metric2.metric(
    label="Companies Analysed",
    value=len(filtered_data),
)


total_index_weight = sector_summary[
    "total_index_weight"
].sum()


metric3.metric(
    label="Combined Index Weight",
    value=(
        f"{total_index_weight:.2f}%"
        if pd.notna(total_index_weight)
        else "N/A"
    ),
)


total_market_cap = sector_summary[
    "total_market_cap"
].sum()


metric4.metric(
    label="Combined Market Cap",
    value=(
        f"₹{total_market_cap:,.2f} Cr"
        if pd.notna(total_market_cap)
        else "N/A"
    ),
)


# ---------------------------------------------------------
# Distribution charts
# ---------------------------------------------------------

st.subheader("Sector Distribution")


distribution_col1, distribution_col2 = st.columns(2)


with distribution_col1:
    company_count_chart = px.bar(
        sector_summary.sort_values(
            "company_count",
            ascending=False,
        ),
        x="broad_sector",
        y="company_count",
        title="Number of Companies by Sector",
        labels={
            "broad_sector": "Sector",
            "company_count": "Company Count",
        },
    )

    st.plotly_chart(
        company_count_chart,
        use_container_width=True,
    )


with distribution_col2:
    index_weight_chart = px.pie(
        sector_summary,
        names="broad_sector",
        values="total_index_weight",
        title="Index Weight Distribution",
        hole=0.4,
    )

    st.plotly_chart(
        index_weight_chart,
        use_container_width=True,
    )


# ---------------------------------------------------------
# Market-cap analysis
# ---------------------------------------------------------

st.subheader("Market Capitalisation Analysis")


market_cap_col1, market_cap_col2 = st.columns(2)


with market_cap_col1:
    total_market_cap_chart = px.bar(
        sector_summary.sort_values(
            "total_market_cap",
            ascending=False,
        ),
        x="broad_sector",
        y="total_market_cap",
        title="Total Market Cap by Sector",
        labels={
            "broad_sector": "Sector",
            "total_market_cap": "Market Cap (₹ Crore)",
        },
    )

    st.plotly_chart(
        total_market_cap_chart,
        use_container_width=True,
    )


with market_cap_col2:
    average_market_cap_chart = px.bar(
        sector_summary.sort_values(
            "average_market_cap",
            ascending=False,
        ),
        x="broad_sector",
        y="average_market_cap",
        title="Average Company Market Cap",
        labels={
            "broad_sector": "Sector",
            "average_market_cap": "Average Market Cap (₹ Crore)",
        },
    )

    st.plotly_chart(
        average_market_cap_chart,
        use_container_width=True,
    )


# ---------------------------------------------------------
# Profitability analysis
# ---------------------------------------------------------

st.subheader("Sector Profitability")


profit_col1, profit_col2 = st.columns(2)


with profit_col1:
    roce_chart = px.bar(
        sector_summary.sort_values(
            "average_roce",
            ascending=False,
        ),
        x="broad_sector",
        y="average_roce",
        title="Average ROCE by Sector",
        labels={
            "broad_sector": "Sector",
            "average_roce": "Average ROCE (%)",
        },
    )

    st.plotly_chart(
        roce_chart,
        use_container_width=True,
    )


with profit_col2:
    roe_chart = px.bar(
        sector_summary.sort_values(
            "average_roe",
            ascending=False,
        ),
        x="broad_sector",
        y="average_roe",
        title="Average ROE by Sector",
        labels={
            "broad_sector": "Sector",
            "average_roe": "Average ROE (%)",
        },
    )

    st.plotly_chart(
        roe_chart,
        use_container_width=True,
    )


# ---------------------------------------------------------
# Valuation analysis
# ---------------------------------------------------------

st.subheader("Sector Valuation")


valuation_col1, valuation_col2 = st.columns(2)


with valuation_col1:
    pe_chart = px.bar(
        sector_summary.sort_values(
            "average_pe",
            ascending=True,
        ),
        x="broad_sector",
        y="average_pe",
        title="Average P/E Ratio by Sector",
        labels={
            "broad_sector": "Sector",
            "average_pe": "Average P/E Ratio",
        },
    )

    st.plotly_chart(
        pe_chart,
        use_container_width=True,
    )


with valuation_col2:
    dividend_chart = px.bar(
        sector_summary.sort_values(
            "average_dividend_yield",
            ascending=False,
        ),
        x="broad_sector",
        y="average_dividend_yield",
        title="Average Dividend Yield by Sector",
        labels={
            "broad_sector": "Sector",
            "average_dividend_yield": "Dividend Yield (%)",
        },
    )

    st.plotly_chart(
        dividend_chart,
        use_container_width=True,
    )


# ---------------------------------------------------------
# Sector summary table
# ---------------------------------------------------------

st.subheader("Sector Summary Table")


display_table = sector_summary.rename(
    columns={
        "broad_sector": "Sector",
        "company_count": "Companies",
        "total_index_weight": "Index Weight (%)",
        "total_market_cap": "Total Market Cap (₹ Cr)",
        "average_market_cap": "Average Market Cap (₹ Cr)",
        "average_roce": "Average ROCE (%)",
        "average_roe": "Average ROE (%)",
        "average_pe": "Average P/E",
        "average_pb": "Average P/B",
        "average_dividend_yield": "Average Dividend Yield (%)",
    }
)


display_table = display_table.sort_values(
    "Total Market Cap (₹ Cr)",
    ascending=False,
)


st.dataframe(
    display_table,
    use_container_width=True,
    hide_index=True,
)