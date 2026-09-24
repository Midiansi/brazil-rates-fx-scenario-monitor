"""Load the dated thesis, format its numbers per language and check its rules.

Pure standard library: imported by the Streamlit page, the PDF generator and
the tests.  No network access.
"""
from __future__ import annotations

import json
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src import formatting as f

ROOT = Path(__file__).resolve().parents[1]
FRENCH_SPACING = ((" :", " :"), (" ;", " ;"), (" ?", " ?"), (" !", " !"), (" %", " %"), ("« ", "« "), (" »", " »"))


def read_json(path: Path) -> dict[str, Any]:
    """Read a local JSON file; malformed or missing files become an empty dict."""

    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError, TypeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def load_thesis(path: Path | None = None) -> dict[str, Any]:
    thesis = read_json(path or ROOT / "research" / "thesis.json")
    required = ("as_of", "evidence", "rules", "review", "calendar", "sources")
    if not all(isinstance(thesis.get(key), (dict, list, str)) for key in required):
        return {}
    return thesis


# ---------------------------------------------------------------------------
# Calculations that the page states in words.


def survey_path_average(selic_now: float, year_end_medians: dict[int, float], start: date, years: int, cdi_spread: float = 0.10) -> float:
    """Annualised average overnight rate if policy follows the survey path.

    A straight line joins today's Selic target and the Focus year-end medians;
    the CDI usually trades about 0.10 pp below the target.  Daily compounding
    over ``years`` * 365 calendar days, returned in percent.
    """

    anchors = [(start, selic_now)] + sorted((date(year, 12, 31), value) for year, value in year_end_medians.items() if date(year, 12, 31) > start)

    def rate(day: date) -> float:
        for (d0, r0), (d1, r1) in zip(anchors, anchors[1:]):
            if d0 <= day <= d1:
                return r0 + (r1 - r0) * (day - d0).days / (d1 - d0).days
        return anchors[-1][1]

    days = 365 * years
    log_growth = sum(math.log(1 + (rate(start + timedelta(days=i)) - cdi_spread) / 100) for i in range(days)) / 365
    return (math.exp(log_growth / years) - 1) * 100


def monthly_carry(domestic: float, foreign: float) -> float:
    return (((1 + domestic / 100) / (1 + foreign / 100)) ** (1 / 12) - 1) * 100


# ---------------------------------------------------------------------------
# Placeholders: every number the prose uses, formatted for one language.


