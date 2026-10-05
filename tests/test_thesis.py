"""Every number in the thesis must be reproducible from the saved inputs."""
from __future__ import annotations

import json
import math
from datetime import date, timedelta

import pytest

from src.thesis import first_round_reaction, monthly_carry, placeholders, poll_margin_miss, survey_path_average, vote_shares, volatility

from conftest import ROOT


def closes(frozen, start=None, end=None):
    return [(d, v) for d, v in frozen["history"]["ptax"] if (start is None or d > start) and (end is None or d <= end)]


def test_frozen_inputs_are_the_thesis_date_snapshot(thesis, frozen) -> None:
    # Markets reopen on the thesis date, so the data is the last session before it.
    assert thesis["data_as_of"] < thesis["as_of"]
    assert frozen["history"]["ptax"][-1][0] == thesis["data_as_of"]
    assert frozen["series"]["ptax_usd_brl_midpoint"]["value"] == thesis["evidence"]["ptax"]["value"]


def test_policy_facts_match_official_series(thesis, frozen) -> None:
    ev, series = thesis["evidence"], frozen["series"]
    assert series["selic_target"]["value"] == ev["selic"]["value"] == 13.75
    assert series["selic_target"]["effective_since"] == ev["selic"]["effective"]
    assert (series["fed_target_range"]["lower"], series["fed_target_range"]["upper"]) == (ev["fed_range"]["lower"], ev["fed_range"]["upper"])
    fed_mid = (ev["fed_range"]["lower"] + ev["fed_range"]["upper"]) / 2
    assert ev["policy_gap"]["value"] == pytest.approx(ev["selic"]["value"] - fed_mid)
    assert ev["policy_gap"]["previous"] == pytest.approx(ev["selic"]["previous"] - (ev["fed_range"]["previous_lower"] + ev["fed_range"]["previous_upper"]) / 2)
    assert series["brazil_us_policy_differential"]["value"] == pytest.approx(ev["policy_gap"]["value"])


def test_ptax_evidence_matches_history(thesis, frozen) -> None:
    ev = thesis["evidence"]["ptax"]
    history = dict(frozen["history"]["ptax"])
    assert history[ev["previous_date"]] == pytest.approx(ev["previous"], abs=1e-4)
    since = closes(frozen, start=ev["previous_date"])
    assert max(v for _, v in since) == pytest.approx(ev["high_since_previous"], abs=1e-4)
    assert min(v for _, v in since) == pytest.approx(ev["low_since_previous"], abs=1e-4)
    assert max(since, key=lambda item: item[1])[0] == ev["high_date"]
    assert min(since, key=lambda item: item[1])[0] == ev["low_date"]
    everything = frozen["history"]["ptax"]
    assert max(v for _, v in everything) == pytest.approx(ev["four_month_high"], abs=1e-4)
    assert min(v for _, v in everything) == pytest.approx(ev["four_month_low"], abs=1e-4)
    assert max(everything, key=lambda item: item[1])[0] == ev["four_month_high_date"]
    assert min(everything, key=lambda item: item[1])[0] == ev["four_month_low_date"]


def test_decision_levels_follow_from_the_range(thesis, frozen) -> None:
    rules = thesis["rules"]
    recent = [v for _, v in frozen["history"]["ptax"][-20:]]
    assert rules["range"]["low"] == pytest.approx(min(recent), abs=1e-4)
    assert rules["range"]["high"] == pytest.approx(max(recent), abs=1e-4)
    assert rules["range"]["width"] == pytest.approx(max(recent) - min(recent), abs=1e-4)
    measured = rules["range"]["low"] - rules["range"]["width"]
    assert rules["review_low"] == math.floor(measured * 100) / 100
    # entry near the bottom of the range; exit at its top; abandonment above the four-month high
    assert rules["range"]["low"] < rules["entry_below"] < rules["range"]["midpoint"]
    assert rules["exit_above"] == round(rules["range"]["high"], 2)
    assert rules["abandon_above"] > thesis["evidence"]["ptax"]["four_month_high"]
    # The last close can sit above the exit level: exit only applies once a position exists.
    assert rules["review_high"] < rules["entry_below"] < thesis["evidence"]["ptax"]["value"] < rules["abandon_above"]
    assert rules["entry_us2y_max"] < rules["exit_us2y_above"]
    assert rules["entry_closes"] == rules["exit_closes"] == 2


