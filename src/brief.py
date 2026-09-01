from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable

from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from src.research import load_research_snapshot, validate_research_snapshot


ACCENT = HexColor("#1F4E5F")
INK = HexColor("#172126")
MUTED = HexColor("#5B686E")
PALE = HexColor("#F1F4F5")
GRID = HexColor("#CDD5D8")
WHITE = white
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 28.0
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)


@dataclass(frozen=True)
class TradeThresholds:
    entry: Decimal
    invalidation: Decimal
    range_high: Decimal
    range_midpoint: Decimal
    range_width: Decimal
    measured_move: Decimal
    review_low: Decimal
    review_high: Decimal


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def derive_trade_thresholds(snapshot: dict[str, Any]) -> TradeThresholds:
    saved_range = snapshot["series"]["ptax_usd_brl_midpoint"]["twenty_observation_range"]
    high = _decimal(saved_range["high"])
    midpoint = _decimal(saved_range["midpoint"])
    width = _decimal(saved_range["width"])
    cent = Decimal("0.01")
    measured_move = high + width
    return TradeThresholds(
        entry=high.quantize(cent, rounding=ROUND_HALF_UP),
        invalidation=midpoint.quantize(cent, rounding=ROUND_HALF_UP),
        range_high=high,
        range_midpoint=midpoint,
        range_width=width,
        measured_move=measured_move,
        review_low=(measured_move * 100).to_integral_value(rounding=ROUND_FLOOR) / 100,
        review_high=(measured_move * 100).to_integral_value(rounding=ROUND_CEILING) / 100,
    )


def _format_date(value: str) -> str:
    parsed = date.fromisoformat(value)
    return parsed.strftime("%d %b %Y")


def _format_timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.strftime("%d %b %Y %H:%M %Z")