def placeholders(thesis: dict[str, Any], lang: str) -> dict[str, str]:
    e, r, p = thesis["evidence"], thesis["rules"], thesis["previous_rules"]
    cal = {item["event"]: item["date"] for item in thesis["calendar"]}
    fed_mid = (e["fed_range"]["lower"] + e["fed_range"]["upper"]) / 2
    ptax_change = (e["ptax"]["value"] / e["ptax"]["previous"] - 1) * 100
    sp = e["survey_path_average"]
    values = {
        "as_of": f.day(thesis["as_of"], lang, long=True),
        "selic": f.pct(e["selic"]["value"], 2, lang),
        "selic_prev": f.pct(e["selic"]["previous"], 2, lang),
        "fed_range": f.rate_range(e["fed_range"]["lower"], e["fed_range"]["upper"], lang),
        "fed_prev_range": f.rate_range(e["fed_range"]["previous_lower"], e["fed_range"]["previous_upper"], lang),
        "fed_mid": f.pct(fed_mid, 3, lang),
        "gap": f.pp(e["policy_gap"]["value"], 2, lang),
        "gap_prev": f.pp(e["policy_gap"]["previous"], 2, lang),
        "gap_round": f.num(e["policy_gap"]["value"], 1, lang),
        "carry": f.pct(e["carry_per_month"]["value"], 2, lang),
        "copom_proj": f.pct(e["copom_projection_2028q1"]["value"], 1, lang),
        "target": f.pct(e["copom_projection_2028q1"]["target"], 0, lang),
        "cuts_total": f.pp(e["copom_cuts_since_march"]["value"], 2, lang),
        "cuts_count": str(e["copom_cuts_since_march"]["count"]),
        "ptax": f.num(e["ptax"]["value"], 4, lang),
        "ptax_date": f.day(e["ptax"]["date"], lang, year=False, long=True),
        "ptax_prev": f.num(e["ptax"]["previous"], 4, lang),
        "ptax_chg": f.pct(ptax_change, 1, lang, signed=True),
        "ptax_high": f.num(e["ptax"]["high_since_previous"], 4, lang),
        "ptax_high_date": f.day(e["ptax"]["high_date"], lang, year=False, long=True),
        "ptax_low": f.num(e["ptax"]["low_since_previous"], 4, lang),
        "ptax_low_date": f.day(e["ptax"]["low_date"], lang, year=False, long=True),
        "high4m": f.num(e["ptax"]["four_month_high"], 4, lang),
        "high4m_date": f.day(e["ptax"]["four_month_high_date"], lang, year=False, long=True),
        "low4m": f.num(e["ptax"]["four_month_low"], 4, lang),
        "us2y": f.pct(e["us_2y"]["value"], 2, lang),
        "us2y_prev": f.pct(e["us_2y"]["previous"], 2, lang),
        "us10y": f.pct(e["us_10y"]["value"], 2, lang),
        "br_1y": f.pct(e["br_1y"]["value"], 2, lang),
        "br_2y": f.pct(e["br_2y"]["value"], 2, lang),
        "be_2y": f.pct(e["br_2y_breakeven"]["value"], 1, lang),
        "survey_1y": f.pct(sp["one_year"], 2, lang),
        "survey_2y": f.pct(sp["two_year"], 2, lang),
        "gap_1y": f.pp(sp["one_year_gap"], 2, lang),
        "gap_2y": f.pp(sp["two_year_gap"], 1, lang),
        "focus_date": f.day(e["focus_selic"]["date"], lang, year=False, long=True),
        "focus_selic26": f.pct(e["focus_selic"]["2026"], 2, lang),
        "focus_selic27": f.pct(e["focus_selic"]["2027"], 2, lang),
        "focus_ipca26": f.pct(e["focus_ipca"]["2026"], 1, lang),
        "focus_ipca27": f.pct(e["focus_ipca"]["2027"], 1, lang),
        "focus_fx26": f.num(e["focus_fx"]["2026"], 2, lang),
        "fed_proj_2026": f.pct(e["fed_projection"]["2026"], 1, lang),
        "fed_proj_june": f.pct(e["fed_projection"]["june_2026"], 1, lang),
        "brent": f.usd(e["brent_spot"]["value"], 2, lang),
        "brent_date": f.day(e["brent_spot"]["date"], lang, year=False, long=True),
        "brent_peak": f.usd(e["brent_spot"]["peak"], 2, lang),
        "brent_peak_date": f.day(e["brent_spot"]["peak_date"], lang, year=False, long=True),
        "brent_july": f.usd(e["brent_spot"]["late_july"], 2, lang),
        "brent_fut": f.usd(e["brent_futures_reported"]["value"], 2, lang),
        "brent_fut_date": f.day(e["brent_futures_reported"]["date"], lang, year=False, long=True),
        "eia_2h": f.usd(e["eia_brent_forecast_2h26"]["value"], 0, lang),
        "lula": str(e["poll_first_round"]["lula"]),
        "flavio": str(e["poll_first_round"]["flavio"]),
        "moe": {"en": "{} pts", "pt": "{} p.p.", "fr": "{}\u202fpts"}[lang].format(e["poll_first_round"]["margin"]),
        "runoff_lula": str(e["poll_runoff"]["lula"]),
        "runoff_flavio": str(e["poll_runoff"]["flavio"]),
        "fiscal_gov": f.brl_bn(e["fiscal_2027"]["government"], lang),
        "fiscal_ifi": f.brl_bn(e["fiscal_2027"]["ifi"], lang),
        "entry": f.num(r["entry_below"], 2, lang),
        "us2y_max": f.pct(r["entry_us2y_max"], 2, lang),
        "abandon": f.num(r["abandon_above"], 2, lang),
        "exit": f.num(r["exit_above"], 2, lang),
        "us2y_exit": f.pct(r["exit_us2y_above"], 2, lang),
        "br2y_max": f.pct(r["br2y_max"], 0, lang),
        "review_low": f.num(r["review_low"], 2, lang),
        "review_high": f.num(r["review_high"], 2, lang),
        "review_by": f.day(r["review_by"], lang, year=False, long=True),
        "earliest": f.day(r["earliest_entry"], lang, year=False, long=True),
        "range_low": f.num(r["range"]["low"], 4, lang),
        "range_high": f.num(r["range"]["high"], 4, lang),
        "prev_trigger": f.num(p["trigger"], 2, lang),
        "prev_abandon": f.num(p["abandon_before_entry"], 2, lang),
        "first_round": f.day(cal["election_first"], lang, year=False, long=True),
        "runoff": f.day(cal["election_runoff"], lang, year=False, long=True),
        "fomc_next": f.day(cal["fomc"], lang, year=False, long=True),
        "copom_next": f.day(cal["copom"], lang, year=False, long=True),
    }
    return values


