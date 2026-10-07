"""Scenario integration: UI changes propagate to results without a network call."""
from __future__ import annotations

import json
import re
from datetime import date
from html import unescape

import pytest
from streamlit.testing.v1 import AppTest

from src.lab_content import TEXT
from src.page import render
from conftest import ROOT


def shape(value):
    if isinstance(value, dict):
        return {key: shape(item) for key, item in value.items()}
    if isinstance(value, list):
        return [shape(item) for item in value]
    return type(value).__name__


def markup(app):
    return unescape(" ".join(element.proto.body for element in app.get("html")))


def rerun(app):
    # AppTest treats this single-select segmented control as a list on reruns.
    value = app.button_group[0].value
    app.button_group[0].set_value(value if isinstance(value, list) else [value])
    return app.run()


def test_lab_translations_have_same_structure():
    assert shape(TEXT["en"]) == shape(TEXT["pt"]) == shape(TEXT["fr"])
    for value in TEXT["fr"].values():
        if isinstance(value, str):
            assert not re.search(r" [:;?!%»]", value)


@pytest.mark.parametrize("mode", ["rates", "fx", "producer"])
@pytest.mark.parametrize("lang", ["en", "pt", "fr"])
def test_every_scenario_renders_in_every_language_without_network(mode, lang, no_network):
    app = AppTest.from_file("app.py").run()
    if lang != "en":
        app.button_group[0].set_value([lang.upper()]).run()
    app.radio[0].set_value(mode)
    rerun(app)
    assert not app.exception
    assert TEXT[lang][f'{"rate" if mode == "rates" else mode if mode == "fx" else "producer"}_intro'] in app.caption[0].value
    assert no_network == []
    text = markup(app)
    for label in TEXT[lang][f'{"rate" if mode == "rates" else mode if mode == "fx" else "producer"}_metrics']:
        assert label in text
    assert not re.search(r">\s*(?:nan|None|undefined)\s*<", text)
    assert app.get("download_button")[1].proto.label == TEXT[lang]["download_scenario"]


def test_rate_shock_and_maturity_update_results():
    app = AppTest.from_file("app.py").run()
    price = 1_000_000 / (1 + .126) ** 2
    assert "788,721" in markup(app)
    app.slider[0].set_value(-100)
    rerun(app)
    assert not app.exception
    exact = 1_000_000 / (1 + .116) ** 2 - price
    assert f'{exact:,.0f}' in markup(app)
    app.select_slider[0].set_value(5.0)
    rerun(app)
    assert not app.exception
    assert app.number_input[1].value != .126 * 100  # saved curve value follows tenor


def test_fx_shock_sign_is_correct():
    app = AppTest.from_file("app.py").run()
    app.radio[0].set_value("fx")
    rerun(app)
    app.slider[1].set_value(0.0)
    rerun(app)
    carry = ((1 + .1375) / (1 + .03875)) ** (21 / 252)
    assert f"{(carry - 1) * 100:+.2f}%" in markup(app)
    app.slider[1].set_value(10.0)
    rerun(app)
    assert f"{(carry / 1.10 - 1) * 100:.2f}%".replace("-", "−") in markup(app)
    assert not app.exception


def test_commodity_lens_opens_producer_and_full_hedge_removes_fx_sensitivity():
    app = AppTest.from_file("app.py")
    app.query_params["lens"] = "commodities"
    app.run()
    assert app.radio[0].value == "producer"
    app.slider[2].set_value(100)
    rerun(app)
    base = markup(app)
    app.slider[1].set_value(-10.0)
    rerun(app)
    assert not app.exception
    assert "R$ 4,487,040" in markup(app)  # 90% USD receipts at 4.9856, fully hedged
    assert "R$ 4,487,040" in base


@pytest.mark.parametrize("lang", ["en", "pt", "fr"])
def test_risk_report_summary_and_missing_data_degrade_gracefully(thesis, snapshot, lang):
    report = json.loads((ROOT / "research/risk_2026-10-07.json").read_text())
    blocks = render(lang, thesis, snapshot, date(2026, 10, 7), risk_report=report)
    assert "63 / 2700" in blocks["risk"] and "61 / 2700" in blocks["risk"]
    assert ("&lt;0.001" if lang == "en" else "&lt;0,001") in blocks["risk"]
    for key in ("risk_method", "risk_inputs", "risk_code"):
        assert TEXT[lang][key] in unescape(blocks["risk"])
    broken = render(lang, thesis, snapshot, date(2026, 10, 7), risk_report={})
    assert TEXT[lang]["risk_failure"] in broken["risk"]
    assert broken["body_1"]


@pytest.mark.parametrize("fault", ["latest", "date", "model", "nonfinite", "wrong_type"])
def test_partial_risk_report_cannot_break_market_research(thesis, snapshot, fault):
    report = json.loads((ROOT / "research/risk_2026-10-07.json").read_text())
    if fault == "latest":
        report["latest"] = {"models": {"rolling_normal": {}}}
    elif fault == "date":
        report["evaluation"]["start"] = "invalid"
    elif fault == "model":
        del report["models"][0]["n"]
    elif fault == "nonfinite":
        report["models"][0]["breach_rate_pct"] = float("nan")
    else:
        report = "invalid"
    result = render("en", thesis, snapshot, date(2026, 10, 7), risk_report=report)
    assert TEXT["en"]["risk_failure"] in result["risk"]
    assert "The interest-rate curve" in result["body_1"]