def build_brief_context(payload: dict[str, Any]) -> dict[str, Any]:
    snapshot = validate_research_snapshot(payload)
    thresholds = derive_trade_thresholds(snapshot)
    series = snapshot["series"]
    ptax = series["ptax_usd_brl_midpoint"]
    focus_selic = series["focus_selic"]
    focus_ipca = series["focus_ipca"]
    differential = series["brazil_us_policy_differential"]
    us_2y = series["us_2_year_treasury"]
    curve = series["us_2s10s"]
    audit = snapshot["scenario_label_audit"]
    trade = snapshot["paper_trades"][0]

    usd_brl_five_day = ptax["five_business_day_change_percent"] / 100
    brl_usd_five_day = ((1 / (1 + usd_brl_five_day)) - 1) * 100

    market_metrics = [
        {
            "label": "USD/BRL PTAX midpoint",
            "value": f"{ptax['value']:.4f} BRL per USD",
            "date": _format_date(ptax["latest_observation_date"]),
        },
        {
            "label": "BRL/USD - 5 observations",
            "value": f"{brl_usd_five_day:+.2f}%",
            "date": _format_date(ptax["latest_observation_date"]),
        },
        {
            "label": "Selic target",
            "value": f"{series['selic_target']['value']:.2f}% p.a.",
            "date": _format_date(series["selic_target"]["latest_observation_date"]),
        },
        {
            "label": "Fed target midpoint",
            "value": f"{series['fed_target_range']['midpoint']:.3f}% p.a.",
            "date": _format_date(series["fed_target_range"]["latest_observation_date"]),
        },
        {
            "label": "Brazil-US policy differential",
            "value": f"{differential['value']:.3f} pp",
            "date": _format_date(differential["latest_observation_date"]),
        },
        {
            "label": "US 2s10s slope",
            "value": f"{curve['value']:+.2f} pp",
            "date": _format_date(curve["latest_observation_date"]),
        },
    ]

    what_changed = [
        (
            f"2026 Focus Selic was unchanged over five observations and fell "
            f"{abs(focus_selic['selected_1_month_change_pp']):.2f} pp over one month; "
            f"Focus IPCA edged down {abs(focus_ipca['selected_5_business_day_change_pp']):.4f} pp "
            "over five observations."
        ),
        (
            f"BRL/USD fell {abs(brl_usd_five_day):.2f}% over five observations, the inverse "
            "of the saved PTAX USD/BRL move, indicating mild BRL weakening."
        ),
        (
            f"The Brazil-US policy differential was unchanged over five business days and "
            f"narrowed {abs(differential['one_month_change_pp']):.2f} pp over one month; "
            f"US 2s10s flattened {abs(curve['five_business_day_change_pp']):.2f} pp over five observations."
        ),
    ]

    scenario_rows = []
    for scenario in snapshot["scenarios"]:
        compact = scenario["brief_summary"]
        scenario_rows.append(
            {
                "scenario": scenario["name"],
                "copom": compact["copom"],
                "fomc": compact["fomc"],
                "differential": compact["differential"],
                "brl_usd_pressure": compact["brl_usd_pressure"],
                "confirmation": compact["confirmation"],
            }
        )

    entry_text = (
        f"A daily PTAX midpoint closes above {thresholds.entry:.2f}, the rounded saved "
        f"20-observation high of {thresholds.range_high:.4f}, with US 2Y near or above "
        f"{us_2y['value']:.2f}% or no widening in the policy differential."
    )
    invalidation_text = (
        f"After entry, two consecutive PTAX midpoints below {thresholds.invalidation:.2f}, "
        f"or a differential still near/above {differential['value']:.3f} pp because Copom "
        "does not ease and the FOMC does not hike."
    )
    review_text = (
        f"{thresholds.review_low:.2f}-{thresholds.review_high:.2f}; saved high "
        f"{thresholds.range_high:.4f} + range width {thresholds.range_width:.4f} = "
        f"{thresholds.measured_move:.4f}, bracketed to adjacent cents."
    )
    latest_reference = (
        f"{trade['latest_ptax_reference']['value']:.4f} BRL per USD on "
        f"{_format_date(trade['latest_ptax_reference']['observation_date'])}."
    )

    bottom_line = [
        (
            f"The trade activates only after a daily PTAX midpoint closes above "
            f"{thresholds.entry:.2f} with US 2Y near/above {us_2y['value']:.2f}% or no widening "
            "in the Brazil-US policy differential."
        ),
        (
            f"Abandon the view on two post-entry PTAX midpoints below {thresholds.invalidation:.2f}, "
            "a failure of the differential to narrow, materially lower US 2Y, or the "
            f"{trade['invalidating_scenario'].lower()} outcome."
        ),
    ]

    source_links = [
        ("BCB Focus", series["focus_selic"]["source_url"]),
        ("BCB PTAX", ptax["source_url"]),
        ("BCB SGS", series["selic_target"]["source_url"]),
        ("Federal Reserve", snapshot["policy_communications"]["fomc_latest"]["statement_url"]),
        ("FRED", series["us_2_year_treasury"]["source_url"]),
        ("CME", audit["fomc"]["source_url"]),
        ("B3", audit["copom"]["source_url"]),
    ]

    return {
        "snapshot": snapshot,
        "snapshot_display": _format_timestamp(snapshot["retrieved_at"]),
        "market_metrics": market_metrics,
        "what_changed": what_changed,
        "scenario_rows": scenario_rows,
        "trade": {
            "direction": trade["direction"],
            "status": "NO CURRENT POSITION - activates only if the entry condition occurs",
            "thesis": trade["thesis"],
            "entry": entry_text,
            "latest_reference": latest_reference,
            "invalidation": invalidation_text,
            "review": review_text,
            "holding_period": trade["expected_holding_period"],
            "supporting_scenario": trade["supporting_scenario"],
            "risks": trade["brief_principal_risks"],
        },
        "bottom_line": bottom_line,
        "sources": source_links,
        "limitations": (
            "PTAX is a reference rate; Focus is survey data. Initial reactions remain conditional "
            "on broader risk sentiment, commodities and Brazilian fiscal developments. B3's Copom "
            "move is a curve decomposition that ignores term premia, not an exchange probability."
        ),
        "audit_summary": (
            f"CME FedWatch ({audit['fomc']['pricing_timestamp']}): "
            f"{audit['fomc']['hike_25bp_probability_percent']:.1f}% 25 bp hike / "
            f"{audit['fomc']['no_change_probability_percent']:.1f}% hold. B3 DI1 "
            f"({audit['copom']['pricing_date']}): about "
            f"{audit['copom']['implied_easing_basis_points']:.1f} bp of easing across Copom."
        ),
        "thresholds": thresholds,
    }


def _ascii_hyphens(text: str) -> str:
    return (
        str(text)
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
        .replace("\u00a0", " ")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )


def _wrap(text: str, width: float, font: str, size: float) -> list[str]:
    words = _ascii_hyphens(text).split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if stringWidth(candidate, font, size) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _draw_wrapped(
    pdf: Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    *,
    font: str = "Helvetica",
    size: float = 7.4,
    leading: float = 9.0,
    color: Color = INK,
) -> float:
    pdf.setFont(font, size)
    pdf.setFillColor(color)
    for line in _wrap(text, width, font, size):
        pdf.drawString(x, y, line)
        y -= leading
    return y


