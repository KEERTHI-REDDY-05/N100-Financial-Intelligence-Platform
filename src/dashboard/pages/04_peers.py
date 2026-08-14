import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import (
    get_companies,
    get_peer_groups,
    get_ratios,
    get_valuation,
)


st.set_page_config(
    page_title="Peer Comparison | Nifty 100 Analytics",
    page_icon="👥",
    layout="wide",
)


st.title("Peer Comparison")

st.caption(
    "Compare companies within the same peer group using "
    "profitability and valuation metrics."
)


# ---------------------------------------------------------
# Load required datasets
# ---------------------------------------------------------

try:
    companies = get_companies()
    peer_groups = get_peer_groups()

except Exception as error:
    st.error("Unable to load peer comparison data.")
    st.exception(error)
    st.stop()


required_peer_columns = {
    "peer_group_name",
    "company_id",
    "is_benchmark",
}


if not required_peer_columns.issubset(peer_groups.columns):
    st.error(
        "The peer group dataset does not contain all required columns."
    )

    st.write(
        "Available columns:",
        peer_groups.columns.tolist(),
    )

    st.stop()


# ---------------------------------------------------------
# Prepare company selector
# ---------------------------------------------------------

peer_company_ids = (
    peer_groups["company_id"]
    .dropna()
    .astype(str)
    .str.strip()
    .str.upper()
    .unique()
)


available_companies = companies[
    companies["id"]
    .astype(str)
    .str.strip()
    .str.upper()
    .isin(peer_company_ids)
].copy()


available_companies = (
    available_companies.sort_values("company_name")
    .reset_index(drop=True)
)


if available_companies.empty:
    st.warning("No companies were found in the peer-group dataset.")
    st.stop()


selected_company_name = st.selectbox(
    label="Select a company",
    options=available_companies["company_name"].tolist(),
)


selected_company = available_companies[
    available_companies["company_name"]
    == selected_company_name
].iloc[0]


selected_ticker = str(
    selected_company["id"]
).strip().upper()


# ---------------------------------------------------------
# Find the selected company's peer group
# ---------------------------------------------------------

selected_peer_rows = peer_groups[
    peer_groups["company_id"]
    .astype(str)
    .str.strip()
    .str.upper()
    == selected_ticker
].copy()


if selected_peer_rows.empty:
    st.warning(
        f"No peer group is available for {selected_company_name}."
    )
    st.stop()


peer_group_name = str(
    selected_peer_rows.iloc[0]["peer_group_name"]
).strip()


group_members = peer_groups[
    peer_groups["peer_group_name"]
    .astype(str)
    .str.strip()
    .str.lower()
    == peer_group_name.lower()
].copy()


group_members["company_id"] = (
    group_members["company_id"]
    .astype(str)
    .str.strip()
    .str.upper()
)


# ---------------------------------------------------------
# Normalise benchmark values
# ---------------------------------------------------------

group_members["is_benchmark_normalised"] = (
    group_members["is_benchmark"]
    .astype(str)
    .str.strip()
    .str.lower()
    .isin(
        [
            "true",
            "1",
            "yes",
            "y",
        ]
    )
)


benchmark_rows = group_members[
    group_members["is_benchmark_normalised"]
]


benchmark_ticker = (
    str(benchmark_rows.iloc[0]["company_id"])
    if not benchmark_rows.empty
    else "Not specified"
)


# ---------------------------------------------------------
# Build peer comparison dataset
# ---------------------------------------------------------

comparison_rows = []


