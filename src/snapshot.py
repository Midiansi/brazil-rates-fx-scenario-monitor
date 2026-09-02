from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


SERIES_MAP = {
    "selic_target": ("selic_target", "value"),
    "fed_lower": ("fed_target_range", "lower"),
    "fed_upper": ("fed_target_range", "upper"),
    "us_2y": ("us_2_year_treasury", "value"),
    "us_10y": ("us_10_year_treasury", "value"),
}


def frames_from_research(research: dict | None) -> dict[str, pd.DataFrame]:
    """Build a complete instant-render market snapshot without network I/O."""
    if not research:
        return {}
    series = research["series"]
    frames: dict[str, pd.DataFrame] = {}
    for key, indicator, series_key in (
        ("focus_selic", "Selic", "focus_selic"),
        ("focus_ipca", "IPCA", "focus_ipca"),
    ):
        item = series[series_key]
        frames[key] = pd.DataFrame([
            {"Indicator": indicator, "Date": pd.Timestamp(item["latest_observation_date"]),
             "Reference year": int(year), "Median": float(value), "Calculation base": 0}
            for year, value in item["values_by_reference_year"].items()
        ])
    ptax = series["ptax_usd_brl_midpoint"]
    timestamp = pd.Timestamp(ptax["latest_observation_timestamp"])
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_localize(None)
    frames["ptax"] = pd.DataFrame([{
        "Date": pd.Timestamp(ptax["latest_observation_date"]), "Timestamp": timestamp,
        "Buying rate": float(ptax["buying_rate"]), "Selling rate": float(ptax["selling_rate"]),
        "Midpoint": float(ptax["value"]),
    }])
    for key, (series_key, value_key) in SERIES_MAP.items():
        item = series[series_key]
        frames[key] = pd.DataFrame([{"Date": pd.Timestamp(item["latest_observation_date"]),
                                     "Value": float(item[value_key])}])
    return frames


def load_commodity_snapshot(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload.get("commodities"), dict):
        raise ValueError("Commodity snapshot is missing commodities.")
    return payload


def commodity_rows(snapshot: dict) -> pd.DataFrame:
    rows = []
    for key, item in snapshot.get("commodities", {}).items():
        current, previous = float(item["latest"]), float(item["previous"])
        change = (current / previous - 1) * 100 if previous else float("nan")
        rows.append({"key": key, "label": item["label"], "benchmark": item["benchmark"],
                     "latest": current, "change_percent": change,
                     "latest_date": pd.Timestamp(item["latest_date"]),
                     "previous_date": pd.Timestamp(item["previous_date"]),
                     "frequency": item["frequency"], "unit": item["unit"],
                     "source": item["source"], "source_url": item["source_url"],
                     "channel": item["channel"]})
    return pd.DataFrame(rows)


def commodity_brief(rows: pd.DataFrame) -> str:
    if rows.empty:
        return "Commodity context is temporarily unavailable."
    higher = rows.loc[rows["change_percent"] > 0, "label"].tolist()
    lower = rows.loc[rows["change_percent"] < 0, "label"].tolist()
    if higher and lower:
        return f"Brazil's commodity backdrop is mixed: {', '.join(higher)} moved higher in their latest source periods, while {', '.join(lower)} moved lower."
    if higher:
        return f"The latest available readings are broadly firmer across {', '.join(higher)}."
    if lower:
        return f"The latest available readings are broadly softer across {', '.join(lower)}."
    return "The latest available commodity readings are broadly unchanged."
