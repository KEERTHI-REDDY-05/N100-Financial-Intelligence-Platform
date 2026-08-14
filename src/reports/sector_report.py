from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
SECTOR_REPORT_DIR = PROJECT_ROOT / "reports" / "sector"

COMPANIES_FILE = DATA_DIR / "companies.xlsx"
SECTORS_FILE = DATA_DIR / "sectors.xlsx"
PROFIT_LOSS_FILE = DATA_DIR / "profitandloss.xlsx"
RATIOS_FILE = DATA_DIR / "financial_ratios.xlsx"
MARKET_CAP_FILE = DATA_DIR / "market_cap.xlsx"

CASHFLOW_INTELLIGENCE_FILE = (
    OUTPUT_DIR / "cashflow_intelligence.xlsx"
)

SECTOR_REPORT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# PDF styles
# ============================================================

STYLES = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    "SectorTitle",
    parent=STYLES["Heading1"],
    alignment=TA_CENTER,
    textColor=colors.white,
    fontSize=18,
    leading=22,
)

SECTION_STYLE = ParagraphStyle(
    "Section",
    parent=STYLES["Heading2"],
    fontSize=13,
    leading=16,
    spaceAfter=8,
)

BODY_STYLE = ParagraphStyle(
    "Body",
    parent=STYLES["BodyText"],
    fontSize=8,
    leading=10,
)

SMALL_STYLE = ParagraphStyle(
    "Small",
    parent=STYLES["BodyText"],
    fontSize=7,
    leading=9,
)


# ============================================================
# Helpers
# ============================================================

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in result.columns
    ]
    return result


def normalize_company_id(value: Any) -> str:
    if pd.isna(value):
        return ""

    return str(value).strip().upper()


def extract_year(value: Any) -> float:
    if pd.isna(value):
        return np.nan

    text = str(value).strip()

    four_digit = re.search(r"\b(?:19|20)\d{2}\b", text)

    if four_digit:
        return float(four_digit.group())

    two_digit = re.search(
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"[\s\-]*(\d{2})",
        text,
        re.IGNORECASE,
    )

    if two_digit:
        year = int(two_digit.group(1))

        if year <= 50:
            return float(2000 + year)

        return float(1900 + year)

    return np.nan


def load_excel(
    path: Path,
    header: int = 0,
) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    df = pd.read_excel(path, header=header)
    df = clean_columns(df)

    if "company_id" in df.columns:
        df["company_id"] = df[
            "company_id"
        ].apply(normalize_company_id)

    if "year" in df.columns:
        df["year_number"] = df[
            "year"
        ].apply(extract_year)

    return df


def safe_numeric(
    value: Any,
) -> float:
    result = pd.to_numeric(
        value,
        errors="coerce",
    )

    if pd.isna(result):
        return np.nan

    return float(result)


def latest_numeric_value(
    df: pd.DataFrame,
    column: str,
) -> float:
    if (
        df.empty
        or column not in df.columns
    ):
        return np.nan

    data = df.copy()

    if "year_number" in data.columns:
        data = data.sort_values(
            "year_number"
        )

    values = pd.to_numeric(
        data[column],
        errors="coerce",
    ).dropna()

    if values.empty:
        return np.nan

    return float(values.iloc[-1])


def calculate_cagr(
    values: pd.Series,
    years: int = 5,
) -> float:
    numeric_values = pd.to_numeric(
        values,
        errors="coerce",
    ).dropna()

    if len(numeric_values) < years + 1:
        return np.nan

    start_value = float(
        numeric_values.iloc[-(years + 1)]
    )
    end_value = float(
        numeric_values.iloc[-1]
    )

    if start_value <= 0 or end_value <= 0:
        return np.nan

    return (
        (
            end_value / start_value
        ) ** (1 / years)
        - 1
    ) * 100


def format_value(
    value: Any,
    decimals: int = 1,
    suffix: str = "",
) -> str:
    numeric = safe_numeric(value)

    if pd.isna(numeric):
        return "N/A"

    return f"{numeric:.{decimals}f}{suffix}"