def test_no_entry_before_the_vote_is_over(thesis) -> None:
    rules, runoff = thesis["rules"], date.fromisoformat(thesis["election"]["runoff"])
    first_close = runoff + timedelta(days=1)  # the runoff is a Sunday; PTAX next prints on Monday
    assert runoff.weekday() == 6 and first_close.weekday() == 0
    assert rules["earliest_entry"] == first_close.isoformat()
    assert rules["earliest_entry"] > thesis["as_of"] and rules["review_by"] > rules["earliest_entry"]


def test_derived_figures_are_recomputed(thesis, frozen) -> None:
    ev = thesis["evidence"]
    focus = {int(year): value for year, value in ev["focus_selic"].items() if year.isdigit()}
    start = date.fromisoformat(thesis["as_of"])
    one = survey_path_average(ev["selic"]["value"], focus, start, 1)
    two = survey_path_average(ev["selic"]["value"], focus, start, 2)
    sp = ev["survey_path_average"]
    assert one == pytest.approx(sp["one_year"], abs=0.01)
    assert two == pytest.approx(sp["two_year"], abs=0.01)
    assert sp["one_year_gap"] == pytest.approx(ev["br_1y"]["value"] - one, abs=0.005)
    assert sp["two_year_gap"] == pytest.approx(ev["br_2y"]["value"] - two, abs=0.005)
    fed_mid = (ev["fed_range"]["lower"] + ev["fed_range"]["upper"]) / 2
    assert monthly_carry(ev["selic"]["value"], fed_mid) == pytest.approx(ev["carry_per_month"]["value"], abs=0.005)


def test_first_round_numbers_are_recomputed(thesis, frozen) -> None:
    ev, election = thesis["evidence"], frozen["election"]
    shares = vote_shares(election["valid_votes"])
    first = ev["election_first_round"]
    assert election["reporting_pct"] == first["reporting_pct"] < 100  # the count was not final: the page says so
    assert (election["date"], election["runoff_date"]) == (first["date"], thesis["election"]["runoff"])
    assert shares["leader"] == pytest.approx(first["flavio"], abs=0.005)
    assert shares["trailer"] == pytest.approx(first["lula"], abs=0.005)
    assert shares["others"] == pytest.approx(first["others"], abs=0.005)
    assert shares["margin_pts"] == pytest.approx(first["margin_pts"], abs=0.005)
    assert shares["margin_votes"] == first["margin_votes"]
    assert max(shares["leader"], shares["trailer"]) < 50  # hence a runoff
    arithmetic = ev["runoff_arithmetic"]
    assert shares["leader_needs"] == pytest.approx(arithmetic["flavio_needs"], abs=0.05)
    assert shares["trailer_needs"] == pytest.approx(arithmetic["lula_needs"], abs=0.05)
    assert arithmetic["flavio_needs"] + arithmetic["lula_needs"] == pytest.approx(100, abs=0.1)


def test_poll_miss_is_recomputed(thesis, frozen) -> None:
    polls, result = thesis["evidence"]["final_polls"], vote_shares(frozen["election"]["valid_votes"])
    misses = []
    for name in ("datafolha", "quaest"):
        saved, shown = frozen["polls"][name], polls[name]
        assert (shown["lula"], shown["flavio"]) == (saved["valid_votes"]["lula"], saved["valid_votes"]["flavio"])
        assert (shown["runoff_lula"], shown["runoff_flavio"]) == (saved["runoff_total_votes"]["lula"], saved["runoff_total_votes"]["flavio"])
        miss = poll_margin_miss(saved["valid_votes"], result["margin_pts"])
        assert miss == pytest.approx(shown["margin_miss"], abs=0.01)
        misses.append(miss)
    assert all(miss > 0 for miss in misses)  # both leaned the same wrong way
    assert sum(misses) / 2 == pytest.approx(polls["average_miss"], abs=0.01)


