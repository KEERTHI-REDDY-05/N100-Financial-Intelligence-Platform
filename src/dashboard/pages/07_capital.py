import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import (
    get_companies,
    get_sectors,
    get_valuation,
)


st.set_page_config(
    page_title="Capital Allocation | Nifty 100 Analytics",
    page_icon="💰",
    layout="wide",
)


st.title("Capital Allocation Map")

st.caption(
    "Analyse company size, enterprise value, valuation, "
    "and dividend distribution across Nifty 100 companies."
)


# ---------------------------------------------------------
# Load datasets
# ---------------------------------------------------------

try:
    companies = get_companies()
    sectors = get_sectors()

except Exception as error:
    st.error("Unable to load capital-allocation data.")
    st.exception(error)
    st.stop()


company_data = companies.merge(
    sectors,
    left_on="id",
    right_on="company_id",
    how="left",
    suffixes=("", "_sector"),
)


# ---------------------------------------------------------
# Collect latest valuation for each company
# ---------------------------------------------------------

latest_valuation_rows = []


for ticker in company_data["id"].dropna().astype(str):
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

    latest = valuation.iloc[-1]

    latest_valuation_rows.append(
        {
            "id": ticker,
            "valuation_year": latest.get("year"),
            "market_cap_crore": latest.get(
                "market_cap_crore"
            ),
            "enterprise_value_crore": latest.get(
                "enterprise_value_crore"
            ),
            "pe_ratio": latest.get("pe_ratio"),
            "pb_ratio": latest.get("pb_ratio"),
            "ev_ebitda": latest.get("ev_ebitda"),
            "dividend_yield_pct": latest.get(
                "dividend_yield_pct"
            ),
        }
    )


if not latest_valuation_rows:
    st.warning("No valuation data is available.")
    st.stop()


latest_valuation = pd.DataFrame(
    latest_valuation_rows
)


capital_data = company_data.merge(
    latest_valuation,
    on="id",
    how="inner",
)


# ---------------------------------------------------------
# Convert numeric columns
# ---------------------------------------------------------

numeric_columns = [
    "market_cap_crore",
    "enterprise_value_crore",
    "pe_ratio",
    "pb_ratio",
    "ev_ebitda",
    "dividend_yield_pct",
    "roce_percentage",
    "roe_percentage",
    "index_weight_pct",
]


for column in numeric_columns:
    if column in capital_data.columns:
        capital_data[column] = pd.to_numeric(
            capital_data[column],
            errors="coerce",
        )


# ---------------------------------------------------------
# Filters
# ---------------------------------------------------------

st.sidebar.header("Capital Allocation Filters")


