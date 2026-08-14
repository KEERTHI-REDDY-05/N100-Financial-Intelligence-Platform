import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics.valuation import build_valuation_summary
from src.dashboard.utils.db import (
    format_metric,
    get_companies,
    get_company_sector,
    get_valuation,
)


st.set_page_config(
    page_title="Home | Nifty 100 Analytics",
    page_icon="🏠",
    layout="wide",
)


st.title("Home Dashboard")

st.caption(
    "Explore company information, sector classification, "
    "valuation metrics, and historical trends."
)


# ---------------------------------------------------------
# Load company data
# ---------------------------------------------------------

try:
    companies = get_companies()

except Exception as error:
    st.error("Unable to load company data.")
    st.exception(error)
    st.stop()


company_options = (
    companies.sort_values("company_name")
    .reset_index(drop=True)
)


# ---------------------------------------------------------
# Company selection
# ---------------------------------------------------------

selected_company_name = st.selectbox(
    label="Select a company",
    options=company_options["company_name"].tolist(),
    index=0,
)


selected_company = company_options[
    company_options["company_name"] == selected_company_name
].iloc[0]


ticker = str(selected_company["id"]).strip()


# ---------------------------------------------------------
# Load selected company data
# ---------------------------------------------------------

try:
    sector_data = get_company_sector(ticker)
    valuation_data = get_valuation(ticker)

    valuation_summary = build_valuation_summary(
        valuation_data
    )

except Exception as error:
    st.error(
        f"Unable to load financial data for {selected_company_name}."
    )
    st.exception(error)
    st.stop()


st.markdown("---")


# ---------------------------------------------------------
# Company overview
# ---------------------------------------------------------

details_column, link_column = st.columns([3, 1])


with details_column:
    st.subheader(selected_company_name)

    st.write(f"**Ticker:** {ticker}")

    about_company = selected_company.get(
        "about_company"
    )

    if pd.notna(about_company) and str(about_company).strip():
        st.write(about_company)

    else:
        st.info("Company description is not available.")


with link_column:
    st.markdown("#### Quick Links")

    website = selected_company.get("website")
    nse_profile = selected_company.get("nse_profile")
    bse_profile = selected_company.get("bse_profile")

    if pd.notna(website) and str(website).strip():
        st.link_button(
            "Company Website",
            str(website),
            use_container_width=True,
        )

    if pd.notna(nse_profile) and str(nse_profile).strip():
        st.link_button(
            "NSE Profile",
            str(nse_profile),
            use_container_width=True,
        )

    if pd.notna(bse_profile) and str(bse_profile).strip():
        st.link_button(
            "BSE Profile",
            str(bse_profile),
            use_container_width=True,
        )


st.markdown("---")


# ---------------------------------------------------------
# Sector information
# ---------------------------------------------------------

broad_sector = "N/A"
sub_sector = "N/A"
market_cap_category = "N/A"
index_weight = "N/A"


if not sector_data.empty:
    company_sector = sector_data.iloc[0]

    broad_sector = company_sector.get(
        "broad_sector",
        "N/A",
    )

    sub_sector = company_sector.get(
        "sub_sector",
        "N/A",
    )

    market_cap_category = company_sector.get(
        "market_cap_category",
        "N/A",
    )

    index_weight_value = company_sector.get(
        "index_weight_pct"
    )

    index_weight = format_metric(
        index_weight_value,
        suffix="%",
    )


sector_col1, sector_col2, sector_col3, sector_col4 = (
    st.columns(4)
)


sector_col1.metric(
    label="Broad Sector",
    value=broad_sector,
)

sector_col2.metric(
    label="Sub-sector",
    value=sub_sector,
)

sector_col3.metric(
    label="Market-cap Category",
    value=market_cap_category,
)

sector_col4.metric(
    label="Index Weight",
    value=index_weight,
)


# ---------------------------------------------------------
# Prepare valuation data
# ---------------------------------------------------------

latest_valuation = None

if not valuation_data.empty:
    valuation_data = valuation_data.copy()

    valuation_data["year"] = pd.to_numeric(
        valuation_data["year"],
        errors="coerce",
    )

    valuation_data = (
        valuation_data.dropna(subset=["year"])
        .sort_values("year")
        .reset_index(drop=True)
    )

    if not valuation_data.empty:
        latest_valuation = valuation_data.iloc[-1]


# ---------------------------------------------------------
# Latest valuation metrics
# ---------------------------------------------------------

st.subheader("Latest Valuation Metrics")


metric_col1, metric_col2, metric_col3, metric_col4 = (
    st.columns(4)
)