def test_first_round_reactions_are_recomputed(thesis, frozen) -> None:
    saved = thesis["evidence"]["first_round_reactions"]
    windows = frozen["event_study"]["windows"]
    assert [w["year"] for w in windows] == [item["year"] for item in saved["windows"]] == [2014, 2018, 2022]
    moves = []
    for window, shown in zip(windows, saved["windows"]):
        reaction = first_round_reaction(window)
        assert reaction["monday_move"] == pytest.approx(shown["monday_move"], abs=0.01)
        assert reaction["giveback"] == pytest.approx(shown["giveback"], abs=0.1)
        assert reaction["monday_move"] < 0  # USD/BRL fell: the real rallied
        moves.append(reaction["monday_move"])
        # Friday before the vote, Monday after, Friday before the runoff.
        assert date.fromisoformat(window["closes"]["monday_after"][0]).weekday() == 0
        assert window["closes"]["friday_before"][0] < window["first_round"] < window["closes"]["monday_after"][0] < window["closes"]["friday_before_runoff"][0] < window["runoff"]
    assert sum(moves) / 3 == pytest.approx(saved["average_move"], abs=0.01)
    # Two rallies faded, one carried on: the wording on the page depends on it.
    assert [item["giveback"] > 50 for item in saved["windows"]] == [True, False, True]


def test_levels_are_expressed_in_volatility_units(thesis, frozen) -> None:
    ev, rules = thesis["evidence"], thesis["rules"]
    series = [v for _, v in frozen["history"]["ptax"]]
    saved = ev["volatility"]
    vol = volatility(series, saved["sessions"], saved["horizon_sessions"])
    assert vol["daily_sd"] == pytest.approx(saved["daily_sd"], abs=0.001)
    assert vol["horizon_sd"] == pytest.approx(saved["horizon_sd"], abs=0.01)
    assert vol["annualised"] == pytest.approx(saved["annualised"], abs=0.1)
    last = series[-1]
    assert saved["horizon_brl"] == pytest.approx(last * vol["horizon_sd"] / 100, abs=0.001)
    entry = (rules["entry_below"] / last - 1) * 100
    abandon = (rules["abandon_above"] / last - 1) * 100
    assert entry == pytest.approx(saved["entry_distance"], abs=0.01) and abandon == pytest.approx(saved["abandon_distance"], abs=0.01)
    assert abs(entry) / vol["horizon_sd"] == pytest.approx(saved["entry_sigma"], abs=0.01)
    assert abandon / vol["horizon_sd"] == pytest.approx(saved["abandon_sigma"], abs=0.01)
    typical = abs(ev["first_round_reactions"]["average_move"])
    assert typical / vol["horizon_sd"] == pytest.approx(saved["event_sigma"], abs=0.02)
    # The sessions between the thesis date and the Friday before the runoff.
    day, sessions = date.fromisoformat(thesis["as_of"]), 0
    while day < date.fromisoformat(thesis["election"]["runoff"]):
        sessions += day.weekday() < 5
        day += timedelta(days=1)
    assert sessions == saved["horizon_sessions"]


def test_market_evidence_matches_saved_series(thesis, frozen) -> None:
    ev, series = thesis["evidence"], frozen["series"]
    assert series["us_2_year_treasury"]["value"] == ev["us_2y"]["value"]
    assert series["us_10_year_treasury"]["value"] == ev["us_10y"]["value"]
    us2y = dict(frozen["history"]["us_2y"])
    assert us2y[ev["us_2y"]["previous_date"]] == ev["us_2y"]["previous"]
    since = [(d, v) for d, v in frozen["history"]["us_2y"] if d > ev["us_2y"]["previous_date"]]
    assert max(since, key=lambda item: item[1]) == (ev["us_2y"]["high_date"], ev["us_2y"]["high_since_previous"])
    brent = dict(frozen["history"]["brent"])
    assert brent[ev["brent_spot"]["date"]] == ev["brent_spot"]["value"]
    assert brent[ev["brent_spot"]["peak_date"]] == ev["brent_spot"]["peak"] == max(brent.values())
    assert brent[ev["brent_spot"]["previous_date"]] == ev["brent_spot"]["previous"]
    for key in ("focus_selic", "focus_ipca", "focus_fx"):
        saved = series[key]["values_by_reference_year"]
        for year in ("2026", "2027"):
            assert saved[year] == pytest.approx(ev[key][year], abs=0.005)
    for key in ("iron_ore", "soybeans", "sugar"):
        assert frozen["commodities"][key]["latest"] == pytest.approx(ev[key]["value"], abs=0.01)
    curve = frozen["anbima_ettj"]
    assert curve["date"] == ev["br_2y"]["date"]
    assert curve["fixed_rate"]["252"] == ev["br_1y"]["value"] and curve["fixed_rate"]["504"] == ev["br_2y"]["value"]
    assert curve["implied_inflation"]["504"] == ev["br_2y_breakeven"]["value"]


