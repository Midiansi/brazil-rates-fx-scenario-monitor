"""Load the dated thesis, format its numbers per language and check its rules.

Pure standard library: imported by the Streamlit page, the PDF generator and
the tests.  No network access.
"""
from __future__ import annotations

import json
import math
import statistics
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
    required = ("as_of", "evidence", "rules", "review", "calendar", "sources", "election", "previous_rules", "previous_evidence")
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


def vote_shares(votes: dict[str, int], leader: str = "flavio", trailer: str = "lula") -> dict[str, float]:
    """First-round shares of valid votes and the runoff arithmetic.

    ``*_needs`` is the share of the other candidates' voters a finalist must win
    to reach 50% of valid votes, with turnout and blank votes held constant.
    """

    total = sum(votes.values())
    others = total - votes[leader] - votes[trailer]
    return {
        "leader": votes[leader] / total * 100,
        "trailer": votes[trailer] / total * 100,
        "others": others / total * 100,
        "margin_pts": (votes[leader] - votes[trailer]) / total * 100,
        "margin_votes": float(votes[leader] - votes[trailer]),
        "leader_needs": (total / 2 - votes[leader]) / others * 100,
        "trailer_needs": (total / 2 - votes[trailer]) / others * 100,
    }


def poll_margin_miss(poll_valid_votes: dict[str, float], result_margin: float, leader: str = "flavio", trailer: str = "lula") -> float:
    """Points by which a poll's leader-minus-trailer margin fell short of the result."""

    return result_margin - (poll_valid_votes[leader] - poll_valid_votes[trailer])


def first_round_reaction(window: dict[str, Any]) -> dict[str, float]:
    """PTAX move on the first business day after a first round, and how much of it was undone.

    ``giveback`` is 100 when the real was back at its pre-vote level by the Friday
    before the runoff, and negative when the move was extended.
    """

    friday, monday, runoff = (window["closes"][key][1] for key in ("friday_before", "monday_after", "friday_before_runoff"))
    return {"monday_move": (monday / friday - 1) * 100, "giveback": (runoff - monday) / (friday - monday) * 100}


def volatility(closes: list[float], sessions: int = 20, horizon: int = 15) -> dict[str, float]:
    """Realised volatility of daily log returns, in percent, scaled to a horizon of sessions."""

    window = closes[-(sessions + 1):]
    daily = statistics.stdev(math.log(b / a) for a, b in zip(window, window[1:])) * 100
    return {"daily_sd": daily, "horizon_sd": daily * math.sqrt(horizon), "annualised": daily * math.sqrt(252)}


# ---------------------------------------------------------------------------
# Placeholders: every number the prose uses, formatted for one language.


