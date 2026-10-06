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
    assert "4.9856" in page


def test_one_failed_feed_does_not_blank_the_page(thesis, snapshot) -> None:
    broken = copy.deepcopy(snapshot)
    broken["series"]["us_2_year_treasury"] = {"value": "oops"}
    del broken["commodities"]["brent"]
    page = html(thesis, broken)
    assert "13.75%" in page and "4.9856" in page and "5.2235" in page
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


def charts(thesis, snapshot, lens="quant") -> dict[str, str]:
    return {name: block for name, block in render("en", thesis, snapshot, THESIS_DATE, lens).items() if name.startswith("chart_")}


def test_every_chart_has_both_variants_and_accessible_text(thesis, snapshot) -> None:
    blocks = charts(thesis, snapshot)
    assert len(blocks) == 5  # curve, event paths, commodity scatter, producer prices, PTAX with the decision levels
    for name, chart in blocks.items():
        assert chart.count("<svg") == 2 and "chart-compact" in chart and "chart-wide" in chart, name
        assert "<title" in chart and "<desc" in chart and "<figcaption" in chart, name
        assert "\n\n" not in chart, name  # st.markdown would break the SVG on a blank line
        assert "{" not in re.sub(r"<[^>]+>", "", chart), name  # no unfilled placeholder in figure text
    ptax = next(chart for chart in blocks.values() if "fig-latest" in chart)
    assert "Show the chart data as a table" in ptax


@pytest.mark.parametrize("lang", ["en", "pt", "fr"])
def test_chart_text_is_localized(thesis, snapshot, lang) -> None:
    text = " ".join(render(lang, thesis, snapshot, THESIS_DATE)[name] for name in charts(thesis, snapshot))
    expected = {"en": "Selic 13.75%", "pt": "Selic 13,75%", "fr": "Selic 13,75"}[lang]
    assert expected in text


def test_the_chosen_lens_comes_first(thesis, snapshot) -> None:
    for lens, first, second in (("quant", 'id="quant"', 'id="commodities"'), ("commodities", 'id="commodities"', 'id="quant"'), ("nonsense", 'id="quant"', 'id="commodities"')):
        page = "".join(render("en", thesis, snapshot, THESIS_DATE, lens).values())
        assert page.index(first) < page.index(second), lens
    assert 'class="lens-card first" href="#commodities"' in "".join(render("en", thesis, snapshot, THESIS_DATE, "commodities").values())


def test_study_tables_show_their_figures(thesis, snapshot) -> None:
    page = html(thesis, snapshot)
    for fragment in ("−111 bp", "−4.55%", "+0.35 pp", "pending", "below 2σ", "slope −0.40", "206,912"):
        assert fragment in page, fragment


# --- the mechanical rule monitor -------------------------------------------------

def with_history(snapshot, closes, us2y=4.8):
    data = copy.deepcopy(snapshot)
    data["history"]["ptax"] = data["history"]["ptax"] + closes
    data["history"]["us_2y"] = data["history"]["us_2y"] + [[closes[-1][0], us2y]]
    return data


def test_monitor_waits_for_the_runoff(thesis, snapshot) -> None:
    assert rule_status(thesis, snapshot, THESIS_DATE)["state"] == "waiting"


def test_monitor_abandons_above_5_30(thesis, snapshot) -> None:
    data = with_history(snapshot, [["2026-10-06", 5.31]])
    result = rule_status(thesis, data, date(2026, 10, 7))
    assert result["state"] == "abandoned" and result["date"] == "2026-10-06"


def test_monitor_reports_how_much_of_the_first_monday_move_is_given_back(thesis, snapshot) -> None:
    waiting = rule_status(thesis, snapshot, THESIS_DATE)
    assert waiting["state"] == "waiting" and waiting["giveback"] == pytest.approx(0, abs=0.01)
    half = with_history(snapshot, [["2026-10-06", 5.10]])
    result = rule_status(thesis, half, date(2026, 10, 6))
    assert result["giveback"] == pytest.approx((5.10 - 4.9856) / (5.2235 - 4.9856) * 100, abs=0.01)
    assert "0% of the first-Monday move" in html(thesis, snapshot)
    assert "48% of the first-Monday move" in html(thesis, half, today=date(2026, 10, 6))


def test_monitor_ignores_closes_before_the_runoff_is_over(thesis, snapshot) -> None:
    # A rally on the first Monday does not count, however far it goes.
    rally = [["2026-10-05", 5.02], ["2026-10-06", 5.01], ["2026-10-23", 5.05]]
    data = with_history(snapshot, rally)
    assert rule_status(thesis, data, date(2026, 10, 23))["state"] == "waiting"
    one_close = with_history(snapshot, rally + [["2026-10-26", 5.08]])
    assert rule_status(thesis, one_close, date(2026, 10, 26))["state"] == "watching"


def test_monitor_needs_two_closes_after_the_runoff(thesis, snapshot) -> None:
    data = with_history(snapshot, [["2026-10-26", 5.08], ["2026-10-27", 5.07]])
    result = rule_status(thesis, data, date(2026, 10, 27))
    assert result["state"] == "entered" and result["date"] == "2026-10-27"


def test_monitor_blocks_entry_when_us_rates_surge(thesis, snapshot) -> None:
    data = with_history(snapshot, [["2026-10-26", 5.08], ["2026-10-27", 5.07]], us2y=5.05)
    assert rule_status(thesis, data, date(2026, 10, 27))["state"] == "watching"


def test_monitor_exit_and_review(thesis, snapshot) -> None:
    exited = with_history(snapshot, [["2026-10-26", 5.08], ["2026-10-27", 5.07], ["2026-10-28", 5.23], ["2026-10-29", 5.24]])
    assert rule_status(thesis, exited, date(2026, 10, 29))["state"] == "exited"
    reviewed = with_history(snapshot, [["2026-10-26", 5.08], ["2026-10-27", 5.07], ["2026-10-28", 4.99]])
    assert rule_status(thesis, reviewed, date(2026, 10, 28))["state"] == "review"


def test_monitor_expires_after_the_review_date(thesis, snapshot) -> None:
    assert rule_status(thesis, snapshot, date(2026, 11, 5))["state"] == "expired"
