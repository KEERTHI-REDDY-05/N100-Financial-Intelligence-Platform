from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = PROJECT_ROOT / "reports"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


FEATURES = [
    "return_on_equity_pct",
    "debt_to_equity",
    "revenue_cagr_5yr",
    "fcf_cagr_5yr",
    "operating_profit_margin_pct",
]


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def read_excel_with_header_detection(file_path):
    """
    Read Excel files that may contain a title row before the real header.
    """

    df = pd.read_excel(file_path)

    # Files such as profitandloss.xlsx contain a descriptive first row.
    if any(str(col).startswith("Unnamed:") for col in df.columns):
        df = pd.read_excel(file_path, header=1)

    return df


def extract_year(value):
    """
    Convert values such as 'Mar 2024' or 'Dec 2023' into numeric year.
    """

    if pd.isna(value):
        return np.nan

    text = str(value)

    year = pd.to_numeric(
        text[-4:],
        errors="coerce"
    )

    return year


def calculate_cagr(start_value, end_value, years):
    """
    Calculate CAGR percentage.
    """

    if (
        pd.isna(start_value)
        or pd.isna(end_value)
        or years <= 0
        or start_value <= 0
        or end_value <= 0
    ):
        return np.nan

    return (
        ((end_value / start_value) ** (1 / years)) - 1
    ) * 100


# ---------------------------------------------------------
# Revenue CAGR
# ---------------------------------------------------------

def calculate_revenue_cagr():
    """
    Calculate approximately five-year revenue CAGR
    for every company using P&L sales data.
    """

    pl_path = DATA_DIR / "profitandloss.xlsx"

    pl = read_excel_with_header_detection(pl_path)

    required_columns = {
        "company_id",
        "year",
        "sales",
    }

    missing = required_columns - set(pl.columns)

    if missing:
        raise ValueError(
            f"Missing P&L columns: {sorted(missing)}"
        )

    pl["numeric_year"] = pl["year"].apply(extract_year)

    pl["sales"] = pd.to_numeric(
        pl["sales"],
        errors="coerce"
    )

    results = []

    for company_id, group in pl.groupby("company_id"):

        group = (
            group
            .dropna(subset=["numeric_year", "sales"])
            .sort_values("numeric_year")
        )

        if len(group) < 2:
            results.append(
                {
                    "company_id": company_id,
                    "revenue_cagr_5yr": np.nan,
                }
            )
            continue

        latest = group.iloc[-1]

        latest_year = int(latest["numeric_year"])
        target_year = latest_year - 5

        earlier = group[
            group["numeric_year"] <= target_year
        ]

        if earlier.empty:
            earlier = group.iloc[:-1]

        start = earlier.iloc[-1]

        actual_years = (
            latest["numeric_year"]
            - start["numeric_year"]
        )

        cagr = calculate_cagr(
            start["sales"],
            latest["sales"],
            actual_years,
        )

        results.append(
            {
                "company_id": company_id,
                "revenue_cagr_5yr": cagr,
            }
        )

    return pd.DataFrame(results)


# ---------------------------------------------------------
# Load latest financial metrics
# ---------------------------------------------------------

def load_financial_features():
    """
    Combine all five clustering features into one DataFrame.
    """

    ratios_path = DATA_DIR / "financial_ratios.xlsx"
    sectors_path = DATA_DIR / "sectors.xlsx"
    cashflow_path = OUTPUT_DIR / "cashflow_intelligence.xlsx"

    ratios = pd.read_excel(ratios_path)

    sectors = pd.read_excel(sectors_path)

    cashflow = pd.read_excel(cashflow_path)

    ratios["numeric_year"] = ratios["year"].apply(
        extract_year
    )

    ratios = ratios.sort_values(
        ["company_id", "numeric_year"]
    )

    latest_ratios = (
        ratios
        .groupby("company_id", as_index=False)
        .tail(1)
    )

    latest_ratios = latest_ratios[
        [
            "company_id",
            "return_on_equity_pct",
            "debt_to_equity",
            "operating_profit_margin_pct",
        ]
    ]

    revenue_cagr = calculate_revenue_cagr()

    cashflow = cashflow[
        [
            "company_id",
            "fcf_cagr_5yr",
        ]
    ]

    sectors = sectors[
        [
            "company_id",
            "broad_sector",
        ]
    ]

    df = latest_ratios.merge(
        revenue_cagr,
        on="company_id",
        how="left",
    )

    df = df.merge(
        cashflow,
        on="company_id",
        how="left",
    )

    df = df.merge(
        sectors,
        on="company_id",
        how="left",
    )

    for feature in FEATURES:
        df[feature] = pd.to_numeric(
            df[feature],
            errors="coerce"
        )

    return df