def placeholders(thesis: dict[str, Any], lang: str) -> dict[str, str]:
    e, r, p, q = thesis["evidence"], thesis["rules"], thesis["previous_rules"], thesis["previous_evidence"]
    cal = {item["event"]: item["date"] for item in thesis["calendar"]}
    fed_mid = (e["fed_range"]["lower"] + e["fed_range"]["upper"]) / 2
    ptax_change = (e["ptax"]["value"] / e["ptax"]["previous"] - 1) * 100
    sp, vote, polls, jp, vol = e["survey_path_average"], e["election_first_round"], e["final_polls"], e["jpmorgan"], e["volatility"]
    moves = {w["year"]: w for w in e["first_round_reactions"]["windows"]}
    sizes = [abs(w["monday_move"]) for w in moves.values()]
    million = {"en": " million", "pt": " milhões", "fr": " millions"}[lang]
    values = {
        "as_of": f.day(thesis["as_of"], lang, long=True),
        "first_monday": f.day(thesis["as_of"], lang, year=False, long=True),
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
        "us2y_high": f.pct(e["us_2y"]["high_since_previous"], 2, lang),
        "us2y_high_date": f.day(e["us_2y"]["high_date"], lang, year=False, long=True),
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
        "brent_prev": f.usd(e["brent_spot"]["previous"], 2, lang),
        "brent_peak": f.usd(e["brent_spot"]["peak"], 2, lang),
        "brent_peak_date": f.day(e["brent_spot"]["peak_date"], lang, year=False, long=True),
        "fiscal_gov": f.brl_bn(e["fiscal_2027"]["government"], lang),
        "fiscal_ifi": f.brl_bn(e["fiscal_2027"]["ifi"], lang),
        # First round and final polls.
        "counted": f.pct(vote["reporting_pct"], 1, lang),
        "fl_share": f.pct(vote["flavio"], 1, lang),
        "lu_share": f.pct(vote["lula"], 1, lang),
        "oth_share": f.pct(vote["others"], 1, lang),
        "margin_pts": f.pp(vote["margin_pts"], 1, lang),
        "margin_votes": f.num(vote["margin_votes"] / 1e6, 1, lang) + million,
        "need_fl": f.pct(e["runoff_arithmetic"]["flavio_needs"], 0, lang),
        "need_lu": f.pct(e["runoff_arithmetic"]["lula_needs"], 0, lang),
        "dat_lula": str(polls["datafolha"]["lula"]),
        "dat_flavio": str(polls["datafolha"]["flavio"]),
        "dat_lead": str(polls["datafolha"]["lula"] - polls["datafolha"]["flavio"]),
        "dat_miss": f.pp(polls["datafolha"]["margin_miss"], 1, lang),
        "dat_r_lula": str(polls["datafolha"]["runoff_lula"]),
        "dat_r_flavio": str(polls["datafolha"]["runoff_flavio"]),
        "que_lula": str(polls["quaest"]["lula"]),
        "que_flavio": str(polls["quaest"]["flavio"]),
        "que_lead": str(polls["quaest"]["lula"] - polls["quaest"]["flavio"]),
        "que_miss": f.pp(polls["quaest"]["margin_miss"], 1, lang),
        "que_r_lula": str(polls["quaest"]["runoff_lula"]),
        "que_r_flavio": str(polls["quaest"]["runoff_flavio"]),
        "miss_avg": f.pp(polls["average_miss"], 1, lang),
        # Past first rounds, volatility and bank scenarios.
        "ev_min": f.pct(min(sizes), 1, lang),
        "ev_max": f.pct(max(sizes), 1, lang),
        "ev_avg": f.pct(abs(e["first_round_reactions"]["average_move"]), 1, lang),
        "gb_2014": f.pct(moves[2014]["giveback"], 0, lang),
        "gb_2018": f.pct(abs(moves[2018]["giveback"]), 0, lang),
        "gb_2022": f.pct(moves[2022]["giveback"], 0, lang),
        "vol_daily": f.pct(vol["daily_sd"], 2, lang),
        "vol_ann": f.pct(vol["annualised"], 0, lang),
        "vol15": f.pct(vol["horizon_sd"], 1, lang),
        "vol15_brl": f.num(vol["horizon_brl"], 2, lang),
        "entry_dist": f.pct(abs(vol["entry_distance"]), 1, lang),
        "abandon_dist": f.pct(vol["abandon_distance"], 1, lang),
        "entry_sigma": f.num(vol["entry_sigma"], 1, lang),
        "abandon_sigma": f.num(vol["abandon_sigma"], 1, lang),
        "event_sigma": f.num(vol["event_sigma"], 1, lang),
        "jpm_low": f.num(jp["low"], 2, lang),
        "jpm_high": f.num(jp["high"], 2, lang),
        "jpm_event": f.pct(jp["event_move"], 1, lang),
        "jpm_real": f.pct(jp["real_rate"], 1, lang),
        "jpm_real22": f.pct(jp["real_rate_2022"], 1, lang),
        "jpm_debt": f.pct(jp["gross_debt"], 0, lang),
        "jpm_debt22": f.pct(jp["gross_debt_2022"], 0, lang),
        # The 24 September thesis, for the review table.
        "prev_entry": f.num(p["entry_below"], 2, lang),
        "prev_abandon": f.num(p["abandon_above"], 2, lang),
        "prev_lula": str(q["poll_lula"]),
        "prev_flavio": str(q["poll_flavio"]),
        "prev_moe": {"en": "{} pts", "pt": "{} p.p.", "fr": "{}\u202fpts"}[lang].format(q["poll_margin"]),
        "prev_gap_2y": f.pp(q["br_2y_gap"], 1, lang),
        "prev_br_2y": f.pct(q["br_2y"], 2, lang),
        # Rules.
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
        "first_round": f.day(thesis["election"]["first_round"], lang, year=False, long=True),
        "runoff": f.day(thesis["election"]["runoff"], lang, year=False, long=True),
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
    after = [(d, v) for d, v in clean if d > thesis.get("data_as_of", thesis["as_of"])]

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
