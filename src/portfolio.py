from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def local_market_frames(research: dict | None) -> dict[str, pd.DataFrame]:
    """Build the first-paint market state entirely from the reviewable local snapshot."""
    keys = ("focus_selic", "focus_ipca", "ptax", "selic_target", "fed_lower", "fed_upper", "us_2y", "us_10y")
    data = {key: pd.DataFrame() for key in keys}
    if not research:
        return data
    series = research["series"]
    for key, indicator in (("focus_selic", "Selic"), ("focus_ipca", "IPCA")):
        item = series[key]
        data[key] = pd.DataFrame([
            {"Indicator": indicator, "Date": pd.Timestamp(item["latest_observation_date"]), "Reference year": int(year), "Median": float(value), "Calculation base": 0}
            for year, value in item["values_by_reference_year"].items()
        ])
    ptax = series["ptax_usd_brl_midpoint"]
    timestamp = pd.Timestamp(ptax["latest_observation_timestamp"])
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_localize(None)
    data["ptax"] = pd.DataFrame([{"Date": pd.Timestamp(ptax["latest_observation_date"]), "Timestamp": timestamp, "Buying rate": float(ptax["buying_rate"]), "Selling rate": float(ptax["selling_rate"]), "Midpoint": float(ptax["value"])}])
    for key, series_key, value_key in (
        ("selic_target", "selic_target", "value"), ("fed_lower", "fed_target_range", "lower"),
        ("fed_upper", "fed_target_range", "upper"), ("us_2y", "us_2_year_treasury", "value"),
        ("us_10y", "us_10_year_treasury", "value"),
    ):
        item = series[series_key]
        data[key] = pd.DataFrame([{"Date": pd.Timestamp(item["latest_observation_date"]), "Value": float(item[value_key])}])
    return data


def market_brief(research: dict | None, commodities: dict | None) -> list[tuple[str, str]]:
    if not research:
        return []
    series = research["series"]
    gap = series["brazil_us_policy_differential"]["value"]
    ipca = series["focus_ipca"]
    fx = series["ptax_usd_brl_midpoint"]
    items = [
        ("Rates", f"Brazilian policy rates remain about {gap:.1f} percentage points above the U.S., leaving a large interest-rate advantage while policy stays restrictive."),
        ("Currency", f"BRL has weakened about {abs(fx['one_month_change_percent']):.1f}% against USD over the past month; the move is modest relative to the current rate gap." if fx["one_month_change_percent"] > 0 else f"BRL has strengthened about {abs(fx['one_month_change_percent']):.1f}% against USD over the past month."),
        ("Inflation", f"The 2026 Focus inflation median is near {ipca['selected_value']:.1f}% and has edged lower over the past month, but remains above the BCB's target framework."),
    ]
    if commodities:
        moves = []
        for item in commodities["commodities"].values():
            pct = (float(item["latest"]) / float(item["previous"]) - 1) * 100
            moves.append((item["label"], pct))
        stronger = [name for name, pct in moves if pct > 0]
        weaker = [name for name, pct in moves if pct < 0]
        if stronger and weaker:
            text = f"The commodity backdrop is mixed: {', '.join(stronger)} rose in their latest source periods, while {', '.join(weaker)} weakened."
        elif stronger:
            text = f"The latest available commodity observations are broadly firmer, led by {', '.join(stronger)}."
        else:
            text = f"The latest available commodity observations are broadly softer, led by {', '.join(weaker)}."
        items.append(("Commodities", text))
    return items


def commodity_rows(snapshot: dict | None) -> list[dict]:
    if not snapshot:
        return []
    rows = []
    for key, item in snapshot["commodities"].items():
        pct = (float(item["latest"]) / float(item["previous"]) - 1) * 100
        rows.append({"key": key, **item, "change_percent": pct, "direction": "Higher" if pct > 0 else "Lower" if pct < 0 else "Unchanged"})
    return rows


def commodity_synthesis(snapshot: dict | None) -> list[tuple[str, str]]:
    rows = commodity_rows(snapshot)
    if not rows:
        return []
    export_rows = [row for row in rows if row["key"] in {"iron_ore", "soybeans", "brent", "sugar"}]
    up = sum(row["change_percent"] > 0 for row in export_rows)
    down = sum(row["change_percent"] < 0 for row in export_rows)
    external = "mixed" if up and down else "supportive" if up > down else "softer"
    oil = next((row for row in rows if row["key"] == "brent"), None)
    inflation = "Higher oil is a potential inflation headwind through the fuel-price channel." if oil and oil["change_percent"] > 0 else "Softer oil can reduce pressure through the fuel-price channel." if oil else "Oil data are unavailable."
    return [
        ("External balance", f"The latest source periods give a {external} picture for Brazil's major export commodities; this is an external backdrop, not a forecast for BRL."),
        ("Currency", "Commodity export receipts can support foreign-currency inflows, but domestic rates and the global dollar can dominate over shorter horizons."),
        ("Inflation", inflation),
        ("Rates", "Commodities reach monetary policy through both the currency and inflation channels, so the mix matters more than a single headline index."),
    ]
