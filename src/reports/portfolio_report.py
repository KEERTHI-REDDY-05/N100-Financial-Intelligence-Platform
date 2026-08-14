from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from reportlab.graphics.shapes import Drawing, Line, Polygon
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
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
PORTFOLIO_DIR = PROJECT_ROOT / "reports" / "portfolio"

COMPANIES_FILE = DATA_DIR / "companies.xlsx"
SECTORS_FILE = DATA_DIR / "sectors.xlsx"
PROFIT_LOSS_FILE = DATA_DIR / "profitandloss.xlsx"
RATIOS_FILE = DATA_DIR / "financial_ratios.xlsx"
CASHFLOW_FILE = DATA_DIR / "cashflow.xlsx"
CASHFLOW_INTELLIGENCE_FILE = (
    OUTPUT_DIR / "cashflow_intelligence.xlsx"
)

PORTFOLIO_PDF = (
    PORTFOLIO_DIR / "portfolio_summary.pdf"
)

PORTFOLIO_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# PDF styles
# ============================================================

STYLES = getSampleStyleSheet()

TITLE_STYLE = ParagraphStyle(
    "PortfolioTitle",
    parent=STYLES["Heading1"],
    alignment=TA_CENTER,
    textColor=colors.white,
    fontSize=17,
    leading=21,
)

SUBTITLE_STYLE = ParagraphStyle(
    "PortfolioSubtitle",
    parent=STYLES["BodyText"],
    alignment=TA_CENTER,
    textColor=colors.white,
    fontSize=9,
    leading=12,
)

SECTION_STYLE = ParagraphStyle(
    "PortfolioSection",
    parent=STYLES["Heading2"],
    alignment=TA_LEFT,
    fontSize=13,
    leading=16,
    spaceAfter=8,
)

BODY_STYLE = ParagraphStyle(
    "PortfolioBody",
    parent=STYLES["BodyText"],
    fontSize=9,
    leading=12,
)

SMALL_STYLE = ParagraphStyle(
    "PortfolioSmall",
    parent=STYLES["BodyText"],
    fontSize=8,
    leading=10,
)

KPI_TITLE_STYLE = ParagraphStyle(
    "KpiTitle",
    parent=STYLES["BodyText"],
    alignment=TA_CENTER,
    fontSize=8,
    leading=10,
)

KPI_VALUE_STYLE = ParagraphStyle(
    "KpiValue",
    parent=STYLES["BodyText"],
    alignment=TA_CENTER,
    fontSize=14,
    leading=17,
)


# ============================================================
# General helpers
# ============================================================

