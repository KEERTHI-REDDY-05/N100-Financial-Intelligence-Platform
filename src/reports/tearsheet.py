import re
import numpy as np
import matplotlib.pyplot as plt

from reportlab.platypus import Image
from pathlib import Path
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "tearsheets"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CHART_DIR = PROJECT_ROOT / "output" / "temp_charts"
CHART_DIR.mkdir(parents=True, exist_ok=True)
COMPANIES_FILE = DATA_DIR / "companies.xlsx"
PROFIT_LOSS_FILE = DATA_DIR / "profitandloss.xlsx"
BALANCE_SHEET_FILE = DATA_DIR / "balancesheet.xlsx"
RATIOS_FILE = DATA_DIR / "financial_ratios.xlsx"
CASHFLOW_FILE = DATA_DIR / "cashflow.xlsx"

PROS_CONS_FILE = (
    PROJECT_ROOT
    / "output"
    / "pros_cons_generated.csv"
)

CASHFLOW_INTELLIGENCE_FILE = (
    PROJECT_ROOT
    / "output"
    / "cashflow_intelligence.xlsx"
)
styles = getSampleStyleSheet()

TITLE_STYLE = styles["Heading1"]
TITLE_STYLE.alignment = TA_CENTER
TITLE_STYLE.textColor = colors.white

SECTION_STYLE = styles["Heading2"]

BODY_STYLE = styles["BodyText"]
def clean_columns(dataframe):
    result = dataframe.copy()

    result.columns = [
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        for column in result.columns
    ]

    return result


def normalize_company_id(value):
    if pd.isna(value):
        return ""

    return str(value).strip().upper()


def extract_year(value):
    if pd.isna(value):
        return np.nan

    text = str(value).strip()

    four_digit = re.search(
        r"\b(?:19|20)\d{2}\b",
        text,
    )

    if four_digit:
        return int(four_digit.group())

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
            return 2000 + year

        return 1900 + year

    return np.nan


