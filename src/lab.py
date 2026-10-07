"""Small interactive teaching scenarios. No network, pandas or live execution."""
from __future__ import annotations

import csv
import io
import math
from html import escape
from typing import Any

import streamlit as st

from src import formatting as f, risk
from src.lab_content import TEXT


def _metrics(labels: list[str], values: list[str], note: str, detail: str = "") -> None:
    cells = "".join(f'<div><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>' for label, value in zip(labels, values))
    st.html(f'<div class="bm"><dl class="lab-metrics" aria-live="polite">{cells}</dl>{detail}<p class="fig-caption">{escape(note)}</p></div>')


def _table(headers: list[str], rows: list[list[str]], title: str) -> str:
    head = "".join(f'<th scope="col">{escape(value)}</th>' for value in headers)
    body = "".join('<tr>' + "".join(f'<th scope="row">{escape(value)}</th>' if i == 0 else f'<td class="n">{escape(value)}</td>' for i, value in enumerate(row)) + '</tr>' for row in rows)
    return f'<div class="bm"><p class="label">{escape(title)}</p><div class="table-wrap" tabindex="0" role="region" aria-label="{escape(title)}"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div></div>'


def _download(t: dict[str, Any], scenario: str, inputs: dict[str, Any], results: dict[str, Any]) -> None:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["scenario", "kind", "field", "value"])
    for kind, data in (("input", inputs), ("result", results)):
        for key, value in data.items():
            writer.writerow([scenario, kind, key, value])
    st.download_button(t["download_scenario"], output.getvalue(), f"brazilmacro_{scenario}.csv", "text/csv", on_click="ignore", key="scenario_csv")