def clean_columns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    result = dataframe.copy()

    result.columns = [
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
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

    four_digit = re.search(
        r"\b(?:19|20)\d{2}\b",
        text,
    )

    if four_digit:
        return float(four_digit.group())

    two_digit = re.search(
        (
            r"(?:Jan|Feb|Mar|Apr|May|Jun|"
            r"Jul|Aug|Sep|Oct|Nov|Dec)"
            r"[\s\-]*(\d{2})"
        ),
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
        raise FileNotFoundError(
            f"Required file not found: {path}"
        )

    dataframe = pd.read_excel(
        path,
        header=header,
    )

    dataframe = clean_columns(dataframe)

    if "company_id" in dataframe.columns:
        dataframe["company_id"] = dataframe[
            "company_id"
        ].apply(normalize_company_id)

    if "year" in dataframe.columns:
        dataframe["year_number"] = dataframe[
            "year"
        ].apply(extract_year)

    return dataframe


def safe_numeric(value: Any) -> float:
    result = pd.to_numeric(
        value,
        errors="coerce",
    )

    if pd.isna(result):
        return np.nan

    return float(result)


def format_value(
    value: Any,
    decimals: int = 1,
    suffix: str = "",
) -> str:
    numeric = safe_numeric(value)

    if pd.isna(numeric):
        return "N/A"

    return f"{numeric:.{decimals}f}{suffix}"


def get_company_rows(
    dataframe: pd.DataFrame,
    company_id: str,
) -> pd.DataFrame:
    if (
        dataframe.empty
        or "company_id" not in dataframe.columns
    ):
        return pd.DataFrame()

    result = dataframe[
        dataframe["company_id"] == company_id
    ].copy()

    if "year_number" in result.columns:
        result = result.sort_values(
            "year_number"
        )

    return result


def latest_previous_values(
    dataframe: pd.DataFrame,
    column: str,
) -> tuple[float, float]:
    if (
        dataframe.empty
        or column not in dataframe.columns
    ):
        return np.nan, np.nan

    data = dataframe.copy()

    if "year_number" in data.columns:
        data = data.sort_values(
            "year_number"
        )

    values = pd.to_numeric(
        data[column],
        errors="coerce",
    ).dropna()

    if values.empty:
        return np.nan, np.nan

    latest = float(values.iloc[-1])

    if len(values) < 2:
        return latest, np.nan

    previous = float(values.iloc[-2])

    return latest, previous


# ============================================================
# Trend calculations
# ============================================================

def calculate_change_pct(
    latest: float,
    previous: float,
) -> float:
    if (
        pd.isna(latest)
        or pd.isna(previous)
        or previous == 0
    ):
        return np.nan

    return (
        (latest - previous)
        / abs(previous)
        * 100
    )


def determine_trend(
    latest: float,
    previous: float,
    lower_is_better: bool = False,
) -> str:
    """
    Return:
        up
        down
        flat
        unknown

    A movement within 2% is treated as flat.
    """
    change_pct = calculate_change_pct(
        latest,
        previous,
    )

    if pd.isna(change_pct):
        return "unknown"

    if abs(change_pct) <= 2:
        return "flat"

    if lower_is_better:
        return (
            "up"
            if change_pct < 0
            else "down"
        )

    return (
        "up"
        if change_pct > 0
        else "down"
    )


def create_trend_arrow(
    trend: str,
) -> Drawing:
    """
    Draw arrows without depending on Unicode fonts.
    """
    drawing = Drawing(
        26,
        22,
    )

    if trend == "up":
        drawing.add(
            Line(
                13,
                4,
                13,
                16,
                strokeColor=colors.green,
                strokeWidth=2,
            )
        )

        drawing.add(
            Polygon(
                [
                    7, 13,
                    13, 20,
                    19, 13,
                ],
                fillColor=colors.green,
                strokeColor=colors.green,
            )
        )

    elif trend == "down":
        drawing.add(
            Line(
                13,
                18,
                13,
                6,
                strokeColor=colors.red,
                strokeWidth=2,
            )
        )

        drawing.add(
            Polygon(
                [
                    7, 9,
                    13, 2,
                    19, 9,
                ],
                fillColor=colors.red,
                strokeColor=colors.red,
            )
        )

    elif trend == "flat":
        drawing.add(
            Line(
                5,
                11,
                20,
                11,
                strokeColor=colors.darkorange,
                strokeWidth=2,
            )
        )

        drawing.add(
            Polygon(
                [
                    17, 6,
                    24, 11,
                    17, 16,
                ],
                fillColor=colors.darkorange,
                strokeColor=colors.darkorange,
            )
        )

    else:
        drawing.add(
            Line(
                6,
                11,
                20,
                11,
                strokeColor=colors.grey,
                strokeWidth=1,
            )
        )

    return drawing


# ============================================================
# Load project data
# ============================================================

def load_portfolio_data() -> dict[str, pd.DataFrame]:
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

    cashflow = load_excel(
        CASHFLOW_FILE,
        header=1,
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
        "cashflow": cashflow,
        "cashflow_intelligence": (
            cashflow_intelligence
        ),
    }


# ============================================================
# Build one-company portfolio record
# ============================================================

def build_company_record(
    company_id: str,
    datasets: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    companies = datasets["companies"]
    sectors = datasets["sectors"]

    company_match = companies[
        companies["company_id"] == company_id
    ]

    if company_match.empty:
        raise ValueError(
            f"Company not found: {company_id}"
        )

    company_row = company_match.iloc[0]

    sector_match = sectors[
        sectors["company_id"] == company_id
    ]

    company_name = str(
        company_row.get(
            "company_name",
            company_id,
        )
    )

    sector = "Unknown"

    if (
        not sector_match.empty
        and "broad_sector"
        in sector_match.columns
    ):
        sector = str(
            sector_match.iloc[0][
                "broad_sector"
            ]
        )

    profit_rows = get_company_rows(
        datasets["profit_loss"],
        company_id,
    )

    ratio_rows = get_company_rows(
        datasets["ratios"],
        company_id,
    )

    cashflow_rows = get_company_rows(
        datasets["cashflow"],
        company_id,
    )

    intelligence_match = datasets[
        "cashflow_intelligence"
    ][
        datasets[
            "cashflow_intelligence"
        ]["company_id"] == company_id
    ]

    revenue_latest, revenue_previous = (
        latest_previous_values(
            profit_rows,
            "sales",
        )
    )

    profit_latest, profit_previous = (
        latest_previous_values(
            profit_rows,
            "net_profit",
        )
    )

    roe_latest, roe_previous = (
        latest_previous_values(
            ratio_rows,
            "return_on_equity_pct",
        )
    )

    debt_latest, debt_previous = (
        latest_previous_values(
            ratio_rows,
            "debt_to_equity",
        )
    )

    fcf_latest, fcf_previous = (
        latest_previous_values(
            ratio_rows,
            "free_cash_flow_cr",
        )
    )

    cfo_latest, cfo_previous = (
        latest_previous_values(
            cashflow_rows,
            "operating_activity",
        )
    )

    allocation_label = "Insufficient Data"
    cfo_quality_label = "Insufficient Data"

    if not intelligence_match.empty:
        intelligence_row = (
            intelligence_match.iloc[0]
        )

        allocation_label = str(
            intelligence_row.get(
                "capital_allocation_label",
                "Insufficient Data",
            )
        )

        cfo_quality_label = str(
            intelligence_row.get(
                "cfo_quality_label",
                "Insufficient Data",
            )
        )

    return {
        "company_id": company_id,
        "company_name": company_name,
        "sector": sector,
        "capital_allocation_label": (
            allocation_label
        ),
        "cfo_quality_label": cfo_quality_label,
        "metrics": [
            {
                "name": "Revenue",
                "value": revenue_latest,
                "previous": revenue_previous,
                "formatted": format_value(
                    revenue_latest,
                    decimals=0,
                ),
                "trend": determine_trend(
                    revenue_latest,
                    revenue_previous,
                ),
            },
            {
                "name": "Net Profit",
                "value": profit_latest,
                "previous": profit_previous,
                "formatted": format_value(
                    profit_latest,
                    decimals=0,
                ),
                "trend": determine_trend(
                    profit_latest,
                    profit_previous,
                ),
            },
            {
                "name": "ROE",
                "value": roe_latest,
                "previous": roe_previous,
                "formatted": format_value(
                    roe_latest,
                    suffix="%",
                ),
                "trend": determine_trend(
                    roe_latest,
                    roe_previous,
                ),
            },
            {
                "name": "Debt/Equity",
                "value": debt_latest,
                "previous": debt_previous,
                "formatted": format_value(
                    debt_latest,
                    decimals=2,
                ),
                "trend": determine_trend(
                    debt_latest,
                    debt_previous,
                    lower_is_better=True,
                ),
            },
            {
                "name": "Free Cash Flow",
                "value": fcf_latest,
                "previous": fcf_previous,
                "formatted": format_value(
                    fcf_latest,
                    decimals=0,
                ),
                "trend": determine_trend(
                    fcf_latest,
                    fcf_previous,
                ),
            },
            {
                "name": "Operating Cash Flow",
                "value": cfo_latest,
                "previous": cfo_previous,
                "formatted": format_value(
                    cfo_latest,
                    decimals=0,
                ),
                "trend": determine_trend(
                    cfo_latest,
                    cfo_previous,
                ),
            },
        ],
    }


# ============================================================
# PDF elements
# ============================================================

def create_header(
    record: dict[str, Any],
) -> Table:
    title = Paragraph(
        (
            f"<b>{record['company_name']}</b>"
            f" ({record['company_id']})"
        ),
        TITLE_STYLE,
    )

    subtitle = Paragraph(
        (
            f"Sector: {record['sector']} | "
            f"Capital Allocation: "
            f"{record['capital_allocation_label']}"
        ),
        SUBTITLE_STYLE,
    )

    table = Table(
        [
            [title],
            [subtitle],
        ],
        colWidths=[7.15 * inch],
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
                    (-1, 0),
                    12,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, 0),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 1),
                    (-1, 1),
                    10,
                ),
            ]
        )
    )

    return table


