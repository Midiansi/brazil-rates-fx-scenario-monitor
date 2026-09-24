"""Every number in the thesis must be reproducible from the saved inputs."""
from __future__ import annotations

import json
import math
from datetime import date

import pytest

from src.thesis import monthly_carry, placeholders, survey_path_average

from conftest import ROOT


def closes(frozen, start=None, end=None):
    return [(d, v) for d, v in frozen["history"]["ptax"] if (start is None or d > start) and (end is None or d <= end)]


def test_frozen_inputs_are_the_thesis_date_snapshot(thesis, frozen) -> None:
    assert frozen["history"]["ptax"][-1][0] == thesis["as_of"]
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
    assert rules["review_high"] < rules["entry_below"] < thesis["evidence"]["ptax"]["value"] < rules["exit_above"] < rules["abandon_above"]
    assert rules["entry_us2y_max"] < rules["exit_us2y_above"]
    assert rules["earliest_entry"] > thesis["as_of"] and rules["review_by"] > rules["earliest_entry"]


def test_derived_figures_are_recomputed(thesis) -> None:
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


def test_market_evidence_matches_saved_series(thesis, frozen) -> None:
    ev, series = thesis["evidence"], frozen["series"]
    assert series["us_2_year_treasury"]["value"] == ev["us_2y"]["value"]
    assert series["us_10_year_treasury"]["value"] == ev["us_10y"]["value"]
    assert dict(frozen["history"]["us_2y"])[ev["us_2y"]["previous_date"]] == ev["us_2y"]["previous"]
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


def test_review_verdicts_match_what_happened(thesis, frozen) -> None:
    ev, previous = thesis["evidence"], thesis["previous_rules"]
    verdicts = {item["id"]: item["verdict"] for item in thesis["review"]}
    decisions_as_saved = ev["selic"]["previous"] - ev["selic"]["value"] == 0.25 and ev["fed_range"]["upper"] - ev["fed_range"]["previous_upper"] == 0.25
    assert verdicts["decisions"] == ("confirmed" if decisions_as_saved else "contradicted")
    assert verdicts["gap"] == ("confirmed" if ev["policy_gap"]["previous"] - ev["policy_gap"]["value"] == pytest.approx(0.5) else "contradicted")
    triggered = ev["ptax"]["high_since_previous"] > previous["trigger"] or ev["ptax"]["low_since_previous"] < previous["abandon_before_entry"]
    assert verdicts["trigger"] == ("not_triggered" if not triggered else "triggered")
    # The dollar did rise with U.S. yields, but by less than 2%: only "partly".
    assert ev["us_2y"]["value"] > ev["us_2y"]["previous"] and ev["ptax"]["value"] > ev["ptax"]["previous"]
    assert verdicts["us_yields"] == "partly"


def test_previous_case_is_preserved(thesis) -> None:
    previous = json.loads((ROOT / thesis["previous_file"]).read_text(encoding="utf-8"))
    assert previous["retrieved_at"].startswith("2026-09-13")
    levels = previous["trade_threshold_calculations"]
    assert levels["entry_trigger"]["value"] == thesis["previous_rules"]["trigger"]
    assert levels["invalidation_reference"]["value"] == thesis["previous_rules"]["exit_after_entry"]


def test_calendar_is_forward_looking(thesis) -> None:
    dates = [item["date"] for item in thesis["calendar"]]
    assert dates == sorted(dates) and dates[0] > thesis["as_of"]


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
        assert values["ptax"] == "5.1792" and values["selic"] == "13.75%"
    else:
        assert values["ptax"] == "5,1792" and values["selic"].startswith("13,75")
