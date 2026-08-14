import pandas as pd
import plotly.express as px
import streamlit as st

from src.dashboard.utils.db import (
    get_bs,
    get_cf,
    get_companies,
    get_pl,
    get_ratios,
)


st.set_page_config(
    page_title="Trend Analysis | Nifty 100 Analytics",
    page_icon="📈",
    layout="wide",
)


st.title("Trend Analysis")

st.caption(
    "Analyse historical financial performance and growth trends."
)


# ---------------------------------------------------------
# Load companies
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


selected_company_name = st.selectbox(
    label="Select a company",
    options=company_options["company_name"].tolist(),
)


selected_company = company_options[
    company_options["company_name"] == selected_company_name
].iloc[0]


ticker = str(selected_company["id"]).strip()


# ---------------------------------------------------------
# Load financial statements
# ---------------------------------------------------------

try:
    profit_loss = get_pl(ticker)
    balance_sheet = get_bs(ticker)
    cash_flow = get_cf(ticker)
    ratios = get_ratios(ticker)

except Exception as error:
    st.error(
        f"Unable to load trend data for {selected_company_name}."
    )
    st.exception(error)
    st.stop()


# ---------------------------------------------------------
# Year cleaning helper
# ---------------------------------------------------------

def prepare_year_column(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Extract a numeric year and sort records chronologically.
    """

    dataframe = dataframe.copy()

    if dataframe.empty or "year" not in dataframe.columns:
        return dataframe

    dataframe["year_numeric"] = pd.to_numeric(
        dataframe["year"]
        .astype(str)
        .str.extract(r"(\d{4})")[0],
        errors="coerce",
    )

    dataframe = (
        dataframe.dropna(subset=["year_numeric"])
        .sort_values("year_numeric")
        .reset_index(drop=True)
    )

    dataframe["year_numeric"] = (
        dataframe["year_numeric"].astype(int)
    )

    return dataframe


profit_loss = prepare_year_column(profit_loss)
balance_sheet = prepare_year_column(balance_sheet)
cash_flow = prepare_year_column(cash_flow)
ratios = prepare_year_column(ratios)


# ---------------------------------------------------------
# Company summary
# ---------------------------------------------------------

st.markdown("---")

st.subheader(selected_company_name)

st.write(f"**Ticker:** {ticker}")


latest_sales = None
latest_net_profit = None
latest_eps = None
latest_operating_cash_flow = None


if not profit_loss.empty:
    latest_pl = profit_loss.iloc[-1]

    latest_sales = latest_pl.get("sales")
    latest_net_profit = latest_pl.get("net_profit")
    latest_eps = latest_pl.get("eps")


if not cash_flow.empty:
    latest_cf = cash_flow.iloc[-1]

    latest_operating_cash_flow = latest_cf.get(
        "operating_activity"
    )


metric1, metric2, metric3, metric4 = st.columns(4)


metric1.metric(
    label="Latest Sales",
    value=(
        f"₹{float(latest_sales):,.2f} Cr"
        if pd.notna(latest_sales)
        else "N/A"
    ),
)


metric2.metric(
    label="Latest Net Profit",
    value=(
        f"₹{float(latest_net_profit):,.2f} Cr"
        if pd.notna(latest_net_profit)
        else "N/A"
    ),
)


metric3.metric(
    label="Latest EPS",
    value=(
        f"₹{float(latest_eps):,.2f}"
        if pd.notna(latest_eps)
        else "N/A"
    ),
)


metric4.metric(
    label="Operating Cash Flow",
    value=(
        f"₹{float(latest_operating_cash_flow):,.2f} Cr"
        if pd.notna(latest_operating_cash_flow)
        else "N/A"
    ),
)


# ---------------------------------------------------------
# Sales and profit trends
# ---------------------------------------------------------

st.subheader("Profit and Loss Trends")


if profit_loss.empty:
    st.info("Profit-and-loss data is not available.")

else:
    pl_chart_col1, pl_chart_col2 = st.columns(2)


    with pl_chart_col1:
        sales_columns = [
            column
            for column in ["sales", "expenses"]
            if column in profit_loss.columns
        ]


        if sales_columns:
            sales_chart_data = profit_loss[
                ["year_numeric"] + sales_columns
            ].melt(
                id_vars="year_numeric",
                var_name="Metric",
                value_name="Amount",
            )


            sales_chart = px.line(
                sales_chart_data,
                x="year_numeric",
                y="Amount",
                color="Metric",
                markers=True,
                title="Sales and Expenses Trend",
                labels={
                    "year_numeric": "Year",
                    "Amount": "₹ Crore",
                },
            )


            st.plotly_chart(
                sales_chart,
                use_container_width=True,
            )


    with pl_chart_col2:
        profit_columns = [
            column
            for column in [
                "operating_profit",
                "profit_before_tax",
                "net_profit",
            ]
            if column in profit_loss.columns
        ]


        if profit_columns:
            profit_chart_data = profit_loss[
                ["year_numeric"] + profit_columns
            ].melt(
                id_vars="year_numeric",
                var_name="Metric",
                value_name="Amount",
            )


            profit_chart = px.line(
                profit_chart_data,
                x="year_numeric",
                y="Amount",
                color="Metric",
                markers=True,
                title="Profit Trend",
                labels={
                    "year_numeric": "Year",
                    "Amount": "₹ Crore",
                },
            )


            st.plotly_chart(
                profit_chart,
                use_container_width=True,
            )


# ---------------------------------------------------------
# EPS and growth
# ---------------------------------------------------------

st.subheader("EPS and Growth Analysis")


growth_col1, growth_col2 = st.columns(2)


with growth_col1:
    if (
        not profit_loss.empty
        and "eps" in profit_loss.columns
    ):
        eps_chart = px.bar(
            profit_loss,
            x="year_numeric",
            y="eps",
            title="EPS Trend",
            labels={
                "year_numeric": "Year",
                "eps": "EPS",
            },
        )


        st.plotly_chart(
            eps_chart,
            use_container_width=True,
        )

    else:
        st.info("EPS data is not available.")


with growth_col2:
    if (
        not profit_loss.empty
        and "sales" in profit_loss.columns
        and "net_profit" in profit_loss.columns
    ):
        growth_data = profit_loss[
            [
                "year_numeric",
                "sales",
                "net_profit",
            ]
        ].copy()


        growth_data["sales_growth_pct"] = (
            growth_data["sales"].pct_change() * 100
        )


        growth_data["profit_growth_pct"] = (
            growth_data["net_profit"].pct_change() * 100
        )


        growth_chart_data = growth_data.melt(
            id_vars="year_numeric",
            value_vars=[
                "sales_growth_pct",
                "profit_growth_pct",
            ],
            var_name="Metric",
            value_name="Growth",
        )


        growth_chart = px.line(
            growth_chart_data,
            x="year_numeric",
            y="Growth",
            color="Metric",
            markers=True,
            title="Year-on-Year Growth",
            labels={
                "year_numeric": "Year",
                "Growth": "Growth (%)",
            },
        )


        st.plotly_chart(
            growth_chart,
            use_container_width=True,
        )

    else:
        st.info("Growth data is not available.")


# ---------------------------------------------------------
# Profitability ratios
# ---------------------------------------------------------

st.subheader("Profitability Ratios")


if ratios.empty:
    st.info("Financial-ratio data is not available.")

else:
    ratio_columns = [
        column
        for column in [
            "roce_pct",
            "roe_pct",
            "operating_profit_margin_pct",
            "net_profit_margin_pct",
        ]
        if column in ratios.columns
    ]


    if ratio_columns:
        ratio_chart_data = ratios[
            ["year_numeric"] + ratio_columns
        ].melt(
            id_vars="year_numeric",
            var_name="Metric",
            value_name="Percentage",
        )


        ratio_chart = px.line(
            ratio_chart_data,
            x="year_numeric",
            y="Percentage",
            color="Metric",
            markers=True,
            title="Profitability Ratio Trend",
            labels={
                "year_numeric": "Year",
                "Percentage": "Percentage (%)",
            },
        )


        st.plotly_chart(
            ratio_chart,
            use_container_width=True,
        )

    else:
        st.info(
            "ROCE, ROE, or margin columns are unavailable."
        )


# ---------------------------------------------------------
# Balance sheet trends
# ---------------------------------------------------------

st.subheader("Balance Sheet Trends")


if balance_sheet.empty:
    st.info("Balance-sheet data is not available.")

else:
    balance_columns = [
        column
        for column in [
            "reserves",
            "borrowings",
            "fixed_assets",
            "total_assets",
        ]
        if column in balance_sheet.columns
    ]


    if balance_columns:
        balance_chart_data = balance_sheet[
            ["year_numeric"] + balance_columns
        ].melt(
            id_vars="year_numeric",
            var_name="Metric",
            value_name="Amount",
        )


        balance_chart = px.line(
            balance_chart_data,
            x="year_numeric",
            y="Amount",
            color="Metric",
            markers=True,
            title="Balance Sheet Growth",
            labels={
                "year_numeric": "Year",
                "Amount": "₹ Crore",
            },
        )


        st.plotly_chart(
            balance_chart,
            use_container_width=True,
        )


# ---------------------------------------------------------
# Cash-flow trends
# ---------------------------------------------------------

st.subheader("Cash Flow Trends")


if cash_flow.empty:
    st.info("Cash-flow data is not available.")

else:
    cash_flow_columns = [
        column
        for column in [
            "operating_activity",
            "investing_activity",
            "financing_activity",
            "net_cash_flow",
        ]
        if column in cash_flow.columns
    ]


    if cash_flow_columns:
        cash_flow_chart_data = cash_flow[
            ["year_numeric"] + cash_flow_columns
        ].melt(
            id_vars="year_numeric",
            var_name="Activity",
            value_name="Cash Flow",
        )


        cash_flow_chart = px.bar(
            cash_flow_chart_data,
            x="year_numeric",
            y="Cash Flow",
            color="Activity",
            barmode="group",
            title="Cash Flow Activity Trend",
            labels={
                "year_numeric": "Year",
                "Cash Flow": "₹ Crore",
            },
        )


        st.plotly_chart(
            cash_flow_chart,
            use_container_width=True,
        )


# ---------------------------------------------------------
# Financial data table
# ---------------------------------------------------------

st.subheader("Profit and Loss Data")


if not profit_loss.empty:
    display_columns = [
        "year",
        "sales",
        "expenses",
        "operating_profit",
        "profit_before_tax",
        "net_profit",
        "eps",
        "dividend_payout",
    ]


    available_columns = [
        column
        for column in display_columns
        if column in profit_loss.columns
    ]


    trend_table = profit_loss[
        available_columns
    ].copy()


    trend_table = trend_table.rename(
        columns={
            "year": "Year",
            "sales": "Sales (₹ Cr)",
            "expenses": "Expenses (₹ Cr)",
            "operating_profit": "Operating Profit (₹ Cr)",
            "profit_before_tax": "Profit Before Tax (₹ Cr)",
            "net_profit": "Net Profit (₹ Cr)",
            "eps": "EPS",
            "dividend_payout": "Dividend Payout (%)",
        }
    )


    trend_table = trend_table.iloc[::-1]


    st.dataframe(
        trend_table,
        use_container_width=True,
        hide_index=True,
    )