# N100 Financial Intelligence API

Version: 1.0.0

Base URL:

http://127.0.0.1:8000

## Health

GET /api/v1/health

Returns API status, uptime and database row counts.

## Companies

GET /api/v1/companies

Returns all companies with optional:
- sector
- market_cap_category
- search

GET /api/v1/companies/{ticker}

Returns company profile, sector information and latest KPIs.

GET /api/v1/companies/{ticker}/pl

Returns profit and loss history with optional:
- from_year
- to_year

GET /api/v1/companies/{ticker}/bs

Returns balance sheet history with optional:
- from_year
- to_year

GET /api/v1/companies/{ticker}/cashflow

Returns deduplicated cash-flow history with optional:
- from_year
- to_year

GET /api/v1/companies/{ticker}/ratios

Returns financial ratios with optional:
- year

GET /api/v1/companies/{ticker}/tearsheet

Returns the generated company tearsheet PDF.

## Screener

GET /api/v1/screener

Supported filters:
- min_roe
- max_de
- min_fcf
- sector
- min_rev_cagr_5yr
- min_pat_cagr_5yr
- max_pe

## Sectors

GET /api/v1/sectors

Returns sector-level company counts and median metrics.

GET /api/v1/sectors/{sector}/companies

Returns companies in a selected sector.

## Peers

GET /api/v1/peers/{group_name}

Returns peer-group companies with percentile ranks.

## Valuation

GET /api/v1/valuation/{ticker}

Returns valuation history, historical averages, valuation signals,
market-cap growth and valuation score.

## Portfolio

GET /api/v1/portfolio/clusters

Returns the five company clusters and their members.

GET /api/v1/portfolio/stats

Returns percentile and statistical summaries for ten core KPIs.

## Documents

GET /api/v1/documents/{ticker}

Returns annual-report links for the selected company.

## Documentation

Swagger UI:

http://127.0.0.1:8000/docs

ReDoc:

http://127.0.0.1:8000/redoc

OpenAPI schema:

http://127.0.0.1:8000/openapi.json

## Testing

Run API tests with:

python -m pytest tests/api -v

Current automated API suite:

60 passing tests

Performance target:

All tested endpoints respond in under 500 ms in the local test environment.