sector_options = sorted(
    capital_data["broad_sector"]
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
    capital_data["market_cap_category"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)


selected_market_caps = st.sidebar.multiselect(
    label="Market-cap Category",
    options=market_cap_options,
)


minimum_market_cap = st.sidebar.number_input(
    label="Minimum Market Cap (₹ Cr)",
    min_value=0.0,
    value=0.0,
    step=10000.0,
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


filtered_data = capital_data.copy()


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


filtered_data = filtered_data[
    filtered_data["market_cap_crore"].fillna(-1)
    >= minimum_market_cap
]


filtered_data = filtered_data[
    filtered_data["pe_ratio"].fillna(float("inf"))
    <= maximum_pe
]


filtered_data = filtered_data[
    filtered_data["dividend_yield_pct"].fillna(-1)
    >= minimum_dividend_yield
]


if filtered_data.empty:
    st.warning("No companies match the selected filters.")
    st.stop()


# ---------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------

st.subheader("Capital Overview")


metric1, metric2, metric3, metric4 = st.columns(4)


metric1.metric(
    label="Companies Analysed",
    value=len(filtered_data),
)


total_market_cap = filtered_data[
    "market_cap_crore"
].sum()


metric2.metric(
    label="Total Market Cap",
    value=f"₹{total_market_cap:,.2f} Cr",
)


total_enterprise_value = filtered_data[
    "enterprise_value_crore"
].sum()


metric3.metric(
    label="Total Enterprise Value",
    value=f"₹{total_enterprise_value:,.2f} Cr",
)


average_dividend_yield = filtered_data[
    "dividend_yield_pct"
].mean()


metric4.metric(
    label="Average Dividend Yield",
    value=(
        f"{average_dividend_yield:.2f}%"
        if pd.notna(average_dividend_yield)
        else "N/A"
    ),
)


# ---------------------------------------------------------
# Market cap charts
# ---------------------------------------------------------

st.subheader("Company Size Analysis")


size_col1, size_col2 = st.columns(2)


with size_col1:
    top_market_cap = filtered_data.nlargest(
        15,
        "market_cap_crore",
    )

    market_cap_chart = px.bar(
        top_market_cap.sort_values(
            "market_cap_crore"
        ),
        x="market_cap_crore",
        y="company_name",
        orientation="h",
        title="Top 15 Companies by Market Cap",
        labels={
            "market_cap_crore": "Market Cap (₹ Crore)",
            "company_name": "Company",
        },
        hover_data=[
            "id",
            "broad_sector",
        ],
    )

    st.plotly_chart(
        market_cap_chart,
        use_container_width=True,
    )


with size_col2:
    top_enterprise_value = filtered_data.nlargest(
        15,
        "enterprise_value_crore",
    )

    enterprise_value_chart = px.bar(
        top_enterprise_value.sort_values(
            "enterprise_value_crore"
        ),
        x="enterprise_value_crore",
        y="company_name",
        orientation="h",
        title="Top 15 Companies by Enterprise Value",
        labels={
            "enterprise_value_crore": (
                "Enterprise Value (₹ Crore)"
            ),
            "company_name": "Company",
        },
        hover_data=[
            "id",
            "broad_sector",
        ],
    )

    st.plotly_chart(
        enterprise_value_chart,
        use_container_width=True,
    )


# ---------------------------------------------------------
# Capital allocation scatter charts
# ---------------------------------------------------------

st.subheader("Capital Allocation Map")


scatter_col1, scatter_col2 = st.columns(2)


with scatter_col1:
    scatter_data = filtered_data.dropna(
        subset=[
            "market_cap_crore",
            "pe_ratio",
            "pb_ratio",
        ]
    )


    if not scatter_data.empty:
        valuation_scatter = px.scatter(
            scatter_data,
            x="pe_ratio",
            y="market_cap_crore",
            size="pb_ratio",
            color="broad_sector",
            hover_name="company_name",
            hover_data=[
                "id",
                "enterprise_value_crore",
                "dividend_yield_pct",
            ],
            title="Market Cap vs P/E Ratio",
            labels={
                "pe_ratio": "P/E Ratio",
                "market_cap_crore": (
                    "Market Cap (₹ Crore)"
                ),
                "broad_sector": "Sector",
                "pb_ratio": "P/B Ratio",
            },
        )


        st.plotly_chart(
            valuation_scatter,
            use_container_width=True,
        )

    else:
        st.info("Not enough data for the valuation scatter plot.")


with scatter_col2:
    bubble_data = filtered_data.dropna(
        subset=[
            "market_cap_crore",
            "enterprise_value_crore",
            "dividend_yield_pct",
        ]
    )


    if not bubble_data.empty:
        dividend_scatter = px.scatter(
            bubble_data,
            x="market_cap_crore",
            y="enterprise_value_crore",
            size="dividend_yield_pct",
            color="market_cap_category",
            hover_name="company_name",
            hover_data=[
                "id",
                "pe_ratio",
                "pb_ratio",
            ],
            title="Market Cap vs Enterprise Value",
            labels={
                "market_cap_crore": (
                    "Market Cap (₹ Crore)"
                ),
                "enterprise_value_crore": (
                    "Enterprise Value (₹ Crore)"
                ),
                "dividend_yield_pct": (
                    "Dividend Yield (%)"
                ),
                "market_cap_category": (
                    "Market-cap Category"
                ),
            },
        )


        st.plotly_chart(
            dividend_scatter,
            use_container_width=True,
        )

    else:
        st.info("Not enough data for the capital bubble chart.")


# ---------------------------------------------------------
# Sector capital distribution
# ---------------------------------------------------------

st.subheader("Sector Capital Distribution")


sector_summary = (
    filtered_data.groupby("broad_sector")
    .agg(
        total_market_cap=(
            "market_cap_crore",
            "sum",
        ),
        total_enterprise_value=(
            "enterprise_value_crore",
            "sum",
        ),
        average_pe=("pe_ratio", "mean"),
        average_pb=("pb_ratio", "mean"),
        average_dividend_yield=(
            "dividend_yield_pct",
            "mean",
        ),
        company_count=("id", "count"),
    )
    .reset_index()
)


sector_col1, sector_col2 = st.columns(2)


with sector_col1:
    sector_market_cap_chart = px.pie(
        sector_summary,
        names="broad_sector",
        values="total_market_cap",
        title="Market Cap Distribution by Sector",
        hole=0.4,
    )

    st.plotly_chart(
        sector_market_cap_chart,
        use_container_width=True,
    )


with sector_col2:
    sector_enterprise_chart = px.bar(
        sector_summary.sort_values(
            "total_enterprise_value",
            ascending=False,
        ),
        x="broad_sector",
        y="total_enterprise_value",
        title="Enterprise Value by Sector",
        labels={
            "broad_sector": "Sector",
            "total_enterprise_value": (
                "Enterprise Value (₹ Crore)"
            ),
        },
    )

    st.plotly_chart(
        sector_enterprise_chart,
        use_container_width=True,
    )


# ---------------------------------------------------------
# Comparison table
# ---------------------------------------------------------

st.subheader("Capital Allocation Table")


display_columns = [
    "id",
    "company_name",
    "broad_sector",
    "market_cap_category",
    "valuation_year",
    "market_cap_crore",
    "enterprise_value_crore",
    "pe_ratio",
    "pb_ratio",
    "ev_ebitda",
    "dividend_yield_pct",
    "roce_percentage",
    "roe_percentage",
]


available_columns = [
    column
    for column in display_columns
    if column in filtered_data.columns
]


capital_table = filtered_data[
    available_columns
].copy()


capital_table = capital_table.rename(
    columns={
        "id": "Ticker",
        "company_name": "Company",
        "broad_sector": "Sector",
        "market_cap_category": "Market-cap Category",
        "valuation_year": "Valuation Year",
        "market_cap_crore": "Market Cap (₹ Cr)",
        "enterprise_value_crore": (
            "Enterprise Value (₹ Cr)"
        ),
        "pe_ratio": "P/E Ratio",
        "pb_ratio": "P/B Ratio",
        "ev_ebitda": "EV/EBITDA",
        "dividend_yield_pct": "Dividend Yield (%)",
        "roce_percentage": "ROCE (%)",
        "roe_percentage": "ROE (%)",
    }
)


capital_table = capital_table.sort_values(
    "Market Cap (₹ Cr)",
    ascending=False,
)


st.dataframe(
    capital_table,
    use_container_width=True,
    hide_index=True,
)


# ---------------------------------------------------------
# Download
# ---------------------------------------------------------

csv_data = capital_table.to_csv(
    index=False
).encode("utf-8")


st.download_button(
    label="Download Capital Allocation Data",
    data=csv_data,
    file_name="nifty100_capital_allocation.csv",
    mime="text/csv",
)