from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import (
    companies,
    screener,
    sectors,
    peers,
    valuation,
    portfolio,
    documents,
    health,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "n100_financial.db"

START_TIME = time.time()


def get_db_connection():
    """
    Create and return a SQLite database connection.
    """
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


app = FastAPI(
    title="N100 Financial Intelligence API",
    description="REST API for the N100 Financial Intelligence Platform",
    version="1.0.0",
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """
    Convert FastAPI validation errors from 422 to 400.
    """

    return JSONResponse(
        status_code=400,
        content={
            "detail": "Invalid request parameter",
            "errors": exc.errors(),
        },
    )
# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log request method, path and response time.
    """

    start_time = time.perf_counter()

    response = await call_next(request)

    process_time = (
        time.perf_counter() - start_time
    ) * 1000

    print(
        f"{request.method} "
        f"{request.url.path} "
        f"- {process_time:.2f} ms"
    )

    return response


# ---------------------------------------------------------
# Register routers
# ---------------------------------------------------------

app.include_router(
    health.router,
    prefix="/api/v1",
)

app.include_router(
    companies.router,
    prefix="/api/v1",
)

app.include_router(
    screener.router,
    prefix="/api/v1",
)

app.include_router(
    sectors.router,
    prefix="/api/v1",
)

app.include_router(
    peers.router,
    prefix="/api/v1",
)

app.include_router(
    valuation.router,
    prefix="/api/v1",
)

app.include_router(
    portfolio.router,
    prefix="/api/v1",
)

app.include_router(
    documents.router,
    prefix="/api/v1",
)


@app.get("/")
def root():
    """
    Root API endpoint.
    """

    return {
        "message": "N100 Financial Intelligence API",
        "version": "1.0.0",
        "docs": "/docs",
    }