for ticker in group_members["company_id"].dropna().unique():
    company_row = companies[
        companies["id"]
        .astype(str)
        .str.strip()
        .str.upper()
        == ticker
    ]


    if company_row.empty:
        company_name = ticker
        roce = None
        roe = None

    else:
        company_record = company_row.iloc[0]

        company_name = company_record.get(
            "company_name",
            ticker,
        )

        roce = pd.to_numeric(
            company_record.get("roce_percentage"),
            errors="coerce",
        )

        roe = pd.to_numeric(
            company_record.get("roe_percentage"),
            errors="coerce",
        )


    valuation = get_valuation(ticker)


    market_cap = None
    pe_ratio = None
    pb_ratio = None
    ev_ebitda = None
    dividend_yield = None
    valuation_year = None


    if not valuation.empty:
        valuation = valuation.copy()

        valuation["year_numeric"] = pd.to_numeric(
            valuation["year"],
            errors="coerce",
        )

        valuation = (
            valuation.dropna(subset=["year_numeric"])
            .sort_values("year_numeric")
        )


        if not valuation.empty:
            latest_valuation = valuation.iloc[-1]

            valuation_year = latest_valuation.get("year")
            market_cap = latest_valuation.get(
                "market_cap_crore"
            )
            pe_ratio = latest_valuation.get(
                "pe_ratio"
            )
            pb_ratio = latest_valuation.get(
                "pb_ratio"
            )
            ev_ebitda = latest_valuation.get(
                "ev_ebitda"
            )
            dividend_yield = latest_valuation.get(
                "dividend_yield_pct"
            )


    ratios = get_ratios(ticker)


    latest_ratio_year = None


    if not ratios.empty:
        ratios = ratios.copy()

        ratios["year_numeric"] = pd.to_numeric(
            ratios["year"]
            .astype(str)
            .str.extract(r"(\d{4})")[0],
            errors="coerce",
        )

        ratios = (
            ratios.dropna(subset=["year_numeric"])
            .sort_values("year_numeric")
        )


        if not ratios.empty:
            latest_ratio = ratios.iloc[-1]

            latest_ratio_year = latest_ratio.get("year")

            if pd.isna(roce):
                roce = pd.to_numeric(
                    latest_ratio.get("roce_pct"),
                    errors="coerce",
                )

            if pd.isna(roe):
                roe = pd.to_numeric(
                    latest_ratio.get("roe_pct"),
                    errors="coerce",
                )


    member_row = group_members[
        group_members["company_id"] == ticker
    ].iloc[0]


    comparison_rows.append(
        {
            "ticker": ticker,
            "company_name": company_name,
            "peer_group": peer_group_name,
            "is_benchmark": bool(
                member_row["is_benchmark_normalised"]
            ),
            "roce_percentage": roce,
            "roe_percentage": roe,
            "market_cap_crore": market_cap,
            "pe_ratio": pe_ratio,
            "pb_ratio": pb_ratio,
            "ev_ebitda": ev_ebitda,
            "dividend_yield_pct": dividend_yield,
            "valuation_year": valuation_year,
            "ratio_year": latest_ratio_year,
        }
    )


comparison_data = pd.DataFrame(comparison_rows)


numeric_columns = [
    "roce_percentage",
    "roe_percentage",
    "market_cap_crore",
    "pe_ratio",
    "pb_ratio",
    "ev_ebitda",
    "dividend_yield_pct",
]


for column in numeric_columns:
    comparison_data[column] = pd.to_numeric(
        comparison_data[column],
        errors="coerce",
    )


# ---------------------------------------------------------
# Peer-group summary
# ---------------------------------------------------------

st.markdown("---")

st.subheader(peer_group_name)


summary1, summary2, summary3, summary4 = st.columns(4)


summary1.metric(
    label="Selected Company",
    value=selected_ticker,
)


summary2.metric(
    label="Peer Companies",
    value=len(comparison_data),
)


summary3.metric(
    label="Benchmark",
    value=benchmark_ticker,
)


average_roe = comparison_data[
    "roe_percentage"
].mean()


summary4.metric(
    label="Average Peer ROE",
    value=(
        f"{average_roe:.2f}%"
        if pd.notna(average_roe)
        else "N/A"
    ),
)


# ---------------------------------------------------------
# Ranking calculations
# ---------------------------------------------------------

comparison_data["roce_rank"] = (
    comparison_data["roce_percentage"]
    .rank(
        method="min",
        ascending=False,
    )
)


comparison_data["roe_rank"] = (
    comparison_data["roe_percentage"]
    .rank(
        method="min",
        ascending=False,
    )
)


comparison_data["market_cap_rank"] = (
    comparison_data["market_cap_crore"]
    .rank(
        method="min",
        ascending=False,
    )
)


comparison_data["pe_rank"] = (
    comparison_data["pe_ratio"]
    .rank(
        method="min",
        ascending=True,
    )
)


# ---------------------------------------------------------
# Comparison table
# ---------------------------------------------------------

st.subheader("Peer Comparison Table")


display_table = comparison_data[
    [
        "ticker",
        "company_name",
        "is_benchmark",
        "roce_percentage",
        "roe_percentage",
        "market_cap_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "dividend_yield_pct",
        "roce_rank",
        "roe_rank",
        "market_cap_rank",
        "pe_rank",
    ]
].copy()


display_table = display_table.rename(
    columns={
        "ticker": "Ticker",
        "company_name": "Company",
        "is_benchmark": "Benchmark",
        "roce_percentage": "ROCE (%)",
        "roe_percentage": "ROE (%)",
        "market_cap_crore": "Market Cap (₹ Cr)",
        "pe_ratio": "P/E Ratio",
        "pb_ratio": "P/B Ratio",
        "ev_ebitda": "EV/EBITDA",
        "dividend_yield_pct": "Dividend Yield (%)",
        "roce_rank": "ROCE Rank",
        "roe_rank": "ROE Rank",
        "market_cap_rank": "Market Cap Rank",
        "pe_rank": "P/E Rank",
    }
)


