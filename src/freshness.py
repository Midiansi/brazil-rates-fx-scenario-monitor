"""How old may an observation be before the page should call it delayed or stale?

The thresholds depend on how often a source publishes, so a monthly IMF price
from two months ago is normal while a two-week-old PTAX is not.  Used by the
page, the refresh job and the CI freshness gate, so all three agree.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

# (fresh up to, delayed up to) in calendar days since the observation date or
# period start.  Anything older is stale.  Daily limits allow for weekends and
# a Brazilian or U.S. holiday.
LIMITS = {
    "daily": (4, 7),
    "weekly": (10, 17),
    "monthly": (100, 130),
    "quarterly": (200, 260),
}

# Series whose staleness should turn the scheduled workflow red.
CRITICAL = ("ptax_usd_brl_midpoint", "selic_target", "fed_target_range", "us_2_year_treasury")


def _as_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def age_days(observed: object, today: date) -> int | None:
    parsed = _as_date(observed)
    if parsed is None:
        return None
    return (today - parsed).days


def status(observed: object, frequency: str, today: date) -> str:
    """Return 'fresh', 'delayed', 'stale' or 'unknown'."""

    age = age_days(observed, today)
    if age is None or age < -1:
        return "unknown"
    fresh, delayed = LIMITS.get(frequency.lower(), LIMITS["daily"])
    if age <= fresh:
        return "fresh"
    if age <= delayed:
        return "delayed"
    return "stale"


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def run_age_days(timestamp: object, today: date) -> int | None:
    """Age of the last refresh attempt, from an ISO timestamp."""

    if not isinstance(timestamp, str):
        return None
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(timezone.utc).date()
    except ValueError:
        return None
    return (today - parsed).days
