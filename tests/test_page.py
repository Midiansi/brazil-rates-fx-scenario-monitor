"""The rendered HTML: complete, honest about freshness, robust to bad data."""
from __future__ import annotations

import copy
import re
from datetime import date
from html import unescape

import pytest

from src.page import SECTIONS, render
from src.thesis import rule_status

from conftest import THESIS_DATE


def html(thesis, snapshot, lang="en", today=THESIS_DATE) -> str:
    return "".join(render(lang, thesis, snapshot, today).values())


@pytest.mark.parametrize("lang", ["en", "pt", "fr"])
def test_all_sections_and_no_placeholders(thesis, snapshot, lang) -> None:
    page = html(thesis, snapshot, lang)
    for section in SECTIONS:
        assert f'id="{section}"' in page
    text = unescape(re.sub(r"<[^>]+>", " ", page))
    assert not re.search(r"\{[a-z_0-9]+\}", text)
    assert not re.search(r"\bnan\b|\bNone\b|\bundefined\b", text)


def test_external_links_are_https_and_isolated(thesis, snapshot) -> None:
    page = html(thesis, snapshot)
    links = re.findall(r'<a href="([^"]+)"([^>]*)>', page)
    assert len(links) > 40
    for url, attributes in links:
        if url.startswith("#"):
            continue
        assert url.startswith("https://"), url
        assert 'target="_blank"' in attributes and "noopener" in attributes


def test_fresh_data_shows_no_warning(thesis, snapshot) -> None:
    page = html(thesis, snapshot)
    assert 'class="banner"' not in page
    assert 'class="fresh stale"' not in page


def test_stale_data_is_flagged_not_hidden(thesis, snapshot) -> None:
    later = date(2026, 10, 20)
    page = html(thesis, snapshot, today=later)
    # The refresh has not run for weeks: say so, keep the values with their dates.
    assert "has not run since" in page
    assert 'class="fresh stale"' in page
    assert "5.1792" in page


def test_one_failed_feed_does_not_blank_the_page(thesis, snapshot) -> None:
    broken = copy.deepcopy(snapshot)
    broken["series"]["us_2_year_treasury"] = {"value": "oops"}
    del broken["commodities"]["brent"]
    page = html(thesis, broken)
    assert "13.75%" in page and "5.1792" in page
    assert "Unavailable" in page


@pytest.mark.parametrize("snapshot_value", [{}, None, {"series": None, "commodities": "x", "history": None}])
def test_missing_or_malformed_snapshot_still_renders(thesis, snapshot_value) -> None:
    page = html(thesis, snapshot_value)
    assert "Brazil macro, from policy to price." in page
    assert "Rule check unavailable" in page


def test_missing_thesis_degrades_gracefully(snapshot) -> None:
    blocks = render("en", {}, snapshot, THESIS_DATE)
    assert "Brazil macro" in blocks["hero"]
    assert "body_1" not in blocks


def test_chart_has_both_variants_and_accessible_text(thesis, snapshot) -> None:
    chart = render("en", thesis, snapshot, THESIS_DATE)["chart"]
    assert chart.count("<svg") == 2 and "chart-compact" in chart and "chart-wide" in chart
    assert "<title" in chart and "<desc" in chart
    assert "\n\n" not in chart  # st.markdown would break the SVG on a blank line
    assert "Show the chart data as a table" in chart


# --- the mechanical rule monitor -------------------------------------------------

def with_history(snapshot, closes, us2y=4.8):
    data = copy.deepcopy(snapshot)
    data["history"]["ptax"] = data["history"]["ptax"] + closes
    data["history"]["us_2y"] = data["history"]["us_2y"] + [[closes[-1][0], us2y]]
    return data


def test_monitor_waits_before_the_first_round(thesis, snapshot) -> None:
    assert rule_status(thesis, snapshot, THESIS_DATE)["state"] == "waiting"


def test_monitor_abandons_above_5_30(thesis, snapshot) -> None:
    data = with_history(snapshot, [["2026-09-29", 5.31]])
    result = rule_status(thesis, data, date(2026, 9, 30))
    assert result["state"] == "abandoned" and result["date"] == "2026-09-29"


def test_monitor_needs_two_closes_after_the_vote(thesis, snapshot) -> None:
    # A close below 5.10 before 5 October does not count.
    data = with_history(snapshot, [["2026-10-02", 5.05], ["2026-10-05", 5.08]])
    assert rule_status(thesis, data, date(2026, 10, 5))["state"] == "watching"
    data = with_history(snapshot, [["2026-10-05", 5.08], ["2026-10-06", 5.07]])
    result = rule_status(thesis, data, date(2026, 10, 6))
    assert result["state"] == "entered" and result["date"] == "2026-10-06"


def test_monitor_blocks_entry_when_us_rates_surge(thesis, snapshot) -> None:
    data = with_history(snapshot, [["2026-10-05", 5.08], ["2026-10-06", 5.07]], us2y=5.05)
    assert rule_status(thesis, data, date(2026, 10, 6))["state"] == "watching"


def test_monitor_exit_and_review(thesis, snapshot) -> None:
    exited = with_history(snapshot, [["2026-10-05", 5.08], ["2026-10-06", 5.07], ["2026-10-07", 5.21], ["2026-10-08", 5.22]])
    assert rule_status(thesis, exited, date(2026, 10, 8))["state"] == "exited"
    reviewed = with_history(snapshot, [["2026-10-05", 5.08], ["2026-10-06", 5.07], ["2026-10-07", 4.99]])
    assert rule_status(thesis, reviewed, date(2026, 10, 7))["state"] == "review"


def test_monitor_expires_after_the_review_date(thesis, snapshot) -> None:
    assert rule_status(thesis, snapshot, date(2026, 11, 5))["state"] == "expired"