def _draw_section_heading(pdf: Canvas, text: str, y: float) -> float:
    pdf.setFillColor(ACCENT)
    pdf.setFont("Helvetica-Bold", 9.0)
    pdf.drawString(MARGIN, y, _ascii_hyphens(text).upper())
    pdf.setStrokeColor(ACCENT)
    pdf.setLineWidth(0.8)
    pdf.line(MARGIN, y - 4, PAGE_WIDTH - MARGIN, y - 4)
    return y - 13


def _draw_metric_cards(pdf: Canvas, metrics: list[dict[str, str]], y_top: float) -> float:
    gap = 5.0
    card_width = (CONTENT_WIDTH - (2 * gap)) / 3
    card_height = 37.0
    for index, metric in enumerate(metrics):
        row, column = divmod(index, 3)
        x = MARGIN + column * (card_width + gap)
        y = y_top - row * (card_height + 5) - card_height
        pdf.setFillColor(PALE)
        pdf.setStrokeColor(GRID)
        pdf.roundRect(x, y, card_width, card_height, 2, fill=1, stroke=1)
        pdf.setFillColor(ACCENT)
        pdf.rect(x, y, 2.2, card_height, fill=1, stroke=0)
        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica", 6.4)
        pdf.drawString(x + 7, y + 26, _ascii_hyphens(metric["label"]))
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica-Bold", 9.5)
        pdf.drawString(x + 7, y + 14, _ascii_hyphens(metric["value"]))
        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica", 6.2)
        pdf.drawRightString(x + card_width - 6, y + 5, metric["date"])
    return y_top - (2 * card_height) - 10


def _draw_bullets(pdf: Canvas, bullets: Iterable[str], y: float, width: float) -> float:
    for bullet in bullets:
        pdf.setFillColor(ACCENT)
        pdf.circle(MARGIN + 2.5, y + 2.2, 1.2, fill=1, stroke=0)
        y = _draw_wrapped(pdf, bullet, MARGIN + 9, y, width - 9, size=7.15, leading=8.5)
        y -= 1.5
    return y


def _draw_scenario_table(pdf: Canvas, rows: list[dict[str, str]], y_top: float) -> float:
    columns = [
        ("Scenario", "scenario", 74.0),
        ("Copom", "copom", 83.0),
        ("FOMC", "fomc", 87.0),
        ("Differential", "differential", 77.0),
        ("Likely initial BRL/USD pressure", "brl_usd_pressure", 92.0),
        ("Key confirmation", "confirmation", CONTENT_WIDTH - 413.0),
    ]
    header_height = 22.0
    pdf.setFillColor(ACCENT)
    pdf.rect(MARGIN, y_top - header_height, CONTENT_WIDTH, header_height, fill=1, stroke=0)
    x = MARGIN
    for heading, _, width in columns:
        _draw_wrapped(
            pdf,
            heading,
            x + 3,
            y_top - 8,
            width - 6,
            font="Helvetica-Bold",
            size=6.3,
            leading=6.7,
            color=WHITE,
        )
        x += width
    y = y_top - header_height
    for row_index, row in enumerate(rows):
        wrapped_cells = [
            _wrap(row[key], width - 6, "Helvetica", 6.55) for _, key, width in columns
        ]
        row_height = max(27.0, max(len(lines) for lines in wrapped_cells) * 7.4 + 6)
        pdf.setFillColor(WHITE if row_index % 2 == 0 else PALE)
        pdf.setStrokeColor(GRID)
        pdf.rect(MARGIN, y - row_height, CONTENT_WIDTH, row_height, fill=1, stroke=1)
        x = MARGIN
        for column_index, ((_, _, width), lines) in enumerate(zip(columns, wrapped_cells)):
            if column_index:
                pdf.line(x, y, x, y - row_height)
            pdf.setFillColor(INK)
            pdf.setFont("Helvetica-Bold" if column_index == 0 else "Helvetica", 6.55)
            text_y = y - 9
            for line in lines:
                pdf.drawString(x + 3, text_y, line)
                text_y -= 7.4
            x += width
        y -= row_height
    return y


def _measure_label_value(label: str, value: str, width: float) -> float:
    label_width = 66.0
    lines = _wrap(value, width - label_width - 12, "Helvetica", 7.15)
    return max(9.0, len(lines) * 8.2)


def _draw_label_value(
    pdf: Canvas,
    label: str,
    value: str,
    x: float,
    y: float,
    width: float,
) -> float:
    label_width = 66.0
    pdf.setFillColor(ACCENT)
    pdf.setFont("Helvetica-Bold", 7.15)
    pdf.drawString(x, y, _ascii_hyphens(label))
    return _draw_wrapped(
        pdf,
        value,
        x + label_width,
        y,
        width - label_width,
        size=7.15,
        leading=8.2,
    )


