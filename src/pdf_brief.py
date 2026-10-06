"""Printable research brief, generated offline from the same content as the page.

Same section order, labels and palette as the website, on a light page for
printing.  Text is real text (searchable, ATS-friendly); the font is Bitstream
Vera, which ships with ReportLab, so every machine renders the same glyphs.
Development dependency only: never imported by app.py.
"""
from __future__ import annotations

import os
from html import escape
from pathlib import Path
from typing import Any

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src import formatting as f
from src.content import TEXT
from src.page import GITHUB
from src.thesis import fill, placeholders

INK = colors.HexColor("#102431")
INK_2 = colors.HexColor("#3A5260")
MUTED = colors.HexColor("#607782")
LINE = colors.HexColor("#D3DEDC")
TEAL = colors.HexColor("#0B7F70")
TEAL_TINT = colors.HexColor("#E8F4F1")
COPPER = colors.HexColor("#B45E33")
COPPER_TINT = colors.HexColor("#FBEFE8")
SAND = colors.HexColor("#8A7440")
PANEL = colors.HexColor("#F3F7F6")
VERDICT_COLORS = {"confirmed": TEAL, "partly": SAND, "unresolved": MUTED, "not_triggered": MUTED, "underweighted": COPPER}
MARGIN = 48
WIDTH = A4[0] - 2 * MARGIN

_FONT_DIR = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
for _name, _file in (("Sans", "Vera.ttf"), ("Sans-Bold", "VeraBd.ttf"), ("Sans-Italic", "VeraIt.ttf"), ("Sans-BoldItalic", "VeraBI.ttf")):
    pdfmetrics.registerFont(TTFont(_name, os.path.join(_FONT_DIR, _file)))
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-Bold", italic="Sans-Italic", boldItalic="Sans-BoldItalic")


def _styles() -> dict[str, ParagraphStyle]:
    def style(name: str, size: float, leading: float, font: str = "Sans", color: Any = INK, **extra: Any) -> ParagraphStyle:
        return ParagraphStyle(name, fontName=font, fontSize=size, leading=leading, textColor=color, **extra)

    return {
        "eyebrow": style("eyebrow", 7, 10, color=TEAL, spaceAfter=6),
        "title": style("title", 19, 23, "Sans-Bold", spaceAfter=4),
        "subtitle": style("subtitle", 9, 13, color=MUTED, spaceAfter=14),
        "h2": style("h2", 11.5, 15, "Sans-Bold", spaceBefore=12, spaceAfter=5),
        "label": style("label", 6.8, 9, "Sans-Bold", color=MUTED, spaceAfter=3),
        "lead": style("lead", 11.2, 15.5, "Sans-Bold", spaceAfter=8),
        "body": style("body", 8.5, 11.9, color=INK_2, spaceAfter=4),
        "small": style("small", 7.4, 10.0, color=MUTED, spaceAfter=3),
        "tiny": style("tiny", 6.7, 8.4, color=MUTED),
        "cell": style("cell", 7.9, 10.6, color=INK_2),
        "metric": style("metric", 8, 15, color=INK_2),
    }


def _pdf_text(text: str) -> str:
    """Escape for ReportLab markup and cover the glyphs Vera lacks (arrow, sigma)."""

    safe = escape(text, quote=False).replace(" ", " ")
    return (safe.replace("→", '<font name="Symbol">→</font>').replace("σ", '<font name="Symbol">σ</font>')
            .replace("Σ", '<font name="Symbol">Σ</font>').replace("₂", "2").replace("₁", "1"))