display_table = display_table.sort_values(
    by="Market Cap (₹ Cr)",
    ascending=False,
    na_position="last",
)


st.dataframe(
    display_table,
    use_container_width=True,
    hide_index=True,
)


# ---------------------------------------------------------
# Profitability charts
# ---------------------------------------------------------

st.subheader("Profitability Comparison")


profitability_col1, profitability_col2 = st.columns(2)


with profitability_col1:
    roce_chart_data = comparison_data.dropna(
        subset=["roce_percentage"]
    ).sort_values(
        "roce_percentage",
        ascending=False,
    )


    if not roce_chart_data.empty:
        roce_chart = px.bar(
            roce_chart_data,
            x="company_name",
            y="roce_percentage",
            title="ROCE Comparison",
            labels={
                "company_name": "Company",
                "roce_percentage": "ROCE (%)",
            },
            hover_data=[
                "ticker",
                "is_benchmark",
            ],
        )


        st.plotly_chart(
            roce_chart,
            use_container_width=True,
        )

    else:
        st.info("ROCE data is unavailable.")


with profitability_col2:
    roe_chart_data = comparison_data.dropna(
        subset=["roe_percentage"]
    ).sort_values(
        "roe_percentage",
        ascending=False,
    )


    if not roe_chart_data.empty:
        roe_chart = px.bar(
            roe_chart_data,
            x="company_name",
            y="roe_percentage",
            title="ROE Comparison",
            labels={
                "company_name": "Company",
                "roe_percentage": "ROE (%)",
            },
            hover_data=[
                "ticker",
                "is_benchmark",
            ],
        )


        st.plotly_chart(
            roe_chart,
            use_container_width=True,
        )

    else:
        st.info("ROE data is unavailable.")


# ---------------------------------------------------------
# Valuation charts
# ---------------------------------------------------------

st.subheader("Valuation Comparison")


valuation_col1, valuation_col2 = st.columns(2)


with valuation_col1:
    pe_chart_data = comparison_data.dropna(
        subset=["pe_ratio"]
    ).sort_values(
        "pe_ratio",
        ascending=True,
    )


    if not pe_chart_data.empty:
        pe_chart = px.bar(
            pe_chart_data,
            x="company_name",
            y="pe_ratio",
            title="P/E Ratio Comparison",
            labels={
                "company_name": "Company",
                "pe_ratio": "P/E Ratio",
            },
            hover_data=[
                "ticker",
                "is_benchmark",
            ],
        )


        st.plotly_chart(
            pe_chart,
            use_container_width=True,
        )

    else:
        st.info("P/E ratio data is unavailable.")


with valuation_col2:
    market_cap_chart_data = comparison_data.dropna(
        subset=["market_cap_crore"]
    ).sort_values(
        "market_cap_crore",
        ascending=False,
    )


    if not market_cap_chart_data.empty:
        market_cap_chart = px.bar(
            market_cap_chart_data,
            x="company_name",
            y="market_cap_crore",
            title="Market Capitalisation Comparison",
            labels={
                "company_name": "Company",
                "market_cap_crore": "Market Cap (₹ Crore)",
            },
            hover_data=[
                "ticker",
                "is_benchmark",
            ],
        )


        st.plotly_chart(
            market_cap_chart,
            use_container_width=True,
        )

    else:
        st.info("Market-cap data is unavailable.")


# ---------------------------------------------------------
# Selected company position
# ---------------------------------------------------------

st.subheader("Selected Company Position")


selected_position = comparison_data[
    comparison_data["ticker"] == selected_ticker
]


if selected_position.empty:
    st.info("Ranking information is unavailable.")

else:
    position = selected_position.iloc[0]

    rank1, rank2, rank3, rank4 = st.columns(4)


    rank1.metric(
        label="ROCE Rank",
        value=(
            int(position["roce_rank"])
            if pd.notna(position["roce_rank"])
            else "N/A"
        ),
    )


    rank2.metric(
        label="ROE Rank",
        value=(
            int(position["roe_rank"])
            if pd.notna(position["roe_rank"])
            else "N/A"
        ),
    )


    rank3.metric(
        label="Market-cap Rank",
        value=(
            int(position["market_cap_rank"])
            if pd.notna(position["market_cap_rank"])
            else "N/A"
        ),
    )


    rank4.metric(
        label="P/E Rank",
        value=(
            int(position["pe_rank"])
            if pd.notna(position["pe_rank"])
            else "N/A"
        ),
    )