def create_metric_card(
    metric: dict[str, Any],
) -> Table:
    title = Paragraph(
        f"<b>{metric['name']}</b>",
        KPI_TITLE_STYLE,
    )

    value = Paragraph(
        metric["formatted"],
        KPI_VALUE_STYLE,
    )

    arrow = create_trend_arrow(
        metric["trend"]
    )

    previous_text = format_value(
        metric["previous"],
        decimals=1,
    )

    change = calculate_change_pct(
        metric["value"],
        metric["previous"],
    )

    if pd.isna(change):
        change_text = "Previous: N/A"
    else:
        change_text = (
            f"Previous: {previous_text}"
            f"<br/>Change: {change:.1f}%"
        )

    details = Paragraph(
        change_text,
        SMALL_STYLE,
    )

    card = Table(
        [
            [title],
            [value],
            [arrow],
            [details],
        ],
        colWidths=[2.15 * inch],
        rowHeights=[
            0.28 * inch,
            0.38 * inch,
            0.30 * inch,
            0.40 * inch,
        ],
    )

    card.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.whitesmoke,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    colors.grey,
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
            ]
        )
    )

    return card


def create_metric_grid(
    record: dict[str, Any],
) -> Table:
    cards = [
        create_metric_card(metric)
        for metric in record["metrics"]
    ]

    grid = Table(
        [
            cards[0:3],
            cards[3:6],
        ],
        colWidths=[2.28 * inch] * 3,
        rowHeights=[1.55 * inch] * 2,
        hAlign="CENTER",
    )

    grid.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
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
            ]
        )
    )

    return grid