def test_review_verdicts_match_what_happened(thesis, frozen) -> None:
    ev, rules, before = thesis["evidence"], thesis["previous_rules"], thesis["previous_evidence"]
    verdicts = {item["id"]: item["verdict"] for item in thesis["review"]}
    since = closes(frozen, start=thesis["previous_id"])
    # The 24 September rules: nothing could trigger before the vote, and the drop level was never hit.
    assert all(d < rules["earliest_entry"] for d, _ in since)
    assert max(v for _, v in since) < rules["abandon_above"]
    assert verdicts["trigger"] == "not_triggered"
    # Polls had Lula ahead in the first round; Flávio finished first, in a runoff.
    first = ev["election_first_round"]
    assert before["poll_lula"] > before["poll_flavio"] and first["flavio"] > first["lula"] and max(first["flavio"], first["lula"]) < 50
    assert verdicts["election"] == "partly"
    # The gap did not move and the dollar rose: the cushion held the range without strengthening the real.
    assert ev["policy_gap"]["value"] == before["policy_gap"] and ev["ptax"]["value"] > before["ptax"]
    assert verdicts["cushion"] == "partly"
    # The two-year premium over the economists' path stayed about where it was.
    assert abs(ev["survey_path_average"]["two_year_gap"] - before["br_2y_gap"]) < 0.25
    assert verdicts["premium"] == "unresolved"
    assert ev["us_2y"]["high_since_previous"] <= rules["entry_us2y_max"]
    assert verdicts["us_yields"] == "confirmed"
    assert set(verdicts) == {"trigger", "election", "cushion", "premium", "us_yields"}


def test_previous_case_is_preserved(thesis) -> None:
    previous = json.loads((ROOT / thesis["previous_file"]).read_text(encoding="utf-8"))
    assert previous["id"] == previous["as_of"] == thesis["previous_id"]
    for key in ("earliest_entry", "entry_below", "abandon_above", "exit_above", "entry_us2y_max"):
        assert previous["rules"][key] == thesis["previous_rules"][key], key
    saved, then = thesis["previous_evidence"], previous["evidence"]
    assert (saved["poll_lula"], saved["poll_flavio"], saved["poll_margin"]) == (then["poll_first_round"]["lula"], then["poll_first_round"]["flavio"], then["poll_first_round"]["margin"])
    assert saved["ptax"] == then["ptax"]["value"] and saved["us_2y"] == then["us_2y"]["value"]
    assert saved["br_2y"] == then["br_2y"]["value"] and saved["br_2y_gap"] == pytest.approx(then["survey_path_average"]["two_year_gap"], abs=0.005)
    assert saved["brent"] == then["brent_spot"]["value"] and saved["policy_gap"] == then["policy_gap"]["value"]
    assert (ROOT / previous["inputs_file"]).is_file()
    assert (ROOT / previous["previous_file"]).is_file()


def test_calendar_is_forward_looking(thesis) -> None:
    dates = [item["date"] for item in thesis["calendar"]]
    assert dates == sorted(dates) and dates[0] > thesis["as_of"]
    events = {item["event"]: item["date"] for item in thesis["calendar"]}
    assert events["election_runoff"] == thesis["election"]["runoff"]
    assert thesis["election"]["first_round"] < thesis["as_of"]


def test_sources_are_dated_https_links(thesis) -> None:
    for key, source in thesis["sources"].items():
        assert source["url"].startswith("https://"), key
        date.fromisoformat(source["date"])
    referenced = {value["source"] for value in thesis["evidence"].values() if isinstance(value, dict) and "source" in value}
    assert referenced <= set(thesis["sources"])


@pytest.mark.parametrize("lang", ["en", "pt", "fr"])
def test_placeholders_use_local_decimal_marks(thesis, lang) -> None:
    values = placeholders(thesis, lang)
    if lang == "en":
        assert values["ptax"] == "5.2235" and values["selic"] == "13.75%" and values["fl_share"] == "47.1%"
    else:
        assert values["ptax"] == "5,2235" and values["selic"].startswith("13,75") and values["fl_share"].startswith("47,1")