def render(lang: str, saved_thesis: dict[str, Any], lens: str = "quant") -> None:
    """One mode at a time keeps the page light and the mobile controls usable."""
    t, lang = TEXT.get(lang, TEXT["en"]), lang if lang in TEXT else "en"
    modes = ("rates", "fx", "producer")
    mode = st.radio(t["lab_nav"], modes, index=2 if lens == "commodities" else 0,
                    format_func=lambda item: t["lab_modes"][modes.index(item)], horizontal=True,
                    label_visibility="collapsed", key="scenario_mode")
    money = lambda value: "R$ " + f.num(0 if abs(value) < .5 else value, 0, lang)
    ev = saved_thesis.get("evidence") or {}
    study = saved_thesis.get("study") or {}
    try:
        if mode == "rates":
            curve = study.get("curve")
            raw_rows = curve.get("rows") if isinstance(curve, dict) else []
            curve_rows = [row for row in (raw_rows if isinstance(raw_rows, list) else [])
                          if isinstance(row, dict) and isinstance(row.get("years"), (int, float))
                          and isinstance(row.get("after"), (int, float)) and math.isfinite(row["after"])]
            complete_curve = {row.get("years") for row in curve_rows} >= {.5, 1, 2, 3, 5, 10}
            st.caption(t["rate_intro"] if complete_curve else t["rate_intro_fallback"])
            left, right = st.columns(2)
            with left:
                years = st.select_slider(t["maturity"], options=[.5, 1.0, 2.0, 3.0, 5.0, 10.0], value=2.0, key="rate_years")
                principal = st.number_input(t["principal"], min_value=1000.0, max_value=100000000.0, value=1000000.0, step=10000.0, key="rate_principal")
            matching = next((row["after"] for row in curve_rows if row["years"] == years), 13.0)
            # The default follows the selected tenor. A visitor may then override it.
            with right:
                annual_yield = st.number_input(t["yield"], min_value=0.0, max_value=40.0, value=float(round(matching, 3)), step=.1, format="%.3f", key=f"rate_yield_{years}")
                shock = st.slider(t["rate_shock"], min_value=-200, max_value=200, value=100, step=25, key="rate_shock")
            result = risk.zero_coupon_stress(principal, annual_yield / 100, round(years * 252), shock)
            approximation = -result["price"] * result["modified_duration"] * shock / 10000
            detail = f'<p class="small muted">{escape(t["rate_detail"])}: {escape(money(approximation))} · {escape(t["rate_gap"])}: {escape(money(result["pnl"] - approximation))}</p>'
            _metrics(t["rate_metrics"], [money(result["price"]), "R$ " + f.num(result["dv01"], 2, lang), money(result["pnl"]) + " / " + f.pct(result["pnl_pct"], 2, lang, signed=True)], t["rate_note"], detail)
            rows = []
            for shift in (-100, -50, 0, 50, 100):
                stressed = risk.zero_coupon_stress(principal, annual_yield / 100, round(years * 252), shift)
                approx = -result["price"] * result["modified_duration"] * shift / 10000
                rows.append([f.num(shift, 0, lang, signed=True), money(stressed["pnl"]), money(approx)])
            st.html(_table(t["rate_cols"], rows, t["result_label"]))
            _download(t, mode, {"face_value_brl": principal, "annual_yield_pct": annual_yield, "years": years, "shock_bp": shock, "source_date": saved_thesis.get("data_as_of")}, {**result, "duration_pnl_brl": approximation})
        elif mode == "fx":
            st.caption(t["fx_intro"])
            left, right = st.columns(2)
            fed = ev.get("fed_range") or {}
            midpoint = (fed.get("lower", 3.75) + fed.get("upper", 4.0)) / 2
            with left:
                br_rate = st.number_input(t["br_rate"], min_value=0.0, max_value=40.0, value=float(ev.get("selic", {}).get("value", 13.75)), step=.25, key="br_rate")
                us_rate = st.number_input(t["us_rate"], min_value=0.0, max_value=40.0, value=float(midpoint), step=.25, format="%.3f", key="us_rate")
            with right:
                days = st.slider(t["days"], 1, 252, 21, key="carry_days")
                fx = st.slider(t["fx_shock"], -20.0, 20.0, 5.0, step=.5, key="carry_fx")
            result = risk.carry_stress(br_rate / 100, us_rate / 100, days, fx)
            _metrics(t["fx_metrics"], [f.pct(result[field], 2, lang, signed=True) for field in ("carry_before_fx_pct", "fx_only_return_pct", "net_return_pct")], t["fx_note"])
            _download(t, mode, {"br_rate_pct": br_rate, "us_rate_pct": us_rate, "business_days": days, "usd_brl_change_pct": fx}, result)
        else:
            st.caption(t["producer_intro"])
            left, right = st.columns(2)
            with left:
                receipts = st.number_input(t["revenue"], 1000.0, 100000000.0, 1000000.0, step=10000.0, key="producer_receipts")
                spot = st.number_input(t["spot"], .1, 20.0, float(ev.get("ptax", {}).get("value", 5.0)), step=.01, format="%.4f", key="producer_spot")
                forward = st.number_input(t["forward"], .1, 20.0, float(ev.get("ptax", {}).get("value", 5.0)), step=.01, format="%.4f", key="producer_forward")
            with right:
                commodity = st.slider(t["commodity_shock"], -30.0, 30.0, -10.0, step=1.0, key="producer_commodity")
                fx = st.slider(t["fx_shock"], -20.0, 20.0, 5.0, step=.5, key="producer_fx")
                hedge = st.slider(t["hedge"], 0, 100, 50, step=5, key="producer_hedge")
            result = risk.producer_stress(receipts, spot, commodity, fx, hedge, forward)
            _metrics(t["producer_metrics"], [money(result["baseline_brl"]), f.pct(result["unhedged_change_pct"], 2, lang, signed=True), money(result["hedged_brl"])], t["producer_note"], f'<p class="small muted">{escape(t["hedge_difference"])}: {escape(money(result["hedged_brl"] - result["unhedged_brl"]))}</p>')
            rows = [[f.pct(c, 0, lang, signed=True), *[f.pct(((1 + c / 100) * (1 + x / 100) - 1) * 100, 1, lang, signed=True) for x in (-5, 0, 5)]] for c in (-10, 0, 10)]
            st.html(_table(t["producer_cols"], rows, t["matrix_label"]))
            _download(t, mode, {"receipts_usd": receipts, "spot_brl_per_usd": spot, "commodity_change_pct": commodity, "fx_change_pct": fx, "hedge_pct": hedge, "forward_brl_per_usd": forward}, result)
    except (ValueError, OverflowError):
        st.error(t["error"])
