from __future__ import annotations

import pandas as pd


VALUATION_COLUMNS = [
    "year",
    "market_cap_crore",
    "enterprise_value_crore",
    "pe_ratio",
    "pb_ratio",
    "ev_ebitda",
    "dividend_yield_pct",
]


def prepare_valuation_data(
    valuation_data: pd.DataFrame,
) -> pd.DataFrame:
    """
    Clean and arrange historical valuation data.

    The returned records are sorted from oldest to newest year.
    """

    if valuation_data is None or valuation_data.empty:
        return pd.DataFrame(columns=VALUATION_COLUMNS)

    data = valuation_data.copy()

    if "year" not in data.columns:
        raise KeyError(
            "Expected column 'year' was not found in valuation data."
        )

    data["year"] = pd.to_numeric(
        data["year"],
        errors="coerce",
    )

    numeric_columns = [
        "market_cap_crore",
        "enterprise_value_crore",
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "dividend_yield_pct",
    ]

    for column in numeric_columns:
        if column in data.columns:
            data[column] = pd.to_numeric(
                data[column],
                errors="coerce",
            )

    data = (
        data.dropna(subset=["year"])
        .sort_values("year")
        .reset_index(drop=True)
    )

    data["year"] = data["year"].astype(int)

    return data


def get_latest_valuation(
    valuation_data: pd.DataFrame,
) -> pd.Series | None:
    """
    Return the latest valuation record.

    Returns None when no valid valuation record is available.
    """

    data = prepare_valuation_data(valuation_data)

    if data.empty:
        return None

    return data.iloc[-1]


def calculate_historical_averages(
    valuation_data: pd.DataFrame,
) -> dict[str, float | None]:
    """
    Calculate historical averages for important valuation ratios.
    """

    data = prepare_valuation_data(valuation_data)

    ratio_columns = [
        "pe_ratio",
        "pb_ratio",
        "ev_ebitda",
        "dividend_yield_pct",
    ]

    averages: dict[str, float | None] = {}

    for column in ratio_columns:
        if column not in data.columns:
            averages[column] = None
            continue

        average = data[column].mean()

        averages[column] = (
            round(float(average), 2)
            if pd.notna(average)
            else None
        )

    return averages


def calculate_growth_rate(
    current_value: float | int | None,
    previous_value: float | int | None,
) -> float | None:
    """
    Calculate percentage growth between two values.
    """

    if current_value is None or previous_value is None:
        return None

    if pd.isna(current_value) or pd.isna(previous_value):
        return None

    previous_value = float(previous_value)
    current_value = float(current_value)

    if previous_value == 0:
        return None

    growth_rate = (
        (current_value - previous_value)
        / abs(previous_value)
        * 100
    )

    return round(growth_rate, 2)


def calculate_market_cap_growth(
    valuation_data: pd.DataFrame,
) -> float | None:
    """
    Calculate growth in market capitalisation between
    the latest two available years.
    """

    data = prepare_valuation_data(valuation_data)

    if (
        data.empty
        or "market_cap_crore" not in data.columns
    ):
        return None

    valid_data = data.dropna(
        subset=["market_cap_crore"]
    )

    if len(valid_data) < 2:
        return None

    previous_value = valid_data.iloc[-2][
        "market_cap_crore"
    ]

    current_value = valid_data.iloc[-1][
        "market_cap_crore"
    ]

    return calculate_growth_rate(
        current_value,
        previous_value,
    )


