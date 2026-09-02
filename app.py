from __future__ import annotations

from datetime import date, timedelta
import os
from pathlib import Path
from typing import Callable, TypeVar

import pandas as pd
import streamlit as st

from src.analytics import (
    calendar_change,
    observation_change,
    policy_rate_differential,
    summarize_expectations,
    us_curve,
)
from src.charts import focus_expectations_chart, policy_diff_chart, ptax_chart
from src.data import (
    BCB_EXPECTATIONS_URL,
    BCB_PTAX_URL,
    BCB_SELIC_URL,
    FRED_SERIES_URL,
    fetch_focus_expectations,
    fetch_fred_series,
    fetch_ptax,
    fetch_selic_target,
)
from src.research import ResearchDataError, load_research_snapshot


T = TypeVar("T")


st.set_page_config(
    page_title="Brazil Rates & FX Scenario Monitor",
    page_icon="🇧🇷",
    layout="wide",
)


@st.cache_data(ttl=900, show_spinner=False)
def load_snapshot(as_of: date) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    """Load each source independently so one outage does not take down the app."""

    data: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}

    def capture(key: str, loader: Callable[[], pd.DataFrame]) -> None:
        try:
            data[key] = loader()
        except Exception as exc:  # Deliberate UI boundary around external services.
            errors[key] = str(exc)
            data[key] = pd.DataFrame()

    focus_start = as_of - timedelta(days=400)
    market_start = as_of - timedelta(days=120)
    rates_start = as_of - timedelta(days=365 * 3 + 10)

    capture("focus_selic", lambda: fetch_focus_expectations("Selic", focus_start))
    capture("focus_ipca", lambda: fetch_focus_expectations("IPCA", focus_start))
    capture("ptax", lambda: fetch_ptax(market_start, as_of))
    capture("selic_target", lambda: fetch_selic_target(rates_start, as_of))
    capture("fed_lower", lambda: fetch_fred_series("DFEDTARL", rates_start))
    capture("fed_upper", lambda: fetch_fred_series("DFEDTARU", rates_start))
    capture("us_2y", lambda: fetch_fred_series("DGS2", rates_start))
    capture("us_10y", lambda: fetch_fred_series("DGS10", rates_start))
    return data, errors


def apply_saved_fallback(
    data: dict[str, pd.DataFrame],
    errors: dict[str, str],
    research: dict | None,
) -> dict[str, str]:
    """Fill only unavailable live series from the validated saved snapshot."""

    if research is None:
        return {}

    series = research["series"]
    saved_frames: dict[str, pd.DataFrame] = {}

    for key, indicator, series_key in (
        ("focus_selic", "Selic", "focus_selic"),
        ("focus_ipca", "IPCA", "focus_ipca"),
    ):
        item = series[series_key]
        rows = [
            {
                "Indicator": indicator,
                "Date": pd.Timestamp(item["latest_observation_date"]),
                "Reference year": int(reference_year),
                "Median": float(value),
                "Calculation base": 0,
            }
            for reference_year, value in item["values_by_reference_year"].items()
        ]
        saved_frames[key] = pd.DataFrame(rows)

    ptax = series["ptax_usd_brl_midpoint"]
    ptax_timestamp = pd.Timestamp(ptax["latest_observation_timestamp"])
    if ptax_timestamp.tzinfo is not None:
        ptax_timestamp = ptax_timestamp.tz_localize(None)
    saved_frames["ptax"] = pd.DataFrame(
        [
            {
                "Date": pd.Timestamp(ptax["latest_observation_date"]),
                "Timestamp": ptax_timestamp,
                "Buying rate": float(ptax["buying_rate"]),
                "Selling rate": float(ptax["selling_rate"]),
                "Midpoint": float(ptax["value"]),
            }
        ]
    )

    rate_items = {
        "selic_target": ("selic_target", "value"),
        "fed_lower": ("fed_target_range", "lower"),
        "fed_upper": ("fed_target_range", "upper"),
        "us_2y": ("us_2_year_treasury", "value"),
        "us_10y": ("us_10_year_treasury", "value"),
    }
    for key, (series_key, value_key) in rate_items.items():
        item = series[series_key]
        saved_frames[key] = pd.DataFrame(
            [
                {
                    "Date": pd.Timestamp(item["latest_observation_date"]),
                    "Value": float(item[value_key]),
                }
            ]
        )

    fallback_dates: dict[str, str] = {}
    for key, frame in saved_frames.items():
        if key in errors or data.get(key, pd.DataFrame()).empty:
            data[key] = frame
            fallback_dates[key] = frame["Date"].max().strftime("%Y-%m-%d")
    return fallback_dates


