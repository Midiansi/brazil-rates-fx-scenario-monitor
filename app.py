from __future__ import annotations

import json
from datetime import datetime
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


def snapshot_label(value: str) -> str:
    """Turn an ISO snapshot timestamp into a compact, human-readable label."""

    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return value or "unavailable"
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
    .block-container {max-width: 1160px; padding-top: 3.2rem; padding-bottom: 5rem;}
    html, body, .stApp {font-family: "Avenir Next", "Helvetica Neue", Arial, sans-serif;}
    .material-symbols-rounded, [data-testid="stIconMaterial"] {
        font-family: "Material Symbols Rounded" !important;
        font-weight: normal !important;
        font-style: normal !important;
    }
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
    .identity-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1.5rem;
        padding-bottom: 1.2rem;
        margin-bottom: 2.6rem;
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
    .decision-grid {grid-template-columns: repeat(4, minmax(0, 1fr)); margin-top: 1rem;}
    .decision-card {background: var(--macro-panel); border: 1px solid var(--macro-line); border-radius: 14px; padding: 1.25rem 1.3rem 1.4rem; min-height: 174px;}
    .decision-card.signal {box-shadow: inset 0 3px 0 var(--macro-copper);}
    .decision-number {
        color: var(--macro-sand);
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: .78rem;
        margin: .65rem 0 .45rem;
    }
    .decision-copy {color: #d8e4e2; font-size: .94rem; line-height: 1.52;}
    .brief-card, .commodity-card, .trade-detail {background: var(--macro-panel); border: 1px solid var(--macro-line); border-radius: 14px; padding: 1.35rem 1.45rem 1.5rem;}
    .brief-copy {font-size: 1rem; line-height: 1.55; margin-top: .7rem; color: #dbe6e4;}
    .commodity-card {min-height: 210px;}
    .commodity-title {font-size: 1.35rem; font-weight: 610; letter-spacing: -.025em; margin: .45rem 0 .25rem;}
    .commodity-move {color: var(--macro-sand); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .82rem;}
    .commodity-meta {color: var(--macro-muted); font-size: .76rem; margin: .55rem 0 1rem;}
    .commodity-copy {color: #c3d1d3; line-height: 1.55;}
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
    .scenario-strip {grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 1.1rem 0 1.2rem;}
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
    .trade-detail-grid {margin: .75rem 0;}
    .trade-detail strong {display: block; color: var(--macro-sand); margin-bottom: .5rem; font-size: .8rem; letter-spacing: .04em; text-transform: uppercase;}
    .trade-detail {color: #bac9cc; font-size: .9rem; line-height: 1.55;}
    .evidence-list {margin: .4rem 0 0; padding-left: 1.15rem; color: #c8d5d6;}
    .evidence-list li {margin-bottom: .65rem; line-height: 1.5;}
    .mind-change {border: 1px solid var(--macro-line); border-left: 4px solid var(--macro-teal); background: rgba(53, 195, 173, .045); padding: 1rem 1.2rem; margin: 1rem 0 1.4rem; color: #cbd8d8; line-height: 1.55;}
    .proof-grid {grid-template-columns: repeat(4, minmax(0, 1fr)); margin: 1rem 0 1px;}
    .proof-card {background: var(--macro-panel); border: 1px solid var(--macro-line); border-radius: 14px; padding: 1rem 1.05rem 1.1rem;}
    .proof-value {font-size: 1.45rem; color: var(--macro-sand); font-weight: 650;}
    .proof-label {color: var(--macro-muted); font-size: .72rem; line-height: 1.35; margin-top: .25rem;}
    .process-grid {grid-template-columns: repeat(4, minmax(0, 1fr));}
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
        margin-top: 1.2rem;
        border-radius: 16px;
    }
    .builder-name {font-size: 1.55rem; font-weight: 650; letter-spacing: -.035em; margin: .35rem 0 .55rem;}
    .builder-copy {color: #c8d5d6; line-height: 1.56; max-width: 720px;}
    .builder-links {display: flex; justify-content: flex-end; gap: .7rem; flex-wrap: wrap;}
    .builder-links a {border: 1px solid var(--macro-line); padding: .62rem .8rem; text-decoration: none; font-size: .8rem;}
    [data-testid="stDataFrame"] {border: 1px solid var(--macro-line); border-radius: 14px; overflow: hidden; background: var(--macro-panel);}
    [data-testid="stExpander"] {border: 1px solid var(--macro-line); border-radius: 12px; background: rgba(12, 29, 41, .55);}
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
        h1 {font-size: 3.25rem !important;}
        .identity-bar {align-items: flex-start; flex-direction: column; margin-bottom: 2rem;}
        .market-strip, .decision-grid, .brief-grid, .commodity-grid, .scenario-strip,
        .trade-detail-grid, .pricing-grid, .proof-grid, .process-grid, .builder-card {grid-template-columns: 1fr;}
        .path-table {grid-template-columns: 1fr repeat(5, minmax(3rem, 1fr)); overflow-x: auto;}
        .path-cell {padding: .65rem .35rem; font-size: .78rem;}
        .builder-links {justify-content: flex-start;}
        .market-cell {border-right: 0; border-bottom: 1px solid var(--macro-line);}
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
pricing_audit = research.get("scenario_label_audit", {})
thresholds = research.get("trade_threshold_calculations", {})
base_scenario = next((item for item in scenarios if item.get("name") == "Base case"), {})
trade = paper_trades[0] if len(paper_trades) == 1 else {}

language_left, language_right = st.columns([8, 2])
with language_right:
    portuguese = st.toggle("🇧🇷 Português", value=False, key="portuguese")


def ui(english: str, portuguese_text: str) -> str:
    return portuguese_text if portuguese else english

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
        f"Research snapshot: {snapshot_label(retrieved)} · live refresh is optional · every published figure links back to a reviewable source",
        f"Dados salvos em {snapshot_label(retrieved)} · cada número pode ser conferido na fonte",
    )
)

if series:
    tape = (
        (ui("Brazil interest rate", "Juro no Brasil"), f"{series.get('selic_target', {}).get('value', 0):.2f}%", ui("Selic target", "Meta Selic")),
        (ui("One U.S. dollar", "Um dólar"), f"{series.get('ptax_usd_brl_midpoint', {}).get('value', 0):.4f}", ui("Brazilian reais", "reais")),
        (ui("Brazil's rate lead", "Vantagem de juros do Brasil"), f"{series.get('brazil_us_policy_differential', {}).get('value', 0):.2f} pp", ui("above the U.S.", "acima dos EUA")),
        (ui("U.S. two-year rate", "Juro de dois anos nos EUA"), f"{series.get('us_2_year_treasury', {}).get('value', 0):.2f}%", ui("government bond", "título público")),
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

st.header(ui("The short version", "Resumo"))
st.caption(ui("What I expect, why it matters, when I would act and when I would admit the idea is wrong.", "O cenário esperado, por que importa, quando eu agiria e quando admitiria que a ideia está errada."))
if series and base_scenario and trade:
    base_brief = base_scenario.get("brief_summary", {})
    entry_value = thresholds.get("entry_trigger", {}).get("value", 5.22)
    invalidation_value = thresholds.get("invalidation_reference", {}).get("value", 5.16)
    decision_cards = (
        (
            ui("Most expected outcome", "Cenário mais esperado"),
            ui("BRAZIL CUTS / U.S. RAISES", "BRASIL CORTA / EUA SOBEM"),
            ui("Markets currently point to a small Brazilian rate cut and a small U.S. rate increase.", "Os mercados apontam para um pequeno corte no Brasil e uma pequena alta nos EUA."),
            "",
        ),
        (
            ui("Why the real may weaken", "Por que o real pode enfraquecer"),
            ui("THE REAL LOSES SOME SUPPORT", "O REAL PERDE PARTE DO APOIO"),
            ui(f"Brazil's rate lead over the U.S. would fall to about {base_brief.get('differential', '9.88 pp').split('to')[-1].strip()}.", "A vantagem de juros do Brasil sobre os EUA cairia para cerca de 9,88 pontos percentuais."),
            "",
        ),
        (
            ui("When I would act", "Quando eu agiria"),
            ui(f"ONLY ABOVE {entry_value:.2f}", f"SÓ ACIMA DE {entry_value:.2f}"),
            ui("I would buy dollars against reais only after USD/BRL breaks above its recent range.", "Eu só compraria dólares se o USD/BRL rompesse a máxima recente."),
            "signal",
        ),
        (
            ui("When the idea is wrong", "Quando a ideia está errada"),
            ui(f"BELOW {invalidation_value:.2f} TWICE", f"ABAIXO DE {invalidation_value:.2f} DUAS VEZES"),
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
    st.info("The saved decision frame is temporarily unavailable.")

st.header(ui("Why these numbers matter", "Por que esses números importam"))
if series:
    selic = series["selic_target"]["value"]
    gap = series["brazil_us_policy_differential"]["value"]
    fx = series["ptax_usd_brl_midpoint"]
    ipca = series["focus_ipca"]
    briefs = (
        (
            ui("Rates", "Juros"),
            ui(f"Brazil's main interest rate is {selic:.1f}%, about {gap:.1f} percentage points above the comparable U.S. rate. That attracts capital, but also reflects persistent inflation risk.", f"O principal juro brasileiro está em {selic:.1f}%, cerca de {gap:.1f} pontos acima do juro americano comparável. Isso atrai capital, mas também reflete risco de inflação."),
        ),
        (
            ui("Currency", "Câmbio"),
            ui(f"USD/BRL PTAX is {fx['value']:.2f}; BRL weakened {abs(fx['one_month_change_percent']):.1f}% over the month in the saved official data.", f"O dólar de referência está em {fx['value']:.2f}; o real caiu {abs(fx['one_month_change_percent']):.1f}% no mês nos dados oficiais salvos."),
        ),
        (
            ui("Inflation", "Inflação"),
            ui(f"Economists surveyed by Brazil's central bank expect 2026 inflation near {ipca['selected_value']:.1f}%, slightly lower than one month earlier.", f"Economistas consultados pelo Banco Central esperam inflação perto de {ipca['selected_value']:.1f}% em 2026, um pouco abaixo do mês anterior."),
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
    st.info("The saved market snapshot is temporarily unavailable.")

st.header(ui("Why interest rates matter for the real", "Por que os juros importam para o real"))
if series:
    left, right = st.columns([1, 1.7])
    with left:
        st.metric(ui("Selic target", "Meta Selic"), f"{series['selic_target']['value']:.1f}%")
        st.metric(
            ui("Brazil–U.S. rate gap", "Diferença Brasil–EUA"),
            f"{series['brazil_us_policy_differential']['value']:.1f} pp",
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
        path_cells = [f'<div class="path-cell year">{ui("FORECAST", "PREVISÃO")}</div>']
        path_cells.extend(f'<div class="path-cell year">{escape(year)}</div>' for year in years)
        for label, values in (
            (ui("Brazil interest rate", "Juro no Brasil"), focus_selic["values_by_reference_year"]),
            (ui("Inflation", "Inflação"), focus_ipca["values_by_reference_year"]),
        ):
            path_cells.append(f'<div class="path-cell label">{escape(label)}</div>')
            path_cells.extend(
                f'<div class="path-cell value">{float(values[year]):.2f}%</div>' for year in years
            )
        st.markdown('<div class="path-table">' + "".join(path_cells) + "</div>", unsafe_allow_html=True)
        st.caption(
            ui(f"Median forecasts from economists surveyed by Brazil's central bank · latest observation {focus_selic['latest_observation_date']}", f"Medianas da pesquisa do Banco Central · última observação {focus_selic['latest_observation_date']}")
        )

    copom_anchor = pricing_audit.get("copom", {})
    fomc_anchor = pricing_audit.get("fomc", {})
    if copom_anchor and fomc_anchor:
        st.subheader(ui("What markets expect in September", "O que o mercado espera em setembro"))
        pricing_cards = (
            (
                ui("Brazil / B3 interest-rate futures", "Brasil / futuros de juros da B3"),
                ui("Close to a 0.25-point cut", "Quase um corte de 0,25 ponto"),
                ui("This estimate comes from market prices around Brazil's September central-bank meeting.", "Estimativa baseada nos preços de mercado ao redor da reunião de setembro."),
            ),
            (
                ui("United States / CME FedWatch", "Estados Unidos / CME FedWatch"),
                ui(f"{fomc_anchor.get('hike_25bp_probability_percent', 0):.1f}% chance of a 0.25% rise", f"{fomc_anchor.get('hike_25bp_probability_percent', 0):.1f}% de chance de alta de 0,25 ponto"),
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

st.header(ui("The real against the dollar", "O real frente ao dólar"))
if series:
    fx = series["ptax_usd_brl_midpoint"]
    left, right = st.columns([1, 1.7])
    with left:
        st.metric("USD/BRL", f"{fx['value']:.2f}")
        st.caption(f"{ui('Official reference', 'Referência oficial')} · {fx['latest_observation_date']}")
    with right:
        st.subheader(ui("What changed", "O que mudou"))
        move = fx["one_month_change_percent"]
        verb = "weakened" if move > 0 else "strengthened"
        st.write(ui(f"BRL {verb} about {abs(move):.1f}% against USD over the past month. The move is best read alongside Brazil's still-large rate advantage.", f"O real caiu cerca de {abs(move):.1f}% frente ao dólar no último mês. O movimento deve ser lido junto com a ainda grande vantagem de juros do Brasil."))

    observed_range = fx.get("twenty_observation_range", {})
    if observed_range:
        low = float(observed_range["low"])
        high = float(observed_range["high"])
        current_position = bounded_position(float(fx["value"]), low, high)
        entry_value = float(thresholds.get("entry_trigger", {}).get("value", high))
        entry_position = bounded_position(entry_value, low, high)
        st.subheader(ui("Where USD/BRL sits in its recent range", "Onde o dólar está na faixa recente"))
        st.markdown(
            f'<div class="range-box"><div class="brief-label">PTAX range / saved observations</div>'
            f'<div class="range-track"><div class="range-fill" style="width:{current_position:.1f}%"></div>'
            f'<div class="range-dot" style="left:{current_position:.1f}%"></div>'
            f'<div class="range-trigger" style="left:{entry_position:.1f}%"></div></div>'
            f'<div class="range-labels"><span>{ui("LOW", "MÍNIMA")} {low:.4f}</span><span>{ui("CURRENT", "ATUAL")} {float(fx["value"]):.4f}</span>'
            f'<span>{ui("HIGH", "MÁXIMA")} {high:.4f}</span></div><div class="range-caption">'
            f'{ui(f"The orange marker is where I would consider the idea. Until USD/BRL closes above {entry_value:.2f}, there is no trade.", f"A marca laranja indica onde eu consideraria a ideia. Até o dólar fechar acima de {entry_value:.2f}, não há operação.")}</div></div>',
            unsafe_allow_html=True,
        )

st.header(ui("Brazil's export backdrop", "O cenário das exportações brasileiras"))
st.write(ui(
    "Brazil earns dollars by exporting products such as oil, iron ore, soybeans and sugar. Their prices can therefore affect the real, company earnings and inflation.",
    "O Brasil recebe dólares ao exportar petróleo, minério de ferro, soja e açúcar. Por isso, esses preços podem afetar o real, os lucros das empresas e a inflação.",
))
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

st.header(ui("Three ways the September meetings could go", "Três caminhos para as reuniões de setembro"))
st.caption(ui("Three simple stories: Brazil stays tougher, follows the expected path or cuts faster.", "Três histórias simples: o Brasil mantém juros altos, segue o esperado ou corta mais rápido."))
if len(scenarios) == 3:
    scenario_rows = []
    scenario_cards = []
    friendly_scenarios = {
        "Hawkish relative to expectations": (ui("Brazil stays tougher", "Brasil mantém juros altos"), ui("The real would probably strengthen", "O real provavelmente se fortaleceria")),
        "Base case": (ui("Most expected path", "Caminho mais esperado"), ui("The real would probably weaken slightly", "O real provavelmente enfraqueceria um pouco")),
        "Dovish relative to expectations": (ui("Brazil cuts faster", "Brasil corta mais rápido"), ui("The real would probably weaken more", "O real provavelmente enfraqueceria mais")),
    }
    for scenario in scenarios:
        brief = scenario.get("brief_summary", {})
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
            f'<div class="scenario-diff">{escape(str(friendly_differentials.get(scenario.get("name", ""), brief.get("differential", ""))))}</div></article>'
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
    with st.expander(ui("See the exact decisions, evidence and risks", "Ver decisões, evidências e riscos em detalhe")):
        st.dataframe(scenario_rows, hide_index=True, width="stretch")
        for scenario in scenarios:
            st.markdown(f"#### {scenario.get('name', 'Scenario')}")
            scenario_left, scenario_right = st.columns(2)
            with scenario_left:
                st.markdown("**Policy path**")
                st.write(scenario.get("copom_outcome_and_guidance", "Unavailable"))
                st.write(scenario.get("fomc_outcome_and_guidance", "Unavailable"))
                st.markdown("**Why it differs from pricing**")
                st.write(scenario.get("difference_from_current_expectations", "Unavailable"))
            with scenario_right:
                st.markdown("**What should confirm it**")
                for signal in scenario.get("confirmation_signals", []):
                    st.markdown(f"- {signal}")
                st.markdown("**Principal risk**")
                st.write(scenario.get("principal_risk", "Unavailable"))
            st.divider()
else:
    st.info("The saved three-scenario comparison is temporarily unavailable.")

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

st.subheader(ui("A paper trade - only if the market confirms it", "Uma operação simulada - só com confirmação do mercado"))
if len(paper_trades) == 1:
    trade = paper_trades[0]
    entry_value = float(thresholds.get("entry_trigger", {}).get("value", 5.22))
    invalidation_value = float(thresholds.get("invalidation_reference", {}).get("value", 5.16))
    review_low = float(thresholds.get("review_zone", {}).get("low", 5.35))
    review_high = float(thresholds.get("review_zone", {}).get("high", 5.36))
    st.markdown(
        f'<div class="trade-card"><div class="trade-kicker">{ui("Conditional / no position at snapshot", "Condicional / sem posição no momento")}</div>'
        f'<div class="trade-title">{ui(f"Buy dollars only above {entry_value:.2f}", f"Comprar dólares só acima de {entry_value:.2f}")}</div>'
        f'<div class="trade-thesis">{ui("If Brazil cuts interest rates while the U.S. raises them, holding reais becomes slightly less attractive. Because much of that path is already expected, I would act only if price confirms it; fiscal news, export prices and global risk can still dominate.", "Se o Brasil cortar juros enquanto os EUA os elevam, manter reais fica um pouco menos atraente. Como boa parte desse caminho já é esperada, eu só agiria se o preço confirmasse; notícias fiscais, exportações e o risco global ainda podem dominar.")}</div></div>',
        unsafe_allow_html=True,
    )
    trade_details = (
        (ui("Wait for confirmation", "Esperar confirmação"), ui(f"Do nothing at the current reference. Consider the trade only after USD/BRL closes above {entry_value:.2f}.", f"Não fazer nada no preço atual. Considerar a operação apenas após um fechamento acima de {entry_value:.2f}.")),
        (ui("Admit it is wrong", "Admitir quando está errada"), ui(f"Leave the trade after two closes below {invalidation_value:.2f}, or if the expected rate moves do not happen.", f"Sair após dois fechamentos abaixo de {invalidation_value:.2f}, ou se os movimentos de juros esperados não ocorrerem.")),
        (ui("Reassess the reward", "Reavaliar o retorno"), ui(f"Review the position around {review_low:.2f}-{review_high:.2f}; do not treat that range as a guaranteed target.", f"Reavaliar a posição perto de {review_low:.2f}-{review_high:.2f}; essa faixa não é um alvo garantido.")),
        (
            ui("Why September matters", "Por que setembro importa"),
            ui("Brazil's and the U.S. central banks announce their decisions on the same two days, creating a clear test of the idea.", "Os bancos centrais do Brasil e dos EUA anunciam suas decisões nos mesmos dois dias, criando um teste claro da ideia."),
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
        + ui(f'USD/BRL fails to stay above {entry_value:.2f}; Brazil keeps its rate lead; or new fiscal, export or global-market evidence strengthens the real.', f'O dólar não se mantém acima de {entry_value:.2f}; o Brasil mantém sua vantagem de juros; ou novas informações fiscais, de exportação ou globais fortalecem o real.')
        + "</div>",
        unsafe_allow_html=True,
    )
    with st.expander(ui("See the calculations and full trade rules", "Ver cálculos e regras completas")):
        st.markdown("**Original thesis**")
        st.write(trade.get("thesis", "Unavailable"))
        st.markdown("**Entry rule**")
        st.write(trade.get("entry_logic", "Unavailable"))
        st.markdown("**Invalidation rule**")
        st.write(trade.get("invalidation_condition", "Unavailable"))
        st.markdown("**Review-zone calculation**")
        st.write(trade.get("profit_taking_logic", "Unavailable"))
else:
    st.info("The saved conditional paper trade is temporarily unavailable.")

brief_path = ROOT / "outputs" / "Brazil_Rates_FX_Trade_Brief.pdf"
try:
    brief_bytes = brief_path.read_bytes()
except OSError:
    brief_bytes = b""
if brief_bytes:
    st.download_button(
        ui("Download the one-page market brief (PDF)", "Baixar o relatório de uma página (PDF)"),
        data=brief_bytes,
        file_name=brief_path.name,
        mime="application/pdf",
    )

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
    ("01 / Evidence", "Use primary sources", "Start with central-bank and exchange data, and keep every date visible."),
    ("02 / Scenarios", "Separate the paths", "Ask what changes if Brazil stays tougher, follows expectations or cuts faster."),
    ("03 / Decision", "Wait for confirmation", "Set the entry, exit and risks before any trade would begin."),
    ("04 / Challenge", "Try to break it", "Check the numbers, test the rules and keep the page working when a data feed fails."),
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
    '<div class="builder-card"><div><div class="macro-kicker">Project author</div>'
    '<div class="builder-name">Romeo Mugnier de Almeida</div>'
    '<div class="builder-copy">EPFL Mechanical Engineering student based between São Paulo and Lausanne. '
    'I built this project to show how I approach an ambiguous market question: find the primary data, '
    'separate expectations from outcomes, define a decision rule and state in advance what would prove the '
    'view wrong. Every conclusion is linked to saved evidence and a rule that another reader can check.</div>'
    '</div><div class="builder-links">'
    '<a href="https://github.com/Midiansi/brazil-rates-fx-scenario-monitor" target="_blank" '
    'rel="noopener noreferrer">Inspect the code</a><a href="https://linkedin.com/in/romeomugnier" '
    'target="_blank" rel="noopener noreferrer">LinkedIn profile</a></div></div>',
    unsafe_allow_html=True,
)

with st.expander(ui("Data and method", "Dados e método")):
    st.write(
        "For readers who want to check the work: the page uses a saved copy of public data so it can be "
        "reproduced even when a source is temporarily unavailable. Commodity observations keep their real "
        "publication dates rather than being forced into a false like-for-like index."
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

with st.expander(ui("Official source links", "Fontes oficiais")):
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
    f"Built by Romeo Mugnier de Almeida · research snapshot {snapshot_label(retrieved)} · "
    "educational analysis, not investment advice"
)
