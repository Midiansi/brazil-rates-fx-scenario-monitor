from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path
import time

import pandas as pd
import streamlit as st

from src.analytics import policy_rate_differential, us_curve
from src.data import fetch_focus_expectations, fetch_fred_series, fetch_ptax, fetch_selic_target
from src.portfolio import commodity_rows, commodity_synthesis, load_json, local_market_frames, market_brief
from src.research import ResearchDataError, load_research_snapshot

ROOT = Path(__file__).resolve().parent
RESEARCH_PATH = ROOT / "research" / "data_snapshot.json"
COMMODITY_PATH = ROOT / "research" / "commodity_snapshot.json"

st.set_page_config(page_title="Brazil Macro", page_icon="🇧🇷", layout="wide")
st.markdown("""
<style>
.block-container {max-width: 1120px; padding-top: 2.4rem; padding-bottom: 5rem;}
h1 {font-size: 3rem !important; letter-spacing: -0.045em; font-weight: 650 !important;}
h2 {margin-top: 3.5rem !important; letter-spacing: -0.025em;}
h3 {letter-spacing: -0.015em;}
[data-testid="stMetric"] {background: transparent; border: 0; padding: 0;}
[data-testid="stExpander"] {border-color: rgba(128,128,128,.22);}
.brief {padding: 1.15rem 0 1.25rem; border-top: 1px solid rgba(128,128,128,.22);}
.brief-label {font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; opacity: .62; margin-bottom: .3rem;}
.brief-copy {font-size: 1.12rem; line-height: 1.55; max-width: 850px;}
.commodity {padding: .8rem 0 1.1rem; border-bottom: 1px solid rgba(128,128,128,.18);}
.muted {opacity: .66; font-size: .88rem;}
</style>
""", unsafe_allow_html=True)

try:
    research = load_research_snapshot(RESEARCH_PATH)
except ResearchDataError:
    research = None
try:
    commodities = load_json(COMMODITY_PATH)
except (OSError, ValueError):
    commodities = None

# First meaningful render is local-only: no network call occurs above this point.
local_data = local_market_frames(research)
retrieved = research.get("retrieved_at_brasilia", research.get("retrieved_at")) if research else "local snapshot unavailable"

st.title("Brazil macro, without the terminal clutter")
st.markdown("Rates, currency and commodities — selected for what they say about Brazil, not for how many numbers fit on a screen.")
st.caption(f"Local snapshot: {retrieved} · live refresh is optional and never blocks this page")

st.header("Brazil in brief")
brief = market_brief(research, commodities)
if brief:
    for label, copy in brief:
        st.markdown(f'<div class="brief"><div class="brief-label">{label}</div><div class="brief-copy">{copy}</div></div>', unsafe_allow_html=True)
else:
    st.info("The reviewable local market snapshot is unavailable.")

st.header("Inflation & rates")
if research:
    s = research["series"]
    gap = s["brazil_us_policy_differential"]["value"]
    c1, c2 = st.columns([1, 1.7])
    with c1:
        st.metric("Selic target", f"{s['selic_target']['value']:.1f}%")
        st.metric("Brazil–U.S. rate gap", f"{gap:.1f} pp")
    with c2:
        st.subheader("Why it matters")
        st.write("Brazil still offers a large interest-rate advantage over the U.S. That can matter for the currency, but high domestic rates also reflect inflation that remains uncomfortable for the central bank.")
        ipca = s["focus_ipca"]
        st.write(f"The Focus median for 2026 inflation is about {ipca['selected_value']:.1f}%, down {abs(ipca['selected_1_month_change_pp']):.1f} percentage point over the latest month in the saved survey data.")

st.header("Currency")
if research:
    fx = research["series"]["ptax_usd_brl_midpoint"]
    c1, c2 = st.columns([1, 1.7])
    with c1:
        st.metric("USD/BRL", f"{fx['value']:.2f}")
        st.caption(f"PTAX · {fx['latest_observation_date']}")
    with c2:
        move = fx["one_month_change_percent"]
        verb = "weakened" if move > 0 else "strengthened"
        st.subheader("What changed")
        st.write(f"BRL {verb} about {abs(move):.1f}% against USD over the past month. The move is worth reading alongside Brazil's still-large rate advantage rather than in isolation.")

