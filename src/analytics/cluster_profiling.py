import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import pandas as pd

from src.analytics.clustering import (
    FEATURES,
    load_financial_features,
    impute_sector_medians,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def create_cluster_profiles():
    """
    Calculate mean and median values for each KMeans cluster.
    """

    labels_path = OUTPUT_DIR / "cluster_labels.csv"

    if not labels_path.exists():
        raise FileNotFoundError(
            "cluster_labels.csv was not found. "
            "Run clustering.py first."
        )

    # Load the financial features used for clustering
    financial_data = load_financial_features()

    # Apply the same missing-value treatment used during clustering
    financial_data = impute_sector_medians(financial_data)

    # Load cluster assignments
    cluster_labels = pd.read_csv(labels_path)

    # Merge company financial data with cluster IDs
    df = financial_data.merge(
        cluster_labels[
            [
                "company_id",
                "cluster_id",
            ]
        ],
        on="company_id",
        how="inner",
    )

    print()
    print(f"Companies available for profiling: {len(df)}")

    # -----------------------------------------------------
    # Number of companies in each cluster
    # -----------------------------------------------------

    cluster_counts = (
        df.groupby("cluster_id")
        .size()
        .rename("company_count")
    )

    # -----------------------------------------------------
    # Mean values
    # -----------------------------------------------------

    means = (
        df.groupby("cluster_id")[FEATURES]
        .mean()
        .round(2)
    )

    means.columns = [
        f"{column}_mean"
        for column in means.columns
    ]

    # -----------------------------------------------------
    # Median values
    # -----------------------------------------------------

    medians = (
        df.groupby("cluster_id")[FEATURES]
        .median()
        .round(2)
    )

    medians.columns = [
        f"{column}_median"
        for column in medians.columns
    ]

    # -----------------------------------------------------
    # Combine statistics
    # -----------------------------------------------------

    profiles = pd.concat(
        [
            cluster_counts,
            means,
            medians,
        ],
        axis=1,
    ).reset_index()

    # Save profile
    output_path = OUTPUT_DIR / "cluster_profiles.csv"

    profiles.to_csv(
        output_path,
        index=False,
    )

    # -----------------------------------------------------
    # Display results
    # -----------------------------------------------------

    print()
    print("=" * 80)
    print("CLUSTER COUNTS")
    print("=" * 80)

    print(cluster_counts)

    print()
    print("=" * 80)
    print("CLUSTER MEANS")
    print("=" * 80)

    print(means.to_string())

    print()
    print("=" * 80)
    print("CLUSTER MEDIANS")
    print("=" * 80)

    print(medians.to_string())

    print()
    print(
        f"Cluster profile saved to: {output_path}"
    )

    return profiles
def generate_correlation_heatmap():
    """
    Generate Pearson correlation heatmap for 10 core KPIs
    using the latest available year for each company.
    """

    ratios_path = PROJECT_ROOT / "data" / "financial_ratios.xlsx"

    df = pd.read_excel(ratios_path)

    kpis = [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "free_cash_flow_cr",
        "earnings_per_share",
        "dividend_payout_ratio_pct",
        "cash_from_operations_cr",
    ]

    # Convert year into numeric form
    df["numeric_year"] = (
        df["year"]
        .astype(str)
        .str.extract(r"(\d{4})")[0]
    )

    df["numeric_year"] = pd.to_numeric(
        df["numeric_year"],
        errors="coerce",
    )

    # Keep latest available year for each company
    latest = (
        df.sort_values(
            ["company_id", "numeric_year"]
        )
        .groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
        .copy()
    )

    # Convert KPI values to numeric
    for column in kpis:
        latest[column] = pd.to_numeric(
            latest[column],
            errors="coerce",
        )

    print()
    print(
        f"Companies used for correlation: "
        f"{latest['company_id'].nunique()}"
    )

    # Pearson correlation
    correlation = latest[kpis].corr(
        method="pearson"
    )

    # Save numeric correlation matrix too
    correlation_csv = (
        OUTPUT_DIR / "correlation_matrix.csv"
    )

    correlation.to_csv(correlation_csv)

    # Create heatmap
    plt.figure(figsize=(14, 10))

    sns.heatmap(
        correlation,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        square=True,
        linewidths=0.5,
    )

    plt.title(
        "Pearson Correlation Matrix - 10 Financial KPIs"
    )

    plt.xticks(
        rotation=45,
        ha="right",
    )

    plt.yticks(rotation=0)

    plt.tight_layout()

    output_path = (
        REPORTS_DIR / "correlation_heatmap.png"
    )

    plt.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(
        f"Correlation heatmap saved to: {output_path}"
    )

    print(
        f"Correlation matrix saved to: {correlation_csv}"
    )

    return correlation
def generate_outlier_report():
    """
    Detect financial outliers within each broad sector
    using absolute Z-score greater than 3.
    """

    ratios_path = PROJECT_ROOT / "data" / "financial_ratios.xlsx"
    sectors_path = PROJECT_ROOT / "data" / "sectors.xlsx"

    ratios = pd.read_excel(ratios_path)
    sectors = pd.read_excel(sectors_path)

    kpis = [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "free_cash_flow_cr",
        "earnings_per_share",
        "dividend_payout_ratio_pct",
        "cash_from_operations_cr",
    ]

    # -----------------------------------------------------
    # Get latest available year for every company
    # -----------------------------------------------------

    ratios["numeric_year"] = (
        ratios["year"]
        .astype(str)
        .str.extract(r"(\d{4})")[0]
    )

    ratios["numeric_year"] = pd.to_numeric(
        ratios["numeric_year"],
        errors="coerce",
    )

    latest = (
        ratios
        .sort_values(
            ["company_id", "numeric_year"]
        )
        .groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
        .copy()
    )

    # -----------------------------------------------------
    # Add broad sector
    # -----------------------------------------------------

    sector_data = sectors[
        [
            "company_id",
            "broad_sector",
        ]
    ].drop_duplicates(
        subset=["company_id"]
    )

    df = latest.merge(
        sector_data,
        on="company_id",
        how="left",
    )

    # -----------------------------------------------------
    # Ensure KPIs are numeric
    # -----------------------------------------------------

    for metric in kpis:
        df[metric] = pd.to_numeric(
            df[metric],
            errors="coerce",
        )

    # -----------------------------------------------------
    # Calculate sector-level Z-scores
    # -----------------------------------------------------

    outlier_records = []

    for metric in kpis:

        sector_mean = df.groupby(
            "broad_sector"
        )[metric].transform("mean")

        sector_std = df.groupby(
            "broad_sector"
        )[metric].transform("std")

        # Avoid division by zero
        sector_std = sector_std.replace(
            0,
            pd.NA,
        )

        zscore_column = (
            df[metric] - sector_mean
        ) / sector_std

        for index in df.index:

            z_score = zscore_column.loc[index]

            if pd.notna(z_score) and abs(z_score) > 3:

                outlier_records.append(
                    {
                        "company_id": df.loc[
                            index,
                            "company_id",
                        ],
                        "broad_sector": df.loc[
                            index,
                            "broad_sector",
                        ],
                        "metric": metric,
                        "metric_value": df.loc[
                            index,
                            metric,
                        ],
                        "z_score": round(
                            float(z_score),
                            4,
                        ),
                        "absolute_z_score": round(
                            abs(float(z_score)),
                            4,
                        ),
                    }
                )

    # -----------------------------------------------------
    # Create report
    # -----------------------------------------------------

    outliers = pd.DataFrame(
        outlier_records
    )

    if not outliers.empty:

        outliers = outliers.sort_values(
            "absolute_z_score",
            ascending=False,
        )

    output_path = (
        OUTPUT_DIR / "outlier_report.csv"
    )

    outliers.to_csv(
        output_path,
        index=False,
    )

    print()
    print("=" * 80)
    print("OUTLIER DETECTION")
    print("=" * 80)

    print(
        f"Companies analysed: "
        f"{df['company_id'].nunique()}"
    )

    print(
        f"Outlier observations found: "
        f"{len(outliers)}"
    )

    if not outliers.empty:

        print(
            f"Unique companies flagged: "
            f"{outliers['company_id'].nunique()}"
        )

        print()
        print(
            outliers[
                [
                    "company_id",
                    "broad_sector",
                    "metric",
                    "z_score",
                ]
            ].to_string(index=False)
        )

    else:

        print(
            "No observations exceeded "
            "|Z-score| > 3."
        )

    print()
    print(
        f"Outlier report saved to: {output_path}"
    )

    return outliers
def generate_portfolio_stats():
    """
    Generate portfolio-level descriptive statistics
    for 10 core financial KPIs.
    """

    ratios_path = PROJECT_ROOT / "data" / "financial_ratios.xlsx"

    df = pd.read_excel(ratios_path)

    kpis = [
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "return_on_equity_pct",
        "debt_to_equity",
        "interest_coverage",
        "asset_turnover",
        "free_cash_flow_cr",
        "earnings_per_share",
        "dividend_payout_ratio_pct",
        "cash_from_operations_cr",
    ]

    # Extract numeric year
    df["numeric_year"] = (
        df["year"]
        .astype(str)
        .str.extract(r"(\d{4})")[0]
    )

    df["numeric_year"] = pd.to_numeric(
        df["numeric_year"],
        errors="coerce",
    )

    # Keep latest available year for each company
    latest = (
        df.sort_values(
            ["company_id", "numeric_year"]
        )
        .groupby(
            "company_id",
            as_index=False,
        )
        .tail(1)
        .copy()
    )

    # Convert KPI columns to numeric
    for metric in kpis:
        latest[metric] = pd.to_numeric(
            latest[metric],
            errors="coerce",
        )

    # Calculate required statistics
    records = []

    for metric in kpis:

        values = latest[metric].dropna()

        records.append(
            {
                "kpi": metric,
                "P10": values.quantile(0.10),
                "P25": values.quantile(0.25),
                "P50": values.quantile(0.50),
                "P75": values.quantile(0.75),
                "P90": values.quantile(0.90),
                "Mean": values.mean(),
                "Std": values.std(),
            }
        )

    stats = pd.DataFrame(records)

    numeric_columns = [
        "P10",
        "P25",
        "P50",
        "P75",
        "P90",
        "Mean",
        "Std",
    ]

    stats[numeric_columns] = (
        stats[numeric_columns].round(2)
    )

    output_path = (
        OUTPUT_DIR / "portfolio_stats.csv"
    )

    stats.to_csv(
        output_path,
        index=False,
    )

    print()
    print("=" * 80)
    print("PORTFOLIO STATISTICS")
    print("=" * 80)

    print(
        f"Companies analysed: "
        f"{latest['company_id'].nunique()}"
    )

    print()
    print(stats.to_string(index=False))

    print()
    print(
        f"Portfolio statistics saved to: {output_path}"
    )

    return stats
if __name__ == "__main__":
    create_cluster_profiles()
    generate_correlation_heatmap()
    generate_outlier_report()
    generate_portfolio_stats()