def safe_filename(value: str) -> str:
    return re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        str(value).strip(),
    )


# ============================================================
# Load datasets
# ============================================================

def load_sector_data() -> dict[str, pd.DataFrame]:
    companies = load_excel(
        COMPANIES_FILE,
        header=1,
    )

    if "id" in companies.columns:
        companies = companies.rename(
            columns={"id": "company_id"}
        )

    companies["company_id"] = companies[
        "company_id"
    ].apply(normalize_company_id)

    sectors = load_excel(
        SECTORS_FILE,
        header=0,
    )

    profit_loss = load_excel(
        PROFIT_LOSS_FILE,
        header=1,
    )

    ratios = load_excel(
        RATIOS_FILE,
        header=0,
    )

    market_cap = load_excel(
        MARKET_CAP_FILE,
        header=0,
    )

    cashflow_intelligence = load_excel(
        CASHFLOW_INTELLIGENCE_FILE,
        header=0,
    )

    return {
        "companies": companies,
        "sectors": sectors,
        "profit_loss": profit_loss,
        "ratios": ratios,
        "market_cap": market_cap,
        "cashflow_intelligence": (
            cashflow_intelligence
        ),
    }


# ============================================================
# Build latest company metrics
# ============================================================

def build_company_metrics(
    datasets: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    companies = datasets["companies"]
    sectors = datasets["sectors"]
    profit_loss = datasets["profit_loss"]
    ratios = datasets["ratios"]
    market_cap = datasets["market_cap"]
    cashflow_intelligence = datasets[
        "cashflow_intelligence"
    ]

    rows: list[dict[str, Any]] = []

    company_ids = (
        companies["company_id"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .unique()
        .tolist()
    )

    for company_id in company_ids:
        company_match = companies[
            companies["company_id"] == company_id
        ]

        sector_match = sectors[
            sectors["company_id"] == company_id
        ]

        profit_rows = profit_loss[
            profit_loss["company_id"] == company_id
        ].copy()

        ratio_rows = ratios[
            ratios["company_id"] == company_id
        ].copy()

        market_rows = market_cap[
            market_cap["company_id"] == company_id
        ].copy()

        cashflow_match = cashflow_intelligence[
            cashflow_intelligence["company_id"]
            == company_id
        ]

        company_name = company_id

        if (
            not company_match.empty
            and "company_name" in company_match.columns
        ):
            company_name = str(
                company_match.iloc[0]["company_name"]
            )

        broad_sector = "Unknown"

        if (
            not sector_match.empty
            and "broad_sector" in sector_match.columns
        ):
            broad_sector = str(
                sector_match.iloc[0]["broad_sector"]
            )

        revenue_cagr = calculate_cagr(
            profit_rows.get(
                "sales",
                pd.Series(dtype=float),
            ),
            years=5,
        )

        pat_cagr = calculate_cagr(
            profit_rows.get(
                "net_profit",
                pd.Series(dtype=float),
            ),
            years=5,
        )

        latest_roe = latest_numeric_value(
            ratio_rows,
            "return_on_equity_pct",
        )

        latest_roce = np.nan

        if (
            not company_match.empty
            and "roce_percentage"
            in company_match.columns
        ):
            latest_roce = safe_numeric(
                company_match.iloc[0][
                    "roce_percentage"
                ]
            )

        latest_de = latest_numeric_value(
            ratio_rows,
            "debt_to_equity",
        )

        latest_pe = latest_numeric_value(
            market_rows,
            "price_to_earnings",
        )

        if pd.isna(latest_pe):
            latest_pe = latest_numeric_value(
                market_rows,
                "pe_ratio",
            )

        fcf_conversion = np.nan
        distress_flag = False

        if not cashflow_match.empty:
            row = cashflow_match.iloc[0]

            fcf_conversion = safe_numeric(
                row.get(
                    "fcf_conversion_pct",
                    np.nan,
                )
            )

            distress_flag = bool(
                row.get(
                    "distress_flag",
                    False,
                )
            )

        rows.append(
            {
                "company_id": company_id,
                "company_name": company_name,
                "sector": broad_sector,
                "revenue_cagr_5yr": revenue_cagr,
                "pat_cagr_5yr": pat_cagr,
                "roe_pct": latest_roe,
                "roce_pct": latest_roce,
                "debt_to_equity": latest_de,
                "pe_ratio": latest_pe,
                "fcf_conversion_pct": (
                    fcf_conversion
                ),
                "distress_flag": distress_flag,
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# PDF elements
# ============================================================

def create_sector_header(
    sector_name: str,
) -> Table:
    title = Paragraph(
        f"<b>{sector_name} Sector Report</b>",
        TITLE_STYLE,
    )

    table = Table(
        [[title]],
        colWidths=[10.8 * inch],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.darkblue,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    12,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    12,
                ),
            ]
        )
    )

    return table


def create_summary_cards(
    sector_df: pd.DataFrame,
) -> Table:
    distress_count = int(
        sector_df["distress_flag"].fillna(False).sum()
    )

    metrics = [
        (
            "Companies",
            str(len(sector_df)),
        ),
        (
            "Median Revenue CAGR",
            format_value(
                sector_df[
                    "revenue_cagr_5yr"
                ].median(),
                suffix="%",
            ),
        ),
        (
            "Median PAT CAGR",
            format_value(
                sector_df[
                    "pat_cagr_5yr"
                ].median(),
                suffix="%",
            ),
        ),
        (
            "Median ROE",
            format_value(
                sector_df["roe_pct"].median(),
                suffix="%",
            ),
        ),
        (
            "Median ROCE",
            format_value(
                sector_df["roce_pct"].median(),
                suffix="%",
            ),
        ),
        (
            "Median Debt/Equity",
            format_value(
                sector_df[
                    "debt_to_equity"
                ].median(),
                decimals=2,
            ),
        ),
        (
            "Median P/E",
            format_value(
                sector_df["pe_ratio"].median(),
                decimals=1,
            ),
        ),
        (
            "Median FCF Conversion",
            format_value(
                sector_df[
                    "fcf_conversion_pct"
                ].median(),
                suffix="%",
            ),
        ),
        (
            "Distress Flags",
            str(distress_count),
        ),
    ]

    cells = []

    for title, value in metrics:
        cells.append(
            Paragraph(
                (
                    f"<b>{title}</b><br/>"
                    f"<font size='12'>{value}</font>"
                ),
                BODY_STYLE,
            )
        )

    rows = [
        cells[0:3],
        cells[3:6],
        cells[6:9],
    ]

    table = Table(
        rows,
        colWidths=[3.45 * inch] * 3,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.grey,
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.whitesmoke,
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )

    return table


def create_company_table(
    sector_df: pd.DataFrame,
) -> Table:
    header = [
        Paragraph("<b>Ticker</b>", SMALL_STYLE),
        Paragraph("<b>Company</b>", SMALL_STYLE),
        Paragraph("<b>Revenue CAGR</b>", SMALL_STYLE),
        Paragraph("<b>PAT CAGR</b>", SMALL_STYLE),
        Paragraph("<b>ROE</b>", SMALL_STYLE),
        Paragraph("<b>ROCE</b>", SMALL_STYLE),
        Paragraph("<b>D/E</b>", SMALL_STYLE),
        Paragraph("<b>P/E</b>", SMALL_STYLE),
        Paragraph("<b>FCF Conversion</b>", SMALL_STYLE),
    ]

    rows = [header]

    sorted_df = sector_df.sort_values(
        "company_id"
    )

    for _, row in sorted_df.iterrows():
        rows.append(
            [
                Paragraph(
                    str(row["company_id"]),
                    SMALL_STYLE,
                ),
                Paragraph(
                    str(row["company_name"]),
                    SMALL_STYLE,
                ),
                Paragraph(
                    format_value(
                        row["revenue_cagr_5yr"],
                        suffix="%",
                    ),
                    SMALL_STYLE,
                ),
                Paragraph(
                    format_value(
                        row["pat_cagr_5yr"],
                        suffix="%",
                    ),
                    SMALL_STYLE,
                ),
                Paragraph(
                    format_value(
                        row["roe_pct"],
                        suffix="%",
                    ),
                    SMALL_STYLE,
                ),
                Paragraph(
                    format_value(
                        row["roce_pct"],
                        suffix="%",
                    ),
                    SMALL_STYLE,
                ),
                Paragraph(
                    format_value(
                        row["debt_to_equity"],
                        decimals=2,
                    ),
                    SMALL_STYLE,
                ),
                Paragraph(
                    format_value(
                        row["pe_ratio"],
                        decimals=1,
                    ),
                    SMALL_STYLE,
                ),
                Paragraph(
                    format_value(
                        row["fcf_conversion_pct"],
                        suffix="%",
                    ),
                    SMALL_STYLE,
                ),
            ]
        )

    table = Table(
        rows,
        repeatRows=1,
        colWidths=[
            0.75 * inch,
            2.15 * inch,
            1.05 * inch,
            1.0 * inch,
            0.7 * inch,
            0.7 * inch,
            0.65 * inch,
            0.65 * inch,
            1.15 * inch,
        ],
        splitByRow=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.darkblue,
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.grey,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (2, 1),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.whitesmoke,
                    ],
                ),
            ]
        )
    )

    return table