def show_source_warning(
    source_name: str,
    key: str,
    errors: dict[str, str],
    fallback_dates: dict[str, str],
    saved_retrieval: str | None,
) -> None:
    if key in fallback_dates:
        st.warning(
            f"{source_name} live refresh was unavailable or returned no usable observations. "
            f"Showing saved fallback retrieved {saved_retrieval}; latest saved observation "
            f"{fallback_dates[key]}."
        )
    elif key in errors:
        st.warning(f"{source_name} is temporarily unavailable; no saved fallback is available.")


def fmt_number(value: float | None, decimals: int = 2, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:,.{decimals}f}{suffix}"


def fmt_delta(value: float | None, decimals: int = 2, suffix: str = "") -> str | None:
    if value is None or pd.isna(value):
        return None
    return f"{value:+.{decimals}f}{suffix}"


def direction(value: float, positive: str, negative: str) -> str:
    if value > 0:
        return positive
    if value < 0:
        return negative
    return "was unchanged"


def build_market_summary(
    data: dict[str, pd.DataFrame],
    differential: pd.DataFrame,
    curve: pd.DataFrame,
) -> list[str]:
    statements: list[str] = []

    for key, label in (("focus_selic", "Selic"), ("focus_ipca", "IPCA")):
        table = summarize_expectations(data[key]) if not data[key].empty else pd.DataFrame()
        if not table.empty:
            row = table.sort_values("Reference year").iloc[0]
            change = row["5-business-day change (pp)"]
            if pd.notna(change):
                move = direction(change, "moved higher", "moved lower")
                statements.append(
                    f"{int(row['Reference year'])} {label} expectations {move} "
                    f"by {abs(change):.2f} pp over five available business-day observations."
                )

    if not data["ptax"].empty:
        change = observation_change(data["ptax"], "Date", "Midpoint", periods=5)
        if change is not None:
            if change.absolute > 0:
                move = "BRL weakened"
            elif change.absolute < 0:
                move = "BRL strengthened"
            else:
                move = "BRL was unchanged"
            statements.append(
                f"{move} against USD: the PTAX midpoint changed "
                f"{change.percentage:+.2f}% over five available business-day observations."
            )

    if not differential.empty:
        change = observation_change(
            differential, "Date", "Policy differential", periods=5, business_days_only=True
        )
        if change is not None:
            move = direction(change.absolute, "widened", "narrowed")
            statements.append(
                f"The Brazil–US policy-rate differential {move} by "
                f"{abs(change.absolute):.2f} pp over five business days."
            )

    if not curve.empty:
        change = observation_change(curve, "Date", "2s10s", periods=5)
        if change is not None:
            move = direction(change.absolute, "steepened", "flattened")
            statements.append(
                f"The U.S. 2s10s curve {move} by {abs(change.absolute):.2f} pp "
                "over five available Treasury observations."
            )
    return statements


research_path = Path(
    os.environ.get(
        "SCENARIO_RESEARCH_PATH",
        Path(__file__).resolve().parent / "research" / "data_snapshot.json",
    )
)
brief_pdf_path = Path(
    os.environ.get(
        "MARKET_BRIEF_PDF_PATH",
        Path(__file__).resolve().parent / "outputs" / "Brazil_Rates_FX_Trade_Brief.pdf",
    )
)
try:
    research_snapshot = load_research_snapshot(research_path)
    research_error = None
except ResearchDataError as exc:
    research_snapshot = None
    research_error = str(exc)

today = date.today()
with st.spinner("Loading official market data…"):
    snapshot, source_errors = load_snapshot(today)

fallback_dates = apply_saved_fallback(snapshot, source_errors, research_snapshot)
saved_retrieval = research_snapshot["retrieved_at"] if research_snapshot else None

