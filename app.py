from __future__ import annotations

import json
import importlib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st

from src import localization as _localization

# Streamlit reruns app.py in a long-lived process.  After a deployment that
# adds translation tables, Python can otherwise retain the older imported
# module and raise ImportError until the container is manually rebooted.
if not hasattr(_localization, "COMMODITY_PT"):
    _localization = importlib.reload(_localization)

COMMODITY_FR = _localization.COMMODITY_FR
SCENARIO_FR = _localization.SCENARIO_FR
SERIES_FR = _localization.SERIES_FR
SOURCE_FR = _localization.SOURCE_FR
TRADE_FR = _localization.TRADE_FR
UI_FR = _localization.UI_FR
COMMODITY_PT = _localization.COMMODITY_PT
SCENARIO_PT = _localization.SCENARIO_PT
SERIES_PT = _localization.SERIES_PT
SOURCE_PT = _localization.SOURCE_PT
TRADE_PT = _localization.TRADE_PT
from src.editorial import copy_for, format_period, snapshot_age, sanitize_snapshot, safe_url, source_url_for


ROOT = Path(__file__).resolve().parent


def read_json(name: str) -> dict[str, Any]:
    """Read a versioned local snapshot without making the page depend on a network."""

    try:
        with (ROOT / "research" / name).open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError, TypeError):
        return {}
    return sanitize_snapshot(name, payload)


def signed(value: float, digits: int = 1) -> str:
    return f"{value:+.{digits}f}"


def snapshot_label(value: str, portuguese: bool = False, french: bool = False) -> str:
    """Turn an ISO snapshot timestamp into a compact, human-readable label."""

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(ZoneInfo("America/Sao_Paulo"))
    except (TypeError, ValueError):
        return value or ("indisponível" if portuguese else "indisponible" if french else "unavailable")
    if portuguese:
        months = (
            "jan",
            "fev",
            "mar",
            "abr",
            "mai",
            "jun",
            "jul",
            "ago",
            "set",
            "out",
            "nov",
            "dez",
        )
        return f"{parsed.day} {months[parsed.month - 1]} {parsed.year}, {parsed:%H:%M} BRT"
    if french:
        months = (
            "janv.",
            "févr.",
            "mars",
            "avr.",
            "mai",
            "juin",
            "juil.",
            "août",
            "sept.",
            "oct.",
            "nov.",
            "déc.",
        )
        return f"{parsed.day} {months[parsed.month - 1]} {parsed.year}, {parsed:%H:%M} BRT"
    return parsed.strftime("%d %b %Y, %H:%M BRT").lstrip("0")


def bounded_position(value: float, low: float, high: float) -> float:
    """Return a safe percentage position for an observation inside a range."""

    if high <= low:
        return 50.0
    return max(0.0, min(100.0, (value - low) / (high - low) * 100))