st.header("Brazil commodities")
st.write("Four exposures that connect physical markets to Brazil's export income, currency and inflation backdrop. Each source keeps its own publication frequency; dates are shown rather than forced into a false real-time comparison.")
rows = commodity_rows(commodities)
for row in rows:
    sign = "+" if row["change_percent"] > 0 else ""
    st.markdown(f'<div class="commodity"><strong>{row["label"]}</strong> · {row["direction"]} in the latest source period ({sign}{row["change_percent"]:.1f}%)<br><span class="muted">{row["benchmark"]} · {row["latest_date"]} · {row["frequency"]}</span></div>', unsafe_allow_html=True)
    st.write(row["channel"])

st.subheader("How commodities feed into the macro story")
for label, copy in commodity_synthesis(commodities):
    st.markdown(f"**{label}.** {copy}")

if research and commodities:
    st.subheader("Export commodities and BRL: a useful question, not a causal claim")
    st.write("The current local snapshot is intentionally conservative: commodity benchmarks have different frequencies, so the site does not manufacture a synchronized index from mismatched dates. The deeper-data layer exposes dates and sources; a future scheduled snapshot can add a properly aligned daily export basket once the underlying histories are stored locally.")

with st.expander("Deeper data & methodology"):
    st.write("Exact observations are kept here for auditability; the opening page uses rounded values and plain-language synthesis.")
    if research:
        exact = []
        for key in ("focus_selic", "focus_ipca", "ptax_usd_brl_midpoint", "selic_target", "fed_target_range", "brazil_us_policy_differential", "us_2_year_treasury", "us_10_year_treasury"):
            item = research["series"][key]
            value = item.get("selected_value", item.get("value", item.get("midpoint", "See source")))
            exact.append({"Series": item["label"], "Value": value, "Unit": item["unit"], "Latest observation": item["latest_observation_date"]})
        st.dataframe(pd.DataFrame(exact), hide_index=True, width="stretch")
    if rows:
        st.dataframe(pd.DataFrame([{"Commodity": r["benchmark"], "Latest": r["latest"], "Unit": r["unit"], "Date": r["latest_date"], "Frequency": r["frequency"], "Source": r["source"]} for r in rows]), hide_index=True, width="stretch")

@st.cache_data(ttl=3600, show_spinner=False)
def refresh_live(as_of: date):
    focus_start, market_start, rates_start = as_of - timedelta(days=400), as_of - timedelta(days=120), as_of - timedelta(days=365 * 3 + 10)
    jobs = {
        "focus_selic": lambda: fetch_focus_expectations("Selic", focus_start),
        "focus_ipca": lambda: fetch_focus_expectations("IPCA", focus_start),
        "ptax": lambda: fetch_ptax(market_start, as_of),
        "selic_target": lambda: fetch_selic_target(rates_start, as_of),
        "fed_lower": lambda: fetch_fred_series("DFEDTARL", rates_start),
        "fed_upper": lambda: fetch_fred_series("DFEDTARU", rates_start),
        "us_2y": lambda: fetch_fred_series("DGS2", rates_start),
        "us_10y": lambda: fetch_fred_series("DGS10", rates_start),
    }
    data, errors = {}, {}
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(loader): key for key, loader in jobs.items()}
        for future in as_completed(futures):
            key = futures[future]
            try: data[key] = future.result()
            except Exception: errors[key] = "unavailable"
    return data, errors, time.perf_counter() - started

with st.expander("Live refresh"):
    st.caption("Optional. The portfolio renders from local data first, so external APIs are never on the first-paint path.")
    if st.button("Check official sources now"):
        live, errors, elapsed = refresh_live(date.today())
        st.success(f"Checked {len(live)} of 8 sources in {elapsed:.1f}s." if live else f"Official sources were unavailable after {elapsed:.1f}s; the local snapshot remains visible.")
        if errors:
            st.caption(f"Unavailable this check: {', '.join(sorted(errors))}")
        try:
            diff = policy_rate_differential(live.get("selic_target", pd.DataFrame()), live.get("fed_lower", pd.DataFrame()), live.get("fed_upper", pd.DataFrame()))
            curve = us_curve(live.get("us_2y", pd.DataFrame()), live.get("us_10y", pd.DataFrame()))
            if not diff.empty: st.write(f"Latest live Brazil–U.S. policy gap: {diff.iloc[-1]['Policy differential']:.1f} pp")
            if not curve.empty: st.write(f"Latest live U.S. yield curve (10-year minus 2-year): {curve.iloc[-1]['2s10s']:.2f} pp")
        except Exception:
            pass

st.divider()
st.caption("Educational market-monitoring project · source-grounded, rules-based synthesis · not investment advice")
