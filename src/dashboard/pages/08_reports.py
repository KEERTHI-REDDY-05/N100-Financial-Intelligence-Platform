import pandas as pd
import streamlit as st

from src.dashboard.utils.db import (
    get_companies,
    get_documents,
)


st.set_page_config(
    page_title="Annual Reports | Nifty 100 Analytics",
    page_icon="📄",
    layout="wide",
)

st.title("Annual Reports")

st.caption(
    "Browse and open annual reports for Nifty 100 companies."
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

selected_company = st.selectbox(
    "Select Company",
    company_options["company_name"]
)

selected_row = company_options[
    company_options["company_name"] == selected_company
].iloc[0]

ticker = str(selected_row["id"]).strip()

# ---------------------------------------------------------
# Load reports
# ---------------------------------------------------------

try:
    reports = get_documents(ticker)

except Exception as error:
    st.error("Unable to load annual reports.")
    st.exception(error)
    st.stop()

st.markdown("---")

st.subheader(selected_company)

st.write(f"**Ticker:** {ticker}")

if reports.empty:
    st.info("No annual reports available.")
    st.stop()

reports = reports.copy()

reports["year_numeric"] = pd.to_numeric(
    reports["year"]
    .astype(str)
    .str.extract(r"(\d{4})")[0],
    errors="coerce",
)

reports = reports.sort_values(
    "year_numeric",
    ascending=False
)

# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

metric1, metric2 = st.columns(2)

metric1.metric(
    "Available Reports",
    len(reports)
)

latest_year = reports.iloc[0]["year"]

metric2.metric(
    "Latest Report",
    latest_year
)

# ---------------------------------------------------------
# Report table
# ---------------------------------------------------------

st.subheader("Available Annual Reports")

table = reports[
    [
        "year",
        "annual_report",
    ]
].rename(
    columns={
        "year": "Year",
        "annual_report": "Report URL",
    }
)

st.dataframe(
    table,
    hide_index=True,
    use_container_width=True,
)

# ---------------------------------------------------------
# Report buttons
# ---------------------------------------------------------

st.subheader("Open Reports")

for _, row in reports.iterrows():

    year = row["year"]

    report_url = row["annual_report"]

    col1, col2 = st.columns([3,1])

    with col1:
        st.write(f"### {year}")

    with col2:
        if pd.notna(report_url):

            st.link_button(
                "Open Report",
                report_url,
                use_container_width=True,
            )

        else:
            st.button(
                "Unavailable",
                disabled=True,
                use_container_width=True,
            )

# ---------------------------------------------------------
# Download links csv
# ---------------------------------------------------------

csv = reports.to_csv(
    index=False
).encode("utf-8")

st.download_button(
    "Download Report List",
    csv,
    "annual_reports.csv",
    "text/csv",
)