def load_excel_file(
    file_path,
    header=0,
):
    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    dataframe = pd.read_excel(
        file_path,
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


def load_tearsheet_data():
    companies = load_excel_file(
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

    profit_loss = load_excel_file(
        PROFIT_LOSS_FILE,
        header=1,
    )

    balance_sheet = load_excel_file(
        BALANCE_SHEET_FILE,
        header=1,
    )

    ratios = load_excel_file(
        RATIOS_FILE,
        header=0,
    )

    cashflow = load_excel_file(
        CASHFLOW_FILE,
        header=1,
    )

    pros_cons = pd.read_csv(
        PROS_CONS_FILE
    )

    pros_cons = clean_columns(pros_cons)

    pros_cons["company_id"] = pros_cons[
        "company_id"
    ].apply(normalize_company_id)

    cashflow_intelligence = pd.read_excel(
        CASHFLOW_INTELLIGENCE_FILE
    )

    cashflow_intelligence = clean_columns(
        cashflow_intelligence
    )

    cashflow_intelligence[
        "company_id"
    ] = cashflow_intelligence[
        "company_id"
    ].apply(normalize_company_id)

    return {
        "companies": companies,
        "profit_loss": profit_loss,
        "balance_sheet": balance_sheet,
        "ratios": ratios,
        "cashflow": cashflow,
        "pros_cons": pros_cons,
        "cashflow_intelligence": (
            cashflow_intelligence
        ),
    }


def get_company_rows(
    dataframe,
    company_id,
):
    if "company_id" not in dataframe.columns:
        return pd.DataFrame()

    result = dataframe[
        dataframe["company_id"] == company_id
    ].copy()

    if "year_number" in result.columns:
        result = result.sort_values(
            "year_number"
        )

    return result


def latest_numeric_value(
    dataframe,
    column,
):
    if (
        dataframe.empty
        or column not in dataframe.columns
    ):
        return np.nan

    values = pd.to_numeric(
        dataframe[column],
        errors="coerce",
    ).dropna()

    if values.empty:
        return np.nan

    return float(values.iloc[-1])


def format_number(
    value,
    decimals=1,
    suffix="",
):
    if pd.isna(value):
        return "N/A"

    return f"{value:.{decimals}f}{suffix}"


def calculate_cagr(
    values,
    years=5,
):
    numeric_values = pd.to_numeric(
        pd.Series(values),
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
def get_company_report_data(
    ticker,
    datasets,
):
    company_id = normalize_company_id(
        ticker
    )

    companies = datasets["companies"]

    company_match = companies[
        companies["company_id"]
        == company_id
    ]

    if company_match.empty:
        raise ValueError(
            f"Company not found: {company_id}"
        )

    company_row = company_match.iloc[0]

    company_name = str(
        company_row.get(
            "company_name",
            company_id,
        )
    )

    profit_loss = get_company_rows(
        datasets["profit_loss"],
        company_id,
    )

    balance_sheet = get_company_rows(
        datasets["balance_sheet"],
        company_id,
    )

    ratios = get_company_rows(
        datasets["ratios"],
        company_id,
    )

    cashflow = get_company_rows(
        datasets["cashflow"],
        company_id,
    )

    pros_cons = datasets["pros_cons"]

    company_pros = pros_cons[
        (pros_cons["company_id"] == company_id)
        & (pros_cons["type"] == "pro")
    ].sort_values(
        "confidence_pct",
        ascending=False,
    )

    company_cons = pros_cons[
        (pros_cons["company_id"] == company_id)
        & (pros_cons["type"] == "con")
    ].sort_values(
        "confidence_pct",
        ascending=False,
    )

    intelligence = datasets[
        "cashflow_intelligence"
    ]

    intelligence_match = intelligence[
        intelligence["company_id"]
        == company_id
    ]

    if intelligence_match.empty:
        allocation_label = (
            "Insufficient Data"
        )

        fcf_conversion = np.nan

    else:
        intelligence_row = (
            intelligence_match.iloc[0]
        )

        allocation_label = str(
            intelligence_row.get(
                "capital_allocation_label",
                "Insufficient Data",
            )
        )

        fcf_conversion = pd.to_numeric(
            intelligence_row.get(
                "fcf_conversion_pct",
                np.nan,
            ),
            errors="coerce",
        )

    revenue_cagr = calculate_cagr(
        profit_loss.get(
            "sales",
            pd.Series(dtype=float),
        ),
        years=5,
    )

    pat_cagr = calculate_cagr(
        profit_loss.get(
            "net_profit",
            pd.Series(dtype=float),
        ),
        years=5,
    )

    latest_roe = latest_numeric_value(
        ratios,
        "return_on_equity_pct",
    )

    latest_roce = pd.to_numeric(
        company_row.get(
            "roce_percentage",
            np.nan,
        ),
        errors="coerce",
    )

    latest_debt_equity = (
        latest_numeric_value(
            ratios,
            "debt_to_equity",
        )
    )

    pros = (
        company_pros["text"]
        .head(3)
        .astype(str)
        .tolist()
    )

    cons = (
        company_cons["text"]
        .head(3)
        .astype(str)
        .tolist()
    )

    return {
        "company_id": company_id,
        "company_name": company_name,
        "profit_loss": profit_loss,
        "balance_sheet": balance_sheet,
        "ratios": ratios,
        "cashflow": cashflow,
        "pros": pros,
        "cons": cons,
        "capital_allocation_label": (
            allocation_label
        ),
        "kpis": {
            "Revenue CAGR": format_number(
                revenue_cagr,
                suffix="%",
            ),
            "PAT CAGR": format_number(
                pat_cagr,
                suffix="%",
            ),
            "ROE": format_number(
                latest_roe,
                suffix="%",
            ),
            "ROCE": format_number(
                latest_roce,
                suffix="%",
            ),
            "Debt/Equity": format_number(
                latest_debt_equity,
                decimals=2,
            ),
            "FCF Conversion": format_number(
                fcf_conversion,
                suffix="%",
            ),
        },
    }
def clean_columns(dataframe):
    result = dataframe.copy()

    result.columns = [
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        for column in result.columns
    ]

    return result


def normalize_company_id(value):
    if pd.isna(value):
        return ""

    return str(value).strip().upper()


def extract_year(value):
    if pd.isna(value):
        return np.nan

    text = str(value).strip()

    four_digit = re.search(
        r"\b(?:19|20)\d{2}\b",
        text,
    )

    if four_digit:
        return int(four_digit.group())

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
            return 2000 + year

        return 1900 + year

    return np.nan


def load_excel_file(
    file_path,
    header=0,
):
    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    dataframe = pd.read_excel(
        file_path,
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


def load_tearsheet_data():
    companies = load_excel_file(
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

    profit_loss = load_excel_file(
        PROFIT_LOSS_FILE,
        header=1,
    )

    balance_sheet = load_excel_file(
        BALANCE_SHEET_FILE,
        header=1,
    )

    ratios = load_excel_file(
        RATIOS_FILE,
        header=0,
    )

    cashflow = load_excel_file(
        CASHFLOW_FILE,
        header=1,
    )

    pros_cons = pd.read_csv(
        PROS_CONS_FILE
    )

    pros_cons = clean_columns(pros_cons)

    pros_cons["company_id"] = pros_cons[
        "company_id"
    ].apply(normalize_company_id)

    cashflow_intelligence = pd.read_excel(
        CASHFLOW_INTELLIGENCE_FILE
    )

    cashflow_intelligence = clean_columns(
        cashflow_intelligence
    )

    cashflow_intelligence[
        "company_id"
    ] = cashflow_intelligence[
        "company_id"
    ].apply(normalize_company_id)

    return {
        "companies": companies,
        "profit_loss": profit_loss,
        "balance_sheet": balance_sheet,
        "ratios": ratios,
        "cashflow": cashflow,
        "pros_cons": pros_cons,
        "cashflow_intelligence": (
            cashflow_intelligence
        ),
    }


def get_company_rows(
    dataframe,
    company_id,
):
    if "company_id" not in dataframe.columns:
        return pd.DataFrame()

    result = dataframe[
        dataframe["company_id"] == company_id
    ].copy()

    if "year_number" in result.columns:
        result = result.sort_values(
            "year_number"
        )

    return result


def latest_numeric_value(
    dataframe,
    column,
):
    if (
        dataframe.empty
        or column not in dataframe.columns
    ):
        return np.nan

    values = pd.to_numeric(
        dataframe[column],
        errors="coerce",
    ).dropna()

    if values.empty:
        return np.nan

    return float(values.iloc[-1])


def format_number(
    value,
    decimals=1,
    suffix="",
):
    if pd.isna(value):
        return "N/A"

    return f"{value:.{decimals}f}{suffix}"


def calculate_cagr(
    values,
    years=5,
):
    numeric_values = pd.to_numeric(
        pd.Series(values),
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
def create_header(company_name, ticker):
    title = Paragraph(
        f"<b>{company_name} ({ticker})</b>",
        TITLE_STYLE,
    )

    table = Table([[title]], colWidths=[7.2 * inch])

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.darkblue),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )

    return table


def create_kpi_cards(kpis):
    rows = []

    row = []

    for title, value in kpis.items():
        cell = Paragraph(
            f"<b>{title}</b><br/><font size=14>{value}</font>",
            BODY_STYLE,
        )

        row.append(cell)

        if len(row) == 3:
            rows.append(row)
            row = []

    if row:
        while len(row) < 3:
            row.append("")
        rows.append(row)

    table = Table(rows, colWidths=[2.2 * inch] * 3)

    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    return table
def create_revenue_profit_chart(
    profit_loss,
    ticker,
):
    chart_path = (
        CHART_DIR
        / f"{ticker}_revenue_profit.png"
    )

    data = profit_loss.copy()

    required_columns = [
        "year_number",
        "sales",
        "net_profit",
    ]

    missing = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing:
        raise ValueError(
            f"Missing profit-and-loss columns: {missing}"
        )

    data = data.dropna(
        subset=["year_number"]
    ).sort_values(
        "year_number"
    ).tail(10)

    years = (
        data["year_number"]
        .astype(int)
        .astype(str)
        .tolist()
    )

    revenue = pd.to_numeric(
        data["sales"],
        errors="coerce",
    ).fillna(0).tolist()

    net_profit = pd.to_numeric(
        data["net_profit"],
        errors="coerce",
    ).fillna(0).tolist()

    positions = np.arange(len(years))
    width = 0.38

    fig, axis = plt.subplots(
        figsize=(8, 3.2)
    )

    axis.bar(
        positions - width / 2,
        revenue,
        width=width,
        label="Revenue",
    )

    axis.bar(
        positions + width / 2,
        net_profit,
        width=width,
        label="Net Profit",
    )

    axis.set_title(
        "10-Year Revenue and Net Profit"
    )
    axis.set_xlabel("Financial Year")
    axis.set_ylabel("Amount")
    axis.set_xticks(positions)
    axis.set_xticklabels(
        years,
        rotation=45,
    )
    axis.legend()
    axis.grid(
        axis="y",
        alpha=0.25,
    )

    fig.tight_layout()

    fig.savefig(
        chart_path,
        dpi=160,
        bbox_inches="tight",
    )

    plt.close(fig)

    return chart_path


def create_roe_roce_chart(
    ratios,
    ticker,
):
    chart_path = (
        CHART_DIR
        / f"{ticker}_roe_roce.png"
    )

    data = ratios.copy()

    if "year_number" not in data.columns:
        raise ValueError(
            "Ratios data is missing year_number."
        )

    data = data.dropna(
        subset=["year_number"]
    ).sort_values(
        "year_number"
    ).tail(10)

    years = (
        data["year_number"]
        .astype(int)
        .astype(str)
        .tolist()
    )

    roe = pd.to_numeric(
        data.get(
            "return_on_equity_pct",
            pd.Series(
                [np.nan] * len(data),
                index=data.index,
            ),
        ),
        errors="coerce",
    )

    fig, axis = plt.subplots(
        figsize=(8, 3.2)
    )

    if roe.notna().any():
        axis.plot(
            years,
            roe,
            marker="o",
            label="ROE",
        )

    axis.set_title("ROE Trend")
    axis.set_xlabel("Financial Year")
    axis.set_ylabel("Percentage")
    axis.tick_params(
        axis="x",
        rotation=45,
    )
    axis.grid(alpha=0.25)

    if axis.lines:
        axis.legend()

    fig.tight_layout()

    fig.savefig(
        chart_path,
        dpi=160,
        bbox_inches="tight",
    )

    plt.close(fig)

    return chart_path


def create_balance_sheet_chart(
    balance_sheet,
    ticker,
):
    chart_path = (
        CHART_DIR
        / f"{ticker}_balance_sheet.png"
    )

    data = balance_sheet.copy()

    required_columns = [
        "year_number",
        "equity_capital",
        "reserves",
        "borrowings",
        "total_liabilities",
    ]

    missing = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing:
        raise ValueError(
            f"Missing balance-sheet columns: {missing}"
        )

    data = data.dropna(
        subset=["year_number"]
    ).sort_values(
        "year_number"
    ).tail(10)

    years = (
        data["year_number"]
        .astype(int)
        .astype(str)
        .tolist()
    )

    equity_capital = pd.to_numeric(
        data["equity_capital"],
        errors="coerce",
    ).fillna(0)

    reserves = pd.to_numeric(
        data["reserves"],
        errors="coerce",
    ).fillna(0)

    equity = (
        equity_capital
        + reserves
    ).tolist()

    borrowings = pd.to_numeric(
        data["borrowings"],
        errors="coerce",
    ).fillna(0).tolist()

    total_liabilities = pd.to_numeric(
        data["total_liabilities"],
        errors="coerce",
    ).fillna(0)

    other_liabilities = (
        total_liabilities
        - pd.Series(
            equity,
            index=data.index,
        )
        - pd.Series(
            borrowings,
            index=data.index,
        )
    ).clip(lower=0).tolist()

    fig, axis = plt.subplots(
        figsize=(8, 3.3)
    )

    axis.bar(
        years,
        equity,
        label="Equity",
    )

    axis.bar(
        years,
        borrowings,
        bottom=equity,
        label="Borrowings",
    )

    equity_and_borrowings = [
        equity[index] + borrowings[index]
        for index in range(len(years))
    ]

    axis.bar(
        years,
        other_liabilities,
        bottom=equity_and_borrowings,
        label="Other Liabilities",
    )

    axis.set_title(
        "Balance Sheet Composition"
    )
    axis.set_xlabel("Financial Year")
    axis.set_ylabel("Amount")
    axis.tick_params(
        axis="x",
        rotation=45,
    )
    axis.legend()
    axis.grid(
        axis="y",
        alpha=0.25,
    )

    fig.tight_layout()

    fig.savefig(
        chart_path,
        dpi=160,
        bbox_inches="tight",
    )

    plt.close(fig)

    return chart_path


def create_cashflow_chart(
    cashflow,
    ticker,
):
    chart_path = (
        CHART_DIR
        / f"{ticker}_cashflow.png"
    )

    if cashflow.empty:
        raise ValueError(
            f"No cash-flow data found for {ticker}"
        )

    latest = cashflow.sort_values(
        "year_number"
    ).iloc[-1]

    labels = [
        "CFO",
        "CFI",
        "CFF",
        "Net Cash Flow",
    ]

    values = [
        pd.to_numeric(
            latest.get(
                "operating_activity",
                np.nan,
            ),
            errors="coerce",
        ),
        pd.to_numeric(
            latest.get(
                "investing_activity",
                np.nan,
            ),
            errors="coerce",
        ),
        pd.to_numeric(
            latest.get(
                "financing_activity",
                np.nan,
            ),
            errors="coerce",
        ),
        pd.to_numeric(
            latest.get(
                "net_cash_flow",
                np.nan,
            ),
            errors="coerce",
        ),
    ]

    values = [
        0 if pd.isna(value) else float(value)
        for value in values
    ]

    latest_year = int(
        latest["year_number"]
    )

    fig, axis = plt.subplots(
        figsize=(8, 3)
    )

    axis.bar(labels, values)

    axis.set_title(
        f"Cash Flow Waterfall — {latest_year}"
    )
    axis.set_ylabel("Amount")
    axis.axhline(
        y=0,
        linewidth=0.8,
    )
    axis.grid(
        axis="y",
        alpha=0.25,
    )

    fig.tight_layout()

    fig.savefig(
        chart_path,
        dpi=160,
        bbox_inches="tight",
    )

    plt.close(fig)

    return chart_path

def create_capital_badge(text):
    badge_text = Paragraph(
        f"<b>Capital Allocation: {text}</b>",
        BODY_STYLE,
    )

    badge = Table(
        [[badge_text]],
        colWidths=[3.5 * inch],
    )

    badge.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.lightblue,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    colors.darkblue,
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
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    return badge
def create_bullet_section(title, items):
    section = []

    section.append(
        Paragraph(
            f"<b>{title}</b>",
            SECTION_STYLE,
        )
    )

    if not items:
        section.append(
            Paragraph(
                "No significant items available.",
                BODY_STYLE,
            )
        )
        return section

    for item in items:
        section.append(
            Paragraph(
                f"&#8226; {item}",
                BODY_STYLE,
            )
        )

        section.append(
            Spacer(1, 0.04 * inch)
        )

    return section
def create_company_tearsheet(ticker="TCS"):
    datasets = load_tearsheet_data()

    report_data = get_company_report_data(
        ticker,
        datasets,
    )

    company_id = report_data["company_id"]
    company_name = report_data["company_name"]

    pdf_path = (
        OUTPUT_DIR
        / f"{company_id}_tearsheet.pdf"
    )

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=24,
        rightMargin=24,
        topMargin=24,
        bottomMargin=24,
    )

    story = []

    # ---------------- Page 1 ----------------

    story.append(
        create_header(
            company_name,
            company_id,
        )
    )

    story.append(
        Spacer(1, 0.20 * inch)
    )

    story.append(
        create_kpi_cards(
            report_data["kpis"]
        )
    )

    story.append(
        Spacer(1, 0.18 * inch)
    )

    revenue_chart_path = (
        create_revenue_profit_chart(
            report_data["profit_loss"],
            company_id,
        )
    )

    story.append(
        Image(
            str(revenue_chart_path),
            width=7.0 * inch,
            height=2.60 * inch,
        )
    )

    story.append(
        Spacer(1, 0.08 * inch)
    )

    roe_roce_chart_path = (
        create_roe_roce_chart(
            report_data["ratios"],
            company_id,
        )
    )

    story.append(
        Image(
            str(roe_roce_chart_path),
            width=7.0 * inch,
            height=2.55 * inch,
        )
    )

    # ---------------- Page 2 ----------------

    story.append(PageBreak())

    balance_chart_path = (
        create_balance_sheet_chart(
            report_data["balance_sheet"],
            company_id,
        )
    )

    story.append(
        Image(
            str(balance_chart_path),
            width=7.0 * inch,
            height=2.50 * inch,
        )
    )

    story.append(
        Spacer(1, 0.10 * inch)
    )

    cashflow_chart_path = (
        create_cashflow_chart(
            report_data["cashflow"],
            company_id,
        )
    )

    story.append(
        Image(
            str(cashflow_chart_path),
            width=7.0 * inch,
            height=2.25 * inch,
        )
    )

    story.append(
        Spacer(1, 0.10 * inch)
    )

    story.append(
        create_capital_badge(
            report_data[
                "capital_allocation_label"
            ]
        )
    )

    story.append(
        Spacer(1, 0.14 * inch)
    )

    story.extend(
        create_bullet_section(
            "Pros",
            report_data["pros"],
        )
    )

    story.append(
        Spacer(1, 0.10 * inch)
    )

    story.extend(
        create_bullet_section(
            "Cons",
            report_data["cons"],
        )
    )

    doc.build(story)

    print(f"Created: {pdf_path}")

    return pdf_path
def generate_all_tearsheets():
    datasets = load_tearsheet_data()

    companies = datasets["companies"]

    skipped = []

    generated = 0

    company_ids = (
        companies["company_id"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .unique()
    )

    print(f"\nGenerating {len(company_ids)} company tearsheets...\n")

    for company_id in company_ids:

        try:

            create_company_tearsheet(company_id)

            generated += 1

            print(f"✓ {company_id}")

        except Exception as error:

            skipped.append(
                {
                    "company_id": company_id,
                    "reason": str(error),
                }
            )

            print(f"✗ {company_id}")

    skipped_df = pd.DataFrame(skipped)

    skipped_file = (
        PROJECT_ROOT
        / "output"
        / "skipped_tearsheets.csv"
    )

    skipped_df.to_csv(
        skipped_file,
        index=False,
    )

    print("\n--------------------------------")

    print(f"Generated : {generated}")

    print(f"Skipped   : {len(skipped)}")

    print(f"Skipped log: {skipped_file}")

    print("--------------------------------")
if __name__ == "__main__":
    generate_all_tearsheets()