def _draw_paper_trade(pdf: Canvas, trade: dict[str, Any], y_top: float) -> float:
    content_width = CONTENT_WIDTH - 16
    rows = [
        ("Thesis", trade["thesis"]),
        ("Entry trigger", trade["entry"]),
        ("PTAX reference", trade["latest_reference"]),
        ("Invalidation", trade["invalidation"]),
        ("Review zone", trade["review"]),
        (
            "Horizon / case",
            f"{trade['holding_period']} Supporting scenario: {trade['supporting_scenario']}.",
        ),
    ]
    row_height = sum(_measure_label_value(label, value, content_width) + 2 for label, value in rows)
    risks_height = sum(max(8.2, len(_wrap(risk, content_width - 10, "Helvetica", 6.9)) * 7.8) for risk in trade["risks"])
    box_height = 31 + row_height + risks_height + 13
    y_bottom = y_top - box_height
    pdf.setFillColor(PALE)
    pdf.setStrokeColor(ACCENT)
    pdf.setLineWidth(0.8)
    pdf.roundRect(MARGIN, y_bottom, CONTENT_WIDTH, box_height, 3, fill=1, stroke=1)

    pdf.setFillColor(ACCENT)
    pdf.setFont("Helvetica-Bold", 10.2)
    pdf.drawString(MARGIN + 8, y_top - 14, trade["direction"].upper())
    pdf.setFont("Helvetica-Bold", 6.8)
    pdf.drawRightString(PAGE_WIDTH - MARGIN - 8, y_top - 13, trade["status"])

    y = y_top - 27
    for label, value in rows:
        y = _draw_label_value(pdf, f"{label}:", value, MARGIN + 8, y, content_width)
        y -= 2

    pdf.setFillColor(ACCENT)
    pdf.setFont("Helvetica-Bold", 7.15)
    pdf.drawString(MARGIN + 8, y, "Principal risks:")
    y -= 8
    for index, risk in enumerate(trade["risks"], start=1):
        y = _draw_wrapped(
            pdf,
            f"{index}. {risk}",
            MARGIN + 16,
            y,
            content_width - 8,
            size=6.9,
            leading=7.8,
        )
    return y_bottom


def _draw_link_labels(
    pdf: Canvas,
    links: list[tuple[str, str]],
    x: float,
    y: float,
    max_width: float,
) -> float:
    pdf.setFont("Helvetica", 6.2)
    cursor_x = x
    for index, (label, url) in enumerate(links):
        display = _ascii_hyphens(label)
        suffix = " | " if index < len(links) - 1 else ""
        label_width = stringWidth(display, "Helvetica", 6.2)
        suffix_width = stringWidth(suffix, "Helvetica", 6.2)
        if cursor_x + label_width + suffix_width > x + max_width:
            y -= 7.5
            cursor_x = x
        pdf.setFillColor(ACCENT)
        pdf.drawString(cursor_x, y, display)
        pdf.linkURL(url, (cursor_x, y - 1, cursor_x + label_width, y + 6), relative=0)
        cursor_x += label_width
        pdf.setFillColor(MUTED)
        pdf.drawString(cursor_x, y, suffix)
        cursor_x += suffix_width
    return y - 8


