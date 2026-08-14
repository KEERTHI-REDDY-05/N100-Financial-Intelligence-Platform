from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException


router = APIRouter(
    prefix="/portfolio",
    tags=["Portfolio"],
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CLUSTER_FILE = (
    PROJECT_ROOT
    / "output"
    / "cluster_labels.csv"
)


@router.get("/clusters")
def get_clusters():
    """
    Return all 5 portfolio clusters
    with their assigned companies.
    """

    if not CLUSTER_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="cluster_labels.csv not found",
        )

    df = pd.read_csv(CLUSTER_FILE)

    required_columns = {
        "company_id",
        "cluster_id",
        "cluster_name",
        "distance_from_centroid",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise HTTPException(
            status_code=500,
            detail=(
                "Missing cluster columns: "
                + ", ".join(sorted(missing))
            ),
        )

    clusters = []

    for cluster_id, group in df.groupby(
    "cluster_id",
    sort=True,
):

        cluster_name = (
            group["cluster_name"]
            .iloc[0]
        )

        companies = (
            group.sort_values(
                "distance_from_centroid"
            )[
                [
                    "company_id",
                    "distance_from_centroid",
                ]
            ]
            .to_dict(orient="records")
        )

        clusters.append(
            {
                "cluster_id": int(cluster_id),
                "cluster_name": cluster_name,
                "company_count": len(companies),
                "companies": companies,
            }
        )

    return {
        "count": len(clusters),
        "total_companies": len(df),
        "clusters": clusters,
    }
STATS_FILE = (
    PROJECT_ROOT
    / "output"
    / "portfolio_stats.csv"
)


@router.get("/stats")
def get_portfolio_stats():
    """
    Return portfolio-level statistics
    for the 10 core KPIs.
    """

    if not STATS_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="portfolio_stats.csv not found",
        )

    df = pd.read_csv(STATS_FILE)

    required_columns = {
        "kpi",
        "P10",
        "P25",
        "P50",
        "P75",
        "P90",
        "Mean",
        "Std",
    }

    missing = required_columns - set(df.columns)

    if missing:
        raise HTTPException(
            status_code=500,
            detail=(
                "Missing portfolio statistics columns: "
                + ", ".join(sorted(missing))
            ),
        )

    records = (
        df.where(pd.notnull(df), None)
        .to_dict(orient="records")
    )

    return {
        "count": len(records),
        "statistics": records,
    }