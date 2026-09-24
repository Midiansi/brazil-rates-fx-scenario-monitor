"""The scheduled refresh: independent sources, official fallbacks, honest status."""
from __future__ import annotations

import copy
from datetime import date, datetime, timezone

import pandas as pd
import pytest

from src.live_refresh import build_commodity, build_fed_range, build_focus, build_ptax, build_selic, build_yields, refresh_payload

AS_OF = date(2026, 9, 24)
NOW = datetime(2026, 9, 24, 22, 20, tzinfo=timezone.utc)


def business_days(periods: int, end: str = "2026-09-24") -> pd.DatetimeIndex:
    return pd.bdate_range(end=end, periods=periods)


def values(entries: list[float], end: str = "2026-09-24") -> pd.DataFrame:
    return pd.DataFrame({"Date": business_days(len(entries), end), "Value": entries})


def focus_frame(indicator: str, base: float) -> pd.DataFrame:
    rows = []
    for index, observed in enumerate(business_days(60, "2026-09-18")):
        for year in range(2026, 2030):
            rows.append({"Indicator": indicator, "Date": observed, "Reference year": year, "Median": base - (year - 2026) * 0.5 + index * 0.001, "Calculation base": 0})
    return pd.DataFrame(rows)


def ptax_frame() -> pd.DataFrame:
    dates = business_days(90)
    frame = pd.DataFrame({"Date": dates, "Timestamp": dates + pd.Timedelta(hours=13),
                          "Buying rate": [5.0 + i / 1000 for i in range(90)], "Selling rate": [5.001 + i / 1000 for i in range(90)]})
    frame["Midpoint"] = (frame["Buying rate"] + frame["Selling rate"]) / 2
    return frame


def fed_frame(lower=3.75, upper=4.0) -> pd.DataFrame:
    dates = business_days(30)
    return pd.DataFrame({"Date": dates, "Lower": [3.5] * 20 + [lower] * 10, "Upper": [3.75] * 20 + [upper] * 10, "EFFR": [3.88] * 30})


def yields_frame() -> pd.DataFrame:
    dates = business_days(60)
    return pd.DataFrame({"Date": dates, "2y": [4.3 + i / 100 for i in range(60)], "10y": [4.8 + i / 200 for i in range(60)]})


def plan(**overrides):
    good = {
        "focus_selic": [("BCB Focus", lambda: focus_frame("Selic", 13.5))],
        "focus_ipca": [("BCB Focus", lambda: focus_frame("IPCA", 4.9))],
        "focus_fx": [("BCB Focus", lambda: focus_frame("Câmbio", 5.2))],
        "ptax": [("BCB PTAX", ptax_frame)],
        "selic_target": [("BCB SGS 432", lambda: values([14.0] * 30 + [13.75] * 6))],
        "fed_range": [("New York Fed (EFFR feed)", fed_frame)],
        "us_yields": [("U.S. Treasury par yield curve", yields_frame)],
        "brent": [("FRED DCOILBRENTEU", lambda: values([100.0, 110.0, 120.0]))],
        "iron_ore": [("FRED PIORECRUSDM", lambda: values([103.8, 101.6]))],
        "soybeans": [("FRED PSOYBUSDM", lambda: values([414.5, 442.4]))],
        "sugar": [("FRED PSUGAISAUSDM", lambda: values([13.9, 14.8]))],
    }
    good.update(overrides)
    return good


def failing(name: str = "FRED"):
    def load():
        raise TimeoutError(f"{name} timed out")
    return load


def test_builders_create_the_production_schema() -> None:
    assert build_selic(values([14.0] * 30 + [13.75] * 6))["effective_since"] == str(business_days(6)[0].date())
    fed = build_fed_range(fed_frame(), "New York Fed (EFFR feed)")
    assert (fed["lower"], fed["upper"], fed["midpoint"]) == (3.75, 4.0, 3.875)
    ptax, history = build_ptax(ptax_frame())
    assert len(history) == 90 and len(ptax["twenty_observation_range"]) == 6
    series, us2y = build_yields(yields_frame(), "U.S. Treasury par yield curve")
    assert series["us_2s10s"]["value"] == pytest.approx(series["us_10_year_treasury"]["value"] - series["us_2_year_treasury"]["value"])
    assert "treasury.gov" in series["us_2_year_treasury"]["source_url"]
    focus = build_focus(focus_frame("Selic", 13.5), "Selic", AS_OF)
    assert set(focus["values_by_reference_year"]) == {"2026", "2027", "2028", "2029"}
    brent, brent_history = build_commodity("brent", values([100.0, 110.0]))
    assert brent["latest"] == 110.0 and brent_history


