import pandas as pd
import streamlit as st

from src.dashboard.utils.db import (
    format_metric,
    get_companies,
    get_company,
    get_company_sector,
    get_documents,
    get_pros_and_cons,
)


st.set_page_config(
    page_title="Company Profile | Nifty 100 Analytics",
    page_icon="🏢",
    layout="wide",
)


st.title("Company Profile")

st.caption(
    "View company details, financial highlights, strengths, "
    "risks, and annual reports."
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


# ---------------------------------------------------------
# Company selection
# ---------------------------------------------------------

selected_company_name = st.selectbox(
    label="Select a company",
    options=company_options["company_name"].tolist(),
)


selected_row = company_options[
    company_options["company_name"] == selected_company_name
].iloc[0]


ticker = str(selected_row["id"]).strip()


# ---------------------------------------------------------
# Load selected company information
# ---------------------------------------------------------

try:
    company_data = get_company(ticker)
    sector_data = get_company_sector(ticker)
    pros_cons_data = get_pros_and_cons(ticker)
    documents_data = get_documents(ticker)

except Exception as error:
    st.error(
        f"Unable to load profile data for {selected_company_name}."
    )
    st.exception(error)
    st.stop()


if company_data.empty:
    st.warning("Company information is not available.")
    st.stop()


company = company_data.iloc[0]


# ---------------------------------------------------------
# Company overview
# ---------------------------------------------------------

st.markdown("---")

profile_column, links_column = st.columns([3, 1])


with profile_column:
    st.subheader(selected_company_name)

    st.write(f"**Ticker:** {ticker}")

    about_company = company.get("about_company")

    if pd.notna(about_company) and str(about_company).strip():
        st.write(str(about_company))

    else:
        st.info("Company description is not available.")


with links_column:
    st.markdown("#### External Links")

    website = company.get("website")
    nse_profile = company.get("nse_profile")
    bse_profile = company.get("bse_profile")
    chart_link = company.get("chart_link")

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

    if pd.notna(chart_link) and str(chart_link).strip():
        st.link_button(
            "Stock Chart",
            str(chart_link),
            use_container_width=True,
        )


# ---------------------------------------------------------
# Company metrics
# ---------------------------------------------------------

st.markdown("---")

st.subheader("Company Highlights")


face_value = company.get("face_value")
book_value = company.get("book_value")
roce = company.get("roce_percentage")
roe = company.get("roe_percentage")


metric1, metric2, metric3, metric4 = st.columns(4)


metric1.metric(
    label="Face Value",
    value=(
        f"₹{format_metric(face_value)}"
        if pd.notna(face_value)
        else "N/A"
    ),
)


metric2.metric(
    label="Book Value",
    value=(
        f"₹{format_metric(book_value)}"
        if pd.notna(book_value)
        else "N/A"
    ),
)


metric3.metric(
    label="ROCE",
    value=(
        format_metric(roce, suffix="%")
        if pd.notna(roce)
        else "N/A"
    ),
)


metric4.metric(
    label="ROE",
    value=(
        format_metric(roe, suffix="%")
        if pd.notna(roe)
        else "N/A"
    ),
)


# ---------------------------------------------------------
# Sector information
# ---------------------------------------------------------

st.subheader("Sector Classification")


broad_sector = "N/A"
sub_sector = "N/A"
market_cap_category = "N/A"
index_weight = "N/A"


if not sector_data.empty:
    sector = sector_data.iloc[0]

    broad_sector = sector.get(
        "broad_sector",
        "N/A",
    )

    sub_sector = sector.get(
        "sub_sector",
        "N/A",
    )

    market_cap_category = sector.get(
        "market_cap_category",
        "N/A",
    )

    index_weight_value = sector.get(
        "index_weight_pct"
    )

    if pd.notna(index_weight_value):
        index_weight = format_metric(
            index_weight_value,
            suffix="%",
        )


sector1, sector2, sector3, sector4 = st.columns(4)


sector1.metric(
    label="Broad Sector",
    value=broad_sector,
)

sector2.metric(
    label="Sub-sector",
    value=sub_sector,
)

sector3.metric(
    label="Market-cap Category",
    value=market_cap_category,
)

sector4.metric(
    label="Index Weight",
    value=index_weight,
)


# ---------------------------------------------------------
# Pros and cons
# ---------------------------------------------------------

st.markdown("---")

st.subheader("Company Strengths and Risks")


pros_column, cons_column = st.columns(2)


if not pros_cons_data.empty:
    pros_cons = pros_cons_data.iloc[0]

    pros = pros_cons.get("pros")
    cons = pros_cons.get("cons")

else:
    pros = None
    cons = None


with pros_column:
    st.markdown("### Strengths")

    if pd.notna(pros) and str(pros).strip():
        pros_items = [
            item.strip()
            for item in str(pros).split("|")
            if item.strip()
        ]

        if len(pros_items) == 1:
            pros_items = [
                item.strip()
                for item in str(pros).split("\n")
                if item.strip()
            ]

        for item in pros_items:
            st.success(item)

    else:
        st.info("Strength information is not available.")


with cons_column:
    st.markdown("### Risks")

    if pd.notna(cons) and str(cons).strip():
        cons_items = [
            item.strip()
            for item in str(cons).split("|")
            if item.strip()
        ]

        if len(cons_items) == 1:
            cons_items = [
                item.strip()
                for item in str(cons).split("\n")
                if item.strip()
            ]

        for item in cons_items:
            st.warning(item)

    else:
        st.info("Risk information is not available.")


# ---------------------------------------------------------
# Annual reports
# ---------------------------------------------------------

st.markdown("---")

st.subheader("Annual Reports")


if documents_data.empty:
    st.info("No annual reports are available for this company.")

else:
    reports = documents_data.copy()

    reports["year_sort"] = pd.to_numeric(
        reports["year"]
        .astype(str)
        .str.extract(r"(\d{4})")[0],
        errors="coerce",
    )

    reports = reports.sort_values(
        by="year_sort",
        ascending=False,
    )


    for _, report in reports.iterrows():
        year = report.get("year", "Annual Report")
        report_url = report.get("annual_report")

        report_col1, report_col2 = st.columns([3, 1])

        with report_col1:
            st.write(f"**Annual Report — {year}**")

        with report_col2:
            if pd.notna(report_url) and str(report_url).strip():
                st.link_button(
                    "Open Report",
                    str(report_url),
                    use_container_width=True,
                )

            else:
                st.button(
                    "Report Unavailable",
                    disabled=True,
                    use_container_width=True,
                )