st.set_page_config(
    page_title="Brazil Macro | Romeo Mugnier de Almeida",
    page_icon="🇧🇷",
    layout="wide",
)
st.markdown(
    """
    <style>
    :root {
        --macro-bg: #07131d;
        --macro-panel: #0c1d29;
        --macro-panel-2: #102634;
        --macro-ink: #edf4f2;
        --macro-muted: #8ea5ae;
        --macro-line: rgba(148, 178, 184, .18);
        --macro-teal: #35c3ad;
        --macro-copper: #e58a54;
        --macro-sand: #d8c9a7;
    }
    .stApp {
        background:
            radial-gradient(circle at 84% 8%, rgba(53, 195, 173, .075), transparent 26rem),
            var(--macro-bg);
        color: var(--macro-ink);
    }
    .stApp::before {
        content: "";
        position: fixed;
        inset: 0 0 auto 0;
        height: 3px;
        background: linear-gradient(90deg, var(--macro-teal) 0 58%, var(--macro-copper) 58% 76%, var(--macro-sand) 76%);
        z-index: 99999;
    }
    [data-testid="stHeader"] {background: transparent;}
    [data-testid="stToolbar"] {visibility: hidden;}
    .block-container {max-width: 1160px; padding-top: 1.4rem; padding-bottom: 5rem;}
    html, body, .stApp {font-family: "Avenir Next", "Helvetica Neue", Arial, sans-serif;}
    .material-symbols-rounded, [data-testid="stIconMaterial"] {
        font-family: "Material Symbols Rounded" !important;
        font-weight: normal !important;
        font-style: normal !important;
    }
    h1 {
        max-width: 900px;
        color: var(--macro-ink) !important;
        font-size: clamp(2.5rem, 4.8vw, 4.2rem) !important;
        line-height: 1.08 !important;
        letter-spacing: -.045em !important;
        font-weight: 640 !important;
        margin: .35rem 0 1.25rem !important;
    }
    h2 {
        color: var(--macro-ink) !important;
        margin-top: 3rem !important;
        padding-bottom: .7rem;
        border-bottom: 1px solid var(--macro-line);
        font-size: 1.8rem !important;
        letter-spacing: -.035em !important;
        font-weight: 570 !important;
    }
    h3 {color: var(--macro-ink) !important; letter-spacing: -.025em !important; font-weight: 570 !important; margin-top: 1.6rem !important;}
    p {line-height: 1.62;}
    a {color: var(--macro-teal) !important; text-underline-offset: 3px;}
    a:focus-visible, button:focus-visible {outline: 2px solid var(--macro-teal) !important; outline-offset: 3px;}
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {color: #b5c7cc !important;}
    .macro-kicker, .brief-label, .commodity-label, .trade-kicker {
        color: var(--macro-teal);
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: .72rem;
        font-weight: 650;
        letter-spacing: .13em;
        text-transform: uppercase;
    }
    .identity-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1.5rem;
        padding-bottom: 1.2rem;
        margin-bottom: 1.2rem;
        border-bottom: 1px solid var(--macro-line);
        color: var(--macro-muted);
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: .7rem;
        letter-spacing: .09em;
        text-transform: uppercase;
    }
    .identity-name {color: var(--macro-ink); font-weight: 720; margin-right: .7rem;}
    .identity-links {display: flex; gap: 1rem; white-space: nowrap;}
    .identity-links a {text-decoration: none;}
    .macro-intro {
        max-width: 760px;
        color: #bccbd0;
        font-size: 1.16rem;
        line-height: 1.6;
        margin-bottom: .75rem;
    }
    .market-strip {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        margin: 2.4rem 0 .5rem;
        border: 1px solid var(--macro-line);
        border-radius: 16px;
        overflow: hidden;
    }
    .market-cell {padding: 1rem 1.1rem 1.15rem; border-right: 1px solid var(--macro-line);}
    .market-cell:last-child {border-right: 0;}
    .market-label {
        color: var(--macro-muted);
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: .68rem;
        letter-spacing: .1em;
        text-transform: uppercase;
    }
    .market-value {font-size: 1.65rem; font-weight: 620; letter-spacing: -.035em; margin-top: .2rem;}
    .market-note {color: var(--macro-muted); font-size: .76rem; margin-top: .15rem;}
    .decision-grid, .brief-grid, .commodity-grid, .scenario-strip, .trade-detail-grid,
    .proof-grid, .process-grid, .pricing-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: .75rem;
        background: transparent;
        border: 0;
    }
    .decision-grid {grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1.15rem; margin: 1.25rem 0 2.25rem;}
    .decision-card {position: relative; background: var(--macro-panel); border: 1px solid var(--macro-line); border-radius: 14px; padding: 1.25rem 1.3rem 1.4rem; min-height: 174px;}
    .decision-card:not(:last-child)::after {
        content: "→";
        position: absolute;
        right: -.92rem;
        top: 46%;
        z-index: 3;
        width: 1.65rem;
        height: 1.65rem;
        border: 1px solid var(--macro-line);
        border-radius: 50%;
        background: var(--macro-bg);
        color: var(--macro-teal);
        text-align: center;
        line-height: 1.55rem;
        font-size: 1rem;
    }
    .decision-card.signal {box-shadow: inset 0 3px 0 var(--macro-copper);}
    .decision-number {
        color: var(--macro-sand);
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: .78rem;
        margin: .65rem 0 .45rem;
    }
    .decision-copy {color: #d8e4e2; font-size: .94rem; line-height: 1.52;}
    .brief-card, .commodity-card, .trade-detail {background: var(--macro-panel); border: 1px solid var(--macro-line); border-radius: 14px; padding: 1.35rem 1.45rem 1.5rem;}
    .brief-grid, .commodity-grid, .pricing-grid {margin: 1.25rem 0 2.1rem;}
    .brief-copy {font-size: 1rem; line-height: 1.55; margin-top: .7rem; color: #dbe6e4;}
    .commodity-card {min-height: 210px;}
    .commodity-title {font-size: 1.35rem; font-weight: 610; letter-spacing: -.025em; margin: .45rem 0 .25rem;}
    .commodity-move {color: var(--macro-sand); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .82rem;}
    .commodity-meta {color: var(--macro-muted); font-size: .76rem; margin: .55rem 0 1rem;}
    .commodity-copy {color: #c3d1d3; line-height: 1.55;}
    .commodity-crosscheck {
        margin: .25rem 0 2.4rem;
        padding: 1.45rem 1.55rem 1.55rem;
        border: 1px solid var(--macro-line);
        border-left: 4px solid var(--macro-teal);
        border-radius: 16px;
        background: linear-gradient(110deg, rgba(53, 195, 173, .07), rgba(12, 29, 41, .76));
    }
    .crosscheck-title {font-size: 1.2rem; font-weight: 650; letter-spacing: -.025em; margin: .3rem 0 .45rem;}
    .crosscheck-intro {color: #d4dfde; line-height: 1.55; max-width: 900px;}
    .crosscheck-grid {display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .8rem; margin: 1.15rem 0;}
    .crosscheck-cell {padding: .9rem 1rem; border: 1px solid var(--macro-line); border-radius: 12px; background: rgba(7, 19, 29, .42);}
    .crosscheck-label {color: var(--macro-sand); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .69rem; letter-spacing: .08em; text-transform: uppercase;}
    .crosscheck-copy {color: #bdcbcd; font-size: .86rem; line-height: 1.5; margin-top: .45rem;}
    .crosscheck-verdict {color: var(--macro-ink); line-height: 1.55; padding-top: .9rem; border-top: 1px solid var(--macro-line);}
    .path-table {
        display: grid;
        grid-template-columns: 1.05fr repeat(5, minmax(0, 1fr));
        border: 1px solid var(--macro-line);
        background: var(--macro-line);
        gap: 1px;
        margin: 1rem 0 .75rem;
    }
    .path-cell {background: var(--macro-panel); padding: .8rem .85rem; text-align: center;}
    .path-cell.label {text-align: left; color: var(--macro-muted); font-size: .78rem;}
    .path-cell.year {color: var(--macro-muted); font-size: .72rem; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;}
    .path-cell.value {color: var(--macro-ink); font-weight: 640;}
    .pricing-grid {margin-top: 1rem;}
    .pricing-card {background: var(--macro-panel); border: 1px solid var(--macro-line); border-radius: 14px; padding: 1.2rem 1.35rem;}
    .pricing-value {font-size: 1.45rem; font-weight: 650; margin: .45rem 0 .3rem; letter-spacing: -.03em;}
    .pricing-copy {color: var(--macro-muted); font-size: .82rem; line-height: 1.48;}
    .range-box {background: var(--macro-panel); border: 1px solid var(--macro-line); border-radius: 14px; padding: 1.35rem 1.5rem 1.15rem;}
    .range-track {height: 6px; background: #27404b; position: relative; margin: 2rem .15rem .8rem;}
    .range-fill {position: absolute; inset: 0 auto 0 0; background: var(--macro-teal);}
    .range-dot {position: absolute; top: 50%; width: 16px; height: 16px; border-radius: 50%; background: var(--macro-ink); border: 4px solid var(--macro-teal); transform: translate(-50%, -50%);}
    .range-trigger {position: absolute; top: -8px; height: 22px; width: 2px; background: var(--macro-copper);}
    .range-labels {display: flex; justify-content: space-between; color: var(--macro-muted); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .7rem;}
    .range-caption {color: #c5d2d3; font-size: .87rem; line-height: 1.5; margin-top: 1rem;}
    .scenario-strip {grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 1.35rem 0 2rem;}
    .scenario-card {background: var(--macro-panel); border: 1px solid var(--macro-line); border-radius: 14px; padding: 1.15rem 1.25rem 1.3rem;}
    .scenario-card.base {background: var(--macro-panel-2); box-shadow: inset 0 3px 0 var(--macro-teal);}
    .scenario-name {font-weight: 620; letter-spacing: -.02em; margin-bottom: .65rem;}
    .scenario-direction {color: #d2dfdd; font-size: .88rem; line-height: 1.45;}
    .scenario-diff {color: var(--macro-muted); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .72rem; margin-top: .65rem;}
    .trade-card {
        border-left: 4px solid var(--macro-copper);
        background: linear-gradient(105deg, rgba(229, 138, 84, .09), rgba(12, 29, 41, .72));
        padding: 1.35rem 1.55rem 1.5rem;
        margin: .5rem 0 1px;
        border-radius: 14px;
    }
    .trade-title {font-size: 1.65rem; font-weight: 620; letter-spacing: -.035em; margin: .35rem 0 .6rem;}
    .trade-thesis {max-width: 920px; color: #d5e1df; font-size: 1.02rem; line-height: 1.58;}
    .trade-detail-grid {margin: 1.15rem 0 1.4rem;}
    .trade-detail strong {display: block; color: var(--macro-sand); margin-bottom: .5rem; font-size: .8rem; letter-spacing: .04em; text-transform: uppercase;}
    .trade-detail {color: #bac9cc; font-size: .9rem; line-height: 1.55;}
    .evidence-list {margin: .4rem 0 0; padding-left: 1.15rem; color: #c8d5d6;}
    .evidence-list li {margin-bottom: .65rem; line-height: 1.5;}
    .mind-change {border: 1px solid var(--macro-line); border-left: 4px solid var(--macro-teal); background: rgba(53, 195, 173, .045); padding: 1rem 1.2rem; margin: 1rem 0 1.4rem; color: #cbd8d8; line-height: 1.55;}
    .proof-grid {grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 1.4rem 0 2rem;}
    .proof-card {background: var(--macro-panel); border: 1px solid var(--macro-line); border-radius: 14px; padding: 1rem 1.05rem 1.1rem;}
    .proof-value {font-size: 1.45rem; color: var(--macro-sand); font-weight: 650;}
    .proof-label {color: var(--macro-muted); font-size: .72rem; line-height: 1.35; margin-top: .25rem;}
    .process-grid {grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 0 0 2.2rem;}
    .process-card {background: var(--macro-panel); border: 1px solid var(--macro-line); border-radius: 14px; padding: 1.25rem 1.35rem 1.4rem;}
    .process-step {color: var(--macro-teal); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .68rem; letter-spacing: .1em; text-transform: uppercase;}
    .process-title {font-size: 1.05rem; font-weight: 620; margin: .5rem 0;}
    .process-copy {color: var(--macro-muted); font-size: .82rem; line-height: 1.5;}
    .builder-card {
        display: grid;
        grid-template-columns: 1.7fr 1fr;
        gap: 2rem;
        align-items: end;
        padding: 1.6rem 1.7rem;
        border: 1px solid var(--macro-line);
        background: linear-gradient(120deg, rgba(53, 195, 173, .07), rgba(12, 29, 41, .8));
        margin: .5rem 0 2rem;
        border-radius: 16px;
    }
    .builder-name {font-size: 1.55rem; font-weight: 650; letter-spacing: -.035em; margin: .35rem 0 .55rem;}
    .builder-copy {color: #c8d5d6; line-height: 1.56; max-width: 720px;}
    .builder-links {display: flex; justify-content: flex-end; gap: .7rem; flex-wrap: wrap;}
    .builder-links a {border: 1px solid var(--macro-line); padding: .62rem .8rem; text-decoration: none; font-size: .8rem;}
    [data-testid="stDataFrame"] {border: 1px solid var(--macro-line); border-radius: 14px; overflow: hidden; background: var(--macro-panel);}
    [data-testid="stExpander"] {border: 1px solid var(--macro-line); border-radius: 12px; background: rgba(12, 29, 41, .55); margin: .75rem 0;}
    [data-testid="stDownloadButton"] {margin: 1.25rem 0 2.6rem;}
    [data-testid="stDownloadButton"] button {
        background: var(--macro-teal);
        color: #04120f;
        border: 0;
        border-radius: 10px;
        font-weight: 700;
        min-height: 2.8rem;
    }
    [data-testid="stDownloadButton"] button:hover {background: #55d3bf; color: #04120f;}
    hr {border-color: var(--macro-line) !important;}
    @media (max-width: 760px) {
        .block-container {padding-top: 2rem; padding-left: 1.2rem; padding-right: 1.2rem;}
        h1 {font-size: clamp(1.9rem, 8.5vw, 2.4rem) !important;}
        .identity-bar {align-items: flex-start; flex-direction: column; gap: .7rem; margin-bottom: .7rem;}
        .market-strip, .decision-grid, .brief-grid, .commodity-grid, .scenario-strip,
        .trade-detail-grid, .pricing-grid, .proof-grid, .process-grid, .builder-card,
        .crosscheck-grid {grid-template-columns: 1fr;}
        .path-table {grid-template-columns: 1fr repeat(5, minmax(3rem, 1fr)); overflow-x: auto;}
        .path-cell {padding: .65rem .35rem; font-size: .78rem;}
        .builder-links {justify-content: flex-start;}
        .market-cell {border-right: 0; border-bottom: 1px solid var(--macro-line);}
        .decision-card:not(:last-child)::after {content: "↓"; right: auto; left: 50%; top: auto; bottom: -1.42rem; transform: translateX(-50%);}
        .market-cell:last-child {border-bottom: 0;}
        .commodity-card {min-height: 0;}
    }
    @media (prefers-reduced-motion: reduce) {*, *::before, *::after {scroll-behavior: auto !important; transition: none !important;}}
    .jump-nav {display:flex; flex-wrap:wrap; gap:.55rem; margin:.5rem 0 1rem;}
    .jump-nav a {border:1px solid var(--macro-line); border-radius:24px; padding:.55rem .9rem; font-size:.86rem; text-decoration:none;}
    .takeaway {border-left:3px solid var(--macro-teal); padding:.9rem 1.2rem; border-radius:0 12px 12px 0; background:var(--macro-panel-2); margin:.3rem 0; font-size:1.08rem; line-height:1.6;}
    .takeaway strong {color:var(--macro-teal); display:block; font-size:.75rem; letter-spacing:.08em; margin-bottom:.35rem;}
    .source-note {color:#b5c7cc; font-size:.8rem; line-height:1.55; margin-top:.75rem;}
    .scenario-rule {border-top:1px solid var(--macro-line); margin-top:.9rem; padding-top:.8rem; font-size:.88rem; line-height:1.55;}
    .scenario-rule strong {display:block; color:var(--macro-teal); margin:.6rem 0 .2rem;}
    .scenario-diff {font-size:.83rem; line-height:1.5;}
    .market-label,.market-note {font-size:.78rem; line-height:1.5;}
    .market-cell {min-width:0;}
    .market-strip {margin:1rem 0 .5rem;}
    .range-labels {gap:.6rem; flex-wrap:wrap; line-height:1.6;}
    .macro-table {width:100%; border-collapse:collapse; font-size:.9rem;}
    .macro-table th,.macro-table td {padding:.8rem .7rem; text-align:right; border-bottom:1px solid var(--macro-line);}
    .macro-table th:first-child {text-align:left;}
    .table-scroll {overflow-x:auto; border:1px solid var(--macro-line); border-radius:14px;}
    article, .trade-detail, .source-note, .builder-copy {overflow-wrap:anywhere;}
    [id] {scroll-margin-top:2rem;}
    @media (max-width:760px) {
        .market-strip {grid-template-columns:repeat(2,minmax(0,1fr));}
        .market-cell {padding:.85rem; border-bottom:1px solid var(--macro-line);}
        .market-value {font-size:1.45rem;}
        .market-label {letter-spacing:.03em;}
        .decision-card {min-height:0;}
        .decision-card:not(:last-child)::after {display:none;}
        .block-container {padding-top:1rem;}
        .macro-intro {font-size:1rem;}
        .takeaway {font-size:1rem;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

research = read_json("data_snapshot.json")
commodity_snapshot = read_json("commodity_snapshot.json")
live_snapshot = read_json("live_snapshot.json")

# Keep the first paint network-free: a scheduled GitHub job writes a tiny
# last-known-good snapshot, and the app only overlays values that passed the
# same lightweight validation as the original research case.
if live_snapshot.get("series"):
    research["series"] = {**research.get("series", {}), **live_snapshot["series"]}
live_commodities = sanitize_snapshot(
    "commodity_snapshot.json", {"commodities": live_snapshot.get("commodities", {})}
).get("commodities", {})
if live_commodities:
    commodity_snapshot["commodities"] = {
        **commodity_snapshot.get("commodities", {}),
        **live_commodities,
    }
series = research.get("series", {})
scenarios = research.get("scenarios", [])
paper_trades = research.get("paper_trades", [])
source_registry = research.get("source_registry", [])
commodities = commodity_snapshot.get("commodities", {})
case_retrieved = research.get("retrieved_at_brasilia", research.get("retrieved_at", "unavailable"))
data_updated = live_snapshot.get("updated_at", research.get("retrieved_at", "unavailable"))
retrieved = data_updated
pricing_audit = research.get("scenario_label_audit", {})
thresholds = research.get("trade_threshold_calculations", {})
base_scenario = next((item for item in scenarios if item.get("name") == "Base case"), {})
trade = paper_trades[0] if len(paper_trades) == 1 else {}

language_left, language_right = st.columns([7, 3])
with language_right:
    language = st.segmented_control(
        "Language / Idioma / Langue",
        options=("🇬🇧 EN", "🇧🇷 PT", "🇫🇷 FR"),
        default="🇬🇧 EN",
        key="language",
        label_visibility="collapsed",
    )

portuguese = language == "🇧🇷 PT"
french = language == "🇫🇷 FR"

lang = "pt" if portuguese else "fr" if french else "en"
c = copy_for(lang)


def ui(english: str, portuguese_text: str, french_text: str | None = None) -> str:
    if portuguese:
        return portuguese_text
    if french:
        return (french_text if french_text is not None else UI_FR.get(english, english)).replace("commodities", "matières premières").replace("commodity", "matière première")
    return english




def localized_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    if not portuguese and not french:
        return scenario
    translations = SCENARIO_PT if portuguese else SCENARIO_FR
    translation = translations.get(str(scenario.get("name", "")))
    return translation if translation else scenario


def localized_commodity(key: str, item: dict[str, Any]) -> dict[str, Any]:
    if not portuguese and not french:
        return item
    translations = COMMODITY_PT if portuguese else COMMODITY_FR
    return {**item, **translations.get(key, {})}

st.markdown(
    '<div class="identity-bar"><div><span class="identity-name">Romeo Mugnier de Almeida</span>'
    '<span>EPFL · São Paulo / Lausanne</span></div><div class="identity-links">'
    '<a href="https://github.com/Midiansi/brazil-rates-fx-scenario-monitor" target="_blank" '
    'rel="noopener noreferrer">GitHub</a><a href="https://linkedin.com/in/romeomugnier" '
    'target="_blank" rel="noopener noreferrer">LinkedIn</a></div></div>',
    unsafe_allow_html=True,
)
st.markdown(
    f'<div class="macro-kicker">{ui("Brazil rates / FX / commodities", "Juros / câmbio / commodities")}</div>',
    unsafe_allow_html=True,
)
st.title(ui("Brazil macro, from policy to price.", "Brasil: da política econômica aos preços."))
st.markdown(
    f'<div class="macro-intro">{ui("A clear view of what Brazilian interest rates, U.S. rates and export prices could mean for the real.", "Uma visão clara de como os juros no Brasil e nos EUA e os preços das exportações podem afetar o real.")}</div>',
    unsafe_allow_html=True,
)
st.caption(
    ui(
        f"Official data updated: {snapshot_label(data_updated)} · refreshed automatically on weekdays · the decision case remains dated {snapshot_label(case_retrieved)}",
        f"Dados oficiais atualizados em {snapshot_label(data_updated, True)} · atualização automática em dias úteis · o estudo de decisão permanece datado de {snapshot_label(case_retrieved, True)}",
        f"Données officielles actualisées le {snapshot_label(data_updated, french=True)} · mise à jour automatique en semaine · l'étude de décision reste datée du {snapshot_label(case_retrieved, french=True)}",
    )
)


if trade and base_scenario and series.get("ptax_usd_brl_midpoint"):
    st.markdown(f'<div class="takeaway"><strong>{c["takeaway_label"]}</strong>{c["takeaway"]}</div>', unsafe_allow_html=True)
age = snapshot_age(data_updated)
if age is not None:
    st.caption(c["age"].format(days=age))
st.markdown('<nav class="jump-nav" aria-label="'+c["navigation"]+'">' + ''.join(f'<a href="#{target}">{label}</a>' for target, label in zip(("scenarios", "paper-trade", "commodities", "evidence"), c["nav"])) + '</nav>', unsafe_allow_html=True)

if series:
    tape = []
    for key, label, unit, source in (
        ("selic_target", ui("Brazil interest rate", "Juro no Brasil"), "%", "BCB · SGS 432"),
        ("ptax_usd_brl_midpoint", ui("One U.S. dollar", "Um dólar"), "BRL", "BCB · PTAX"),
        ("brazil_us_policy_differential", ui("Brazil's rate lead", "Vantagem de juros do Brasil"), ui("pp", "p.p."), "BCB / FRED"),
        ("us_2_year_treasury", ui("U.S. two-year rate", "Juro de dois anos nos EUA"), "%", "FRED · DGS2"),
    ):
        item = series.get(key)
        if not item:
            continue
        value = f"{item['value']:.4f}" if key == "ptax_usd_brl_midpoint" else f"{item['value']:.2f}"
        tape.append(f'<div class="market-cell"><div class="market-label">{escape(label)}</div><div class="market-value">{value} {unit}</div><div class="market-note">{source}<br>{item["latest_observation_date"]}</div></div>')
    st.markdown('<div class="market-strip">'+''.join(tape)+'</div>', unsafe_allow_html=True)

st.header(ui("The short version", "Resumo"))
st.caption(ui("What I expect, why it matters, when I would act and when I would admit the idea is wrong.", "O cenário esperado, por que importa, quando eu agiria e quando admitiria que a ideia está errada."))
if all(k in series for k in ("selic_target", "brazil_us_policy_differential", "ptax_usd_brl_midpoint")) and base_scenario and trade:
    base_brief = base_scenario.get("brief_summary", {})
    entry_value = thresholds.get("entry_trigger", {}).get("value", 5.22)
    invalidation_value = thresholds.get("invalidation_reference", {}).get("value", 5.16)
    decision_cards = (
        (
            ui("1 / Starting point", "1 / Ponto de partida"),
            ui("BRAZIL CUTS / U.S. RAISES", "BRASIL CORTA / EUA SOBEM"),
            ui("The saved pricing suggested a small Brazilian rate cut and a small U.S. rate increase.", "Os preços salvos sugeriam um pequeno corte no Brasil e uma pequena alta nos EUA."),
            "",
        ),
        (
            ui("2 / Market mechanism", "2 / Mecanismo de mercado"),
            ui("THE REAL LOSES SOME SUPPORT", "O REAL PERDE PARTE DO APOIO"),
            ui(f"Brazil's rate lead over the U.S. would fall to about {base_brief.get('differential', '9.88 pp').split('to')[-1].strip()}.", "A vantagem de juros do Brasil sobre os EUA cairia para cerca de 9,88 pontos percentuais.", "L'avantage de taux du Brésil sur les États-Unis tomberait à environ 9,88 points."),
            "",
        ),
        (
            ui("3 / Confirmation", "3 / Confirmação"),
            ui(f"ONLY ABOVE {entry_value:.2f}", f"SÓ ACIMA DE {entry_value:.2f}", f"UNIQUEMENT AU-DESSUS DE {entry_value:.2f}"),
            ui("I would buy dollars against reais only after USD/BRL breaks above its recent range.", "Eu só compraria dólares se o USD/BRL rompesse a máxima recente."),
            "signal",
        ),
        (
            ui("4 / Risk control", "4 / Controle de risco"),
            ui(f"BELOW {invalidation_value:.2f} TWICE", f"ABAIXO DE {invalidation_value:.2f} DUAS VEZES", f"SOUS {invalidation_value:.2f} DEUX FOIS"),
            ui("I would abandon the idea if the price move fails or Brazil keeps its rate lead.", "Eu abandonaria a ideia se o movimento falhar ou se o Brasil mantiver sua vantagem de juros."),
            "",
        ),
    )
    st.markdown(
        '<div class="decision-grid">'
        + "".join(
            f'<article class="decision-card {card_class}"><div class="brief-label">{escape(label)}</div>'
            f'<div class="decision-number">{escape(number)}</div><div class="decision-copy">'
            f'{escape(copy)}</div></article>'
            for label, number, copy, card_class in decision_cards
        )
        + "</div>",
        unsafe_allow_html=True,
    )
else:
    st.info(ui("The saved decision frame is temporarily unavailable.", "O quadro de decisão salvo está temporariamente indisponível."))

st.markdown('<div id="scenarios"></div>', unsafe_allow_html=True)
st.header(ui("September 2026 scenario case", "Estudo de cenários de setembro de 2026"))
st.caption(ui("Three paths set before the meetings: Brazil stays tougher, follows the expected path or cuts faster.", "Três caminhos definidos antes das reuniões: o Brasil mantém juros altos, segue o esperado ou corta mais rápido."))
st.caption(c["scenario_note"])
st.caption(c["meeting"])
if len(scenarios) == 3:
    scenario_rows = []
    scenario_cards = []
    friendly_scenarios = {
        "Hawkish relative to expectations": (ui("Brazil stays tougher", "Brasil mantém juros altos"), ui("The real would probably strengthen", "O real provavelmente se fortaleceria")),
        "Base case": (ui("Saved base case", "Cenário-base salvo"), ui("The real would probably weaken slightly", "O real provavelmente enfraqueceria um pouco")),
        "Dovish relative to expectations": (ui("Brazil cuts faster", "Brasil corta mais rápido"), ui("The real would probably weaken more", "O real provavelmente enfraqueceria mais")),
    }
    for scenario in scenarios:
        brief = scenario.get("brief_summary", {})
        display_scenario = localized_scenario(scenario)
        display_brief = display_scenario.get("brief_summary", brief)
        card_class = "scenario-card base" if scenario.get("name") == "Base case" else "scenario-card"
        friendly_name, friendly_direction = friendly_scenarios.get(
            scenario.get("name", ""), (scenario.get("name", ""), brief.get("brl_usd_pressure", ""))
        )
        friendly_differentials = {
            "Hawkish relative to expectations": ui("Likely unchanged near 10.38 pp", "Perto de 10,38 p.p."),
            "Base case": ui("Likely narrows 50 bp to 9.88 pp", "Cai 0,50 ponto para 9,88 p.p."),
            "Dovish relative to expectations": ui("Likely narrows 75 bp to 9.63 pp", "Cai 0,75 ponto para 9,63 p.p."),
        }
        scenario_cards.append(
            f'<article class="{card_class}"><div class="scenario-name">{escape(str(friendly_name))}</div>'
            f'<div class="scenario-direction">{escape(str(friendly_direction))}</div>'
            f'<div class="scenario-diff">{escape(str(friendly_differentials.get(scenario.get("name", ""), brief.get("differential", ""))))}</div>'
            f'<div class="scenario-rule"><strong>{c["assumptions"]}</strong>{c["brazil_bank"]}: {escape(display_brief.get("copom", ""))}<br>{c["us_bank"]}: {escape(display_brief.get("fomc", ""))}'
            f'<strong>{c["watch"]}</strong>{escape(display_brief.get("confirmation", ""))}</div></article>'
        )
        scenario_rows.append(
            {
                ui("Scenario", "Cenário"): display_scenario.get("name", ""),
                "Copom": display_brief.get("copom", ""),
                "FOMC": display_brief.get("fomc", ""),
                ui("Brazil-US differential", "Diferencial Brasil-EUA"): display_brief.get("differential", ""),
                ui("Likely initial FX pressure", "Provável pressão inicial no câmbio"): display_brief.get("brl_usd_pressure", ""),
                ui("Confirmation", "Confirmação"): display_brief.get("confirmation", ""),
            }
        )
    st.markdown('<div class="scenario-strip">' + "".join(scenario_cards) + "</div>", unsafe_allow_html=True)
    st.caption(c["units_note"])
    with st.expander(ui("See the exact decisions, evidence and risks", "Ver decisões, evidências e riscos em detalhe")):
        for scenario in scenarios:
            display_scenario = localized_scenario(scenario)
            st.markdown(f"#### {display_scenario.get('name', ui('Scenario', 'Cenário'))}")
            scenario_left, scenario_right = st.columns(2)
            with scenario_left:
                st.markdown(ui("**Policy path**", "**Caminho dos juros**"))
                st.write(display_scenario.get("copom_outcome_and_guidance", ui("Unavailable", "Indisponível")))
                st.write(display_scenario.get("fomc_outcome_and_guidance", ui("Unavailable", "Indisponível")))
                st.markdown(ui("**Why it differs from pricing**", "**Por que difere dos preços de mercado**"))
                st.write(display_scenario.get("difference_from_current_expectations", ui("Unavailable", "Indisponível")))
            with scenario_right:
                st.markdown(ui("**What should confirm it**", "**O que deve confirmar o cenário**"))
                for signal in display_scenario.get("confirmation_signals", []):
                    st.markdown(f"- {signal}")
                st.markdown(ui("**Principal risk**", "**Principal risco**"))
                st.write(display_scenario.get("principal_risk", ui("Unavailable", "Indisponível")))
            st.divider()
else:
    st.info(ui("The saved three-scenario comparison is temporarily unavailable.", "A comparação dos três cenários está temporariamente indisponível."))

with st.expander(ui("What the numbers cannot decide", "O que os números não decidem sozinhos")):
    st.subheader(ui("What the numbers cannot decide", "O que os números não decidem sozinhos"))
    market_context = (
        (
            ui("What is already priced", "O que já está no preço"),
            ui("A small Brazilian cut and a small U.S. increase are already expected. The reaction depends on the surprise, not only the decision.", "Um pequeno corte no Brasil e uma pequena alta nos EUA já são esperados. A reação depende da surpresa, não apenas da decisão."),
        ),
        (
            ui("Policy tone", "Tom dos bancos centrais"),
            ui("Guidance about what comes next can matter more than the rate change announced on the day.", "A mensagem sobre os próximos passos pode importar mais do que a mudança de juros anunciada no dia."),
        ),
        (
            ui("News that can overpower it", "Notícias que podem dominar"),
            ui("Brazilian fiscal news, U.S. inflation and jobs data, export prices and global risk appetite can reverse the currency move.", "Notícias fiscais no Brasil, inflação e emprego nos EUA, preços das exportações e o apetite global por risco podem inverter o movimento do câmbio."),
        ),
        (
            ui("Why price confirmation matters", "Por que esperar confirmação"),
            ui("Waiting for USD/BRL to break its recent range tests whether the market agrees before taking the risk.", "Esperar o dólar romper a faixa recente testa se o mercado concorda antes de assumir o risco."),
        ),
    )
    st.markdown(
        '<div class="brief-grid">'
        + "".join(
            f'<article class="brief-card"><div class="brief-label">{escape(label)}</div>'
            f'<div class="brief-copy">{escape(copy)}</div></article>'
            for label, copy in market_context
        )
        + "</div>",
        unsafe_allow_html=True,
    )

st.markdown('<div id="paper-trade"></div>', unsafe_allow_html=True)
st.subheader(ui("A paper trade - only if the market confirms it", "Uma operação simulada - só com confirmação do mercado"))
if len(paper_trades) == 1 and series.get("ptax_usd_brl_midpoint"):
    trade = paper_trades[0]
    entry_value = float(thresholds.get("entry_trigger", {}).get("value", 5.22))
    invalidation_value = float(thresholds.get("invalidation_reference", {}).get("value", 5.16))
    review_low = float(thresholds.get("measured_move_review_zone", {}).get("lower", 5.35))
    review_high = float(thresholds.get("measured_move_review_zone", {}).get("upper", 5.36))
    st.markdown(
        f'<div class="trade-card"><div class="trade-kicker">{ui("Conditional / no position at snapshot", "Condicional / sem posição no momento")}</div>'
        f'<div class="trade-title">{ui(f"Buy dollars only above {entry_value:.2f}", f"Comprar dólares só acima de {entry_value:.2f}", f"Acheter des dollars uniquement au-dessus de {entry_value:.2f}")}</div>'
        f'<div class="trade-thesis">{ui("If Brazil cuts interest rates while the U.S. raises them, holding reais becomes slightly less attractive. Because much of that path is already expected, I would act only if price confirms it; fiscal news, export prices and global risk can still dominate.", "Se o Brasil cortar juros enquanto os EUA os elevam, manter reais fica um pouco menos atraente. Como boa parte desse caminho já é esperada, eu só agiria se o preço confirmasse; notícias fiscais, exportações e o risco global ainda podem dominar.")}</div></div>',
        unsafe_allow_html=True,
    )
    display_trade = TRADE_PT if portuguese else TRADE_FR if french else trade
    trade_details = (
        (c["entry"], c["entry_short"]),
        (c["invalidation"], c["invalidation_short"]),
        (c["review"], c["review_short"]),
        (c["catalyst"], c["meeting"]),
    )
    st.markdown(
        '<div class="trade-detail-grid">'
        + "".join(
            f'<div class="trade-detail"><strong>{escape(label)}</strong>{escape(str(copy))}</div>'
            for label, copy in trade_details
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    st.caption(c["ptax_limit"])
    st.caption(
        ui("Educational exercise only: no real money, no claimed performance and no position at the saved snapshot.", "Exercício educacional: sem dinheiro real, sem desempenho alegado e sem posição no momento dos dados.")
    )
    evidence_col, risk_col = st.columns(2)
    with evidence_col:
        st.markdown(ui("#### Why the idea is plausible", "#### Por que a ideia é plausível"))
        evidence_items = (
            ui("The dollar rose about 1.6% against the real over the latest month in the saved data.", "O dólar subiu cerca de 1,6% frente ao real no último mês dos dados salvos."),
            ui("Brazil's interest-rate lead over the U.S. already narrowed by 0.25 percentage point.", "A vantagem de juros do Brasil sobre os EUA já caiu 0,25 ponto."),
            ui("If the expected September decisions happen, that lead narrows by another 0.50 point.", "Se as decisões esperadas ocorrerem, essa vantagem cai mais 0,50 ponto."),
        )
        if evidence_items:
            st.markdown(
                '<ul class="evidence-list">'
                + "".join(f"<li>{escape(str(item))}</li>" for item in evidence_items)
                + "</ul>",
                unsafe_allow_html=True,
            )
        st.markdown(ui("#### Catalyst", "#### Catalisador"))
        st.write(ui("The Brazilian and U.S. central-bank decisions on 15-16 September.", "As decisões dos bancos centrais do Brasil e dos EUA em 15-16 de setembro."))
    with risk_col:
        st.markdown(ui("#### What could go wrong", "#### O que pode dar errado"))
        risk_items = (
            ui("Brazil keeps rates unchanged or signals that high rates will last longer.", "O Brasil mantém os juros ou indica que ficarão altos por mais tempo."),
            ui("The U.S. does not raise rates or signals lower rates ahead.", "Os EUA não elevam os juros ou sinalizam cortes à frente."),
            ui("Better fiscal news, stronger exports or a global rally strengthens the real instead.", "Notícias fiscais melhores, exportações fortes ou uma alta global fortalecem o real."),
        )
        if risk_items:
            st.markdown(
                '<ul class="evidence-list">'
                + "".join(f"<li>{escape(str(item))}</li>" for item in risk_items)
                + "</ul>",
                unsafe_allow_html=True,
            )
    st.markdown(
        f'<div class="mind-change"><strong>{ui("What would make me change my mind", "O que me faria mudar de opinião")}</strong><br>'
        + ui(f'USD/BRL fails to stay above {entry_value:.2f}; Brazil keeps its rate lead; or new fiscal, export or global-market evidence strengthens the real.', f'O dólar não se mantém acima de {entry_value:.2f}; o Brasil mantém sua vantagem de juros; ou novas informações fiscais, de exportação ou globais fortalecem o real.', f"L'USD/BRL ne reste pas au-dessus de {entry_value:.2f} ; le Brésil conserve son avantage de taux ; ou de nouvelles données budgétaires, commerciales ou mondiales renforcent le real.")
        + "</div>",
        unsafe_allow_html=True,
    )
    with st.expander(ui("See the calculations and full trade rules", "Ver cálculos e regras completas")):
        st.write(c["horizon"])
        display_trade = TRADE_PT if portuguese else TRADE_FR if french else trade
        st.markdown(ui("**Original thesis**", "**Tese original**"))
        st.write(display_trade.get("thesis", ui("Unavailable", "Indisponível")))
        st.markdown(ui("**Entry rule**", "**Regra de entrada**"))
        st.write(display_trade.get("entry_logic", ui("Unavailable", "Indisponível")))
        st.markdown(ui("**Invalidation rule**", "**Regra de invalidação**"))
        st.write(display_trade.get("invalidation_condition", ui("Unavailable", "Indisponível")))
        st.markdown(ui("**Review-zone calculation**", "**Cálculo da zona de reavaliação**"))
        st.write(display_trade.get("profit_taking_logic", ui("Unavailable", "Indisponível")))
else:
    st.info(ui("The saved conditional paper trade is temporarily unavailable.", "A operação simulada condicional está temporariamente indisponível."))

brief_path = ROOT / "outputs" / ("Brazil_Rates_FX_Trade_Brief.pdf" if lang == "en" else f"Brazil_Rates_FX_Trade_Brief_{lang.upper()}.pdf")
try:
    brief_bytes = brief_path.read_bytes()
except OSError:
    brief_bytes = b""
if brief_bytes:
    st.download_button(
        c["download"],
        data=brief_bytes,
        file_name=brief_path.name,
        mime="application/pdf",
        on_click="ignore",
    )


st.markdown('<div id="evidence"></div>', unsafe_allow_html=True)
st.header(ui("Why these numbers matter", "Por que esses números importam"))
if all(k in series for k in ("selic_target", "brazil_us_policy_differential", "ptax_usd_brl_midpoint", "focus_ipca")):
    selic = series["selic_target"]["value"]
    gap = series["brazil_us_policy_differential"]["value"]
    fx = series["ptax_usd_brl_midpoint"]
    ipca = series["focus_ipca"]
    briefs = (
        (
            ui("Rates", "Juros"),
            ui(f"Brazil's main interest rate is {selic:.1f}%, about {gap:.1f} percentage points above the comparable U.S. rate. That attracts capital, but also reflects persistent inflation risk.", f"O principal juro brasileiro está em {selic:.1f}%, cerca de {gap:.1f} pontos acima do juro americano comparável. Isso atrai capital, mas também reflete risco de inflação.", f"Le principal taux brésilien est de {selic:.1f} %, soit environ {gap:.1f} points au-dessus du taux américain comparable. Cela attire des capitaux, mais reflète aussi un risque d'inflation persistant."),
        ),
        (
            ui("Currency", "Câmbio"),
            ui(f"USD/BRL PTAX is {fx['value']:.2f}; USD/BRL rose {abs(fx['one_month_change_percent']):.1f}% over the month in the saved official data.", c["fx_change"].format(change=f"{fx['one_month_change_percent']:+.2f}"), c["fx_change"].format(change=f"{fx['one_month_change_percent']:+.2f}")),
        ),
        (
            ui("Inflation", "Inflação"),
            ui(f"Economists surveyed by Brazil's central bank expect 2026 inflation near {ipca['selected_value']:.1f}%, slightly lower than one month earlier.", f"Economistas consultados pelo Banco Central esperam inflação perto de {ipca['selected_value']:.1f}% em 2026, um pouco abaixo do mês anterior.", f"Les économistes interrogés par la banque centrale brésilienne anticipent une inflation proche de {ipca['selected_value']:.1f} % en 2026, légèrement inférieure au mois précédent."),
        ),
        (
            ui("Commodities", "Commodities"),
            ui("Oil, iron ore, soybeans and sugar affect Brazil's export income and therefore help shape the outlook for the real and inflation.", "Petróleo, minério, soja e açúcar afetam a receita de exportação e, portanto, o real e a inflação."),
        ),
    )
    st.markdown(
        '<div class="brief-grid">'
        + "".join(
            f'<article class="brief-card"><div class="brief-label">{escape(label)}</div>'
            f'<div class="brief-copy">{escape(copy)}</div></article>'
            for label, copy in briefs
        )
        + "</div>",
        unsafe_allow_html=True,
    )
else:
    st.info(ui("The saved market snapshot is temporarily unavailable.", "Os dados de mercado salvos estão temporariamente indisponíveis."))

st.header(ui("Why interest rates matter for the real", "Por que os juros importam para o real"))
if all(k in series for k in ("selic_target", "brazil_us_policy_differential", "focus_selic", "focus_ipca")):
    left, right = st.columns([1, 1.7])
    with left:
        st.metric(ui("Selic target", "Meta Selic"), f"{series['selic_target']['value']:.1f}%")
        st.metric(
            ui("Brazil–U.S. rate gap", "Diferença Brasil–EUA"),
            f"{series['brazil_us_policy_differential']['value']:.1f} {ui('pp', 'p.p.')}",
        )
    with right:
        st.subheader(ui("The simple link", "A relação, de forma simples"))
        st.write(ui("Brazil pays much higher interest than the U.S. That can support the real because investors earn more by holding Brazilian assets. The trade-off is that rates are high because inflation is still uncomfortable.", "O Brasil paga juros muito maiores que os EUA. Isso pode apoiar o real porque investidores ganham mais ao manter ativos brasileiros. Em contrapartida, os juros estão altos porque a inflação ainda preocupa."))
        st.write(ui("The saved Focus survey shows 2026 inflation expectations easing over the latest month, but still above the central bank's target.", "A pesquisa Focus mostra que a inflação esperada para 2026 caiu no último mês, mas ainda está acima da meta do Banco Central."))

    focus_selic = series["focus_selic"]
    focus_ipca = series["focus_ipca"]
    years = sorted(
        set(focus_selic.get("values_by_reference_year", {}))
        & set(focus_ipca.get("values_by_reference_year", {}))
    )
    if years:
        st.subheader(ui("What economists expect next", "O que os economistas esperam"))
        table = '<div class="table-scroll" tabindex="0" role="region" aria-label="'+c["forecast_table"]+'"><table class="macro-table"><thead><tr><th scope="col">'+ui("FORECAST", "PREVISÃO")+'</th>'
        table += ''.join(f'<th scope="col">{escape(year)}</th>' for year in years) + '</tr></thead><tbody>'
        for label, values in ((ui("Brazil interest rate", "Juro no Brasil"), focus_selic["values_by_reference_year"]), (ui("Inflation", "Inflação"), focus_ipca["values_by_reference_year"])):
            table += '<tr><th scope="row">'+label+'</th>'+''.join(f'<td>{float(values[year]):.2f}%</td>' for year in years)+'</tr>'
        st.markdown(table+'</tbody></table></div>', unsafe_allow_html=True)
        st.caption(
            ui(f"Median forecasts from economists surveyed by Brazil's central bank · latest observation {focus_selic['latest_observation_date']}", f"Medianas da pesquisa do Banco Central · última observação {focus_selic['latest_observation_date']}", f"Prévisions médianes des économistes interrogés par la banque centrale brésilienne · dernière observation {focus_selic['latest_observation_date']}")
        )

    copom_anchor = pricing_audit.get("copom", {})
    fomc_anchor = pricing_audit.get("fomc", {})
    if copom_anchor and fomc_anchor:
        st.subheader(ui("Pricing used in the saved case", "Preços usados no estudo salvo"))
        pricing_cards = (
            (
                ui("Brazil / B3 interest-rate futures", "Brasil / futuros de juros da B3"),
                ui("Close to a 0.25-point cut", "Quase um corte de 0,25 ponto"),
                ui("This estimate comes from market prices around Brazil's September central-bank meeting.", "Estimativa baseada nos preços de mercado ao redor da reunião de setembro."),
            ),
            (
                ui("United States / CME FedWatch", "Estados Unidos / CME FedWatch"),
                ui(f"{fomc_anchor.get('hike_25bp_probability_percent', 0):.1f}% chance of a 0.25-point rise", f"{fomc_anchor.get('hike_25bp_probability_percent', 0):.1f}% de chance de alta de 0,25 ponto", f"{fomc_anchor.get('hike_25bp_probability_percent', 0):.1f} % de probabilité d'une hausse de 0,25 point"),
                ui("CME's official tool gave this outcome the highest weight in the saved observation.", "A ferramenta oficial da CME atribuiu o maior peso a esse resultado."),
            ),
        )
        st.markdown(
            '<div class="pricing-grid">'
            + "".join(
                f'<article class="pricing-card"><div class="brief-label">{escape(label)}</div>'
                f'<div class="pricing-value">{escape(value)}</div><div class="pricing-copy">'
                f'{escape(copy)}</div></article>'
                for label, value, copy in pricing_cards
            )
            + "</div>",
            unsafe_allow_html=True,
        )
        st.caption(c["pricing_note"])
        st.markdown(f'[B3]({safe_url(copom_anchor.get("source_url"))}) · [CME FedWatch]({safe_url(fomc_anchor.get("source_url"))})')

st.header(ui("The real against the dollar", "O real frente ao dólar"))
if "ptax_usd_brl_midpoint" in series:
    fx = series["ptax_usd_brl_midpoint"]
    left, right = st.columns([1, 1.7])
    with left:
        st.metric("USD/BRL", f"{fx['value']:.2f}")
        st.caption(f"{ui('Official reference', 'Referência oficial')} · {fx['latest_observation_date']}")
    with right:
        st.subheader(ui("What changed", "O que mudou"))
        move = fx["one_month_change_percent"]
        verb = "rose" if move > 0 else "fell"
        st.write(c["fx_change"].format(change=f"{move:+.2f}"))
        st.caption(c["ptax_limit"])


    observed_range = fx.get("twenty_observation_range", {})
    if observed_range:
        low = float(observed_range["low"])
        high = float(observed_range["high"])
        current_position = bounded_position(float(fx["value"]), low, high)
        entry_value = float(thresholds.get("entry_trigger", {}).get("value", high))
        entry_position = bounded_position(entry_value, low, high)
        st.subheader(ui("Where USD/BRL sits in its recent range", "Onde o dólar está na faixa recente"))
        st.markdown(
            f'<div class="range-box"><div class="brief-label">{ui("PTAX range / latest 20 observations", "Faixa da PTAX / 20 observações mais recentes")}</div>'
            f'<div class="range-track"><div class="range-fill" style="width:{current_position:.1f}%"></div>'
            f'<div class="range-dot" style="left:{current_position:.1f}%"></div>'
            f'<div class="range-trigger" style="left:{entry_position:.1f}%"></div></div>'
            f'<div class="range-labels"><span>{ui("LOW", "MÍNIMA")} {low:.4f}</span><span>{ui("LATEST", "MAIS RECENTE")} {float(fx["value"]):.4f}</span>'
            f'<span>{ui("HIGH", "MÁXIMA")} {high:.4f}</span></div><div class="range-caption">'
            f'{ui(f"The orange marker is where I would consider the idea. Until USD/BRL closes above {entry_value:.2f}, there is no trade.", f"A marca laranja indica onde eu consideraria a ideia. Até o dólar fechar acima de {entry_value:.2f}, não há operação.", f"Le repère orange indique le niveau auquel j’envisagerais l’idée. Tant que l’USD/BRL ne clôture pas au-dessus de {entry_value:.2f}, il n’y a pas d’opération.")}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown('<div id="commodities"></div>', unsafe_allow_html=True)
st.header(ui("Brazil's export backdrop", "O cenário das exportações brasileiras"))
st.write(ui(
    "Brazil earns dollars by exporting products such as oil, iron ore, soybeans and sugar. Their prices can therefore affect the real, company earnings and inflation.",
    "O Brasil recebe dólares ao exportar petróleo, minério de ferro, soja e açúcar. Por isso, esses preços podem afetar o real, os lucros das empresas e a inflação.",
))
if commodities:
    commodity_cards = []
    for key, original_item in commodities.items():
        item = localized_commodity(key, original_item)
        previous = float(item["previous"])
        change = (float(item["latest"]) / previous - 1) * 100 if previous else 0.0
        direction = c["directions"][0 if change > 0 else 1 if change < 0 else 2]
        period = format_period(item["latest_date"], original_item["frequency"], lang)
        previous_period = format_period(item["previous_date"], original_item["frequency"], lang)
        unit = c["units"].get(item["unit"], item["unit"])
        source_name = "EIA / FRED" if key == "brent" else "FMI / FRED" if lang != "en" else "IMF / FRED"
        commodity_cards.append(
            f'<article class="commodity-card"><div class="commodity-label">{ui("External channel", "Canal externo")}</div>'
            f'<div class="commodity-title">{escape(str(item["label"]))}</div>'
            f'<div class="commodity-move">{escape(direction)} / {signed(change)}%</div>'
            f'<div class="commodity-meta">{escape(str(item["benchmark"]))} · '
            f'{escape(period)} · {escape(str(item["frequency"]))}<br>{c["comparison"]}: {escape(previous_period)}<br>{float(item["latest"]):.2f} {unit} · <a href="{safe_url(item["source_url"])}">{source_name}</a></div>'
            f'<div class="commodity-copy">{escape(str(item["channel"]))}</div></article>'
        )
    st.markdown('<div class="commodity-grid">' + "".join(commodity_cards) + "</div>", unsafe_allow_html=True)
    higher_count = sum(item["latest"] > item["previous"] for item in commodities.values())
    lower_count = sum(item["latest"] < item["previous"] for item in commodities.values())
    st.markdown(
        '<section class="commodity-crosscheck"><div class="macro-kicker">'
        + ui("Commodity cross-check for the trade", "Teste das commodities para a operação")
        + '</div><div class="crosscheck-title">'
        + ui("Higher export prices can help the real—but the inflation channel can push the other way.", "Preços de exportação mais altos podem ajudar o real, mas a inflação pode agir no sentido oposto.")
        + '</div><div class="crosscheck-intro">'
        + ui(
            f"In the latest observations, {higher_count} benchmarks are higher and {lower_count} lower than their previous readings. The dates and frequencies differ, so this is a cross-check—not a single commodity index.",
            f"Nas observações mais recentes, {higher_count} referências estão em alta e {lower_count} em baixa frente à leitura anterior. As datas e frequências diferem; isto é um teste de coerência, não um índice único.",
            f"Dans les observations les plus récentes, {higher_count} références sont en hausse et {lower_count} en baisse par rapport à leur lecture précédente. Les dates et fréquences diffèrent : il s'agit d'une vérification, pas d'un indice unique des commodities.",
        )
        + '</div><div class="crosscheck-grid">'
        + '<div class="crosscheck-cell"><div class="crosscheck-label">'
        + ui("External support", "Apoio externo")
        + '</div><div class="crosscheck-copy">'
        + ui("Broad, sustained strength in oil, iron ore, soy and sugar can increase export dollars and support BRL.", "Uma alta ampla e persistente de petróleo, minério, soja e açúcar pode elevar as receitas em dólares e apoiar o real.")
        + '</div></div><div class="crosscheck-cell"><div class="crosscheck-label">'
        + ui("Inflation tension", "Tensão inflacionária")
        + '</div><div class="crosscheck-copy">'
        + ui("Oil, food and ethanol channels can raise domestic prices, making faster BCB rate cuts less likely.", "Petróleo, alimentos e etanol podem pressionar preços domésticos e reduzir a chance de cortes mais rápidos do Banco Central.")
        + '</div></div><div class="crosscheck-cell"><div class="crosscheck-label">'
        + ui("Global demand", "Demanda global")
        + '</div><div class="crosscheck-copy">'
        + ui("Iron ore and soy also reveal demand conditions—especially in China—that can outweigh the rate story.", "Minério e soja também revelam condições de demanda, especialmente na China, que podem superar o efeito dos juros.")
        + '</div></div></div><div class="crosscheck-verdict"><strong>'
        + ui("Trade implication: ", "Implicação para a operação: ")
        + '</strong>'
        + ui(
            "A broad commodity rally would weaken the long-USD/short-BRL case. Falling export prices alongside firm U.S. yields would strengthen it. Mixed signals reinforce the decision to wait for USD/BRL confirmation.",
            "Uma alta ampla das commodities enfraqueceria a tese de compra de dólar. Queda dos preços de exportação com juros americanos firmes a fortaleceria. Sinais mistos reforçam a necessidade de esperar a confirmação do USD/BRL.",
        )
        + '</div></section>',
        unsafe_allow_html=True,
    )
else:
    st.info(ui("The saved commodity snapshot is temporarily unavailable.", "Os dados salvos de commodities estão temporariamente indisponíveis."))

st.header(ui("From a commodity move to an investment case", "Do movimento da commodity à tese de investimento"))
st.write(ui(
    "A commodity price move is only the starting point. Before judging a producer as an investment, I would test how much of that move reaches its revenue, margins, cash flow and valuation.",
    "O movimento do preço de uma commodity é apenas o ponto de partida. Antes de avaliar uma produtora como investimento, eu testaria quanto desse movimento chega à receita, às margens, ao caixa e à avaliação da empresa.",
))
equity_questions = (
    (
        ui("1 / Revenue exposure", "1 / Exposição da receita"),
        ui("What does the company actually sell?", "O que a empresa realmente vende?"),
        ui("Check production volumes, product mix, realized prices, hedging and the currencies in which revenue is earned.", "Analisar volumes produzidos, mix de produtos, preços realizados, proteção financeira e as moedas em que a receita é recebida."),
    ),
    (
        ui("2 / Margin and cost curve", "2 / Margem e curva de custos"),
        ui("Does a higher price become higher profit?", "Um preço maior vira lucro maior?"),
        ui("Compare operating costs, energy and freight exposure, FX sensitivity and the producer's position on the industry cost curve.", "Comparar custos operacionais, exposição a energia e frete, sensibilidade cambial e a posição da produtora na curva de custos do setor."),
    ),
    (
        ui("3 / Balance sheet", "3 / Balanço patrimonial"),
        ui("Can the company use the cash well?", "A empresa consegue usar bem o caixa?"),
        ui("Review leverage, liquidity, capital spending and the discipline behind dividends, buybacks and new projects.", "Revisar endividamento, liquidez, investimentos e a disciplina por trás de dividendos, recompras e novos projetos."),
    ),
    (
        ui("4 / Valuation and decision", "4 / Avaliação e decisão"),
        ui("Is the opportunity already in the price?", "A oportunidade já está no preço?"),
        ui("Value the business under normalized and downside assumptions, then identify the catalyst and the evidence that would invalidate the thesis.", "Avaliar o negócio com premissas normalizadas e adversas, depois identificar o catalisador e a evidência que invalidaria a tese."),
    ),
)
st.markdown(
    '<div class="brief-grid">'
    + "".join(
        f'<article class="brief-card"><div class="brief-label">{escape(step)}</div>'
        f'<div class="process-title">{escape(question)}</div><div class="brief-copy">{escape(answer)}</div></article>'
        for step, question, answer in equity_questions
    )
    + "</div>",
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="mind-change"><strong>'
    + ui("Research discipline: ", "Disciplina de análise: ")
    + "</strong>"
    + ui(
        "The dashboard identifies macro and commodity signals; a stock recommendation would still require company filings, management evidence, competitive analysis and a valuation with a margin of safety.",
        "O painel identifica sinais macroeconômicos e de commodities; uma recomendação de ação ainda exigiria demonstrações financeiras, evidências da administração, análise competitiva e uma avaliação com margem de segurança.",
    )
    + "</div>",
    unsafe_allow_html=True,
)

with st.expander(c["process"]):
    st.header(ui("How I approached the question", "Como analisei a questão"))
    st.write(ui(
        "Start with public evidence. Compare a few plausible outcomes. Form one view. Decide what would prove it wrong before acting. The calculations come afterward so anyone can check the reasoning.",
        "Começar com dados públicos. Comparar alguns resultados plausíveis. Formar uma visão. Decidir antes o que provaria que ela está errada. Os cálculos vêm depois, para que qualquer pessoa possa conferir o raciocínio.",
    ))
    proof_items = (
        (str(len(series)), ui("market series", "séries de mercado")),
        (str(len(commodities)), ui("export benchmarks", "referências de exportação")),
        (str(len(scenarios)), ui("decision scenarios", "cenários")),
        ("1", ui("conditional trade", "operação condicional")),
    )
    st.markdown(
        '<div class="proof-grid">'
        + "".join(
            f'<div class="proof-card"><div class="proof-value">{escape(value)}</div>'
            f'<div class="proof-label">{escape(label)}</div></div>'
            for value, label in proof_items
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    process_items = (
        (ui("01 / Evidence", "01 / Evidências"), ui("Use primary sources", "Usar fontes primárias"), ui("Start with central-bank and exchange data, and keep every date visible.", "Começar com dados de bancos centrais e bolsas e manter todas as datas visíveis.")),
        (ui("02 / Scenarios", "02 / Cenários"), ui("Separate the paths", "Separar os caminhos"), ui("Ask what changes if Brazil stays tougher, follows expectations or cuts faster.", "Perguntar o que muda se o Brasil mantiver os juros, seguir as expectativas ou cortar mais rápido.")),
        (ui("03 / Decision", "03 / Decisão"), ui("Wait for confirmation", "Esperar confirmação"), ui("Set the entry, exit and risks before any trade would begin.", "Definir entrada, saída e riscos antes de qualquer operação começar.")),
        (ui("04 / Challenge", "04 / Teste"), ui("Try to break it", "Tentar refutar"), ui("Check the numbers, test the rules and keep the page working when a data feed fails.", "Conferir os números, testar as regras e manter a página funcionando quando uma fonte falhar.")),
    )
    st.markdown(
        '<div class="process-grid">'
        + "".join(
            f'<article class="process-card"><div class="process-step">{escape(step)}</div>'
            f'<div class="process-title">{escape(title)}</div><div class="process-copy">'
            f'{escape(copy)}</div></article>'
            for step, title, copy in process_items
        )
        + "</div>",
        unsafe_allow_html=True,
    )
st.markdown(
    f'<div class="builder-card"><div><div class="macro-kicker">{ui("Project author", "Autor do projeto")}</div>'
    '<div class="builder-name">Romeo Mugnier de Almeida</div>'
    f'<div class="builder-copy">{ui("EPFL Mechanical Engineering student based between São Paulo and Lausanne. I built this project to show how I approach an ambiguous market question: find primary data, separate expectations from outcomes, trace commodity signals into company-level questions and state in advance what would prove a view wrong. Every conclusion is linked to evidence and a rule another reader can check.", "Estudante de Engenharia Mecânica na EPFL, entre São Paulo e Lausanne. Construí este projeto para mostrar como analiso uma pergunta de mercado ambígua: buscar dados primários, separar expectativas de resultados, transformar sinais de commodities em perguntas sobre empresas e declarar antecipadamente o que provaria que uma visão está errada. Cada conclusão está ligada a evidências e a uma regra que outra pessoa pode conferir.")}</div>'
    '</div><div class="builder-links">'
    '<a href="https://github.com/Midiansi/brazil-rates-fx-scenario-monitor" target="_blank" '
    f'rel="noopener noreferrer">{ui("Inspect the code", "Ver o código")}</a><a href="https://linkedin.com/in/romeomugnier" '
    f'target="_blank" rel="noopener noreferrer">{ui("LinkedIn profile", "Perfil no LinkedIn")}</a></div></div>',
    unsafe_allow_html=True,
)

with st.expander(ui("Data and method", "Dados e método")):
    st.write(c["limits"])
    st.write(c["pricing_method"])
    st.write(ui(
        "For readers who want to check the work: a scheduled job checks the official feeds and saves only validated observations. The page reads that tiny local file, so it opens quickly and keeps the last good value when a source is temporarily unavailable. Commodity observations retain their actual periods rather than being forced into a false like-for-like index.",
        "Para quem quiser conferir o trabalho: uma rotina programada consulta as fontes oficiais e salva apenas observações validadas. A página lê esse pequeno arquivo local, por isso abre rapidamente e mantém o último valor válido quando uma fonte fica temporariamente indisponível. As observações de commodities preservam seus períodos reais, sem formar um índice artificialmente comparável.",
        "Pour vérifier le travail : une tâche programmée consulte les sources officielles et n'enregistre que les observations validées. La page lit ce petit fichier local, ce qui lui permet de s'ouvrir rapidement et de conserver la dernière valeur fiable lorsqu'une source est indisponible. Les observations sur les commodities gardent leurs périodes réelles au lieu d'être forcées dans un faux indice comparable.",
    ))
    if series:
        for key in (
            "focus_selic",
            "focus_ipca",
            "ptax_usd_brl_midpoint",
            "selic_target",
            "fed_target_range",
            "brazil_us_policy_differential",
            "us_2_year_treasury",
            "us_10_year_treasury",
        ):
            if key not in series:
                continue
            item = series[key]
            value = item.get("selected_value", item.get("value", item.get("midpoint", ui("See source", "Ver fonte"))))
            if key == "fed_target_range":
                value = f"{item['lower']:.2f}–{item['upper']:.2f} / {item['midpoint']:.3f}"
            source = item.get("source_url", item.get("lower_source_url", "https://fred.stlouisfed.org/series/DFEDTARL"))
            if portuguese:
                label, unit = SERIES_PT.get(key, (item["label"], item["unit"]))
            elif french:
                label, unit = SERIES_FR.get(key, (item["label"], item["unit"]))
            else:
                label, unit = item["label"], item["unit"]
            source = source_url_for(source, item["latest_observation_date"])
            st.markdown(
                f"- **{label}**: {value} {unit} · "
                f"{item['latest_observation_date']} · [{ui('source', 'fonte')}]({source})"
            )

with st.expander(ui("Official source links", "Fontes oficiais")):
    if source_registry:
        for source in source_registry:
            source_label = source.get("label", ui("Official source", "Fonte oficial"))
            if portuguese:
                source_label = SOURCE_PT.get(str(source_label), source_label)
            elif french:
                source_label = SOURCE_FR.get(str(source_label), source_label)
            url = source_url_for(source.get("url", ""), series.get("selic_target", {}).get("latest_observation_date"))
            st.markdown(f"- [{source_label}]({url})")
    for key, original_item in commodities.items():
        item = localized_commodity(key, original_item)
        source_url = item.get("source_url", "")
        if source_url:
            st.markdown(f"- [{item.get('label', ui('Commodity source', 'Fonte de commodities'))}]({source_url})")
    if not source_registry and not commodities:
        st.write(ui("Official source links are temporarily unavailable.", "Os links das fontes oficiais estão temporariamente indisponíveis."))

st.divider()
st.caption(
    ui(
        f"Built by Romeo Mugnier de Almeida · official data updated {snapshot_label(data_updated)} · educational analysis, not investment advice",
        f"Criado por Romeo Mugnier de Almeida · dados oficiais atualizados em {snapshot_label(data_updated, True)} · análise educacional, não é recomendação de investimento",
        f"Créé par Romeo Mugnier de Almeida · données officielles actualisées le {snapshot_label(data_updated, french=True)} · analyse pédagogique, pas un conseil en investissement",
    )
)