def test_full_refresh_records_every_source() -> None:
    payload = refresh_payload({}, AS_OF, NOW, plan())
    assert payload["refresh"]["sources_ok"] == payload["refresh"]["sources_total"] == 11
    assert payload["series"]["brazil_us_policy_differential"]["value"] == pytest.approx(13.75 - 3.875)
    assert payload["updated_at"] == payload["refresh"]["attempted_at"] == "2026-09-24T22:20:00Z"


def test_one_failed_feed_keeps_its_last_value_and_does_not_block_others() -> None:
    first = refresh_payload({}, AS_OF, NOW, plan())
    later = datetime(2026, 9, 25, 22, 20, tzinfo=timezone.utc)
    second = refresh_payload(first, date(2026, 9, 25), later, plan(brent=[("FRED DCOILBRENTEU", failing())],
                                                                  selic_target=[("BCB SGS 432", lambda: values([14.0] * 30 + [13.5] * 6, "2026-09-25"))]))
    assert second["commodities"]["brent"] == first["commodities"]["brent"]
    assert second["refresh"]["sources"]["brent"]["status"] == "failed"
    assert "timed out" in second["refresh"]["sources"]["brent"]["error"]
    assert second["refresh"]["sources"]["brent"]["last_success"] == "2026-09-24T22:20:00Z"
    # The unrelated BCB series still updated, and the derived gap followed it.
    assert second["series"]["selic_target"]["value"] == 13.5
    assert second["series"]["brazil_us_policy_differential"]["value"] == pytest.approx(13.5 - 3.875)


def test_fred_outage_uses_official_fallbacks() -> None:
    payload = refresh_payload({}, AS_OF, NOW, plan(
        fed_range=[("New York Fed (EFFR feed)", failing("NY Fed")), ("FRED DFEDTARL/DFEDTARU", fed_frame)],
        us_yields=[("U.S. Treasury par yield curve", yields_frame), ("FRED DGS2/DGS10", failing())],
    ))
    assert payload["refresh"]["sources"]["fed_range"]["source"] == "FRED DFEDTARL/DFEDTARU"
    assert "fallback" in payload["refresh"]["sources"]["fed_range"]["note"]
    assert payload["series"]["us_2_year_treasury"]["source"] == "U.S. Treasury par yield curve"


def test_malformed_source_is_rejected_not_saved() -> None:
    bad = pd.DataFrame({"Date": business_days(3), "Value": [float("nan"), float("inf"), 5.0]})
    first = refresh_payload({}, AS_OF, NOW, plan())
    second = refresh_payload(first, AS_OF, NOW, plan(iron_ore=[("FRED PIORECRUSDM", lambda: bad.iloc[:1])]))
    assert second["commodities"]["iron_ore"] == first["commodities"]["iron_ore"]
    assert second["refresh"]["sources"]["iron_ore"]["status"] == "failed"


def test_total_outage_without_fallback_raises() -> None:
    everything_fails = {key: [(key, failing())] for key in plan()}
    with pytest.raises(RuntimeError):
        refresh_payload({}, AS_OF, NOW, everything_fails)


def test_total_outage_with_history_keeps_values_and_reports() -> None:
    first = refresh_payload({}, AS_OF, NOW, plan())
    everything_fails = {key: [(key, failing())] for key in plan()}
    later = datetime(2026, 9, 25, 22, 20, tzinfo=timezone.utc)
    second = refresh_payload(copy.deepcopy(first), date(2026, 9, 25), later, everything_fails)
    assert second["series"] == first["series"]
    assert second["refresh"]["sources_ok"] == 0
    # Nothing new was observed, so the data timestamp does not move; the attempt does.
    assert second["updated_at"] == first["updated_at"]
    assert second["refresh"]["attempted_at"] == "2026-09-25T22:20:00Z"
