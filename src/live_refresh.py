"""Build the small checked-in snapshot that the production page reads.

Network access belongs here, in a scheduled job, never in the Streamlit render
path.  Every source is fetched and validated on its own: a failed feed keeps
its last good value and is reported in ``refresh.sources`` instead of blanking
or freezing unrelated series.  Two U.S. inputs have an official fallback
because FRED has repeatedly timed out from GitHub-hosted runners.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from math import isfinite
from typing import Any, Callable

import pandas as pd

from src.analytics import calendar_change, observation_change, summarize_expectations
from src.data import (
    BCB_EXPECTATIONS_URL, BCB_PTAX_URL, BCB_SELIC_URL, NYFED_PAGE_URL, TREASURY_PAGE_URL,
    fetch_focus_expectations, fetch_fred_series, fetch_nyfed_target_range, fetch_ptax,
    fetch_selic_target, fetch_treasury_yields, first_success,
)

SCHEMA_VERSION = 2
HISTORY_LENGTH = {"ptax": 90, "us_2y": 40, "brent": 40}

COMMODITY_DEFINITIONS = {
    "brent": {
        "label": "Oil", "benchmark": "Brent crude, spot (EIA)", "series_id": "DCOILBRENTEU",
        "source": "U.S. Energy Information Administration via FRED", "frequency": "Daily", "unit": "USD per barrel",
    },
    "iron_ore": {
        "label": "Iron ore", "benchmark": "IMF global iron-ore price", "series_id": "PIORECRUSDM",
        "source": "International Monetary Fund via FRED", "frequency": "Monthly", "unit": "USD per metric ton",
    },
    "soybeans": {
        "label": "Soybeans", "benchmark": "IMF global soybean price", "series_id": "PSOYBUSDM",
        "source": "International Monetary Fund via FRED", "frequency": "Monthly", "unit": "USD per metric ton",
    },
    "sugar": {
        "label": "Sugar", "benchmark": "IMF Sugar No. 11 world price", "series_id": "PSUGAISAUSDM",
        "source": "International Monetary Fund via FRED", "frequency": "Monthly", "unit": "US cents per pound",
    },
}


def _number(value: object) -> float:
    result = float(value)  # type: ignore[arg-type]
    if not isfinite(result):
        raise ValueError("Expected a finite market value.")
    return result


def _iso_day(value: object) -> str:
    return pd.Timestamp(value).date().isoformat()


def _history(frame: pd.DataFrame, column: str, length: int) -> list[list[Any]]:
    tail = frame.sort_values("Date").tail(length)
    return [[_iso_day(row["Date"]), round(_number(row[column]), 6)] for _, row in tail.iterrows()]


def _changes(frame: pd.DataFrame, column: str) -> tuple[float, float]:
    short = observation_change(frame, "Date", column, periods=5)
    monthly = calendar_change(frame, "Date", column, months=1)
    if short is None or monthly is None:
        raise ValueError("Not enough observations to calculate changes.")
    return _number(short.absolute), _number(monthly.absolute)


# ---------------------------------------------------------------------------
# Builders: one validated frame in, compact production records out.


def build_focus(frame: pd.DataFrame, indicator: str, as_of: date) -> dict[str, Any]:
    summary = summarize_expectations(frame)
    current = summary.loc[summary["Reference year"] == as_of.year]
    if current.empty:
        raise ValueError(f"{indicator} has no current-year Focus observation.")
    row = current.iloc[-1]
    window = summary.loc[summary["Reference year"].between(as_of.year, as_of.year + 3)]
    labels = {"Selic": ("Focus year-end Selic median", "% p.a."), "IPCA": ("Focus annual IPCA median", "% annual change"),
              "Câmbio": ("Focus year-end USD/BRL median", "BRL per USD")}
    label, unit = labels[indicator]
    change = row["1-month change (pp)"]
    return {
        "label": label, "unit": unit, "frequency": "weekly",
        "latest_observation_date": _iso_day(row["Latest observation"]),
        "selected_reference_year": as_of.year,
        "selected_value": _number(row["Median (%)"]),
        "selected_1_month_change_pp": _number(change) if change is not None and pd.notna(change) else 0.0,
        "values_by_reference_year": {str(int(item["Reference year"])): _number(item["Median (%)"]) for _, item in window.iterrows()},
        "source": "BCB Focus survey", "source_url": BCB_EXPECTATIONS_URL,
    }


def build_ptax(frame: pd.DataFrame) -> tuple[dict[str, Any], list[list[Any]]]:
    ptax = frame.sort_values("Date").reset_index(drop=True)
    latest = ptax.iloc[-1]
    five = observation_change(ptax, "Date", "Midpoint", periods=5)
    month = calendar_change(ptax, "Date", "Midpoint", months=1)
    recent = ptax.tail(20)
    if five is None or month is None or len(recent) < 20:
        raise ValueError("PTAX has insufficient history.")
    low, high = _number(recent["Midpoint"].min()), _number(recent["Midpoint"].max())
    item = {
        "label": "USD/BRL PTAX midpoint", "unit": "BRL per USD", "frequency": "daily",
        "latest_observation_date": _iso_day(latest["Date"]),
        "latest_observation_timestamp": pd.Timestamp(latest["Timestamp"]).isoformat(),
        "buying_rate": _number(latest["Buying rate"]), "selling_rate": _number(latest["Selling rate"]),
        "value": _number(latest["Midpoint"]),
        "five_business_day_change_percent": _number(five.percentage),
        "one_month_change_percent": _number(month.percentage),
        "twenty_observation_range": {
            "start_date": _iso_day(recent.iloc[0]["Date"]), "end_date": _iso_day(recent.iloc[-1]["Date"]),
            "low": low, "high": high, "midpoint": (low + high) / 2, "width": high - low,
        },
        "source": "BCB PTAX", "source_url": BCB_PTAX_URL,
    }
    return item, _history(ptax, "Midpoint", HISTORY_LENGTH["ptax"])


def build_selic(frame: pd.DataFrame) -> dict[str, Any]:
    selic = frame.sort_values("Date").reset_index(drop=True)
    latest = selic.iloc[-1]
    changes = selic.loc[selic["Value"].diff().fillna(0) != 0]
    last_change = changes.iloc[-1] if not changes.empty else latest
    return {
        "label": "BCB Selic target", "unit": "% p.a.", "frequency": "daily",
        "latest_observation_date": _iso_day(latest["Date"]), "value": _number(latest["Value"]),
        "effective_since": _iso_day(last_change["Date"]),
        "source": "BCB SGS 432", "source_url": sgs_url(pd.Timestamp(last_change["Date"]).date(), pd.Timestamp(latest["Date"]).date()),
    }


def sgs_url(start: date, end: date) -> str:
    """SGS links must be date-bounded: an open-ended request returns HTTP 406."""

    return f"{BCB_SELIC_URL}&dataInicial={start:%d/%m/%Y}&dataFinal={end:%d/%m/%Y}"


def build_fed_range(frame: pd.DataFrame, source: str) -> dict[str, Any]:
    fed = frame.sort_values("Date").reset_index(drop=True)
    latest = fed.iloc[-1]
    lower, upper = _number(latest["Lower"]), _number(latest["Upper"])
    changes = fed.loc[fed["Upper"].diff().fillna(0) != 0]
    last_change = changes.iloc[-1] if not changes.empty else latest
    nyfed = source.startswith("New York Fed")
    return {
        "label": "Federal-funds target range", "unit": "% p.a.", "frequency": "daily",
        "latest_observation_date": _iso_day(latest["Date"]),
        "lower": lower, "upper": upper, "midpoint": (lower + upper) / 2,
        "effective_since": _iso_day(last_change["Date"]),
        "source": source,
        "source_url": NYFED_PAGE_URL if nyfed else "https://fred.stlouisfed.org/series/DFEDTARU",
    }


def build_yields(frame: pd.DataFrame, source: str) -> tuple[dict[str, dict[str, Any]], list[list[Any]]]:
    yields = frame.sort_values("Date").reset_index(drop=True)
    treasury = source.startswith("U.S. Treasury")
    result: dict[str, dict[str, Any]] = {}
    for column, key, years in (("2y", "us_2_year_treasury", 2), ("10y", "us_10_year_treasury", 10)):
        latest = yields.iloc[-1]
        short, monthly = _changes(yields.rename(columns={column: "Value"}), "Value")
        result[key] = {
            "label": f"U.S. {years}-year Treasury yield", "unit": "% p.a.", "frequency": "daily",
            "latest_observation_date": _iso_day(latest["Date"]), "value": _number(latest[column]),
            "five_business_day_change_pp": short, "one_month_change_pp": monthly,
            "source": source,
            "source_url": TREASURY_PAGE_URL if treasury else f"https://fred.stlouisfed.org/series/DGS{years}",
        }
    latest = yields.iloc[-1]
    result["us_2s10s"] = {
        "label": "U.S. 2s10s slope (10-year minus 2-year)", "unit": "percentage points", "frequency": "daily",
        "latest_observation_date": _iso_day(latest["Date"]), "value": _number(latest["10y"] - latest["2y"]),
        "source": source, "source_url": result["us_10_year_treasury"]["source_url"],
    }
    return result, _history(yields, "2y", HISTORY_LENGTH["us_2y"])


def build_commodity(key: str, frame: pd.DataFrame) -> tuple[dict[str, Any], list[list[Any]] | None]:
    definition = COMMODITY_DEFINITIONS[key]
    ordered = frame.sort_values("Date").reset_index(drop=True)
    if len(ordered) < 2:
        raise ValueError(f"{key} has insufficient history.")
    previous, latest = ordered.iloc[-2], ordered.iloc[-1]
    item = {
        **definition,
        "source_url": f"https://fred.stlouisfed.org/series/{definition['series_id']}",
        "latest_date": _iso_day(latest["Date"]), "latest": _number(latest["Value"]),
        "previous_date": _iso_day(previous["Date"]), "previous": _number(previous["Value"]),
    }
    history = _history(ordered, "Value", HISTORY_LENGTH["brent"]) if key == "brent" else None
    return item, history


def policy_differential(selic: dict[str, Any] | None, fed: dict[str, Any] | None) -> dict[str, Any] | None:
    """Selic target minus the Fed target-range midpoint, dated by the older input."""

    if not selic or not fed:
        return None
    return {
        "label": "Selic target minus federal-funds target-range midpoint", "unit": "percentage points",
        "frequency": "daily",
        "latest_observation_date": min(selic["latest_observation_date"], fed["latest_observation_date"]),
        "value": _number(selic["value"] - fed["midpoint"]),
        "source": "Derived: BCB SGS 432 and " + fed.get("source", "Federal Reserve"),
        "source_url": selic["source_url"], "additional_source_url": fed["source_url"],
    }


# ---------------------------------------------------------------------------
# Orchestration.


def _fred_pair(first: str, second: str, names: tuple[str, str], start: date) -> pd.DataFrame:
    a = fetch_fred_series(first, start).rename(columns={"Value": names[0]})
    b = fetch_fred_series(second, start).rename(columns={"Value": names[1]})
    return a.merge(b, on="Date", how="inner")


def source_plan(as_of: date) -> dict[str, list[tuple[str, Callable[[], pd.DataFrame]]]]:
    start_focus = as_of - timedelta(days=400)
    start_market = as_of - timedelta(days=150)
    start_rates = as_of - timedelta(days=400)
    plan: dict[str, list[tuple[str, Callable[[], pd.DataFrame]]]] = {
        "focus_selic": [("BCB Focus", lambda: fetch_focus_expectations("Selic", start_focus))],
        "focus_ipca": [("BCB Focus", lambda: fetch_focus_expectations("IPCA", start_focus))],
        "focus_fx": [("BCB Focus", lambda: fetch_focus_expectations("Câmbio", start_focus))],
        "ptax": [("BCB PTAX", lambda: fetch_ptax(start_market, as_of))],
        "selic_target": [("BCB SGS 432", lambda: fetch_selic_target(start_rates, as_of))],
        "fed_range": [
            ("New York Fed (EFFR feed)", lambda: fetch_nyfed_target_range(90)),
            ("FRED DFEDTARL/DFEDTARU", lambda: _fred_pair("DFEDTARL", "DFEDTARU", ("Lower", "Upper"), start_rates)),
        ],
        "us_yields": [
            ("U.S. Treasury par yield curve", lambda: fetch_treasury_yields(start_market, as_of)),
            ("FRED DGS2/DGS10", lambda: _fred_pair("DGS2", "DGS10", ("2y", "10y"), start_market)),
        ],
    }
    for key, item in COMMODITY_DEFINITIONS.items():
        plan[key] = [(f"FRED {item['series_id']}", lambda series_id=item["series_id"]: fetch_fred_series(series_id, start_rates))]
    return plan


def _timestamp(now: datetime) -> str:
    return now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def refresh_payload(
    existing: dict | None,
    as_of: date,
    now: datetime | None = None,
    plan: dict[str, list[tuple[str, Callable[[], pd.DataFrame]]]] | None = None,
) -> dict:
    existing = existing if isinstance(existing, dict) else {}
    now = now or datetime.now(timezone.utc)
    stamp = _timestamp(now)
    series: dict[str, Any] = dict(existing.get("series") or {})
    commodities: dict[str, Any] = dict(existing.get("commodities") or {})
    history: dict[str, Any] = dict(existing.get("history") or {})
    previous_sources = (existing.get("refresh") or {}).get("sources") or {}
    sources: dict[str, dict[str, Any]] = {}

    def record(key: str, ok: bool, source: str = "", error: str = "") -> None:
        before = previous_sources.get(key) or {}
        sources[key] = {
            "status": "ok" if ok else "failed",
            "source": source or before.get("source", ""),
            "last_success": stamp if ok else before.get("last_success"),
            "error": "" if ok else error[:300],
        }

    for key, loaders in (plan or source_plan(as_of)).items():
        try:
            name, frame, fallback_errors = first_success(loaders)
            if key in ("focus_selic", "focus_ipca", "focus_fx"):
                indicator = {"focus_selic": "Selic", "focus_ipca": "IPCA", "focus_fx": "Câmbio"}[key]
                series[key] = build_focus(frame, indicator, as_of)
            elif key == "ptax":
                series["ptax_usd_brl_midpoint"], history["ptax"] = build_ptax(frame)
            elif key == "selic_target":
                series["selic_target"] = build_selic(frame)
            elif key == "fed_range":
                series["fed_target_range"] = build_fed_range(frame, name)
            elif key == "us_yields":
                built, history["us_2y"] = build_yields(frame, name)
                series.update(built)
            else:
                commodities[key], extra = build_commodity(key, frame)
                if extra is not None:
                    history[key] = extra
            record(key, True, name)
            if fallback_errors:
                sources[key]["note"] = "Primary source failed; fallback used: " + "; ".join(fallback_errors)[:300]
        except Exception as exc:  # a failed feed must never erase the last good value
            record(key, False, error=str(exc))

    differential = policy_differential(series.get("selic_target"), series.get("fed_target_range"))
    if differential:
        series["brazil_us_policy_differential"] = differential

    if not series and not commodities:
        raise RuntimeError("No source returned a usable value and no fallback exists.")

    changed = (
        series != (existing.get("series") or {})
        or commodities != (existing.get("commodities") or {})
        or history != (existing.get("history") or {})
    )
    ok = sum(item["status"] == "ok" for item in sources.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": stamp if changed else existing.get("updated_at", stamp),
        "refresh": {
            "attempted_at": stamp,
            "sources_ok": ok,
            "sources_total": len(sources),
            "sources": sources,
        },
        "series": series,
        "commodities": commodities,
        "history": history,
        "note": "Written by scripts/refresh_market_data.py from official feeds. A failed source keeps its last good value; see refresh.sources.",
    }
