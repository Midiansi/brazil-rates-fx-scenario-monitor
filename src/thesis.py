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
    # The quantitative study is saved next to the thesis; without it the page still renders its core.
    study = read_json(ROOT / thesis["study_file"]) if isinstance(thesis.get("study_file"), str) else {}
    thesis["study"] = study
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


def ordinal(value: int, lang: str) -> str:
    if lang == "en":
        suffix = "th" if 10 <= value % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
        return f"{value}{suffix}"
    if lang == "pt":
        return f"{value}º"
    return "1er" if value == 1 else f"{value}e"


def giveback_now(thesis: dict[str, Any], latest: float) -> float | None:
    """Share of the first Monday's move that the real has given back at ``latest`` (100 = all of it)."""

    window = next((w for w in (thesis.get("study") or {}).get("elections", []) if w.get("year") == 2026), None)
    if not window:
        return None
    p0, p1 = window["friday_before"][1], window["monday_after"][1]
    return (latest - p1) / (p0 - p1) * 100


def study_placeholders(thesis: dict[str, Any], lang: str) -> dict[str, str]:
    """Figures of the quantitative study (empty when the study file is missing)."""

    study = thesis.get("study") or {}
    if not study:
        return {}
    e = thesis["evidence"]
    elections = {w["year"]: w for w in study["elections"]}
    now, vol, curve, gap = elections[2026], study["volatility"], study["curve"], study["survey_gap"]
    geometry, basket, carry = study["rule_geometry"], study["basket"], study["carry"]
    rows = {row["vertex"]: row for row in curve["rows"]}
    hedge = {item["key"]: item for item in study["hedge"]}
    yoy = {item["key"]: item for item in study["year_on_year"]["rows"]}
    walk, walk_lr = geometry["random_walk"]["diffusion"], geometry["random_walk"]["long_run"]
    market = e["market_5oct"]
    share = study["weights"]["share_of_exports"]
    num, pct, pp = f.num, f.pct, f.pp

    def bp(vertex: str) -> str:
        return num(abs(rows[vertex]["change_bp"]), 0, lang)

    return {
        "mon_move": pct(now["monday_move"], 2, lang, signed=True),
        "mon_move_abs": pct(abs(now["monday_move"]), 2, lang),
        "mon_z": num(abs(now["z"]), 1, lang),
        "event_rank_ord": ordinal(vol["event_rank"], lang),
        "d2y_pp": num(abs(rows["504"]["change_bp"]) / 100, 2, lang), "d1y_bp": bp("252"), "d2y_bp": bp("504"), "d5y_bp": bp("1260"), "d10y_bp": bp("2520"), "d6m_bp": bp("126"),
        "be_share": pct(curve["breakeven_share"], 0, lang),
        "fwd_before": pct(curve["forward_1y1y"]["before"], 2, lang), "fwd_after": pct(curve["forward_1y1y"]["after"], 2, lang),
        "real_2y": pct(curve["real_2y"]["after"], 2, lang), "real_2y_prev": pct(curve["real_2y"]["before"], 2, lang),
        "be_2y_prev": pct(curve["breakeven_2y"]["before"], 2, lang), "be_2y_now": pct(curve["breakeven_2y"]["after"], 2, lang),
        "gap_2y_before": pp(gap["gap_2y_before"], 2, lang), "gap_1y_before": pp(gap["gap_1y_before"], 2, lang),
        "survey_fwd": pct(gap["survey_fwd_1y1y"], 2, lang), "gap_fwd": pp(gap["gap_fwd_after"], 2, lang),
        "idx_entry": num(thesis["rules"]["entry_below"] / now["friday_before"][1] * 100, 1, lang),
        "idx_exit": num(thesis["rules"]["exit_above"] / now["friday_before"][1] * 100, 1, lang),
        "jpm_dist": pct(abs((e["jpmorgan"]["low"] / now["monday_after"][1] - 1) * 100), 1, lang),
        "sugar_now": num(e["sugar"]["value"], 2, lang),
        "gap_2y_now": pp(gap["gap_2y_after"], 2, lang, signed=True), "gap_1y_now": pp(gap["gap_1y_after"], 2, lang, signed=True),
        "gc_2014": pct(elections[2014]["giveback_first_close"], 0, lang), "gc_2018": pct(abs(elections[2018]["giveback_first_close"]), 0, lang),
        "gc_2022": pct(elections[2022]["giveback_first_close"], 0, lang),
        "gb_entry": pct(geometry["giveback"]["entry"], 0, lang), "gb_exit": pct(geometry["giveback"]["exit"], 0, lang),
        "gb_abandon": pct(geometry["giveback"]["abandon"], 0, lang),
        "entry_dist": pct(geometry["distance_pct"]["entry"], 1, lang), "exit_dist": pct(geometry["distance_pct"]["exit"], 1, lang),
        "abandon_dist": pct(geometry["distance_pct"]["abandon"], 1, lang),
        "rw_entry": pct(walk["below_entry"], 0, lang), "rw_entry_lr": pct(walk_lr["below_entry"], 0, lang),
        "rw_exit": pct(walk["above_exit"], 0, lang), "rw_exit_lr": pct(walk_lr["above_exit"], 0, lang),
        "rw_abandon": pct(walk["above_abandon"], 0, lang), "rw_abandon_lr": pct(walk_lr["above_abandon"], 0, lang),
        "runoff_rms": pct(geometry["runoff_rms"], 1, lang), "sessions_to_runoff": str(geometry["sessions"]),
        "vol_ann": pct(vol["diffusion_annual"], 1, lang), "vol_with_jump": pct(vol["with_jump_annual"], 1, lang),
        "vol_bipower": pct(vol["bipower_annual"], 1, lang), "vol_lr": pct(vol["long_run_annual"], 1, lang),
        "jump_share": pct(vol["jump_share"], 0, lang), "event_ret": pct(abs(vol["event_return"]), 2, lang),
        "carry_annual": pct(carry["annual"], 1, lang), "c2v": num(carry["to_vol_diffusion"], 1, lang), "c2v_lr": num(carry["to_vol_long_run"], 1, lang),
        "r2": pct(basket["r2"] * 100, 0, lang), "r2_early": pct(basket["early"]["r2"] * 100, 0, lang), "r2_late": pct(basket["late"]["r2"] * 100, 0, lang),
        "unexplained": pct((1 - basket["r2"]) * 100, 0, lang), "slope": num(basket["slope"], 2, lang), "slope10": num(abs(basket["slope"]) * 10, 1, lang),
        "n_months": str(basket["n"]), "first_month": f.period(basket["months"][0] + "-01", "monthly", lang),
        "last_month": f.period(basket["months"][1] + "-01", "monthly", lang),
        "covered": pct(study["weights"]["covered"], 0, lang), "oil_share": pct(share["brent"], 1, lang),
        "top3_share": pct(share["brent"] + share["soybeans"] + share["iron_ore"], 0, lang),
        "hedge_max": pct(hedge["brent"]["hedge"], 0, lang), "hedge_soy": pct(hedge["soybeans"]["hedge"], 0, lang),
        "corr_oil": num(hedge["brent"]["corr_fx"], 2, lang),
        "fx_12m": pct(abs(study["year_on_year"]["fx_change"]), 1, lang), "sugar_usd_12m": pct(abs(yoy["sugar"]["usd"]), 1, lang),
        "sugar_brl_12m": pct(abs(yoy["sugar"]["brl"]), 1, lang),
        "yoy_base": f.period(study["year_on_year"]["base"], "monthly", lang), "yoy_latest": f.period(study["year_on_year"]["latest"], "monthly", lang),
        "ibov_change": pct(market["ibovespa_change"], 1, lang, signed=True), "ibov_close": num(market["ibovespa"], 0, lang),
        "dollar_close": num(market["usd_close"], 4, lang), "brent_change": pct(abs(market["brent_change"]), 1, lang),
        "petro_change": pct(market["petrobras_change"], 1, lang),
        "di28": pct(market["di_jan28"], 2, lang), "di28_bp": num(abs(market["di_jan28_bp"]), 0, lang),
        "di35": pct(market["di_jan35"], 1, lang), "di35_bp": num(abs(market["di_jan35_bp"]), 0, lang),
    }


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
        "ptax_prev_date": f.day(e["ptax"]["previous_date"], lang, year=False, long=True),
        "ptax_chg": f.pct(ptax_change, 2, lang, signed=True),
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
        "gap_1y": f.pp(sp["one_year_gap"], 2, lang, signed=True),
        "gap_2y": f.pp(sp["two_year_gap"], 2, lang, signed=True),
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
        "vol_h": f.pct(vol["horizon_sd"], 1, lang),
        "vol_h_brl": f.num(vol["horizon_brl"], 2, lang),
        "sessions_h": str(vol["horizon_sessions"]),
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
        # The 5 October thesis, for the review table.
        "prev_entry": f.num(p["entry_below"], 2, lang),
        "prev_abandon": f.num(p["abandon_above"], 2, lang),
        "prev_earliest": f.day(p["earliest_entry"], lang, year=False, long=True),
        "prev_ptax": f.num(q["ptax"], 4, lang),
        "prev_us2y": f.pct(q["us_2y"], 2, lang),
        "prev_br_1y": f.pct(q["br_1y"], 2, lang),
        "prev_br_2y": f.pct(q["br_2y"], 2, lang),
        "prev_gap_2y": f.pp(q["br_2y_gap"], 2, lang),
        "prev_gap_1y": f.pp(q["br_1y_gap"], 2, lang),
        "prev_avg_move": f.pct(q["avg_monday_move"], 1, lang),
        "prev_event_sigma": f.num(q["event_sigma"], 1, lang),
        "prev_horizon_sd": f.pct(q["horizon_sd"], 1, lang),
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
    values.update(study_placeholders(thesis, lang))
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
    base = {"latest": latest, "latest_date": latest_date, "giveback": giveback_now(thesis, latest)}
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
