from __future__ import annotations

import json
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
    .block-container {max-width: 1080px; padding-top: 2.5rem; padding-bottom: 5rem;}
    h1 {font-size: 3rem !important; letter-spacing: -.045em; font-weight: 650 !important;}
    h2 {margin-top: 3.2rem !important; letter-spacing: -.025em;}
    [data-testid="stMetric"] {background: transparent; border: 0; padding: 0;}
    .brief {padding: 1rem 0 1.15rem; border-top: 1px solid rgba(128,128,128,.22);}
    .brief-label {font-size: .76rem; text-transform: uppercase; letter-spacing: .09em; opacity: .62;}
    .brief-copy {font-size: 1.08rem; line-height: 1.55; max-width: 850px; margin-top: .25rem;}
    .commodity {padding: 1rem 0; border-bottom: 1px solid rgba(128,128,128,.18);}
    .muted {opacity: .67; font-size: .88rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

research = read_json("data_snapshot.json")
commodity_snapshot = read_json("commodity_snapshot.json")
series = research.get("series", {})
commodities = commodity_snapshot.get("commodities", {})
retrieved = research.get("retrieved_at_brasilia", research.get("retrieved_at", "unavailable"))

st.title("Brazil macro, without the terminal clutter")
st.markdown(
    "Rates, currency and commodities — selected for what they say about Brazil, "
    "not for how many numbers fit on a screen."
)
st.caption(f"Local snapshot: {retrieved} · live refresh is optional and never blocks this page")

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
    for label, copy in briefs:
        st.markdown(
            f'<div class="brief"><div class="brief-label">{label}</div>'
            f'<div class="brief-copy">{copy}</div></div>',
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
    for item in commodities.values():
        previous = float(item["previous"])
        change = (float(item["latest"]) / previous - 1) * 100 if previous else 0.0
        st.markdown(
            f'<div class="commodity"><strong>{item["label"]}</strong> · '
            f'{item["signal"]} in the latest source period ({signed(change)}%)<br>'
            f'<span class="muted">{item["benchmark"]} · {item["latest_date"]} · '
            f'{item["frequency"]}</span></div>',
            unsafe_allow_html=True,
        )
        st.write(item["channel"])
else:
    st.info("The saved commodity snapshot is temporarily unavailable.")

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

st.divider()
st.caption(
    "Educational market-monitoring project · source-grounded, rules-based synthesis · "
    "not investment advice"
)