def fill(text: str, values: dict[str, str], lang: str) -> str:
    result = text.format_map(values).replace("p.p..", "p.p.")
    if lang == "fr":
        for plain, spaced in FRENCH_SPACING:
            result = result.replace(plain, spaced)
    return result


# ---------------------------------------------------------------------------
# Mechanical rule check against the refreshed snapshot.


def _latest_on(history: list[list[Any]], day: str) -> float | None:
    eligible = [value for observed, value in history if observed <= day]
    return eligible[-1] if eligible else None


def rule_status(thesis: dict[str, Any], snapshot: dict[str, Any], today: date) -> dict[str, Any]:
    """Replay the pre-committed rules over PTAX closes after the thesis date."""

    rules = thesis["rules"]
    history = (snapshot.get("history") or {}).get("ptax") or []
    us2y_history = (snapshot.get("history") or {}).get("us_2y") or []
    try:
        clean = sorted((str(d), float(v)) for d, v in history)
    except (TypeError, ValueError):
        clean = []
    if not clean:
        return {"state": "unavailable"}
    latest_date, latest = clean[-1]
    base = {"latest": latest, "latest_date": latest_date}
    after = [(d, v) for d, v in clean if d > thesis["as_of"]]

    entered: tuple[str, float] | None = None
    below = above = 0
    for observed, value in after:
        if entered is None:
            if value > rules["abandon_above"]:
                return {**base, "state": "abandoned", "date": observed, "value": value}
            below = below + 1 if observed >= rules["earliest_entry"] and value < rules["entry_below"] else 0
            us2y = _latest_on(us2y_history, observed)
            if below >= rules["entry_closes"] and us2y is not None and us2y <= rules["entry_us2y_max"]:
                entered = (observed, value)
        else:
            above = above + 1 if value > rules["exit_above"] else 0
            us2y = _latest_on(us2y_history, observed)
            if above >= rules["exit_closes"] or (us2y is not None and us2y > rules["exit_us2y_above"]):
                return {**base, "state": "exited", "date": observed, "value": value}
            if value <= rules["review_high"]:
                return {**base, "state": "review", "date": observed, "value": value}
    if entered:
        return {**base, "state": "entered", "date": entered[0], "value": entered[1]}
    if today.isoformat() > rules["review_by"]:
        return {**base, "state": "expired"}
    if today.isoformat() < rules["earliest_entry"]:
        return {**base, "state": "waiting"}
    return {**base, "state": "watching"}