def render_pdf(thesis: dict[str, Any], snapshot: dict[str, Any], output: Path | str, lang: str = "en") -> Path:
    t, values = TEXT[lang], placeholders(thesis, lang)
    st = _styles()

    def s(text: str, **extra: str) -> str:
        return _pdf_text(fill(text, {**values, **extra}, lang))

    def p(text: str, style: str = "body") -> Paragraph:
        return Paragraph(text, st[style])

    def grid(rows: list[list[Any]], widths: list[float], style: list[tuple] | None = None, header: bool = False) -> Table:
        table = Table(rows, colWidths=widths, hAlign="LEFT", repeatRows=1 if header else 0)
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
            *(style or []),
        ]))
        return table

    ev = thesis["evidence"]
    story: list[Any] = [
        p("BRAZIL MACRO · ROMEO MUGNIER DE ALMEIDA · EPFL", "eyebrow"),
        p(_pdf_text(t["pdf_title"]), "title"),
        p(s(t["pdf_subtitle"]) + " · " + _pdf_text(t["kicker"]), "subtitle"),
    ]

    # 1. The view, why, and the decision rules.
    view_rows = [
        [p(_pdf_text(t["view_label"].upper() + " · " + t["status_no_position"].upper()), "label")],
        [p(s(t["view_headline"]), "lead")],
    ]
    for i, (title, body) in enumerate(t["why"], 1):
        view_rows.append([p(f"<b>{i}. {s(title)}</b> {s(body)}", "body")])
    view = Table(view_rows, colWidths=[WIDTH])
    view.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL), ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, 0), 12), ("TOPPADDING", (0, 1), (-1, -1), 2), ("BOTTOMPADDING", (0, -1), (-1, -1), 10),
        ("LINEBEFORE", (0, 0), (0, -1), 2, TEAL),
    ]))
    story += [view, Spacer(1, 10)]
    decide = Table(
        [[p(f"<b>{_pdf_text(t['act_label'])}</b><br/>{s(t['act'])}", "body"), p(f"<b>{_pdf_text(t['change_label'])}</b><br/>{s(t['change'])}", "body")]],
        colWidths=[WIDTH / 2 - 4, WIDTH / 2 - 4], spaceBefore=0,
    )
    decide.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), TEAL_TINT), ("BACKGROUND", (1, 0), (1, 0), COPPER_TINT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(decide)

    # 2. Key data as of the thesis date.
    story.append(p(_pdf_text(t["pdf_data_label"]) + " · " + s("{as_of}"), "h2"))
    fed_range = f.rate_range(ev["fed_range"]["lower"], ev["fed_range"]["upper"], lang)
    metrics = [
        (t["tape"]["selic_target"], f.pct(ev["selic"]["value"], 2, lang), ev["selic"]["date"], "BCB"),
        (t["tape"]["fed_target_range"], fed_range, ev["fed_range"]["date"], "Fed"),
        (t["tape"]["brazil_us_policy_differential"], f.pp(ev["policy_gap"]["value"], 2, lang), ev["policy_gap"]["date"], "BCB / Fed"),
        (t["tape"]["ptax_usd_brl_midpoint"], f.num(ev["ptax"]["value"], 4, lang), ev["ptax"]["date"], "BCB"),
        (t["tape"]["us_2_year_treasury"], f.pct(ev["us_2y"]["value"], 2, lang), ev["us_2y"]["date"], t["source_short"]["treasury"]),
        (t["tape"]["brent"], f.usd(ev["brent_spot"]["value"], 2, lang), ev["brent_spot"]["date"], "EIA / FRED"),
    ]
    cells = [
        p(f"{_pdf_text(label)}<br/><font name='Sans-Bold' size='11.5' color='#102431'>{_pdf_text(value)}</font><br/>"
          f"<font size='7' color='#607782'>{_pdf_text(f.day(when, lang))} · {_pdf_text(source)}</font>", "metric")
        for label, value, when, source in metrics
    ]
    story.append(grid([cells[:3], cells[3:]], [WIDTH / 3] * 3, [("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))

    # 3. Review of the 5 October thesis.
    story.append(p(_pdf_text(t["review_title"]), "h2"))
    story.append(p(s(t["review_intro"]), "body"))
    rows = [[p(_pdf_text(h.upper()), "label") for h in t["review_head"]]]
    for item in thesis["review"]:
        expected, happened = t["review_rows"][item["id"]]
        color = VERDICT_COLORS[item["verdict"]].hexval().replace("0x", "#")
        rows.append([p(s(expected), "cell"), p(s(happened), "cell"),
                     p(f"<font name='Sans-Bold' color='{color}'>{_pdf_text(t['verdicts'][item['verdict']])}</font>", "cell")])
    story.append(grid(rows, [WIDTH * 0.3, WIDTH * 0.52, WIDTH * 0.18], header=True))
    story.append(Spacer(1, 6))
    story.append(p(f"<b>{_pdf_text(t['review_lesson_label'])}.</b> {s(t['review_lesson'])}", "body"))

    study = thesis.get("study") or {}
    right = [("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("ALIGN", (1, 0), (-1, -1), "RIGHT")]
    if study:
        curve, gap, bp = study["curve"], study["survey_gap"], t["bp"]

        def num(value: float, digits: int = 2, signed: bool = False) -> str:
            return f.num(value, digits, lang, signed)

        # 4. Rates, FX and quant.
        story.append(p(_pdf_text(t["quant_title"]), "h2"))
        story.append(p(f"<b>{_pdf_text(t['quant_curve_title'])}.</b> {s(t['quant_curve_text'])}", "body"))
        rows = [[p(_pdf_text(h.upper()), "label") for h in t["curve_cols"]]]
        for row in curve["rows"]:
            if row["vertex"] in ("126", "252", "504", "756", "1260", "2520"):
                rows.append([p(_pdf_text(t["curve_tenors"][row["vertex"]]), "cell"), p(f.pct(row["before"], 2, lang), "cell"),
                             p(f.pct(row["after"], 2, lang), "cell"), p(f"{num(row['change_bp'], 0, True)} {bp}", "cell")])
        memo = t["curve_memo"]
        for label, before, after, fmt in (
            (memo["fwd"], curve["forward_1y1y"]["before"], curve["forward_1y1y"]["after"], lambda v: f.pct(v, 2, lang)),
            (memo["be"], curve["breakeven_2y"]["before"], curve["breakeven_2y"]["after"], lambda v: f.pct(v, 2, lang)),
            (memo["real"], curve["real_2y"]["before"], curve["real_2y"]["after"], lambda v: f.pct(v, 2, lang)),
        ):
            rows.append([p(_pdf_text(label), "cell"), p(fmt(before), "cell"), p(fmt(after), "cell"), p(f"{num((after - before) * 100, 0, True)} {bp}", "cell")])
        story.append(grid(rows, [WIDTH * 0.46, WIDTH * 0.18, WIDTH * 0.18, WIDTH * 0.18], right, header=True))

        story.append(p(f"<b>{_pdf_text(t['quant_events_title'])}.</b> {s(t['quant_events_text'])}", "body"))
        rows = [[p(_pdf_text(h.upper()), "label") for h in t["events_cols"]]]
        for w in study["elections"]:
            pending = w["year"] == 2026
            dash = _pdf_text(t["events_undefined"])
            cells = [str(w["year"]), f.pct(w["monday_move"], 2, lang, signed=True), num(w["z"], 1, True)]
            if pending:
                cells += [_pdf_text(t["events_pending"])] * 3
            else:
                first, second = w.get("giveback_runoff_friday"), w.get("giveback_first_close")
                cells += [f.pct(first, 0, lang) if first is not None else dash, f.pct(second, 0, lang) if second is not None else dash,
                          f.pct(w["runoff_session_move"], 2, lang, signed=True)]
            weight = "Sans-Bold" if pending or w["surprise"] else "Sans"
            rows.append([p(f"<font name='{weight}'>{c}</font>", "cell") for c in cells])
        story.append(grid(rows, [WIDTH * 0.1, WIDTH * 0.15, WIDTH * 0.12, WIDTH * 0.23, WIDTH * 0.23, WIDTH * 0.17], right, header=True))
        story.append(p(_pdf_text(t["events_note"]), "small"))

        story.append(p(f"<b>{_pdf_text(t['quant_rule_title'])}.</b> {s(t['quant_rule_text'])}", "body"))
        geometry, rules = study["rule_geometry"], thesis["rules"]
        walk, walk_lr = geometry["random_walk"]["diffusion"], geometry["random_walk"]["long_run"]
        rows = [[p(_pdf_text(h.upper()), "label") for h in (s(c) for c in t["rule_cols"])]]
        for key, level, field in (("entry", rules["entry_below"], "below_entry"), ("exit", rules["exit_above"], "above_exit"), ("abandon", rules["abandon_above"], "above_abandon")):
            name, rule, verb = t["rule_rows"][key]
            rows.append([p(f"<b>{num(level)}</b>", "cell"), p(f"<b>{_pdf_text(name)}</b> · {s(rule)}", "cell"), p(f.pct(geometry["giveback"][key], 0, lang), "cell"),
                         p(f.pct(geometry["distance_pct"][key], 1, lang, signed=True), "cell"),
                         p(f"{f.pct(walk[field], 0, lang)} · {_pdf_text(verb)}", "cell"), p(f"{f.pct(walk_lr[field], 0, lang)} · {_pdf_text(verb)}", "cell")])
        story.append(grid(rows, [WIDTH * 0.1, WIDTH * 0.28, WIDTH * 0.13, WIDTH * 0.13, WIDTH * 0.18, WIDTH * 0.18], header=True))
        story.append(Spacer(1, 4))
        for term, body in t["rule_bullets"]:
            story.append(p(f"<b>{_pdf_text(term)}.</b> {s(body)}", "body"))

        # 5. Commodities.
        story.append(p(_pdf_text(t["commodities_title"]), "h2"))
        story.append(p(s(t["commodities_intro"]), "body"))
        story.append(p(f"<b>{_pdf_text(t['c_link_title'])}</b> {s(t['c_link_text'])}", "body"))
        hedge = {item["key"]: item for item in study["hedge"]}
        yoy = {item["key"]: item for item in study["year_on_year"]["rows"]}
        share = study["weights"]["share_of_exports"]
        rows = [[p(_pdf_text(h.upper()), "label") for h in (*t["producer_cols"], t["bars_labels"]["usd"], t["bars_labels"]["brl"])]]
        for key in ("brent", "soybeans", "iron_ore", "coffee", "sugar", "maize"):
            rows.append([p(f"<b>{_pdf_text(t['commodity_names'][key])}</b>", "cell"), p(f.pct(share[key], 1, lang), "cell"), p(f.pct(hedge[key]["vol_usd"], 0, lang), "cell"),
                         p(f.pct(hedge[key]["vol_brl"], 0, lang), "cell"), p(num(hedge[key]["corr_fx"]), "cell"),
                         p(f.pct(yoy[key]["usd"], 1, lang, signed=True), "cell"), p(f.pct(yoy[key]["brl"], 1, lang, signed=True), "cell")])
        story.append(grid(rows, [WIDTH * 0.2, WIDTH * 0.13, WIDTH * 0.13, WIDTH * 0.13, WIDTH * 0.15, WIDTH * 0.13, WIDTH * 0.13], right, header=True))
        story.append(p(f"{_pdf_text(t['producer_note'])} {s(t['bars_title'])}.", "small"))
        for title, body in t["c_oil_points"][:2]:
            story.append(p(f"<b>{_pdf_text(title)}</b> {s(body)}", "body"))

    # 6. Paper trade rules.
    story.append(p(_pdf_text(t["trade_title"]), "h2"))
    story.append(p(s(t["trade_status"]), "small"))
    rows = []
    for i, (term, body) in enumerate(t["trade_rows"]):
        color = "#B45E33" if i in (4, 5, 6) else "#102431"
        rows.append([p(f"<font name='Sans-Bold' color='{color}'>{_pdf_text(term)}</font>", "cell"), p(s(body), "cell")])
    story.append(grid(rows, [WIDTH * 0.24, WIDTH * 0.76]))
    story.append(Spacer(1, 6))
    story.append(p(f"<b>{_pdf_text(t['trade_risks_label'])}.</b> " + " ".join(f"({i}) {s(r)}" for i, r in enumerate(t["trade_risks"], 1)), "body"))

    # 7. Paths.
    paths_block = [p(s(t["paths_title"]), "h2")]
    colon = "\u00a0:" if lang == "fr" else ":"
    path_cells = []
    for letter, (title, signals, meaning, action) in zip("ABCD", t["paths"]):
        path_cells.append(p(
            f"<b>{letter}. {s(title)}</b><br/><font color='#607782'>{_pdf_text(t['path_fields'][0])}{colon}</font> {s(signals)}<br/>"
            f"<font color='#607782'>{_pdf_text(t['path_fields'][1])}{colon}</font> {s(meaning)}<br/>"
            f"<font color='#607782'>{_pdf_text(t['path_fields'][2])}{colon}</font> <b>{s(action)}</b>", "cell"))
    paths_block.append(grid([path_cells[:2], path_cells[2:]], [WIDTH / 2] * 2, [("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story.append(KeepTogether(paths_block))
    dates = " · ".join(f"{_pdf_text(f.day(item['date'], lang, year=False))}{colon} {_pdf_text(t['calendar'][item['event']])}" for item in thesis["calendar"])
    story.append(Spacer(1, 4))
    story.append(p(f"<b>{_pdf_text(t['calendar_label'])}.</b> {dates}", "small"))

    # 8. Method, limits and sources.
    story.append(p(_pdf_text(t["limits_label"]), "h2"))
    story.append(p(" ".join(s(item) for i, item in enumerate(t["limits"]) if i not in (4, 5)), "tiny"))  # the rest is on the website
    story.append(p(_pdf_text(t["sources_label"]), "h2"))
    labels = t["source_labels"]
    links = [
        p(f"<a href='{escape(src['url'], quote=True)}' color='#0B7F70'>{_pdf_text(labels.get(key, src['label']))}</a> "
          f"<font color='#607782'>· {_pdf_text(f.day(src['date'], lang))}</font>", "tiny")
        for key, src in sorted(thesis["sources"].items(), key=lambda item: labels.get(item[0], item[1]["label"]))
    ]
    if len(links) % 2:
        links.append(p("", "tiny"))
    story.append(grid([links[i:i + 2] for i in range(0, len(links), 2)], [WIDTH / 2] * 2,
                      [("LINEBELOW", (0, 0), (-1, -1), 0, colors.white), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    story.append(Spacer(1, 8))
    site = f"https://brasilmacro.streamlit.app/?lang={lang}"
    story.append(p(f"{_pdf_text(t['pdf_more'])} <a href='{site}' color='#0B7F70'>{site.replace('https://', '')}</a> · "
                   f"<a href='{GITHUB}' color='#0B7F70'>{GITHUB.replace('https://', '')}</a>", "small"))
    story.append(p(s(t["footer"]), "small"))

    def decorate(canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(TEAL)
        canvas.setLineWidth(1.6)
        canvas.line(MARGIN, A4[1] - 30, A4[0] - MARGIN, A4[1] - 30)
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, 36, A4[0] - MARGIN, 36)
        canvas.setFillColor(MUTED)
        canvas.setFont("Sans", 7)
        canvas.drawString(MARGIN, 24, f"Brazil Macro · {fill(t['pdf_subtitle'], values, lang)}".replace(" ", " "))
        canvas.drawRightString(A4[0] - MARGIN, 24, f"{t['pdf_page']} {doc.page}")
        canvas.restoreState()

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(destination), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=46, bottomMargin=50,
        title=t["pdf_title"], author="Romeo Mugnier de Almeida", subject=fill(t["pdf_subtitle"], values, lang),
        lang=t["html_lang"], creator="Brazil Macro (scripts/generate_market_brief.py)",
    )
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return destination


def markdown_brief(thesis: dict[str, Any]) -> str:
    """English Markdown companion, generated from the same content."""

    t, values = TEXT["en"], placeholders(thesis, "en")

    def s(text: str) -> str:
        return fill(text, values, "en")

    lines = [f"# {t['pdf_title']}", "", f"*{s(t['pdf_subtitle'])}. Educational research, not investment advice.*", "",
             f"## {t['view_label']} — {t['status_no_position']}", "", s(t["view_headline"]), ""]
    lines += [f"- **{s(label)}:** {s(value)} ({s(detail)})" for label, value, detail in t["reaction"]]
    lines += [""] + [f"{i}. **{s(title)}** {s(body)}" for i, (title, body) in enumerate(t["why"], 1)]
    lines += ["", f"**{t['act_label']}.** {s(t['act'])}", "", f"**{t['change_label']}.** {s(t['change'])}", "",
              f"## {t['review_title']}", "", s(t["review_intro"]), "", "| " + " | ".join(t["review_head"]) + " |", "|---|---|---|"]
    for item in thesis["review"]:
        expected, happened = t["review_rows"][item["id"]]
        lines.append(f"| {s(expected)} | {s(happened)} | {t['verdicts'][item['verdict']]} |")
    lines += ["", f"**{t['review_lesson_label']}.** {s(t['review_lesson'])}", "", f"## {t['quant_title']}", "", s(t["quant_intro"]), "",
              f"**{t['quant_curve_title']}.** {s(t['quant_curve_text'])}", "", f"**{t['quant_events_title']}.** {s(t['quant_events_text'])}", "",
              f"**{t['quant_rule_title']}.** {s(t['quant_rule_text'])}", ""]
    lines += [f"- **{term}.** {s(body)}" for term, body in t["rule_bullets"]]
    lines += ["", f"## {t['commodities_title']}", "", s(t["commodities_intro"]), "", f"**{t['c_link_title']}** {s(t['c_link_text'])}", "",
              f"**{t['c_producer_title']}.** {s(t['c_producer_text'])}", ""]
    lines += [f"- **{title}** {s(body)}" for title, body in t["c_oil_points"]]
    lines += ["", f"**{t['c_sugar_title']}.** {s(t['c_sugar_text'])}", "", f"## {t['trade_title']}", "", s(t["trade_status"]), ""]
    lines += [f"- **{term}.** {s(body)}" for term, body in t["trade_rows"]]
    lines += ["", f"## {s(t['paths_title'])}", ""]
    for letter, (title, signals, meaning, action) in zip("ABCD", t["paths"]):
        lines.append(f"- **{letter}. {s(title)}** — {s(signals)} {s(meaning)} *{s(action)}*")
    lines += ["", f"## {t['evidence_title']}", ""]
    for kind in ("fact", "pricing", "survey", "interpretation"):
        lines.append(f"**{t['kinds'][kind]}**")
        lines += [f"- {s(text)}" for text in t["evidence"][kind]]
        lines.append("")
    lines += [f"## {t['sources_label']}", ""]
    lines += [f"- [{t['source_labels'].get(key, src['label'])}]({src['url']}) — {src['date']}" for key, src in sorted(thesis["sources"].items())]
    lines += ["", s(t["footer"]), ""]
    return "\n".join(lines)