if latest_valuation is not None:
    market_cap = latest_valuation.get(
        "market_cap_crore"
    )

    pe_ratio = latest_valuation.get(
        "pe_ratio"
    )

    pb_ratio = latest_valuation.get(
        "pb_ratio"
    )

    dividend_yield = latest_valuation.get(
        "dividend_yield_pct"
    )

else:
    market_cap = None
    pe_ratio = None
    pb_ratio = None
    dividend_yield = None


metric_col1.metric(
    label="Market Cap",
    value=(
        f"₹{format_metric(market_cap)} Cr"
        if pd.notna(market_cap)
        else "N/A"
    ),
)

metric_col2.metric(
    label="P/E Ratio",
    value=(
        format_metric(pe_ratio)
        if pd.notna(pe_ratio)
        else "N/A"
    ),
)

metric_col3.metric(
    label="P/B Ratio",
    value=(
        format_metric(pb_ratio)
        if pd.notna(pb_ratio)
        else "N/A"
    ),
)

metric_col4.metric(
    label="Dividend Yield",
    value=(
        format_metric(
            dividend_yield,
            suffix="%",
        )
        if pd.notna(dividend_yield)
        else "N/A"
    ),
)


# ---------------------------------------------------------
# Valuation trend charts
# ---------------------------------------------------------

st.subheader("Valuation Trends")


if valuation_data.empty:
    st.warning(
        "Historical valuation data is not available "
        "for this company."
    )

else:
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        market_cap_chart = px.line(
            valuation_data,
            x="year",
            y="market_cap_crore",
            markers=True,
            title="Market Capitalisation Trend",
            labels={
                "year": "Year",
                "market_cap_crore": "Market Cap (₹ Crore)",
            },
        )

        st.plotly_chart(
            market_cap_chart,
            use_container_width=True,
        )

    with chart_col2:
        pe_chart = px.line(
            valuation_data,
            x="year",
            y="pe_ratio",
            markers=True,
            title="P/E Ratio Trend",
            labels={
                "year": "Year",
                "pe_ratio": "P/E Ratio",
            },
        )

        st.plotly_chart(
            pe_chart,
            use_container_width=True,
        )


# ---------------------------------------------------------
# Historical valuation table
# ---------------------------------------------------------

st.subheader("Historical Valuation Data")


if not valuation_data.empty:
    display_columns = [
        "year",
        "market_cap_crore",
        "enterprise_value_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "dividend_yield_pct",
    ]

    available_columns = [
        column
        for column in display_columns
        if column in valuation_data.columns
    ]

    valuation_table = valuation_data[
        available_columns
    ].sort_values(
        by="year",
        ascending=False,
    )

    valuation_table = valuation_table.rename(
        columns={
            "year": "Year",
            "market_cap_crore": "Market Cap (₹ Cr)",
            "enterprise_value_crore": "Enterprise Value (₹ Cr)",
            "pe_ratio": "P/E Ratio",
            "pb_ratio": "P/B Ratio",
            "ev_ebitda": "EV/EBITDA",
            "dividend_yield_pct": "Dividend Yield (%)",
        }
    )

    st.dataframe(
        valuation_table,
        use_container_width=True,
        hide_index=True,
    )

else:
    st.info("No valuation records are available.")


# ---------------------------------------------------------
# Relative valuation analysis
# ---------------------------------------------------------

st.subheader("Relative Valuation Analysis")


valuation_score = valuation_summary[
    "valuation_score"
]

valuation_category = valuation_summary[
    "valuation_category"
]

market_cap_growth = valuation_summary[
    "market_cap_growth_pct"
]

signals = valuation_summary["signals"]


score_col1, score_col2, score_col3 = st.columns(3)


score_col1.metric(
    label="Valuation Score",
    value=f"{valuation_score}/100",
)


score_col2.metric(
    label="Valuation Category",
    value=valuation_category,
)


score_col3.metric(
    label="Market-cap Growth",
    value=(
        f"{market_cap_growth:.2f}%"
        if market_cap_growth is not None
        else "N/A"
    ),
)


signal_col1, signal_col2, signal_col3, signal_col4 = (
    st.columns(4)
)


signal_col1.info(
    f"**P/E Signal**\n\n"
    f"{signals['pe_signal']}"
)


signal_col2.info(
    f"**P/B Signal**\n\n"
    f"{signals['pb_signal']}"
)


signal_col3.info(
    f"**EV/EBITDA Signal**\n\n"
    f"{signals['ev_ebitda_signal']}"
)


signal_col4.info(
    f"**Dividend Yield Signal**\n\n"
    f"{signals['dividend_yield_signal']}"
)


st.caption(
    "The valuation score compares the latest valuation ratios "
    "with the company's historical averages. It is intended "
    "for educational analysis and is not investment advice."
)