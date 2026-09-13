"""Build the tiny checked-in snapshot used by the production dashboard.

Network access belongs here, in a scheduled job, never in the Streamlit render
path.  A failed source retains its last good value instead of blanking the site.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from math import isfinite
from typing import Callable

import pandas as pd

from src.analytics import calendar_change, observation_change, policy_rate_differential, summarize_expectations, us_curve
from src.data import fetch_focus_expectations, fetch_fred_series, fetch_ptax, fetch_selic_target


SERIES_URLS = {
    "focus": "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/",
    "ptax": "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/",
    "selic": "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json",
}

COMMODITY_DEFINITIONS = {
    "brent": {
        "label": "Oil", "benchmark": "Brent crude", "series_id": "DCOILBRENTEU",
        "source": "U.S. Energy Information Administration via FRED",
        "frequency": "Daily", "unit": "USD per barrel",
        "channel": "Brazil is a major oil producer, so crude prices matter for export and producer revenues; fuel costs can also feed into the domestic inflation discussion.",
    },
    "iron_ore": {
        "label": "Iron ore", "benchmark": "IMF global iron-ore price", "series_id": "PIORECRUSDM",
        "source": "International Monetary Fund via FRED",
        "frequency": "Monthly", "unit": "USD per metric ton",
        "channel": "Iron ore is a large Brazilian export. Changes in global demand can therefore alter export income and the external backdrop for BRL.",
    },
    "soybeans": {
        "label": "Soybeans", "benchmark": "IMF global soybean price", "series_id": "PSOYBUSDQ",
        "source": "International Monetary Fund via FRED",
        "frequency": "Quarterly", "unit": "USD per metric ton",
        "channel": "Soy exports generate large foreign-currency receipts for Brazil, with timing shaped by the harvest and export season.",
    },
    "sugar": {
        "label": "Sugar", "benchmark": "IMF Sugar No. 11 world price", "series_id": "PSUGAISAUSDM",
        "source": "International Monetary Fund via FRED",
        "frequency": "Monthly", "unit": "US cents per pound",
        "channel": "Brazilian mills can shift cane between sugar and ethanol, linking the export market to domestic fuel economics.",
    },
}


def _number(value: object) -> float:
    result = float(value)
    if not isfinite(result):
        raise ValueError("Expected a finite market value.")
    return result


def _iso_day(value: object) -> str:
    return pd.Timestamp(value).date().isoformat()


def _move(frame: pd.DataFrame, column: str, periods: int = 5) -> tuple[float, float]:
    short = observation_change(frame, "Date", column, periods=periods)
    monthly = calendar_change(frame, "Date", column, months=1)
    if short is None or monthly is None:
        raise ValueError("Not enough observations to calculate changes.")
    return _number(short.absolute), _number(monthly.absolute)


def build_series(frames: dict[str, pd.DataFrame], as_of: date) -> dict[str, dict]:
    """Normalize official-source frames into the compact production schema."""

    result: dict[str, dict] = {}
    for key, indicator in (("focus_selic", "Selic"), ("focus_ipca", "IPCA")):
        summary = summarize_expectations(frames[key])
        current = summary.loc[summary["Reference year"] == as_of.year]
        if current.empty:
            raise ValueError(f"{indicator} has no current-year Focus observation.")
        row = current.iloc[-1]
        values = {
            str(int(item["Reference year"])): _number(item["Median (%)"])
            for _, item in summary.loc[summary["Reference year"].between(as_of.year, as_of.year + 4)].iterrows()
        }
        result[key] = {
            "label": f"Focus annual {indicator} median",
            "unit": "% p.a." if indicator == "Selic" else "% annual change",
            "latest_observation_date": _iso_day(row["Latest observation"]),
            "selected_reference_year": as_of.year,
            "selected_value": _number(row["Median (%)"]),
            "values_by_reference_year": values,
            "selected_5_business_day_change_pp": _number(row["5-business-day change (pp)"]),
            "selected_1_month_change_pp": _number(row["1-month change (pp)"]),
            "source_url": SERIES_URLS["focus"],
            "is_stale_at_retrieval": False,
            "staleness_note": "Latest usable observation returned by the official BCB Focus endpoint.",
        }

    ptax = frames["ptax"].sort_values("Date").reset_index(drop=True)
    latest = ptax.iloc[-1]
    five = observation_change(ptax, "Date", "Midpoint", periods=5)
    month = calendar_change(ptax, "Date", "Midpoint", months=1)
    recent = ptax.tail(20)
    if five is None or month is None or len(recent) < 20:
        raise ValueError("PTAX has insufficient history.")
    low, high = _number(recent["Midpoint"].min()), _number(recent["Midpoint"].max())
    midpoint = (low + high) / 2
    result["ptax_usd_brl_midpoint"] = {
        "label": "USD/BRL PTAX midpoint", "unit": "BRL per USD",
        "latest_observation_date": _iso_day(latest["Date"]),
        "latest_observation_timestamp": pd.Timestamp(latest["Timestamp"]).isoformat(),
        "buying_rate": _number(latest["Buying rate"]), "selling_rate": _number(latest["Selling rate"]),
        "value": _number(latest["Midpoint"]),
        "five_business_day_change_percent": _number(five.percentage),
        "one_month_change_percent": _number(month.percentage),
        "twenty_observation_range": {
            "start_date": _iso_day(recent.iloc[0]["Date"]), "end_date": _iso_day(recent.iloc[-1]["Date"]),
            "low": low, "high": high, "midpoint": midpoint, "width": high - low,
        },
        "source_url": SERIES_URLS["ptax"], "is_stale_at_retrieval": False,
        "staleness_note": "Latest closing PTAX returned by the official BCB endpoint.",
    }

    selic = frames["selic_target"].sort_values("Date").reset_index(drop=True)
    latest_selic = selic.iloc[-1]
    result["selic_target"] = {
        "label": "BCB Selic target", "unit": "% p.a.",
        "latest_observation_date": _iso_day(latest_selic["Date"]), "value": _number(latest_selic["Value"]),
        "source_url": SERIES_URLS["selic"], "is_stale_at_retrieval": False,
        "staleness_note": "Latest effective target returned by BCB SGS series 432.",
    }

    fed_lower, fed_upper = frames["fed_lower"], frames["fed_upper"]
    lower, upper = _number(fed_lower.iloc[-1]["Value"]), _number(fed_upper.iloc[-1]["Value"])
    fed_date = min(_iso_day(fed_lower.iloc[-1]["Date"]), _iso_day(fed_upper.iloc[-1]["Date"]))
    result["fed_target_range"] = {
        "label": "Federal-funds target range and calculated midpoint", "unit": "% p.a.",
        "latest_observation_date": fed_date, "lower": lower, "upper": upper, "midpoint": (lower + upper) / 2,
        "lower_source_url": "https://fred.stlouisfed.org/series/DFEDTARL",
        "upper_source_url": "https://fred.stlouisfed.org/series/DFEDTARU",
        "is_stale_at_retrieval": False, "staleness_note": "Latest official target-limit observations available through FRED.",
    }

    differential = policy_rate_differential(selic, fed_lower, fed_upper)
    latest_diff = differential.iloc[-1]
    diff_5, diff_1m = _move(differential, "Policy differential")
    result["brazil_us_policy_differential"] = {
        "label": "Selic target minus federal-funds target-range midpoint", "unit": "percentage points",
        "latest_observation_date": _iso_day(latest_diff["Date"]), "value": _number(latest_diff["Policy differential"]),
        "five_business_day_change_pp": diff_5, "one_month_change_pp": diff_1m,
        "source_url": "https://fred.stlouisfed.org/series/DFEDTARU",
        "additional_source_url": SERIES_URLS["selic"], "is_stale_at_retrieval": False,
        "staleness_note": "Derived from the latest common official policy-rate observation.",
    }

    for frame_key, output_key, years in (("us_2y", "us_2_year_treasury", "2"), ("us_10y", "us_10_year_treasury", "10")):
        frame = frames[frame_key].sort_values("Date").reset_index(drop=True)
        latest_rate = frame.iloc[-1]
        rate_5, rate_1m = _move(frame, "Value")
        result[output_key] = {
            "label": f"US {years}-year Treasury constant-maturity yield", "unit": "% p.a.",
            "latest_observation_date": _iso_day(latest_rate["Date"]), "value": _number(latest_rate["Value"]),
            "five_business_day_change_pp": rate_5, "one_month_change_pp": rate_1m,
            "source_url": f"https://fred.stlouisfed.org/series/DGS{years}", "is_stale_at_retrieval": False,
            "staleness_note": "Latest usable official Treasury observation available through FRED.",
        }

    curve = us_curve(frames["us_2y"], frames["us_10y"])
    latest_curve = curve.iloc[-1]
    curve_5 = observation_change(curve, "Date", "2s10s", periods=5)
    result["us_2s10s"] = {
        "label": "US 2s10s curve slope (10-year minus 2-year)", "unit": "percentage points",
        "latest_observation_date": _iso_day(latest_curve["Date"]), "value": _number(latest_curve["2s10s"]),
        "five_business_day_change_pp": _number(curve_5.absolute) if curve_5 else 0.0,
        "source_url": "https://fred.stlouisfed.org/series/DGS10",
        "additional_source_url": "https://fred.stlouisfed.org/series/DGS2",
        "is_stale_at_retrieval": False, "staleness_note": "Derived from the latest common Treasury observation.",
    }
    return result


def build_commodities(frames: dict[str, pd.DataFrame]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for key, definition in COMMODITY_DEFINITIONS.items():
        frame = frames[key].sort_values("Date").reset_index(drop=True)
        if len(frame) < 2:
            raise ValueError(f"{key} has insufficient history.")
        previous, latest = frame.iloc[-2], frame.iloc[-1]
        latest_value, previous_value = _number(latest["Value"]), _number(previous["Value"])
        result[key] = {
            **definition,
            "source_url": f"https://fred.stlouisfed.org/series/{definition['series_id']}",
            "latest_date": _iso_day(latest["Date"]), "latest": latest_value,
            "previous_date": _iso_day(previous["Date"]), "previous": previous_value,
            "signal": "higher" if latest_value > previous_value else "lower" if latest_value < previous_value else "unchanged",
        }
    return result


def fetch_all(as_of: date) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    """Fetch sources independently; callers can retain old values per failure."""

    start_focus = as_of - timedelta(days=400)
    start_market = as_of - timedelta(days=140)
    start_rates = as_of - timedelta(days=1100)
    jobs: dict[str, Callable[[], pd.DataFrame]] = {
        "focus_selic": lambda: fetch_focus_expectations("Selic", start_focus),
        "focus_ipca": lambda: fetch_focus_expectations("IPCA", start_focus),
        "ptax": lambda: fetch_ptax(start_market, as_of),
        "selic_target": lambda: fetch_selic_target(start_rates, as_of),
        "fed_lower": lambda: fetch_fred_series("DFEDTARL", start_rates),
        "fed_upper": lambda: fetch_fred_series("DFEDTARU", start_rates),
        "us_2y": lambda: fetch_fred_series("DGS2", start_rates),
        "us_10y": lambda: fetch_fred_series("DGS10", start_rates),
    }
    jobs.update({key: (lambda series_id=item["series_id"]: fetch_fred_series(series_id, start_rates)) for key, item in COMMODITY_DEFINITIONS.items()})
    frames: dict[str, pd.DataFrame] = {}
    failures: dict[str, str] = {}
    for key, loader in jobs.items():
        try:
            frame = loader()
            if frame.empty:
                raise ValueError("source returned no usable observations")
            frames[key] = frame
        except Exception as exc:  # scheduled-job boundary around external services
            failures[key] = str(exc)
    return frames, failures


def refresh_payload(existing: dict, as_of: date, now: datetime | None = None) -> dict:
    frames, failures = fetch_all(as_of)
    previous_series = existing.get("series", {}) if isinstance(existing, dict) else {}
    previous_commodities = existing.get("commodities", {}) if isinstance(existing, dict) else {}

    try:
        series = build_series(frames, as_of)
    except Exception:
        # The macro series are interdependent; keep the complete last-good set.
        series = previous_series
    try:
        commodities = build_commodities(frames)
    except Exception:
        commodities = previous_commodities
    if not series and not commodities:
        raise RuntimeError("No source returned a usable value and no fallback exists.")

    changed = series != previous_series or commodities != previous_commodities
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "updated_at": timestamp if changed else existing.get("updated_at", timestamp),
        "series": series,
        "commodities": commodities,
        "source_failures": sorted(failures),
        "note": "Refreshed automatically from official BCB and FRED feeds. A failed source keeps its last good value.",
    }