try:
    policy_diff = policy_rate_differential(
        snapshot["selic_target"], snapshot["fed_lower"], snapshot["fed_upper"]
    )
except Exception:
    policy_diff = pd.DataFrame()

try:
    treasury_curve = us_curve(snapshot["us_2y"], snapshot["us_10y"])
except Exception:
    treasury_curve = pd.DataFrame()

st.title("Brazil Rates & FX Scenario Monitor")
st.caption(
    "A source-grounded view of Brazilian expectations, USD/BRL and Brazil–US rates. "
    "All calculations are rules-based; no generated market narrative is used."
)

st.subheader("Market summary")
summary = build_market_summary(snapshot, policy_diff, treasury_curve)
if summary:
    st.markdown("\n".join(f"- {statement}" for statement in summary))
else:
    st.info("No cross-market summary is available until the required source observations load.")
st.caption("Directional statements compare the latest valid value with the stated prior observation.")

expectations_tab, fx_tab, rates_tab = st.tabs(
    ["Brazil expectations", "BRL/USD", "Brazil–US rates"]
)

with expectations_tab:
    st.header("Brazil expectations")
    st.caption(
        "BCB Focus annual survey medians (`baseCalculo = 0`). Changes are absolute "
        "percentage-point moves, not relative percentage changes."
    )

    for key, indicator in (("focus_selic", "Selic"), ("focus_ipca", "IPCA")):
        st.subheader(f"{indicator} expectations")
        show_source_warning(
            "BCB Focus", key, source_errors, fallback_dates, saved_retrieval
        )
        frame = snapshot[key]
        if frame.empty:
            st.info(f"No usable {indicator} expectation observations are available.")
            continue

        table = summarize_expectations(frame)
        display_table = table[
            [
                "Reference year",
                "Median (%)",
                "5-business-day change (pp)",
                "1-month change (pp)",
                "Latest observation",
            ]
        ].copy()
        median_label = "Median (% p.a.)" if indicator == "Selic" else "Median (annual %)"
        display_table = display_table.rename(columns={"Median (%)": median_label})
        display_table["Latest observation"] = display_table["Latest observation"].dt.strftime(
            "%d %b %Y"
        )
        st.dataframe(
            display_table,
            hide_index=True,
            width="stretch",
            column_config={
                median_label: st.column_config.NumberColumn(format="%.4f"),
                "5-business-day change (pp)": st.column_config.NumberColumn(format="%+.4f"),
                "1-month change (pp)": st.column_config.NumberColumn(format="%+.4f"),
            },
        )
        st.plotly_chart(
            focus_expectations_chart(frame, indicator),
            key=f"focus_{indicator.lower()}_chart",
        )
        latest_date = frame["Date"].max()
        st.caption(
            f"Latest usable {indicator} observation: {latest_date:%d %b %Y}. "
            "The five-business-day comparison is t versus t−5 sorted, valid observations; "
            "the one-month comparison uses the latest observation on or before the date one month earlier."
        )

    st.markdown(f"Source: [Banco Central do Brasil — Focus Expectations OData]({BCB_EXPECTATIONS_URL})")

with fx_tab:
    st.header("BRL/USD")
    st.caption(
        "USD/BRL PTAX midpoint, calculated as (official buying rate + official selling rate) / 2. "
        "Units: Brazilian reais per U.S. dollar."
    )
    show_source_warning(
        "BCB PTAX", "ptax", source_errors, fallback_dates, saved_retrieval
    )
    ptax = snapshot["ptax"]
    if ptax.empty:
        st.info("No usable PTAX observations are available.")
    else:
        latest = ptax.iloc[-1]
        previous = ptax.iloc[-2] if len(ptax) > 1 else None
        change_5d = observation_change(ptax, "Date", "Midpoint", periods=5)
        change_1m = calendar_change(ptax, "Date", "Midpoint", months=1)

        col1, col2, col3 = st.columns(3)
        col1.metric("Latest PTAX midpoint", fmt_number(latest["Midpoint"], 5))
        col2.metric(
            "Five-business-day change",
            fmt_delta(change_5d.percentage if change_5d else None, 2, "%") or "N/A",
        )
        col3.metric(
            "Approximately one-month change",
            fmt_delta(change_1m.percentage if change_1m else None, 2, "%") or "N/A",
        )
        previous_text = (
            f"Previous observation: {previous['Date']:%d %b %Y}" if previous is not None else "Previous observation: N/A"
        )
        st.caption(
            f"Latest observation: {latest['Date']:%d %b %Y} at {latest['Timestamp']:%H:%M:%S}; "
            f"{previous_text}. Latest official buying rate: {latest['Buying rate']:.5f}; "
            f"selling rate: {latest['Selling rate']:.5f}."
        )
        st.plotly_chart(ptax_chart(ptax), key="ptax_chart")
        if change_5d is not None:
            st.caption(
                f"Five-business-day reference observation: {change_5d.previous_date:%d %b %Y}."
            )
        if change_1m is not None:
            st.caption(f"One-month reference observation: {change_1m.previous_date:%d %b %Y}.")
    st.markdown(f"Source: [Banco Central do Brasil — PTAX OData]({BCB_PTAX_URL})")