def compare_with_history(
    current_value: float | int | None,
    historical_average: float | int | None,
    lower_is_better: bool = True,
    tolerance_pct: float = 10.0,
) -> str:
    """
    Compare a current metric with its historical average.

    Possible outputs:
    - Undervalued
    - Fairly Valued
    - Overvalued
    - Attractive
    - Neutral
    - Unattractive
    - Insufficient Data
    """

    if (
        current_value is None
        or historical_average is None
        or pd.isna(current_value)
        or pd.isna(historical_average)
    ):
        return "Insufficient Data"

    current_value = float(current_value)
    historical_average = float(historical_average)

    if historical_average == 0:
        return "Insufficient Data"

    difference_pct = (
        (current_value - historical_average)
        / abs(historical_average)
        * 100
    )

    if abs(difference_pct) <= tolerance_pct:
        return (
            "Fairly Valued"
            if lower_is_better
            else "Neutral"
        )

    if lower_is_better:
        return (
            "Undervalued"
            if difference_pct < 0
            else "Overvalued"
        )

    return (
        "Attractive"
        if difference_pct > 0
        else "Unattractive"
    )


def get_valuation_signals(
    valuation_data: pd.DataFrame,
) -> dict[str, str]:
    """
    Compare the latest valuation ratios with their historical averages.
    """

    latest = get_latest_valuation(valuation_data)
    averages = calculate_historical_averages(
        valuation_data
    )

    if latest is None:
        return {
            "pe_signal": "Insufficient Data",
            "pb_signal": "Insufficient Data",
            "ev_ebitda_signal": "Insufficient Data",
            "dividend_yield_signal": "Insufficient Data",
        }

    return {
        "pe_signal": compare_with_history(
            latest.get("pe_ratio"),
            averages.get("pe_ratio"),
            lower_is_better=True,
        ),
        "pb_signal": compare_with_history(
            latest.get("pb_ratio"),
            averages.get("pb_ratio"),
            lower_is_better=True,
        ),
        "ev_ebitda_signal": compare_with_history(
            latest.get("ev_ebitda"),
            averages.get("ev_ebitda"),
            lower_is_better=True,
        ),
        "dividend_yield_signal": compare_with_history(
            latest.get("dividend_yield_pct"),
            averages.get("dividend_yield_pct"),
            lower_is_better=False,
        ),
    }


def calculate_valuation_score(
    valuation_data: pd.DataFrame,
) -> dict[str, int | str]:
    """
    Calculate a simple valuation score out of 100.

    Each of these contributes 25 points:

    - P/E signal
    - P/B signal
    - EV/EBITDA signal
    - Dividend-yield signal

    This is an educational relative-valuation score, not an
    investment recommendation.
    """

    signals = get_valuation_signals(
        valuation_data
    )

    score = 0

    favourable_signals = {
        "Undervalued",
        "Attractive",
    }

    neutral_signals = {
        "Fairly Valued",
        "Neutral",
    }

    for signal in signals.values():
        if signal in favourable_signals:
            score += 25

        elif signal in neutral_signals:
            score += 15

    if score >= 75:
        category = "Attractive Relative Valuation"

    elif score >= 50:
        category = "Reasonable Relative Valuation"

    elif score >= 25:
        category = "Expensive Relative Valuation"

    else:
        category = "Insufficient or Unfavourable Valuation"

    return {
        "score": score,
        "category": category,
    }


def build_valuation_summary(
    valuation_data: pd.DataFrame,
) -> dict:
    """
    Build a complete valuation summary for dashboard use.
    """

    latest = get_latest_valuation(
        valuation_data
    )

    averages = calculate_historical_averages(
        valuation_data
    )

    signals = get_valuation_signals(
        valuation_data
    )

    score_details = calculate_valuation_score(
        valuation_data
    )

    latest_values = {
        "year": None,
        "market_cap_crore": None,
        "enterprise_value_crore": None,
        "pe_ratio": None,
        "pb_ratio": None,
        "ev_ebitda": None,
        "dividend_yield_pct": None,
    }

    if latest is not None:
        for key in latest_values:
            latest_values[key] = latest.get(key)

    return {
        "latest": latest_values,
        "historical_averages": averages,
        "signals": signals,
        "market_cap_growth_pct": (
            calculate_market_cap_growth(
                valuation_data
            )
        ),
        "valuation_score": score_details["score"],
        "valuation_category": score_details["category"],
    }