def create_summary_section(
    record: dict[str, Any],
) -> Table:
    rows = [
        [
            Paragraph(
                "<b>Company</b>",
                BODY_STYLE,
            ),
            Paragraph(
                record["company_name"],
                BODY_STYLE,
            ),
        ],
        [
            Paragraph(
                "<b>Ticker</b>",
                BODY_STYLE,
            ),
            Paragraph(
                record["company_id"],
                BODY_STYLE,
            ),
        ],
        [
            Paragraph(
                "<b>Sector</b>",
                BODY_STYLE,
            ),
            Paragraph(
                record["sector"],
                BODY_STYLE,
            ),
        ],
        [
            Paragraph(
                "<b>CFO Quality</b>",
                BODY_STYLE,
            ),
            Paragraph(
                record["cfo_quality_label"],
                BODY_STYLE,
            ),
        ],
        [
            Paragraph(
                "<b>Capital Allocation</b>",
                BODY_STYLE,
            ),
            Paragraph(
                record[
                    "capital_allocation_label"
                ],
                BODY_STYLE,
            ),
        ],
    ]

    table = Table(
        rows,
        colWidths=[
            1.7 * inch,
            5.1 * inch,
        ],
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
                    (0, -1),
                    colors.lightgrey,
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
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    return table


def create_legend() -> Table:
    legend_rows = [
        [
            create_trend_arrow("up"),
            Paragraph(
                "Improved by more than 2%",
                SMALL_STYLE,
            ),
            create_trend_arrow("down"),
            Paragraph(
                "Deteriorated by more than 2%",
                SMALL_STYLE,
            ),
        ],
        [
            create_trend_arrow("flat"),
            Paragraph(
                "Flat within ±2%",
                SMALL_STYLE,
            ),
            create_trend_arrow("unknown"),
            Paragraph(
                "Insufficient previous data",
                SMALL_STYLE,
            ),
        ],
    ]

    table = Table(
        legend_rows,
        colWidths=[
            0.45 * inch,
            2.5 * inch,
            0.45 * inch,
            2.7 * inch,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.grey,
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.25,
                    colors.lightgrey,
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
            ]
        )
    )

    return table


# ============================================================
# Generate portfolio PDF
# ============================================================

def generate_portfolio_summary() -> Path:
    print("Loading portfolio datasets...")

    datasets = load_portfolio_data()

    company_ids = (
        datasets["companies"]["company_id"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .unique()
        .tolist()
    )

    company_ids = sorted(company_ids)

    print(
        f"Preparing {len(company_ids)} company pages..."
    )

    doc = SimpleDocTemplate(
        str(PORTFOLIO_PDF),
        pagesize=A4,
        leftMargin=24,
        rightMargin=24,
        topMargin=24,
        bottomMargin=24,
    )

    story = []
    failures = []

    for index, company_id in enumerate(
        company_ids
    ):
        try:
            record = build_company_record(
                company_id,
                datasets,
            )

            story.append(
                create_header(record)
            )

            story.append(
                Spacer(1, 0.22 * inch)
            )

            story.append(
                Paragraph(
                    "<b>Top Six Financial KPIs</b>",
                    SECTION_STYLE,
                )
            )

            story.append(
                create_metric_grid(record)
            )

            story.append(
                Spacer(1, 0.20 * inch)
            )

            story.append(
                Paragraph(
                    "<b>Company Summary</b>",
                    SECTION_STYLE,
                )
            )

            story.append(
                create_summary_section(record)
            )

            story.append(
                Spacer(1, 0.22 * inch)
            )

            story.append(
                Paragraph(
                    "<b>Trend Legend</b>",
                    SECTION_STYLE,
                )
            )

            story.append(
                create_legend()
            )

            if index < len(company_ids) - 1:
                story.append(PageBreak())

            print(
                f"Prepared: {company_id}"
            )

        except Exception as error:
            failures.append(
                {
                    "company_id": company_id,
                    "reason": str(error),
                }
            )

            print(
                f"Skipped {company_id}: {error}"
            )

    if not story:
        raise ValueError(
            "No portfolio pages could be generated."
        )

    print("Building portfolio PDF...")

    doc.build(story)

    failure_file = (
        OUTPUT_DIR
        / "portfolio_report_failures.csv"
    )

    pd.DataFrame(
        failures,
        columns=[
            "company_id",
            "reason",
        ],
    ).to_csv(
        failure_file,
        index=False,
    )

    print("\nPortfolio summary completed.")
    print(f"Companies requested: {len(company_ids)}")
    print(
        f"Pages prepared: "
        f"{len(company_ids) - len(failures)}"
    )
    print(f"Failed: {len(failures)}")
    print(f"Created: {PORTFOLIO_PDF}")
    print(f"Failure log: {failure_file}")

    return PORTFOLIO_PDF


if __name__ == "__main__":
    generate_portfolio_summary()