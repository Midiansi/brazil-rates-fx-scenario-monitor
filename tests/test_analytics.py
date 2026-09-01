import math

import pandas as pd
import pytest

from src.analytics import (
    calendar_change,
    observation_change,
    percentage_change,
    percentage_point_change,
    policy_rate_differential,
    us_curve,
)


def test_percentage_change() -> None:
    assert percentage_change(5.25, 5.00) == pytest.approx(5.0)
    assert math.isnan(percentage_change(1.0, 0.0))


def test_percentage_point_change() -> None:
    assert percentage_point_change(13.75, 13.50) == 0.25


def test_business_day_observation_selection_sorts_and_drops_missing() -> None:
    frame = pd.DataFrame(
        {
            "date": ["2026-08-10", "2026-08-06", "2026-08-07", "2026-08-05", "bad"],
            "value": [5.20, 5.00, None, 4.90, 99.0],
        }
    )
    result = observation_change(frame, "date", "value", periods=2)
    assert result is not None
    assert result.latest_date == pd.Timestamp("2026-08-10")
    assert result.previous_date == pd.Timestamp("2026-08-05")
    assert result.absolute == pytest.approx(0.30)


def test_calendar_change_uses_last_observation_on_or_before_cutoff() -> None:
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-06-30", "2026-07-02", "2026-07-31"]),
            "Value": [10.0, 11.0, 12.0],
        }
    )
    result = calendar_change(frame, "Date", "Value", months=1)
    assert result is not None
    assert result.previous_date == pd.Timestamp("2026-06-30")
    assert result.absolute == 2.0


def test_policy_rate_differential_uses_fed_target_midpoint() -> None:
    dates = pd.to_datetime(["2026-08-01", "2026-08-02"])
    selic = pd.DataFrame({"Date": dates, "Value": [14.0, 14.0]})
    lower = pd.DataFrame({"Date": dates, "Value": [3.50, 3.50]})
    upper = pd.DataFrame({"Date": dates, "Value": [3.75, 3.75]})
    result = policy_rate_differential(selic, lower, upper)
    assert list(result["Fed target midpoint"]) == [3.625, 3.625]
    assert list(result["Policy differential"]) == [10.375, 10.375]


def test_us_2s10s_is_ten_year_minus_two_year() -> None:
    dates = pd.to_datetime(["2026-08-01", "2026-08-02"])
    two_year = pd.DataFrame({"Date": dates, "Value": [4.10, 4.20]})
    ten_year = pd.DataFrame({"Date": dates, "Value": [4.60, 4.55]})
    result = us_curve(two_year, ten_year)
    assert list(result["2s10s"].round(2)) == [0.50, 0.35]
