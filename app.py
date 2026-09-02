from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

import streamlit as st


ROOT = Path(__file__).resolve().parent


def read_json(name: str) -> dict[str, Any]:
    """Read a versioned local snapshot without making the page depend on a network."""

    try:
        with (ROOT / "research" / name).open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError, TypeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def signed(value: float, digits: int = 1) -> str:
    return f"{value:+.{digits}f}"


st.set_page_config(page_title="Brazil Macro", page_icon="🇧🇷", layout="wide")
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
    .block-container {max-width: 1160px; padding-top: 3.2rem; padding-bottom: 5rem;}
    html, body, [class*="st-"] {font-family: "Avenir Next", "Helvetica Neue", Arial, sans-serif;}
    h1 {
        max-width: 900px;
        color: var(--macro-ink) !important;
        font-size: clamp(3.1rem, 7vw, 5.9rem) !important;
        line-height: .94 !important;
        letter-spacing: -.065em !important;
        font-weight: 640 !important;
        margin: .35rem 0 1.25rem !important;
    }
    h2 {
        color: var(--macro-ink) !important;
        margin-top: 4.2rem !important;
        padding-bottom: .7rem;
        border-bottom: 1px solid var(--macro-line);
        font-size: 1.8rem !important;
        letter-spacing: -.035em !important;
        font-weight: 570 !important;
    }
    h3 {color: var(--macro-ink) !important; letter-spacing: -.025em !important; font-weight: 570 !important;}
    p {line-height: 1.62;}
    a {color: var(--macro-teal) !important; text-underline-offset: 3px;}
    a:focus-visible, button:focus-visible {outline: 2px solid var(--macro-teal) !important; outline-offset: 3px;}
    [data-testid="stCaptionContainer"] {color: var(--macro-muted);}
    .macro-kicker, .brief-label, .commodity-label, .trade-kicker {
        color: var(--macro-teal);
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: .72rem;
        font-weight: 650;
        letter-spacing: .13em;
        text-transform: uppercase;
    }
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
        border-top: 1px solid var(--macro-line);
        border-bottom: 1px solid var(--macro-line);
    }
    .market-cell {padding: 1rem 1.1rem 1.15rem 0; border-right: 1px solid var(--macro-line);}
    .market-cell:not(:first-child) {padding-left: 1.1rem;}
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
    .brief-grid, .commodity-grid, .scenario-strip, .trade-detail-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1px;
        background: var(--macro-line);
        border: 1px solid var(--macro-line);
    }
    .brief-card, .commodity-card, .trade-detail {background: var(--macro-panel); padding: 1.35rem 1.45rem 1.5rem;}
    .brief-copy {font-size: 1rem; line-height: 1.55; margin-top: .7rem; color: #dbe6e4;}
    .commodity-card {min-height: 210px;}
    .commodity-title {font-size: 1.35rem; font-weight: 610; letter-spacing: -.025em; margin: .45rem 0 .25rem;}
    .commodity-move {color: var(--macro-sand); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .82rem;}
    .commodity-meta {color: var(--macro-muted); font-size: .76rem; margin: .55rem 0 1rem;}
    .commodity-copy {color: #c3d1d3; line-height: 1.55;}
    .scenario-strip {grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 1.1rem 0 1.2rem;}
    .scenario-card {background: var(--macro-panel); padding: 1.15rem 1.25rem 1.3rem;}
    .scenario-card.base {background: var(--macro-panel-2); box-shadow: inset 0 3px 0 var(--macro-teal);}
    .scenario-name {font-weight: 620; letter-spacing: -.02em; margin-bottom: .65rem;}
    .scenario-direction {color: #d2dfdd; font-size: .88rem; line-height: 1.45;}
    .scenario-diff {color: var(--macro-muted); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .72rem; margin-top: .65rem;}
    .trade-card {
        border-left: 4px solid var(--macro-copper);
        background: linear-gradient(105deg, rgba(229, 138, 84, .09), rgba(12, 29, 41, .72));
        padding: 1.35rem 1.55rem 1.5rem;
        margin: .5rem 0 1px;
    }
    .trade-title {font-size: 1.65rem; font-weight: 620; letter-spacing: -.035em; margin: .35rem 0 .6rem;}
    .trade-thesis {max-width: 920px; color: #d5e1df; font-size: 1.02rem; line-height: 1.58;}
    .trade-detail-grid {margin-bottom: .75rem;}
    .trade-detail strong {display: block; color: var(--macro-sand); margin-bottom: .5rem; font-size: .8rem; letter-spacing: .04em; text-transform: uppercase;}
    .trade-detail {color: #bac9cc; font-size: .9rem; line-height: 1.55;}
    [data-testid="stDataFrame"] {border: 1px solid var(--macro-line); background: var(--macro-panel);}
    [data-testid="stExpander"] {border: 1px solid var(--macro-line); border-radius: 2px; background: rgba(12, 29, 41, .55);}
    [data-testid="stDownloadButton"] button {
        background: var(--macro-teal);
        color: #04120f;
        border: 0;
        border-radius: 2px;
        font-weight: 700;
        min-height: 2.8rem;
    }
    [data-testid="stDownloadButton"] button:hover {background: #55d3bf; color: #04120f;}
    hr {border-color: var(--macro-line) !important;}
    @media (max-width: 760px) {
        .block-container {padding-top: 2rem; padding-left: 1.2rem; padding-right: 1.2rem;}
        h1 {font-size: 3.25rem !important;}
        .market-strip, .brief-grid, .commodity-grid, .scenario-strip, .trade-detail-grid {grid-template-columns: 1fr;}
        .market-cell {border-right: 0; border-bottom: 1px solid var(--macro-line); padding-left: 0 !important;}
        .market-cell:last-child {border-bottom: 0;}
        .commodity-card {min-height: 0;}
    }
    @media (prefers-reduced-motion: reduce) {*, *::before, *::after {scroll-behavior: auto !important; transition: none !important;}}
    </style>
    """,
    unsafe_allow_html=True,
)

research = read_json("data_snapshot.json")
commodity_snapshot = read_json("commodity_snapshot.json")
series = research.get("series", {})
scenarios = research.get("scenarios", [])
paper_trades = research.get("paper_trades", [])
source_registry = research.get("source_registry", [])
commodities = commodity_snapshot.get("commodities", {})
retrieved = research.get("retrieved_at_brasilia", research.get("retrieved_at", "unavailable"))

st.markdown('<div class="macro-kicker">Brazil rates / FX / commodities</div>', unsafe_allow_html=True)
st.title("Brazil macro, from policy to price.")
st.markdown(
    '<div class="macro-intro">A source-grounded desk view of how Copom, FOMC and '
    'export commodities transmit into BRL, inflation expectations and the curve.</div>',
    unsafe_allow_html=True,
)
st.caption(f"Local snapshot: {retrieved} · live refresh is optional and never blocks this page")

if series:
    tape = (
        ("Selic", f"{series.get('selic_target', {}).get('value', 0):.2f}%", "current target"),
        ("USD / BRL", f"{series.get('ptax_usd_brl_midpoint', {}).get('value', 0):.4f}", "PTAX reference"),
        ("BR-US gap", f"{series.get('brazil_us_policy_differential', {}).get('value', 0):.2f} pp", "policy midpoint"),
        ("US 2-year", f"{series.get('us_2_year_treasury', {}).get('value', 0):.2f}%", "Treasury yield"),
    )
    st.markdown(
        '<div class="market-strip">'
        + "".join(
            f'<div class="market-cell"><div class="market-label">{escape(label)}</div>'
            f'<div class="market-value">{escape(value)}</div><div class="market-note">{escape(note)}</div></div>'
            for label, value, note in tape
        )
        + "</div>",
        unsafe_allow_html=True,
    )

st.header("Brazil in brief")
if series:
    selic = series["selic_target"]["value"]
    gap = series["brazil_us_policy_differential"]["value"]
    fx = series["ptax_usd_brl_midpoint"]
    ipca = series["focus_ipca"]
    briefs = (
        (
            "Rates",
            f"The Selic target is {selic:.1f}%, leaving Brazil's policy rate about {gap:.1f} "
            "percentage points above the U.S. target-range midpoint.",
        ),
        (
            "Currency",
            f"USD/BRL PTAX is {fx['value']:.2f}; BRL weakened {abs(fx['one_month_change_percent']):.1f}% "
            "over the month in the saved official data.",
        ),
        (
            "Inflation",
            f"The Focus median for 2026 IPCA is {ipca['selected_value']:.1f}%, "
            f"{abs(ipca['selected_1_month_change_pp']):.1f} percentage point lower over one month.",
        ),
        (
            "Commodities",
            "Oil, iron ore, soybeans and sugar connect external prices to Brazil's export income, "
            "currency backdrop and domestic inflation channels.",
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
    st.info("The saved market snapshot is temporarily unavailable.")

st.header("Inflation & rates")
if series:
    left, right = st.columns([1, 1.7])
    with left:
        st.metric("Selic target", f"{series['selic_target']['value']:.1f}%")
        st.metric(
            "Brazil–U.S. rate gap",
            f"{series['brazil_us_policy_differential']['value']:.1f} pp",
        )
    with right:
        st.subheader("Why it matters")
        st.write(
            "Brazil still offers a large interest-rate advantage over the U.S. That can support "
            "the currency, while high domestic rates also signal inflation that remains uncomfortable."
        )
        st.write(
            "The saved Focus survey shows 2026 inflation expectations easing over the latest month, "
            "but still above the central bank's target."
        )

st.header("Currency")
if series:
    fx = series["ptax_usd_brl_midpoint"]
    left, right = st.columns([1, 1.7])
    with left:
        st.metric("USD/BRL", f"{fx['value']:.2f}")
        st.caption(f"PTAX · {fx['latest_observation_date']}")
    with right:
        st.subheader("What changed")
        move = fx["one_month_change_percent"]
        verb = "weakened" if move > 0 else "strengthened"
        st.write(
            f"BRL {verb} about {abs(move):.1f}% against USD over the past month. "
            "The move is best read alongside Brazil's still-large rate advantage."
        )

st.header("Brazil commodities")
st.write(
    "Four exposures that connect physical markets to Brazilian export income, BRL and inflation. "
    "Dates and source frequencies are kept explicit rather than presented as synchronized data."
)
if commodities:
    commodity_cards = []
    for item in commodities.values():
        previous = float(item["previous"])
        change = (float(item["latest"]) / previous - 1) * 100 if previous else 0.0
        commodity_cards.append(
            f'<article class="commodity-card"><div class="commodity-label">External channel</div>'
            f'<div class="commodity-title">{escape(str(item["label"]))}</div>'
            f'<div class="commodity-move">{escape(str(item["signal"]))} / {signed(change)}%</div>'
            f'<div class="commodity-meta">{escape(str(item["benchmark"]))} · '
            f'{escape(str(item["latest_date"]))} · {escape(str(item["frequency"]))}</div>'
            f'<div class="commodity-copy">{escape(str(item["channel"]))}</div></article>'
        )
    st.markdown('<div class="commodity-grid">' + "".join(commodity_cards) + "</div>", unsafe_allow_html=True)
else:
    st.info("The saved commodity snapshot is temporarily unavailable.")

st.header("Scenario Lab")
st.caption(
    "Three conditional Copom/FOMC paths from the saved, timestamped market snapshot. "
    "Reactions are directional hypotheses, not certainties."
)
if len(scenarios) == 3:
    scenario_rows = []
    scenario_cards = []
    for scenario in scenarios:
        brief = scenario.get("brief_summary", {})
        card_class = "scenario-card base" if scenario.get("name") == "Base case" else "scenario-card"
        scenario_cards.append(
            f'<article class="{card_class}"><div class="scenario-name">{escape(str(scenario.get("name", "")))}</div>'
            f'<div class="scenario-direction">{escape(str(brief.get("brl_usd_pressure", "")))}</div>'
            f'<div class="scenario-diff">{escape(str(brief.get("differential", "")))}</div></article>'
        )
        scenario_rows.append(
            {
                "Scenario": scenario.get("name", ""),
                "Copom": brief.get("copom", ""),
                "FOMC": brief.get("fomc", ""),
                "Brazil-US differential": brief.get("differential", ""),
                "Likely initial FX pressure": brief.get("brl_usd_pressure", ""),
                "Confirmation": brief.get("confirmation", ""),
            }
        )
    st.markdown('<div class="scenario-strip">' + "".join(scenario_cards) + "</div>", unsafe_allow_html=True)
    st.dataframe(scenario_rows, hide_index=True, width="stretch")
else:
    st.info("The saved three-scenario comparison is temporarily unavailable.")

st.subheader("Conditional paper trade")
if len(paper_trades) == 1:
    trade = paper_trades[0]
    st.markdown(
        f'<div class="trade-card"><div class="trade-kicker">Conditional / no position at snapshot</div>'
        f'<div class="trade-title">{escape(str(trade.get("direction", "")))}</div>'
        f'<div class="trade-thesis">{escape(str(trade.get("thesis", "")))}</div></div>',
        unsafe_allow_html=True,
    )
    trade_details = (
        ("Entry logic", trade.get("entry_logic", "")),
        ("Invalidation", trade.get("invalidation_condition", "")),
        ("Profit-taking", trade.get("profit_taking_logic", "")),
        (
            "Scenario mapping",
            f"Supported by: {trade.get('supporting_scenario', 'unavailable')} · "
            f"Invalidated by: {trade.get('invalidating_scenario', 'unavailable')}",
        ),
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
    st.caption(
        f"Expected holding period: {trade.get('expected_holding_period', 'unavailable')} · "
        "Educational paper trade only; no position or performance is represented."
    )
else:
    st.info("The saved conditional paper trade is temporarily unavailable.")

brief_path = ROOT / "outputs" / "Brazil_Rates_FX_Trade_Brief.pdf"
try:
    brief_bytes = brief_path.read_bytes()
except OSError:
    brief_bytes = b""
if brief_bytes:
    st.download_button(
        "Download the one-page market brief (PDF)",
        data=brief_bytes,
        file_name=brief_path.name,
        mime="application/pdf",
    )

with st.expander("Deeper data & methodology"):
    st.write(
        "This page renders exclusively from reviewable JSON files stored with the application. "
        "It makes no network request on startup, and it does not manufacture a synchronized "
        "commodity index from observations published at different frequencies."
    )
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
            item = series[key]
            value = item.get("selected_value", item.get("value", item.get("midpoint", "See source")))
            source = item.get("source_url", item.get("lower_source_url", ""))
            st.markdown(
                f"- **{item['label']}**: {value} {item['unit']} · "
                f"{item['latest_observation_date']} · [source]({source})"
            )

with st.expander("Official sources"):
    if source_registry:
        for source in source_registry:
            st.markdown(f"- [{source.get('label', 'Official source')}]({source.get('url', '')})")
    for item in commodities.values():
        source_url = item.get("source_url", "")
        if source_url:
            st.markdown(f"- [{item.get('label', 'Commodity source')}]({source_url})")
    if not source_registry and not commodities:
        st.write("Official source links are temporarily unavailable.")

st.divider()
st.caption(
    "Educational market-monitoring project · source-grounded, rules-based synthesis · "
    "not investment advice"
)
