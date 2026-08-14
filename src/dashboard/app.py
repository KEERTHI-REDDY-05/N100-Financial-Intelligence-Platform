import streamlit as st

from src.dashboard.utils.db import get_companies


st.set_page_config(
    page_title="Nifty 100 Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.title("Nifty 100 Financial Intelligence Platform")

st.caption(
    "Financial analytics dashboard for Nifty 100 companies"
)


try:
    companies = get_companies()

    st.success(
        f"Data loaded successfully: {len(companies)} companies available."
    )

except Exception as error:
    st.error("Unable to load company data.")

    st.exception(error)


st.sidebar.title("Navigation")

st.sidebar.info(
    "Use the page menu to open the dashboard screens."
)


st.subheader("Dashboard Overview")

col1, col2, col3 = st.columns(3)

col1.metric(
    label="Total Companies",
    value=len(companies) if "companies" in locals() else "N/A",
)

col2.metric(
    label="Dashboard Screens",
    value="8",
)

col3.metric(
    label="Project Status",
    value="Active",
)


st.markdown("---")

st.write(
    """
    This dashboard will include:

    - Home dashboard
    - Company profile
    - Financial screener
    - Peer comparison
    - Trend analysis
    - Sector analysis
    - Capital allocation map
    - Annual reports
    """
)