with rates_tab:
    st.header("Brazil–US rates")
    st.caption(
        "Policy comparison: BCB Selic target minus the calculated midpoint of the Federal Reserve's "
        "federal-funds target range. All levels and differences are in percentage points."
    )

    for key, name in (
        ("selic_target", "BCB SGS Selic target"),
        ("fed_lower", "FRED federal-funds lower target"),
        ("fed_upper", "FRED federal-funds upper target"),
        ("us_2y", "FRED U.S. 2-year Treasury"),
        ("us_10y", "FRED U.S. 10-year Treasury"),
    ):
        show_source_warning(name, key, source_errors, fallback_dates, saved_retrieval)

    if policy_diff.empty:
        st.info("The policy-rate comparison is unavailable until all three policy series load.")
    else:
        latest_policy = policy_diff.iloc[-1]
        diff_5d = observation_change(
            policy_diff, "Date", "Policy differential", periods=5, business_days_only=True
        )
        diff_1m = calendar_change(policy_diff, "Date", "Policy differential", months=1)

        col1, col2, col3 = st.columns(3)
        col1.metric(
            "Selic target",
            fmt_number(latest_policy["Selic target"], 2, "% p.a."),
        )
        col2.metric(
            "Fed target-range midpoint",
            fmt_number(latest_policy["Fed target midpoint"], 2, "% p.a."),
        )
        col3.metric(
            "Brazil–US policy differential",
            fmt_number(latest_policy["Policy differential"], 2, " pp"),
            delta=fmt_delta(diff_5d.absolute if diff_5d else None, 2, " pp / 5bd"),
        )

        policy_rows = []
        for column, label in (
            ("Selic target", "BCB Selic target"),
            ("Fed target midpoint", "Fed target-range midpoint"),
            ("Policy differential", "Brazil minus US policy rate"),
        ):
            move_5d = observation_change(
                policy_diff, "Date", column, periods=5, business_days_only=True
            )
            move_1m = calendar_change(policy_diff, "Date", column, months=1)
            policy_rows.append(
                {
                    "Measure": label,
                    "Current": latest_policy[column],
                    "Unit": "pp" if column == "Policy differential" else "% p.a.",
                    "5-business-day change (pp)": move_5d.absolute if move_5d else None,
                    "1-month change (pp)": move_1m.absolute if move_1m else None,
                }
            )
        st.dataframe(
            pd.DataFrame(policy_rows),
            hide_index=True,
            width="stretch",
            column_config={
                "Current": st.column_config.NumberColumn(format="%.2f"),
                "5-business-day change (pp)": st.column_config.NumberColumn(format="%+.2f"),
                "1-month change (pp)": st.column_config.NumberColumn(format="%+.2f"),
            },
        )
        st.caption(
            f"Latest common policy observation: {latest_policy['Date']:%d %b %Y}. "
            f"Fed target range: {latest_policy['Fed target lower']:.2f}%–"
            f"{latest_policy['Fed target upper']:.2f}%. The midpoint is calculated, not a bond yield."
        )
        if diff_1m is not None:
            st.caption(
                f"Differential one-month reference observation: {diff_1m.previous_date:%d %b %Y}."
            )
        st.plotly_chart(policy_diff_chart(policy_diff), key="policy_diff_chart")

    st.subheader("U.S. Treasury curve")
    if treasury_curve.empty:
        st.info("The Treasury curve comparison is unavailable until both yield series load.")
    else:
        latest_curve = treasury_curve.iloc[-1]
        curve_5d = observation_change(treasury_curve, "Date", "2s10s", periods=5)
        col1, col2, col3 = st.columns(3)
        col1.metric("U.S. 2-year Treasury", fmt_number(latest_curve["2-year"], 2, "%"))
        col2.metric("U.S. 10-year Treasury", fmt_number(latest_curve["10-year"], 2, "%"))
        col3.metric(
            "U.S. 2s10s slope (10Y − 2Y)",
            fmt_number(latest_curve["2s10s"], 2, " pp"),
            delta=fmt_delta(curve_5d.absolute if curve_5d else None, 2, " pp / 5 obs"),
        )
        st.caption(f"Latest common Treasury observation: {latest_curve['Date']:%d %b %Y}.")

    st.markdown(
        f"Sources: [BCB SGS series 432 — Selic target]({BCB_SELIC_URL}) · "
        f"[FRED DFEDTARL]({FRED_SERIES_URL}/DFEDTARL) · "
        f"[FRED DFEDTARU]({FRED_SERIES_URL}/DFEDTARU) · "
        f"[FRED DGS2]({FRED_SERIES_URL}/DGS2) · "
        f"[FRED DGS10]({FRED_SERIES_URL}/DGS10)"
    )

