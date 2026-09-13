from datetime import date

import pandas as pd

from src.live_refresh import build_commodities, build_series


def values(start: str, entries: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"Date": pd.date_range(start, periods=len(entries), freq="B"), "Value": entries})


def test_build_series_creates_current_compact_snapshot() -> None:
    dates = pd.date_range("2026-01-02", periods=180, freq="B")
    focus_rows = []
    for indicator, base in (("Selic", 13.0), ("IPCA", 4.5)):
        for day_index, observed in enumerate(dates):
            for year in range(2026, 2031):
                focus_rows.append({"Indicator": indicator, "Date": observed, "Reference year": year, "Median": base + (year - 2026) * .1 + day_index * .001, "Calculation base": 0})
    focus = pd.DataFrame(focus_rows)
    ptax = pd.DataFrame({
        "Date": dates, "Timestamp": dates + pd.Timedelta(hours=13),
        "Buying rate": [5 + i / 1000 for i in range(len(dates))],
        "Selling rate": [5.01 + i / 1000 for i in range(len(dates))],
    })
    ptax["Midpoint"] = (ptax["Buying rate"] + ptax["Selling rate"]) / 2
    frames = {
        "focus_selic": focus.loc[focus["Indicator"] == "Selic"],
        "focus_ipca": focus.loc[focus["Indicator"] == "IPCA"],
        "ptax": ptax,
        "selic_target": values("2026-01-02", [14.0] * 180),
        "fed_lower": values("2026-01-02", [3.5] * 180),
        "fed_upper": values("2026-01-02", [3.75] * 180),
        "us_2y": values("2026-01-02", [4.0 + i / 1000 for i in range(180)]),
        "us_10y": values("2026-01-02", [4.4 + i / 1000 for i in range(180)]),
    }
    result = build_series(frames, date(2026, 9, 13))
    assert result["selic_target"]["value"] == 14.0
    assert result["brazil_us_policy_differential"]["value"] == 10.375
    assert len(result["ptax_usd_brl_midpoint"]["twenty_observation_range"]) == 6
    assert set(result["focus_selic"]["values_by_reference_year"]) == {"2026", "2027", "2028", "2029", "2030"}


def test_build_commodities_uses_latest_two_observations() -> None:
    frames = {key: values("2026-01-02", [100.0, 103.0]) for key in ("brent", "iron_ore", "soybeans", "sugar")}
    result = build_commodities(frames)
    assert result["brent"]["latest"] == 103.0
    assert result["brent"]["signal"] == "higher"
    assert result["soybeans"]["series_id"] == "PSOYBUSDQ"