# ============================================================
# Generate reports
# ============================================================

def generate_sector_report(
    sector_name: str,
    metrics_df: pd.DataFrame,
) -> Path:
    sector_df = metrics_df[
        metrics_df["sector"] == sector_name
    ].copy()

    if sector_df.empty:
        raise ValueError(
            f"No companies found for sector: {sector_name}"
        )

    filename = (
        f"{safe_filename(sector_name)}_report.pdf"
    )

    pdf_path = SECTOR_REPORT_DIR / filename

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=landscape(A4),
        leftMargin=24,
        rightMargin=24,
        topMargin=24,
        bottomMargin=24,
    )

    story = []

    story.append(
        create_sector_header(sector_name)
    )
    story.append(Spacer(1, 0.18 * inch))

    story.append(
        create_summary_cards(sector_df)
    )
    story.append(Spacer(1, 0.20 * inch))

    story.append(
        Paragraph(
            "<b>Companies and Key Metrics</b>",
            SECTION_STYLE,
        )
    )

    story.append(
        create_company_table(sector_df)
    )

    doc.build(story)

    print(f"Created: {pdf_path}")

    return pdf_path


def generate_all_sector_reports() -> None:
    print("Loading sector-report data...")

    datasets = load_sector_data()
    metrics_df = build_company_metrics(
        datasets
    )

    sector_names = (
        metrics_df["sector"]
        .dropna()
        .astype(str)
        .str.strip()
        .replace("", np.nan)
        .dropna()
        .unique()
        .tolist()
    )

    sector_names = sorted(sector_names)

    generated = 0
    failed = []

    print(
        f"Generating {len(sector_names)} sector reports..."
    )

    for sector_name in sector_names:
        try:
            generate_sector_report(
                sector_name,
                metrics_df,
            )
            generated += 1

        except Exception as error:
            failed.append(
                {
                    "sector": sector_name,
                    "reason": str(error),
                }
            )

            print(
                f"Skipped {sector_name}: {error}"
            )

    failures_file = (
        OUTPUT_DIR / "sector_report_failures.csv"
    )

    pd.DataFrame(
        failed,
        columns=["sector", "reason"],
    ).to_csv(
        failures_file,
        index=False,
    )

    print("\nSector report generation completed.")
    print(f"Generated: {generated}")
    print(f"Failed: {len(failed)}")
    print(f"Failure log: {failures_file}")


if __name__ == "__main__":
    generate_all_sector_reports()