# ---------------------------------------------------------
# Missing-value imputation
# ---------------------------------------------------------

def impute_sector_medians(df):
    """
    Replace missing values with sector median,
    then overall median if a sector median is unavailable.
    """

    result = df.copy()

    for feature in FEATURES:

        sector_median = result.groupby(
            "broad_sector"
        )[feature].transform("median")

        result[feature] = (
            result[feature]
            .fillna(sector_median)
        )

        result[feature] = (
            result[feature]
            .fillna(result[feature].median())
        )

    return result


# ---------------------------------------------------------
# Elbow analysis
# ---------------------------------------------------------

def generate_elbow_plot(X_scaled):
    """
    Generate KMeans inertia values for k=2 through k=10.
    """

    inertias = []

    k_values = range(2, 11)

    for k in k_values:

        model = KMeans(
            n_clusters=k,
            random_state=42,
            n_init=10,
        )

        model.fit(X_scaled)

        inertias.append(model.inertia_)

    plt.figure(figsize=(8, 5))

    plt.plot(
        list(k_values),
        inertias,
        marker="o",
    )

    plt.xlabel("Number of Clusters (k)")
    plt.ylabel("Inertia")
    plt.title("KMeans Elbow Plot")

    plt.grid(True)

    output_path = (
        REPORTS_DIR / "elbow_plot.png"
    )

    plt.tight_layout()
    plt.savefig(
        output_path,
        dpi=200,
    )

    plt.close()

    print(
        f"Elbow plot saved to: {output_path}"
    )


# ---------------------------------------------------------
# KMeans clustering
# ---------------------------------------------------------

def run_clustering():
    """
    Run five-cluster KMeans model and save cluster assignments.
    """

    df = load_financial_features()

    print(
        f"Companies loaded: {len(df)}"
    )

    df = impute_sector_medians(df)

    X = df[FEATURES]

    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(X)

    generate_elbow_plot(X_scaled)

    model = KMeans(
        n_clusters=5,
        random_state=42,
        n_init=10,
    )

    df["cluster_id"] = model.fit_predict(
        X_scaled
    )

    distances = model.transform(
        X_scaled
    )

    df["distance_from_centroid"] = [
        distances[i, cluster]
        for i, cluster in enumerate(
            df["cluster_id"]
        )
    ]

    # Temporary descriptive names.
    # We will profile and refine these on Day 37.
    cluster_names = {
    0: "Exceptional Return Outliers",
    1: "High-Quality Compounders",
    2: "Leveraged Cyclicals",
    3: "Emerging Growth Outliers",
    4: "Cash Flow Growth Leaders",
}

    df["cluster_name"] = df[
        "cluster_id"
    ].map(cluster_names)

    output = df[
        [
            "company_id",
            "cluster_id",
            "cluster_name",
            "distance_from_centroid",
        ]
    ].copy()

    output = output.sort_values(
        [
            "cluster_id",
            "distance_from_centroid",
        ]
    )

    output_path = (
        OUTPUT_DIR / "cluster_labels.csv"
    )

    output.to_csv(
        output_path,
        index=False,
    )

    print()
    print("KMeans clustering completed.")
    print(
        f"Cluster labels saved to: {output_path}"
    )

    print()
    print("Cluster distribution:")

    print(
        output[
            "cluster_id"
        ].value_counts().sort_index()
    )

    print()
    print(
        f"Total companies clustered: {len(output)}"
    )

    return df


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

if __name__ == "__main__":
    run_clustering()