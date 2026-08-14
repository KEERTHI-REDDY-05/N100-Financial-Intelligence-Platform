# N100 Financial Intelligence Platform

A financial analytics and intelligence platform for analysing NIFTY 100 companies using financial statements, valuation metrics, peer comparisons, clustering, portfolio statistics, NLP insights, dashboards, PDF reports, and a FastAPI backend.

## Project Overview

The N100 Financial Intelligence Platform is designed to provide structured financial intelligence for 92 companies using historical company data, financial ratios, valuation metrics, sector information, peer groups, clustering, and annual-report documents.

The platform includes:

- Financial statement analysis
- Financial ratio analysis
- Valuation analysis
- Company screening
- Sector analysis
- Peer comparison
- Portfolio clustering
- Portfolio-level statistics
- Annual report document access
- Company tearsheet PDF generation
- Streamlit dashboard
- REST API using FastAPI
- Automated API testing

## Technology Stack

- Python
- Pandas
- NumPy
- Scikit-learn
- SQLite
- FastAPI
- Uvicorn
- Streamlit
- Matplotlib
- ReportLab
- Pytest
- HTTPX

## Requirements

- Python 3.13 or later
- pip
### Install Dependencies

Clone the repository and navigate to the project directory, then install the required Python packages:

```bash
pip install -r requirements.txt
```

### Build the Database

The SQLite database can be rebuilt from the source Excel files using:

```bash
python build_database.py
```

This creates the database tables for companies, financial statements, ratios, sectors, peer groups, valuation data, documents, and pros/cons.

## Project Structure

- `data/` - Source Excel datasets and SQLite financial database
- `output/` - Generated analytics outputs and portfolio statistics
- `reports/` - Company tearsheets, sector reports, and portfolio reports
- `scripts/` - Data processing and utility scripts
- `src/analytics/` - Financial analytics, valuation, clustering, and KPI logic
- `src/api/` - FastAPI backend and API routers
- `src/dashboard/` - Streamlit dashboard, pages, and utilities
- `src/nlp/` - Annual-report parsing and pros/cons generation
- `src/reports/` - PDF report generation
- `tests/` - Automated unit and API tests
- `API_ENDPOINTS.md` - API endpoint documentation
- `build_database.py` - Builds the SQLite database from source datasets
- `requirements.txt` - Python dependencies