st.divider()
st.header("Scenario Lab")
st.info(
    "Educational scenario analysis and one conditional paper trade only — not investment advice, "
    "an execution recommendation or a claim of past performance."
)

try:
    brief_pdf_bytes = brief_pdf_path.read_bytes()
except OSError:
    brief_pdf_bytes = None

if brief_pdf_bytes:
    st.download_button(
        "Download the one-page Brazil Rates & FX Trade Brief (PDF)",
        data=brief_pdf_bytes,
        file_name="Brazil_Rates_FX_Trade_Brief.pdf",
        mime="application/pdf",
    )
else:
    st.caption(
        "The downloadable PDF is not available. Regenerate it from the saved research snapshot; "
        "the live dashboard and Scenario Lab remain usable."
    )

if research_snapshot is None:
    st.warning(
        "Scenario Lab research is unavailable or malformed. The three live dashboard views remain usable."
    )
else:
    st.caption(
        f"Fixed data snapshot retrieved {research_snapshot['retrieved_at']} · "
        "Narrative is loaded from saved, reviewable research and is not generated dynamically."
    )

    event_context = research_snapshot["event_context"]
    copom_dates = "–".join(event_context["copom_september_2026"]["meeting_dates"])
    fomc_dates = "–".join(event_context["fomc_september_2026"]["meeting_dates"])
    event_col1, event_col2 = st.columns(2)
    event_col1.metric("September Copom", copom_dates)
    event_col2.metric("September FOMC", fomc_dates)
    st.caption(research_snapshot["scenario_axis"])

    label_audit = research_snapshot["scenario_label_audit"]
    st.caption(label_audit["result"])
    with st.expander("Scenario-label and exchange-pricing audit"):
        fomc_pricing = label_audit["fomc"]
        copom_pricing = label_audit["copom"]
        st.markdown(
            f"**FOMC:** CME FedWatch at {fomc_pricing['pricing_timestamp']} showed "
            f"{fomc_pricing['hike_25bp_probability_percent']:.1f}% for a 25 bp hike and "
            f"{fomc_pricing['no_change_probability_percent']:.1f}% for no change. "
            f"[Official tool]({fomc_pricing['source_url']}) · "
            f"[Methodology]({fomc_pricing['methodology_url']})"
        )
        st.markdown(
            f"**Copom:** The {copom_pricing['pricing_date']} B3 DI1 curve decomposition "
            f"embeds about {copom_pricing['implied_easing_basis_points']:.1f} bp of easing "
            "across the September meeting window. This is not a B3-published probability. "
            f"[Official daily files]({copom_pricing['source_url']}) · "
            f"[DI1 specification]({copom_pricing['methodology_url']})"
        )
        st.caption(fomc_pricing["staleness_note"])
        st.caption(copom_pricing["staleness_note"])

    st.subheader("Three-scenario comparison")
    scenario_rows = []
    for scenario in research_snapshot["scenarios"]:
        scenario_rows.append(
            {
                "Scenario": scenario["name"],
                "Copom outcome and guidance": scenario["copom_outcome_and_guidance"],
                "FOMC outcome and guidance": scenario["fomc_outcome_and_guidance"],
                "Difference from saved expectations": scenario[
                    "difference_from_current_expectations"
                ],
                "Initial BRL/USD direction": scenario["expected_initial_brl_usd_direction"],
                "Brazil front-end": scenario[
                    "expected_initial_brazil_front_end_rates_direction"
                ],
                "US 2-year": scenario["expected_initial_us_2y_direction"],
                "Brazil–US differential": scenario[
                    "expected_brazil_us_differential_change"
                ],
                "Confirmation signal 1": scenario["confirmation_signals"][0],
                "Confirmation signal 2": scenario["confirmation_signals"][1],
                "Principal risk": scenario["principal_risk"],
            }
        )
    st.dataframe(pd.DataFrame(scenario_rows), hide_index=True, width="stretch", height=420)

    trade = research_snapshot["paper_trades"][0]
    st.subheader("Conditional paper trade")
    with st.container(border=True):
        st.markdown(f"### {trade['direction']}")
        st.markdown(f"**Thesis:** {trade['thesis']}")
        st.markdown("**Supporting dashboard evidence**")
        st.markdown("\n".join(f"- {item}" for item in trade["supporting_evidence"]))
        st.markdown(f"**Catalyst:** {trade['catalyst']}")
        st.markdown(f"**Entry logic:** {trade['entry_logic']}")
        ptax_reference = trade["latest_ptax_reference"]
        st.markdown(
            f"**Latest PTAX reference:** {ptax_reference['value']:.4f} "
            f"{ptax_reference['unit']} on {ptax_reference['observation_date']}."
        )
        st.markdown(f"**Invalidation:** {trade['invalidation_condition']}")
        st.markdown(f"**Profit-taking:** {trade['profit_taking_logic']}")
        st.markdown(f"**Expected holding period:** {trade['expected_holding_period']}")
        st.markdown("**Principal risks**")
        st.markdown("\n".join(f"- {item}" for item in trade["principal_risks"]))
        st.markdown(f"**Evidence that changes the view:** {trade['view_change_evidence']}")
        st.markdown(
            f"**Supporting scenario:** {trade['supporting_scenario']}  \n"
            f"**Invalidating scenario:** {trade['invalidating_scenario']}"
        )
        st.caption(trade["disclaimer"])

    st.subheader("Timestamped snapshot")
    snapshot_rows = []
    for series_key, series in research_snapshot["series"].items():
        if "selected_value" in series:
            value = series["selected_value"]
        elif "value" in series:
            value = series["value"]
        elif "midpoint" in series:
            value = series["midpoint"]
        else:
            value = "See source"
        snapshot_rows.append(
            {
                "Series": series["label"],
                "Value": value,
                "Unit": series["unit"],
                "Latest observation": series["latest_observation_date"],
                "Status": series["staleness_note"],
            }
        )
    st.dataframe(pd.DataFrame(snapshot_rows), hide_index=True, width="stretch")

    stale_series = [
        series["label"]
        for series in research_snapshot["series"].values()
        if series["is_stale_at_retrieval"]
    ]
    if stale_series:
        st.caption("Stale or publication-lagged at retrieval: " + "; ".join(stale_series) + ".")

    with st.expander("Latest policy communications and official sources"):
        for authority, communication in research_snapshot["policy_communications"].items():
            st.markdown(f"**{authority.replace('_', ' ').title()}** — {communication['decision']}")
            st.markdown(
                f"[Statement]({communication['statement_url']}) · "
                f"[Minutes]({communication['minutes_url']})"
            )
        st.markdown("**Official source registry**")
        st.markdown(
            "\n".join(
                f"- [{source['label']}]({source['url']})"
                for source in research_snapshot["source_registry"]
            )
        )

st.divider()
st.caption(
    "Educational market-monitoring project. Data can be revised and may be delayed. "
    "This dashboard is not investment advice."
)
