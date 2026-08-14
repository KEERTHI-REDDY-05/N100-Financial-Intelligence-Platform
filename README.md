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
## Project Structure

```text
N100-Financial-Intelligence-Platform/
│
├── data/
│   └── n100_financial.db
│
├── output/
│   ├── cluster_labels.csv
│   ├── cluster_profiles.csv
│   ├── portfolio_stats.csv
│   ├── outlier_report.csv
│   └── reports/
│
├── src/
│   ├── analytics/
│   ├── api/
│   │   ├── main.py
│   │   └── routers/
│   ├── dashboard/
│   ├── nlp/
│   └── reports/
│
├── tests/
│   └── api/
│
├── API_ENDPOINTS.md
└── README.md