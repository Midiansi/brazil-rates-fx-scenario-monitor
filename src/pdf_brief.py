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
        "h2": style("h2", 11.5, 15, "Sans-Bold", spaceBefore=16, spaceAfter=7),
        "label": style("label", 6.8, 9, "Sans-Bold", color=MUTED, spaceAfter=3),
        "lead": style("lead", 11.2, 15.5, "Sans-Bold", spaceAfter=8),
        "body": style("body", 8.6, 12.4, color=INK_2, spaceAfter=5),
        "small": style("small", 7.6, 10.6, color=MUTED, spaceAfter=3),
        "cell": style("cell", 8, 11, color=INK_2),
        "metric": style("metric", 8, 15, color=INK_2),
    }


def _pdf_text(text: str) -> str:
    """Escape for ReportLab markup and cover the two glyphs Vera lacks."""

    safe = escape(text, quote=False).replace(" ", " ")
    return safe.replace("→", '<font name="Symbol">→</font>')


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
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
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

    # 3. Review of the previous thesis.
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
    story.append(p(f"<b>{_pdf_text(t['review_lesson_label'])}.</b> {_pdf_text(t['review_lesson'])}", "body"))

    # 4. Paper trade rules.
    story.append(p(_pdf_text(t["trade_title"]), "h2"))
    story.append(p(s(t["trade_status"]), "small"))
    rows = []
    for i, (term, body) in enumerate(t["trade_rows"]):
        color = "#B45E33" if i in (4, 5, 6) else "#102431"
        rows.append([p(f"<font name='Sans-Bold' color='{color}'>{_pdf_text(term)}</font>", "cell"), p(s(body), "cell")])
    story.append(grid(rows, [WIDTH * 0.24, WIDTH * 0.76]))
    story.append(Spacer(1, 6))
    story.append(p(f"<b>{_pdf_text(t['trade_risks_label'])}.</b> " + " ".join(f"({i}) {s(r)}" for i, r in enumerate(t["trade_risks"], 1)), "body"))
    story.append(p(f"<b>{_pdf_text(t['trade_change_label'])}.</b> {s(t['trade_change'])}", "body"))

    # 5. Paths after the first round.
    paths_block = [p(s(t["paths_title"]), "h2"), p(_pdf_text(t["paths_intro"]), "body")]
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

    # 6. My interpretation (the full evidence list stays on the website).
    story.append(p(_pdf_text(t["kinds"]["interpretation"]), "h2"))
    for text in t["evidence"]["interpretation"]:
        story.append(p("– " + s(text), "body"))

    # 7. Commodities.
    story.append(p(_pdf_text(t["commodities_title"]), "h2"))
    story.append(p(_pdf_text(t["commodities_intro"]), "body"))
    rows = [[p(_pdf_text(h.upper()), "label") for h in t["commodity_cols"]]]
    commodities = snapshot.get("commodities") or {}
    for key in ("brent", "iron_ore", "soybeans", "sugar"):
        item = commodities.get(key)
        verdict, reason = t["commodity_verdicts"][key]
        if item:
            frequency = item.get("frequency", "Daily")
            unit = t["units"].get(item["unit"], item["unit"])
            latest = f"{_pdf_text(f.num(item['latest'], 2, lang) + ' ' + unit)}<br/><font size='7' color='#607782'>{_pdf_text(f.period(item['latest_date'], frequency, lang))}</font>"
            change = f.pct((item["latest"] / item["previous"] - 1) * 100, 1, lang, signed=True)
            change += f"<br/><font size='7' color='#607782'>{_pdf_text(t['vs'])} {_pdf_text(f.period(item['previous_date'], frequency, lang))}</font>"
        else:
            latest, change = _pdf_text(t["unavailable"]), "—"
        rows.append([p(f"<b>{_pdf_text(t['commodity_names'][key])}</b>", "cell"), p(latest, "cell"),
                     p(change, "cell"), p(f"<b>{_pdf_text(verdict)}.</b> {s(reason)}", "cell")])
    story.append(grid(rows, [WIDTH * 0.2, WIDTH * 0.19, WIDTH * 0.13, WIDTH * 0.48], header=True))

    # 8. Method, limits and sources.
    story.append(p(_pdf_text(t["method_title"]), "h2"))
    for term, body in t["method_calc"][2:4]:
        story.append(p(f"<b>{_pdf_text(term)}.</b> {s(body)}", "body"))
    story.append(p(f"<b>{_pdf_text(t['limits_label'])}.</b> " + " ".join(_pdf_text(item) for item in t["limits"]), "body"))
    story.append(p(_pdf_text(t["sources_label"]), "h2"))
    labels = t["source_labels"]
    links = [
        p(f"<a href='{escape(src['url'], quote=True)}' color='#0B7F70'>{_pdf_text(labels.get(key, src['label']))}</a> "
          f"<font color='#607782'>· {_pdf_text(f.day(src['date'], lang))}</font>", "small")
        for key, src in sorted(thesis["sources"].items(), key=lambda item: labels.get(item[0], item[1]["label"]))
    ]
    if len(links) % 2:
        links.append(p("", "small"))
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
    lines += [f"{i}. **{s(title)}** {s(body)}" for i, (title, body) in enumerate(t["why"], 1)]
    lines += ["", f"**{t['act_label']}.** {s(t['act'])}", "", f"**{t['change_label']}.** {s(t['change'])}", "",
              f"## {t['review_title']}", "", s(t["review_intro"]), "", "| " + " | ".join(t["review_head"]) + " |", "|---|---|---|"]
    for item in thesis["review"]:
        expected, happened = t["review_rows"][item["id"]]
        lines.append(f"| {s(expected)} | {s(happened)} | {t['verdicts'][item['verdict']]} |")
    lines += ["", f"**{t['review_lesson_label']}.** {t['review_lesson']}", "", f"## {t['trade_title']}", "", s(t["trade_status"]), ""]
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
