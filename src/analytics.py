from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ChangeResult:
    latest_value: float
    previous_value: float
    latest_date: pd.Timestamp
    previous_date: pd.Timestamp
    absolute: float
    percentage: float


def percentage_change(current: float, previous: float) -> float:
    """Return a relative percentage change, e.g. 5.0 for a 5% increase."""

    if pd.isna(current) or pd.isna(previous) or previous == 0:
        return float("nan")
    return (float(current) / float(previous) - 1.0) * 100.0


def percentage_point_change(current: float, previous: float) -> float:
    """Return an absolute change between two rates already expressed in percent."""

    if pd.isna(current) or pd.isna(previous):
        return float("nan")
    return float(current) - float(previous)


def clean_observations(
    frame: pd.DataFrame,
    date_col: str,
    value_col: str,
    *,
    business_days_only: bool = False,
) -> pd.DataFrame:
    """Convert, de-duplicate and sort observations before any lag calculation."""

    if frame.empty or date_col not in frame or value_col not in frame:
        return pd.DataFrame(columns=[date_col, value_col])
    clean = frame[[date_col, value_col]].copy()
    clean[date_col] = pd.to_datetime(clean[date_col], errors="coerce")
    clean[value_col] = pd.to_numeric(clean[value_col], errors="coerce")
    clean = clean.dropna(subset=[date_col, value_col])
    if business_days_only:
        clean = clean.loc[clean[date_col].dt.dayofweek < 5]
    return clean.sort_values(date_col).drop_duplicates(date_col, keep="last").reset_index(drop=True)


def observation_change(
    frame: pd.DataFrame,
    date_col: str,
    value_col: str,
    periods: int,
    *,
    business_days_only: bool = False,
) -> ChangeResult | None:
    """Compare t with t-periods after sorting and dropping invalid observations."""

    if periods < 1:
        raise ValueError("periods must be at least one.")
    clean = clean_observations(
        frame, date_col, value_col, business_days_only=business_days_only
    )
    if len(clean) <= periods:
        return None
    latest = clean.iloc[-1]
    previous = clean.iloc[-(periods + 1)]
    absolute = percentage_point_change(latest[value_col], previous[value_col])
    return ChangeResult(
        latest_value=float(latest[value_col]),
        previous_value=float(previous[value_col]),
        latest_date=pd.Timestamp(latest[date_col]),
        previous_date=pd.Timestamp(previous[date_col]),
        absolute=absolute,
        percentage=percentage_change(latest[value_col], previous[value_col]),
    )


def calendar_change(
    frame: pd.DataFrame,
    date_col: str,
    value_col: str,
    *,
    months: int = 1,
) -> ChangeResult | None:
    """Compare latest with the latest valid observation on/before N months earlier."""

    if months < 1:
        raise ValueError("months must be at least one.")
    clean = clean_observations(frame, date_col, value_col)
    if len(clean) < 2:
        return None
    latest = clean.iloc[-1]
    cutoff = pd.Timestamp(latest[date_col]) - pd.DateOffset(months=months)
    eligible = clean.loc[clean[date_col] <= cutoff]
    if eligible.empty:
        return None
    previous = eligible.iloc[-1]
    absolute = percentage_point_change(latest[value_col], previous[value_col])
    return ChangeResult(
        latest_value=float(latest[value_col]),
        previous_value=float(previous[value_col]),
        latest_date=pd.Timestamp(latest[date_col]),
        previous_date=pd.Timestamp(previous[date_col]),
        absolute=absolute,
        percentage=percentage_change(latest[value_col], previous[value_col]),
    )


def summarize_expectations(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "Reference year",
        "Median (%)",
        "5-business-day change (pp)",
        "1-month change (pp)",
        "Latest observation",
    ]
    required = {"Date", "Reference year", "Median"}
    if frame.empty or not required.issubset(frame.columns):
        return pd.DataFrame(columns=columns)

    rows = []
    for reference_year, group in frame.groupby("Reference year", sort=True):
        clean = clean_observations(group, "Date", "Median")
        if clean.empty:
            continue
        move_5d = observation_change(clean, "Date", "Median", periods=5)
        move_1m = calendar_change(clean, "Date", "Median", months=1)
        latest = clean.iloc[-1]
        rows.append(
            {
                "Reference year": int(reference_year),
                "Median (%)": float(latest["Median"]),
                "5-business-day change (pp)": move_5d.absolute if move_5d else None,
                "1-month change (pp)": move_1m.absolute if move_1m else None,
                "Latest observation": pd.Timestamp(latest["Date"]),
            }
        )
    return pd.DataFrame(rows, columns=columns).sort_values("Reference year").reset_index(drop=True)


def _named_series(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    clean = clean_observations(frame, "Date", "Value")
    return clean.rename(columns={"Value": name})


def policy_rate_differential(
    selic: pd.DataFrame,
    fed_lower: pd.DataFrame,
    fed_upper: pd.DataFrame,
) -> pd.DataFrame:
    """Align target-rate observations and calculate Brazil minus Fed-range midpoint."""

    columns = [
        "Date",
        "Selic target",
        "Fed target lower",
        "Fed target upper",
        "Fed target midpoint",
        "Policy differential",
    ]
    if selic.empty or fed_lower.empty or fed_upper.empty:
        return pd.DataFrame(columns=columns)
    merged = _named_series(selic, "Selic target").merge(
        _named_series(fed_lower, "Fed target lower"), on="Date", how="inner"
    )
    merged = merged.merge(_named_series(fed_upper, "Fed target upper"), on="Date", how="inner")
    if merged.empty:
        return pd.DataFrame(columns=columns)
    merged["Fed target midpoint"] = (
        merged["Fed target lower"] + merged["Fed target upper"]
    ) / 2.0
    merged["Policy differential"] = (
        merged["Selic target"] - merged["Fed target midpoint"]
    )
    return merged[columns].sort_values("Date").reset_index(drop=True)


def us_curve(two_year: pd.DataFrame, ten_year: pd.DataFrame) -> pd.DataFrame:
    """Calculate 2s10s as 10-year yield minus 2-year yield in percentage points."""

    columns = ["Date", "2-year", "10-year", "2s10s"]
    if two_year.empty or ten_year.empty:
        return pd.DataFrame(columns=columns)
    merged = _named_series(two_year, "2-year").merge(
        _named_series(ten_year, "10-year"), on="Date", how="inner"
    )
    if merged.empty:
        return pd.DataFrame(columns=columns)
    merged["2s10s"] = merged["10-year"] - merged["2-year"]
    return merged[columns].sort_values("Date").reset_index(drop=True)