def render_market_brief_pdf(context: dict[str, Any], output_path: str | Path) -> None:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    pdf = Canvas(str(destination), pagesize=A4, pageCompression=1)
    pdf.setTitle("Brazil Rates & FX Trade Brief")
    pdf.setAuthor("Brazil Rates & FX Scenario Monitor")

    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 17.0)
    pdf.drawString(MARGIN, PAGE_HEIGHT - 36, "Brazil Rates & FX Trade Brief")
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 6.8)
    pdf.drawRightString(PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 33, context["snapshot_display"])
    pdf.setFillColor(ACCENT)
    pdf.rect(MARGIN, PAGE_HEIGHT - 53, CONTENT_WIDTH, 12, fill=1, stroke=0)
    pdf.setFillColor(WHITE)
    pdf.setFont("Helvetica-Bold", 7.4)
    pdf.drawString(MARGIN + 6, PAGE_HEIGHT - 49, "EDUCATIONAL PAPER TRADE - NOT INVESTMENT ADVICE")

    y = _draw_section_heading(pdf, "Market snapshot", PAGE_HEIGHT - 67)
    y = _draw_metric_cards(pdf, context["market_metrics"], y)
    y = _draw_section_heading(pdf, "What changed", y - 3)
    y = _draw_bullets(pdf, context["what_changed"], y, CONTENT_WIDTH)
    y = _draw_section_heading(pdf, "Three scenarios", y - 1)
    y = _draw_scenario_table(pdf, context["scenario_rows"], y)
    y = _draw_section_heading(pdf, "One conditional paper trade", y - 9)
    y = _draw_paper_trade(pdf, context["trade"], y)
    y = _draw_section_heading(pdf, "Bottom line", y - 9)
    for sentence in context["bottom_line"]:
        y = _draw_wrapped(pdf, sentence, MARGIN, y, CONTENT_WIDTH, size=7.25, leading=8.5)
        y -= 1.5

    y = _draw_section_heading(pdf, "Sources and limitations", y - 2)
    y = _draw_link_labels(pdf, context["sources"], MARGIN, y, CONTENT_WIDTH)
    y = _draw_wrapped(pdf, context["limitations"], MARGIN, y, CONTENT_WIDTH, size=6.25, leading=7.3, color=MUTED)
    y = _draw_wrapped(
        pdf,
        f"Exchange-pricing audit: {context['audit_summary']}",
        MARGIN,
        y - 1,
        CONTENT_WIDTH,
        size=6.25,
        leading=7.3,
        color=MUTED,
    )

    if y < 23:
        raise ValueError(f"Brief content exceeded the one-page layout boundary: y={y:.1f}")

    pdf.setStrokeColor(GRID)
    pdf.line(MARGIN, 22, PAGE_WIDTH - MARGIN, 22)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 5.9)
    pdf.drawString(MARGIN, 13, "Fixed saved snapshot; refresh all data and exchange pricing before discussion or publication.")
    pdf.drawRightString(PAGE_WIDTH - MARGIN, 13, "1 / 1")
    pdf.showPage()
    pdf.save()


def render_market_brief_markdown(context: dict[str, Any]) -> str:
    metrics = "\n".join(
        f"| {item['label']} | {item['value']} | {item['date']} |"
        for item in context["market_metrics"]
    )
    changes = "\n".join(f"- {item}" for item in context["what_changed"])
    scenarios = "\n".join(
        "| {scenario} | {copom} | {fomc} | {differential} | {brl_usd_pressure} | {confirmation} |".format(
            **row
        )
        for row in context["scenario_rows"]
    )
    risks = "\n".join(f"{index}. {risk}" for index, risk in enumerate(context["trade"]["risks"], 1))
    sources = " · ".join(f"[{label}]({url})" for label, url in context["sources"])
    bottom_line = " ".join(context["bottom_line"])
    trade = context["trade"]
    return f"""# Brazil Rates & FX Trade Brief

**Data snapshot:** {context['snapshot_display']}

**Educational paper trade - not investment advice.**

## Scenario-label audit

{context['snapshot']['scenario_label_audit']['result']}

{context['audit_summary']} No Copom probability or joint scenario probability is assigned.

## Market snapshot

| Metric | Value | Observation date |
|---|---:|---|
{metrics}

## What changed

{changes}

## Three scenarios

| Scenario | Copom | FOMC | Rate differential | Likely initial BRL/USD pressure | Key confirmation signal |
|---|---|---|---|---|---|
{scenarios}

Directional reactions are likely initial pressure only, all else equal, and remain subject to broader risk sentiment.

## One conditional paper trade

### {trade['direction']} - conditional, no current position

**Thesis:** {trade['thesis']}

**Entry trigger:** {trade['entry']}

**Latest PTAX reference:** {trade['latest_reference']}

**Invalidation:** {trade['invalidation']}

**Review/profit-taking zone:** {trade['review']}

**Expected holding period:** {trade['holding_period']}

**Supporting scenario:** {trade['supporting_scenario']}

**Three principal risks**

{risks}

## Bottom line

{bottom_line}

## Sources and limitations

{sources}

{context['limitations']}

This is one educational conditional paper trade, not actual execution, investment advice or a claim of past performance.
"""


def generate_market_brief(
    snapshot_path: str | Path,
    pdf_path: str | Path,
    markdown_path: str | Path,
) -> dict[str, Any]:
    snapshot = load_research_snapshot(snapshot_path)
    context = build_brief_context(snapshot)
    markdown_destination = Path(markdown_path)
    markdown_destination.parent.mkdir(parents=True, exist_ok=True)
    markdown_destination.write_text(render_market_brief_markdown(context), encoding="utf-8")
    render_market_brief_pdf(context, pdf_path)
    return context
