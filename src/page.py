"""Build the page as a handful of HTML strings.

Pure functions (no Streamlit import) so the whole page can be rendered and
checked in tests.  All prose comes from ``src.content``; every value comes from
``research/thesis.json`` (dated), ``research/study_*.json`` (the quantitative
study) or ``research/live_snapshot.json`` (refreshed).
"""
from __future__ import annotations

from datetime import date
from html import escape
from typing import Any

from src import formatting as f
from src.chart import bars_svg, curve_svg, events_svg, ptax_svg, scatter_svg
from src.content import TEXT
from src.lab_content import TEXT as LAB_TEXT
from src.freshness import run_age_days, status as fresh_status
from src.thesis import fill, placeholders, rule_status

GITHUB = "https://github.com/Midiansi/brazil-rates-fx-scenario-monitor"
LINKEDIN = "https://www.linkedin.com/in/romeomugnier"
SECTIONS = ("view", "lab", "risk", "review", "quant", "commodities", "trade", "evidence", "method")
LENSES = ("quant", "commodities")
TAPE = ("selic_target", "fed_target_range", "brazil_us_policy_differential", "ptax_usd_brl_midpoint", "us_2_year_treasury", "brent")
EVIDENCE_SOURCES = {
    "fact": (("tse_results",), ("datafolha_1003", "quaest_1003"), ("copom_281", "fomc_statement", "derived_gap"), ("cnn_brasil_0510",), ("ifi_ploa2027",)),
    "pricing": (("bcb_ptax",), ("treasury",), ("anbima_ettj",), ("fred_brent", "eia_steo_q3")),
    "survey": (("bcb_focus",), ("fomc_sep",), ("jpmorgan_infomoney",)),
    "interpretation": (("tse_results",), ("bcb_ptax",), ()),
}
VERDICT_ICONS = {"confirmed": "✓", "partly": "~", "unresolved": "?", "not_triggered": "○", "underweighted": "!"}
CURVE_VERTICES = ("126", "252", "504", "756", "1260", "2520")
COMMODITY_ORDER = ("brent", "soybeans", "iron_ore", "coffee", "sugar", "maize")


def e(text: Any) -> str:
    return escape(str(text), quote=True)


def lens_order(lens: str) -> tuple[str, str]:
    return ("commodities", "quant") if lens == "commodities" else ("quant", "commodities")


class Page:
    """Everything needed to render one language, computed once."""

    def __init__(self, lang: str, thesis: dict[str, Any], snapshot: dict[str, Any], today: date, lens: str = "quant", risk_report: dict[str, Any] | None = None):
        self.lang = lang if lang in TEXT else "en"
        self.t = TEXT[self.lang]
        self.thesis = thesis
        self.snapshot = snapshot if isinstance(snapshot, dict) else {}
        self.series = self.snapshot.get("series") if isinstance(self.snapshot.get("series"), dict) else {}
        self.commodities = self.snapshot.get("commodities") if isinstance(self.snapshot.get("commodities"), dict) else {}
        self.today = today
        self.lens = lens if lens in LENSES else "quant"
        self.values = placeholders(thesis, self.lang) if thesis else {}
        self.study = (thesis or {}).get("study") or {}
        self.lab_text = LAB_TEXT[self.lang]
        self.risk_report = risk_report if isinstance(risk_report, dict) else {}

    # -- helpers -----------------------------------------------------------
    def s(self, text: str, **extra: str) -> str:
        """Fill placeholders, apply French spacing, escape for HTML."""

        return e(fill(text, {**self.values, **extra}, self.lang))

    def raw(self, text: str, **extra: str) -> str:
        """Fill placeholders without escaping (for SVG text, which escapes itself)."""

        return fill(text, {**self.values, **extra}, self.lang)

    def source_link(self, key: str) -> str:
        source = self.thesis.get("sources", {}).get(key)
        if not source:
            return ""
        short = self.t["source_short"].get(key, source["label"].split(" · ")[0])
        return f'<a href="{e(source["url"])}" target="_blank" rel="noopener">{e(short)}</a>'

    def section_head(self, key: str, title: str, intro: str = "") -> str:
        intro_html = f'<p class="intro">{intro}</p>' if intro else ""
        return f'<div class="sec-head"><h2 id="{key}-title">{title}</h2>{intro_html}</div>'

    def sub(self, title: str, text: str = "", take: str = "") -> str:
        """A subsection heading, an optional one-line takeaway, and an optional paragraph."""

        lead = f'<p class="take">{take}</p>' if take else ""
        body = f'<p class="sub-intro">{text}</p>' if text else ""
        return f'<h3 class="sub-head">{title}</h3>{lead}{body}'

    def numbers(self, inner: str) -> str:
        """Dense tables stay one click away, so the first read is the takeaway and the figure."""

        return f'<details class="numbers"><summary>{e(self.t["show_numbers"])}</summary><div class="inner">{inner}</div></details>'

    def stamp(self, value: str | None) -> str:
        """Refresh timestamp, or the localized 'n/a' when missing or unreadable."""

        return (f.timestamp(value, self.lang) if value else "") or self.t["na"]

    def wrap(self, section: str, inner: str) -> str:
        return f'<div class="bm" lang="{self.t["html_lang"]}"><section class="sec" id="{section}" aria-labelledby="{section}-title">{inner}</section></div>'

    def table(self, head: list[str], rows: list[Any], css: str = "", label: str = "", numeric_from: int = 1) -> str:
        """A scrollable table; cells are already escaped HTML.  Columns from ``numeric_from`` are right-aligned."""

        heads = "".join(f'<th scope="col"{" class=n" if i >= numeric_from else ""}>{e(h)}</th>' for i, h in enumerate(head))
        body = ""
        for row in rows:
            cells = row["cells"] if isinstance(row, dict) else row
            html = "".join(
                f'<th scope="row">{cell}</th>' if i == 0 else f'<td class="n">{cell}</td>' if i >= numeric_from else f"<td>{cell}</td>"
                for i, cell in enumerate(cells)
            )
            cls = f' class="{row["class"]}"' if isinstance(row, dict) and row.get("class") else ""
            body += f"<tr{cls}>{html}</tr>"
        name = f' aria-label="{e(label)}"' if label else ""
        return (f'<div class="table-wrap {css}" tabindex="0" role="region"{name}><table class="fig-table {css}">'
                f"<thead><tr>{heads}</tr></thead><tbody>{body}</tbody></table></div>")

    # -- series formatting -------------------------------------------------
    def series_value(self, key: str, item: dict[str, Any]) -> str:
        lang = self.lang
        try:
            if key == "fed_target_range":
                return f.rate_range(item["lower"], item["upper"], lang)
            if key == "brazil_us_policy_differential":
                return f.pp(item["value"], 2, lang)
            if key == "ptax_usd_brl_midpoint":
                return f.num(item["value"], 4, lang)
            if key.startswith("focus_fx"):
                return f.num(item["selected_value"], 2, lang)
            if key.startswith("focus_"):
                return f.pct(item["selected_value"], 2, lang)
            if key == "us_2s10s":
                return f.pp(item["value"], 2, lang)
            return f.pct(item["value"], 2, lang)
        except (KeyError, TypeError, ValueError):
            return self.t["unavailable"]

    def commodity_value(self, key: str, item: dict[str, Any]) -> str:
        unit = self.t["units"].get(item.get("unit", ""), item.get("unit", ""))
        return f"{f.num(float(item['latest']), 2, self.lang)} {unit}"

    def freshness_chip(self, observed: str | None, frequency: str) -> tuple[str, str]:
        state = fresh_status(observed, frequency, self.today)
        return state, f'<span class="fresh {state}">{e(self.t["fresh"][state])}</span>'

    # -- top of the page ---------------------------------------------------
    def top_bar(self) -> str:
        t = self.t
        return (
            f'<div class="bm"><a class="skip" href="#view">{e(t["skip"])}</a>'
            '<div class="bm-top"><span class="brand-mark" aria-hidden="true">B/M</span><strong translate="no">Romeo Mugnier de Almeida</strong>'
            f'<span class="byline">{e(t["byline"])}</span><span class="links">'
            f'<a href="{GITHUB}" target="_blank" rel="noopener">GitHub</a>'
            f'<a href="{LINKEDIN}" target="_blank" rel="noopener">LinkedIn</a></span></div></div>'
        )

    def monitor(self) -> str:
        t = self.t
        result = rule_status(self.thesis, self.snapshot, self.today)
        state = result.get("state", "unavailable")
        extra = {"giveback": t["na"]}
        if result.get("giveback") is not None:
            extra["giveback"] = f.pct(result["giveback"], 0, self.lang)
        if "latest" in result:
            extra["latest"] = f.num(result["latest"], 4, self.lang)
            extra["latest_date"] = f.day(result["latest_date"], self.lang, year=False)
        if "value" in result:
            extra["value"] = f.num(result["value"], 4, self.lang)
            extra["date"] = f.day(result["date"], self.lang, year=False)
        return (
            f'<p class="monitor" data-state="{e(state)}"><span class="label">{e(t["monitor_label"])}</span>'
            f'<span>{self.s(t["monitor"][state], **extra)}</span><span class="note">{e(t["monitor_note"])}</span></p>'
        )

    def tape(self) -> str:
        t = self.t
        cells, states = [], []
        for key in TAPE:
            if key == "brent":
                item = self.commodities.get("brent") or {}
                observed, frequency = item.get("latest_date"), "daily"
                value = f.usd(float(item["latest"]), 2, self.lang) if item else t["unavailable"]
                source = "EIA / FRED"
            else:
                item = self.series.get(key) or {}
                observed, frequency = item.get("latest_observation_date"), item.get("frequency", "daily")
                value = self.series_value(key, item) if item else t["unavailable"]
                source = (item.get("source") or "").replace("Derived: ", "").split(" (")[0]
                source = {"BCB SGS 432": "BCB", "BCB PTAX": "BCB", "U.S. Treasury par yield curve": "U.S. Treasury"}.get(source, source)
                if key == "brazil_us_policy_differential":
                    source = "BCB / Fed"
                if key == "fed_target_range":
                    source = "Fed" if "New York" in source or "FRED" in source else source
            state, chip = self.freshness_chip(observed, frequency)
            states.append(state)
            when = f.day(observed, self.lang, year=False) if observed else t["na"]
            # Every cell shows its date; the chip only speaks up when a value is late.
            flag = f'<span class="m">{chip}</span>' if state != "fresh" else ""
            cells.append(
                f'<div><dt>{e(t["tape"][key])}</dt><dd><span class="v num">{e(value)}</span>'
                f'<span class="m">{e(when)} · {e(source)}</span>{flag}</dd></div>'
            )
        banner = ""
        refresh = self.snapshot.get("refresh") or {}
        run_age = run_age_days(refresh.get("attempted_at"), self.today)
        attempted = refresh.get("attempted_at") or self.snapshot.get("updated_at")
        if run_age is None or run_age > 4:
            when = f.day(attempted[:10], self.lang) if isinstance(attempted, str) and len(attempted) >= 10 else t["na"]
            banner = f'<p class="banner" role="status">{self.s(t["refresh_banner"], date=when)}</p>'
        elif any(state in ("stale", "unknown") for state in states):
            banner = f'<p class="banner" role="status">{e(t["stale_banner"])}</p>'
        caption = self.s(t["refresh_status"], attempted=self.stamp(attempted),
                         ok=str(refresh.get("sources_ok", t["na"])), total=str(refresh.get("sources_total", t["na"])))
        return (
            f'<h2 class="sr-only">{e(t["tape_label"])}</h2><dl class="tape" aria-label="{e(t["tape_label"])}">{"".join(cells)}</dl>'
            f'<div class="tape-caption"><span>{e(t["tape_label"])}</span><span>{caption}</span></div>{banner}'
        )

    def reaction(self) -> str:
        t = self.t
        tiles = "".join(
            f'<div><dt>{e(label)}</dt><dd><span class="v num">{self.s(value)}</span><span class="m">{self.s(detail)}</span></dd></div>'
            for label, value, detail in t["reaction"]
        )
        return f'<div class="reaction"><span class="label">{e(t["reaction_label"])}</span><dl>{tiles}</dl></div>'

    def lenses(self) -> str:
        t = self.t
        cards = []
        for key in lens_order(self.lens):
            title, text = t["lens"][key]
            first = key == self.lens
            badge = f'<span class="badge">{e(t["lens_first"])}</span>' if first else ""
            cards.append(f'<a class="lens-card{" first" if first else ""}" href="#{key}"><span class="lens-title">{e(title)}{badge}</span><span class="lens-text">{e(text)}</span></a>')
        intro = f'<span class="muted">{e(t["lens_intro"])}</span>' if t["lens_intro"] else ""
        return (
            f'<div class="lens"><div class="lens-head"><h2 class="label">{e(t["lens_label"])}</h2>{intro}</div>'
            f'<nav class="lens-cards" aria-label="{e(t["lens_label"])}">{"".join(cards)}</nav></div>'
        )

    def hero(self) -> tuple[str, str]:
        t, lt = self.t, self.lab_text
        why = "".join(f"<div><h3>{self.s(title)}</h3><p>{self.s(body)}</p></div>" for title, body in t["why"])
        keys = ["view", "lab", "risk", *(lens_order(self.lens) if self.study else ()), "trade", "review", "method"]
        labels = {**t["nav"], "lab": lt["lab_nav"], "risk": lt["risk_nav"]}
        nav = "".join(f'<a href="#{key}">{e(labels[key])}</a>' for key in keys)
        scope = ""
        if self.study:
            values = [self.study["volatility"]["observations"] + 1, self.study["basket"]["n"], sum(not w.get("pending") for w in self.study["elections"])]
            scope = '<dl class="research-scope">' + "".join(
                f'<div><dt>{e(label)}</dt><dd>{e(f.num(value, 0, self.lang))}</dd></div>'
                for label, value in zip(lt["scope_labels"], values)) + f'</dl><p class="scope-note">{e(lt["scope_note"])}</p>'
        return (
            f'<div class="bm" lang="{t["html_lang"]}"><section class="hero" id="view" aria-labelledby="view-title">'
            f'<div class="hero-grid"><div class="hero-head"><p class="eyebrow">{e(lt["kicker"])}</p><p class="profile-line">{e(lt["scope"])}</p><h1>{e(t["title"])}</h1><p class="lede">{e(lt["intro"])}</p>'
            f'<div class="hero-actions"><a class="primary-link" href="#lab">{e(lt["lab_cta"])} <span aria-hidden="true">↗</span></a>'
            f'<a href="{GITHUB}/tree/main/research" target="_blank" rel="noopener">{e(lt["code_cta"])}</a></div>{scope}</div>'
            f'<article class="view" aria-labelledby="view-title"><div class="view-meta">'
            f'<h2 class="eyebrow" id="view-title">{e(t["view_label"])}</h2>'
            f'<span class="status">{e(t["status_no_position"])}</span>'
            f'<time datetime="{e(self.thesis["as_of"])}">{e(self.values["as_of"])}</time></div>'
            f'<p class="dated-label">{e(lt["dated"])}</p>'
            f'<p class="view-headline">{self.s(t["view_headline"])}</p>'
            f'{self.reaction() if self.study else ""}'
            '</article></div>'
            f'<details class="thesis-detail"><summary>{e(lt["reasoning"])}</summary><div class="inner">'
            f'<div class="why" aria-label="{e(t["why_label"])}">{why}</div>'
            f'<div class="decide"><div class="act"><h3>{e(t["act_label"])}</h3><p>{self.s(t["act"])}</p></div>'
            f'<div class="change"><h3>{e(t["change_label"])}</h3><p>{self.s(t["change"])}</p></div></div>'
            f'{self.monitor()}</div></details>{self.lenses() if self.study else ""}{self.tape()}</section></div>'
        ), f'<div class="bm"><nav class="toc" aria-label="{e(t["nav_label"])}">{nav}</nav></div>'

    def lab(self) -> str:
        t = self.lab_text
        return self.wrap("lab", self.section_head("lab", e(t["lab_title"]), e(t["lab_intro"])) + f'<p class="small muted">{e(t["scenario_source"])}</p>')

    def risk(self) -> str:
        t, report, lang = self.lab_text, self.risk_report, self.lang
        head = self.section_head("risk", e(t["risk_title"]), e(t["risk_intro"]))
        if not report.get("models") or not report.get("evaluation") or not report.get("latest"):
            return self.wrap("risk", head + f'<p class="study-unavailable">{e(t["risk_failure"])}</p>')
        try:
            return self._risk_report_body(head)
        except (KeyError, TypeError, ValueError, OverflowError, AttributeError):
            return self.wrap("risk", head + f'<p class="study-unavailable">{e(t["risk_failure"])}</p>')

    def _risk_report_body(self, head: str) -> str:
        t, report, lang = self.lab_text, self.risk_report, self.lang
        import math
        if {m["key"] for m in report["models"]} != set(t["model_names"]):
            raise ValueError("missing calibration model")
        for m in report["models"]:
            if m["key"] not in t["model_names"] or not 0 <= m["breaches"] <= m["n"] or m["n"] <= 0:
                raise ValueError("invalid calibration counts")
            if not math.isfinite(m["breach_rate_pct"]) or not 0 <= m["breach_rate_pct"] <= 100 or not 0 <= m["kupiec_p"] <= 1:
                raise ValueError("invalid calibration rate")
        if set(report["latest"]["models"]) != set(t["model_names"]):
            raise ValueError("missing latest model")
        for m in report["latest"]["models"].values():
            if not all(math.isfinite(m[k]) for k in ("var_pct", "es_pct")):
                raise ValueError("nonfinite loss estimate")
        rows = [[e(t["model_names"].get(m["key"], m["label"])), f'{m["breaches"]} / {m["n"]}',
                 e(f.pct(m["breach_rate_pct"], 2, lang)), e(f.num(m["kupiec_p"], 3, lang)) if m["kupiec_p"] >= .001 else "&lt;" + e(f.num(.001, 3, lang))] for m in report["models"]]
        tails = [[e(t["model_names"].get(key, key)), e(f.pct(v["var_pct"], 2, lang)), e(f.pct(v["es_pct"], 2, lang))] for key, v in report["latest"]["models"].items()]
        evaluation = report["evaluation"]
        period = f'{f.day(evaluation["start"], lang)} — {f.day(evaluation["end"], lang)}'
        links = "".join(f'<a href="{GITHUB}/{path}" target="_blank" rel="noopener">{e(t[label])} <span aria-hidden="true">↗</span></a>' for path, label in (
            ("blob/main/research/risk_method.md", "risk_method"), ("blob/main/research/study_inputs_2026-10-06.json", "risk_inputs"), ("blob/main/src/risk.py", "risk_code")))
        inner = head + f'<p class="take">{e(t["risk_take"])}</p><p class="research-date">{e(t["risk_date"])} {e(f.day(report["data_as_of"], lang))}</p>'
        inner += f'<div class="risk-meta"><span>{e(t["risk_scope"])} · {e(period)}</span><span>{e(t["risk_target"])} · 1%</span></div>'
        inner += self.table(t["risk_cols"], rows, "risk-table", label=t["risk_title"])
        inner += f'<p class="fig-caption">{e(t["risk_note"])}</p><div class="research-links">{links}</div>'
        inner += f'<details><summary>{e(t["tail_title"])}</summary><div class="inner">{self.table(t["tail_cols"], tails, label=t["tail_title"])}<p class="small muted">{e(t["tail_note"])}</p></div></details>'
        return self.wrap("risk", inner)

    # -- review of the 5 October thesis ------------------------------------
    def review(self) -> str:
        t = self.t
        head = "".join(f'<th scope="col">{e(h)}</th>' for h in t["review_head"])
        rows = []
        for item in self.thesis["review"]:
            expected, happened = t["review_rows"][item["id"]]
            verdict = item["verdict"]
            rows.append(
                f'<tr><td>{self.s(expected)}</td><td>{self.s(happened)}</td>'
                f'<td><span class="verdict {e(verdict)}"><span class="i" aria-hidden="true">{VERDICT_ICONS[verdict]}</span>{e(t["verdicts"][verdict])}</span></td></tr>'
            )
        inner = (
            self.section_head("review", e(t["review_title"]), self.s(t["review_intro"]))
            + f'<div class="sec-body"><div class="table-wrap" tabindex="0" role="region" aria-labelledby="review-title">'
            f'<table class="review"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            f'<div class="lesson"><span class="label">{e(t["review_lesson_label"])}</span><p>{self.s(t["review_lesson"])}</p></div>'
            f'<p class="muted small">{e(t["review_history"])}</p></div>'
        )
        return self.wrap("review", inner)

    # -- Rates, FX and quant -----------------------------------------------
    def fig(self, svg_wide: str, svg_compact: str, title: str, desc: str, legend: str = "") -> str:
        """One figure as a single line of HTML (it goes through Markdown, which breaks on blank lines)."""

        return (f'<div class="bm sec-body" lang="{self.t["html_lang"]}"><figure class="figure" aria-label="{e(title)}"><span class="label">{e(title)}</span>'
                f'{svg_wide}{svg_compact}{legend}<figcaption class="fig-caption">{e(desc)}</figcaption></figure></div>')

    def legend(self, items: list[tuple[str, str]]) -> str:
        return '<p class="legend always" aria-hidden="true">' + "".join(f'<span><i class="{css}"></i>{e(text)}</span>' for css, text in items) + "</p>"

    def curve_table(self) -> str:
        t, curve, gap = self.t, self.study["curve"], self.study["survey_gap"]
        lang, bp = self.lang, t["bp"]
        rows: list[Any] = []
        for row in curve["rows"]:
            if row["vertex"] in CURVE_VERTICES:
                rows.append([e(t["curve_tenors"][row["vertex"]]), e(f.pct(row["before"], 2, lang)), e(f.pct(row["after"], 2, lang)),
                             e(f"{f.num(row['change_bp'], 0, lang, signed=True)} {bp}")])

        def memo(label: str, before: float, after: float, fmt: Any) -> dict[str, Any]:
            return {"class": "memo", "cells": [e(label), e(fmt(before)), e(fmt(after)), e(f"{f.num((after - before) * 100, 0, lang, signed=True)} {bp}")]}

        pct2 = lambda v: f.pct(v, 2, lang)
        memo_labels = t["curve_memo"]
        rows += [
            memo(memo_labels["fwd"], curve["forward_1y1y"]["before"], curve["forward_1y1y"]["after"], pct2),
            memo(memo_labels["be"], curve["breakeven_2y"]["before"], curve["breakeven_2y"]["after"], pct2),
            memo(memo_labels["real"], curve["real_2y"]["before"], curve["real_2y"]["after"], pct2),
            memo(memo_labels["gap"], gap["gap_2y_before"], gap["gap_2y_after"], lambda v: f.pp(v, 2, lang, signed=True)),
        ]
        return self.table(list(t["curve_cols"]), rows, "curve", self.raw(t["curve_chart_title"]))

    def curve_chart(self) -> str:
        t, curve, gap = self.t, self.study["curve"], self.study["survey_gap"]
        labels = {k: self.raw(v) for k, v in t["curve_labels"].items()}
        survey = [(1.0, gap["survey_1y"], labels["survey"]), (2.0, gap["survey_2y"], labels["survey"])]
        fmt = lambda v: f.num(v, 2, self.lang)
        title, desc = self.raw(t["curve_chart_title"]), self.raw(t["curve_chart_desc"])
        policy = self.thesis["evidence"]["selic"]["value"]
        wide = curve_svg(curve["rows"], survey, policy, labels, fmt, title, desc)
        compact = curve_svg(curve["rows"], survey, policy, labels, fmt, title, desc, compact=True)
        legend = self.legend([("", labels["after"]), ("before", labels["before"]), ("survey", labels["survey"]), ("prev", labels["selic"])])
        return self.fig(wide, compact, title, desc, legend)

    def events_chart(self) -> str:
        t, rules = self.t, self.thesis["rules"]
        labels = {k: self.raw(v) for k, v in t["events_labels"].items()}
        paths = []
        for window in self.study["elections"]:
            if window["year"] != 2026 and not window["surprise"]:
                continue  # the quiet Mondays (2002, 2006, 2010) are in the table; a crisis path would flatten the scale
            kind = "now" if window["year"] == 2026 else "surprise"
            label = f'{window["year"]} · {f.pct(window["monday_move"], 2, self.lang, signed=True)}' if kind == "now" else None
            paths.append({"year": window["year"], "points": window["path"], "kind": kind, "label": label})
        p0 = next(w for w in self.study["elections"] if w["year"] == 2026)["friday_before"][1]
        levels = [
            {"value": rules["abandon_above"] / p0 * 100, "kind": "abandon", "label": self.raw(t["chart_labels"]["abandon"])},
            {"value": rules["exit_above"] / p0 * 100, "kind": "exit", "label": labels["exit"]},
            {"value": rules["entry_below"] / p0 * 100, "kind": "entry", "label": labels["entry"]},
        ]
        fmt = lambda v: f.num(v, 1, self.lang)
        title, desc = self.raw(t["events_chart_title"]), self.raw(t["events_chart_desc"])
        wide = events_svg(paths, levels, labels, fmt, title, desc)
        compact = events_svg(paths, levels, labels, fmt, title, desc, compact=True)
        legend = self.legend([("now", "2026"), ("surprise", "2014 · 2018 · 2022"), ("entry", labels["entry"]), ("exit", labels["exit"]),
                              ("abandon", f'{self.raw(t["chart_labels"]["abandon"])} ({f.num(rules["abandon_above"] / p0 * 100, 1, self.lang)})')])
        return self.fig(wide, compact, title, desc, legend)

    def events_table(self) -> str:
        t, lang = self.t, self.lang
        rows = []
        for w in self.study["elections"]:
            pending = w["year"] == 2026
            dash = e(t["events_undefined"])
            cells = [str(w["year"]), e(f.pct(w["monday_move"], 2, lang, signed=True)), e(f.num(w["z"], 1, lang, signed=True))]
            if pending:
                cells += [e(t["events_pending"])] * 3
            else:
                g1, g2 = w.get("giveback_runoff_friday"), w.get("giveback_first_close")
                cells += [e(f.pct(g1, 0, lang)) if g1 is not None else dash, e(f.pct(g2, 0, lang)) if g2 is not None else dash,
                          e(f.pct(w["runoff_session_move"], 2, lang, signed=True))]
            css = "now" if pending else "surprise" if w["surprise"] else ""
            rows.append({"class": css, "cells": cells})
        return self.table(list(t["events_cols"]), rows, "events") + f'<p class="muted small note">{e(t["events_note"])}</p>'

    def rule_table(self) -> str:
        t, geometry, rules, lang = self.t, self.study["rule_geometry"], self.thesis["rules"], self.lang
        walk, walk_lr = geometry["random_walk"]["diffusion"], geometry["random_walk"]["long_run"]
        spec = {
            "entry": (f.num(rules["entry_below"], 2, lang), "below_entry"),
            "exit": (f.num(rules["exit_above"], 2, lang), "above_exit"),
            "abandon": (f.num(rules["abandon_above"], 2, lang), "above_abandon"),
        }
        rows: list[Any] = []
        for key, (level, field) in spec.items():
            name, rule, verb = t["rule_rows"][key]
            sub = f'<span class="sub">{e(verb)}</span>'
            rows.append([
                f"<strong>{e(level)}</strong>", f'{e(name)}<span class="sub">{self.s(rule)}</span>',
                e(f.pct(geometry["giveback"][key], 0, lang)), e(f.pct(geometry["distance_pct"][key], 1, lang, signed=True)),
                f"{e(f.pct(walk[field], 0, lang))}{sub}", f"{e(f.pct(walk_lr[field], 0, lang))}{sub}",
            ])
        name, rule, _ = t["rule_rows"]["review"]
        low, high = f.num(rules["review_low"], 2, lang), f.num(rules["review_high"], 2, lang)
        rows.append([
            f"<strong>{e(low)}–{e(high)}</strong>", f'{e(name)}<span class="sub">{e(rule)}</span>',
            f'{e(f.pct(geometry["giveback"]["review_low"], 0, lang, signed=True))} … {e(f.pct(geometry["giveback"]["review_high"], 0, lang, signed=True))}',
            f'{e(f.pct(geometry["distance_pct"]["review_low"], 1, lang, signed=True))} … {e(f.pct(geometry["distance_pct"]["review_high"], 1, lang, signed=True))}', "—", "—",
        ])
        return self.table([self.raw(h) for h in t["rule_cols"]], rows, "rules", numeric_from=2)

    def quant_blocks(self) -> list[tuple[str, str]]:
        t = self.t
        notes = "".join(f"<div><dt>{e(term)}</dt><dd>{self.s(body)}</dd></div>" for term, body in t["rule_bullets"])
        limits = "".join(f"<li>{self.s(item)}</li>" for item in t["quant_limits"])
        head = self.section_head("quant", e(t["quant_title"]), self.s(t["quant_intro"]))
        wrap = lambda inner: f'<div class="bm" lang="{t["html_lang"]}">{inner}</div>'
        return [
            ("html", wrap(f'<section class="sec" id="quant" aria-labelledby="quant-title">{head}<div class="sec-body">'
                          + self.sub(e(t["quant_curve_title"]), self.s(t["quant_curve_text"]), e(t["quant_curve_take"])) + "</div></section>")),
            ("svg", self.curve_chart()),
            ("html", wrap(f'<div class="sec-body">{self.numbers(self.curve_table())}'
                          + self.sub(e(t["quant_events_title"]), self.s(t["quant_events_text"]), e(t["quant_events_take"])) + "</div>")),
            ("svg", self.events_chart()),
            ("html", wrap(f'<div class="sec-body">{self.numbers(self.events_table())}'
                          + self.sub(e(t["quant_rule_title"]), self.s(t["quant_rule_text"]), e(t["quant_rule_take"]))
                          + f'<p class="sub-intro">{self.s(t["quant_rule_summary"])}</p>'
                          + self.numbers(self.rule_table() + f'<dl class="notes">{notes}</dl>')
                          + f'<details><summary>{e(t["quant_limits_label"])}</summary><div class="inner"><ul>{limits}</ul></div></details>'
                          "</div>")),
        ]

    # -- Commodities -------------------------------------------------------
    def scatter_chart(self) -> str:
        t, basket = self.t, self.study["basket"]
        labels = {k: self.raw(v) for k, v in t["scatter_labels"].items()}
        title, desc = self.raw(t["scatter_title"]), self.raw(t["scatter_desc"])
        wide = scatter_svg(basket["scatter"], basket["slope"], basket["intercept"], labels, title, desc)
        compact = scatter_svg(basket["scatter"], basket["slope"], basket["intercept"], labels, title, desc, compact=True)
        return self.fig(wide, compact, title, desc)

    def bars_chart(self) -> str:
        t, yoy = self.t, self.study["year_on_year"]
        rows = [{"name": t["commodity_names"][r["key"]], "usd": r["usd"], "brl": r["brl"]} for r in sorted(yoy["rows"], key=lambda r: COMMODITY_ORDER.index(r["key"]))]
        labels = t["bars_labels"]
        fmt = lambda v: f.pct(v, 1, self.lang, signed=True)
        title, desc = self.raw(t["bars_title"]), self.raw(t["bars_desc"])
        wide = bars_svg(rows, labels, fmt, title, desc)
        compact = bars_svg(rows, labels, fmt, title, desc, compact=True)
        legend = self.legend([("bar-usd", labels["usd"]), ("bar-brl", labels["brl"])])
        return self.fig(wide, compact, title, desc, legend)

    def producer_table(self) -> str:
        t, lang = self.t, self.lang
        share = self.study["weights"]["share_of_exports"]
        hedge = {item["key"]: item for item in self.study["hedge"]}
        rows = []
        for key in COMMODITY_ORDER:
            item = hedge[key]
            rows.append([e(t["commodity_names"][key]), e(f.pct(share[key], 1, lang)), e(f.pct(item["vol_usd"], 0, lang)),
                         e(f.pct(item["vol_brl"], 0, lang)), e(f.num(item["corr_fx"], 2, lang))])
        return self.table(list(t["producer_cols"]), rows, "producers") + f'<p class="muted small note">{e(t["producer_note"])}</p>'

    def read_table(self) -> str:
        t = self.t
        rows = [[f"<strong>{self.s(row[0])}</strong>", *[self.s(cell) for cell in row[1:]]] for row in t["read_rows"]]
        return self.table(list(t["read_cols"]), rows, "read", numeric_from=99)

    def commodities_blocks(self) -> list[tuple[str, str]]:
        t = self.t
        head = self.section_head("commodities", e(t["commodities_title"]), self.s(t["commodities_intro"]))
        wrap = lambda inner: f'<div class="bm" lang="{t["html_lang"]}">{inner}</div>'
        oil = "".join(f"<div><h4>{e(title)}</h4><p>{self.s(body)}</p></div>" for title, body in t["c_oil_points"])
        nxt = "".join(f"<li>{self.s(item)}</li>" for item in t["c_next"])
        return [
            ("html", wrap(f'<section class="sec" id="commodities" aria-labelledby="commodities-title">{head}<div class="sec-body">'
                          + self.sub(e(t["c_link_title"]), self.s(t["c_link_text"]), e(t["c_link_take"])) + "</div></section>")),
            ("svg", self.scatter_chart()),
            ("html", wrap(f'<div class="sec-body"><p class="muted small note">{self.s(t["c_link_note"])}</p>'
                          + self.sub(e(t["c_producer_title"]), self.s(t["c_producer_text"]), e(t["c_producer_take"])) + "</div>")),
            ("svg", self.bars_chart()),
            ("html", wrap(f'<div class="sec-body">{self.numbers(self.producer_table())}'
                          + self.sub(e(t["c_oil_title"]), "", e(t["c_oil_take"])) + f'<div class="points">{oil}</div>'
                          + self.sub(e(t["c_sugar_title"]), self.s(t["c_sugar_text"]), e(t["c_sugar_take"]))
                          + self.sub(e(t["c_read_title"]), self.s(t["c_read_intro"]), e(t["c_read_take"])) + self.read_table()
                          + self.sub(e(t["c_next_title"])) + f'<ul class="plain">{nxt}</ul>'
                          "</div>")),
        ]

    # -- Evidence ----------------------------------------------------------
    def focus_table(self) -> str:
        t, ev = self.t, self.thesis["evidence"]
        years = ("2026", "2027", "2028")
        head = "<th scope=\"col\"></th>" + "".join(f'<th scope="col">{y}</th>' for y in years)
        rows = []
        for label, key, digits, kind in zip(t["focus_rows"], ("focus_selic", "focus_ipca", "focus_fx"), (2, 2, 3), ("pct", "pct", "num")):
            cells = []
            for year in years:
                value = ev[key].get(year)
                if value is None:
                    cells.append(f'<td class="muted">{e(t["na"])}</td>')
                else:
                    text = f.pct(value, digits, self.lang) if kind == "pct" else f.num(value, digits, self.lang)
                    cells.append(f"<td>{e(text)}</td>")
            rows.append(f'<tr><th scope="row">{e(label)}</th>{"".join(cells)}</tr>')
        return (
            f'<div class="table-wrap focus" tabindex="0" role="region" aria-label="{self.s(t["focus_table_caption"])}">'
            f'<table><caption>{self.s(t["focus_table_caption"])}</caption><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
        )

    def evidence(self) -> str:
        t = self.t
        blocks = []
        for kind in ("fact", "pricing", "survey", "interpretation"):
            items = []
            for text, sources in zip(t["evidence"][kind], EVIDENCE_SOURCES[kind]):
                links = " · ".join(filter(None, (self.source_link(key) for key in sources)))
                src = f' <span class="src">{links}</span>' if links else ""
                items.append(f"<li>{self.s(text)}{src}</li>")
            blocks.append(
                f'<div class="kind {kind}"><h3><span class="tag {kind}">{e(t["kinds"][kind])}</span>'
                f'<small>{e(t["kind_help"][kind])}</small></h3><ul>{"".join(items)}</ul></div>'
            )
        inner = (
            self.section_head("evidence", e(t["evidence_title"]), self.s(t["evidence_intro"]))
            + f'<div class="sec-body"><div class="kinds">{"".join(blocks)}</div>{self.focus_table()}</div>'
        )
        return self.wrap("evidence", inner)

    # -- Paper trade, scenarios and the PTAX chart ---------------------------
    def trade_top(self) -> str:
        t = self.t
        rows = []
        for i, (term, body) in enumerate(t["trade_rows"]):
            key = "key" if i in (4, 5, 6) else ""
            rows.append(f'<div class="{key}"><dt>{e(term)}</dt><dd>{self.s(body)}</dd></div>')
        inner = (
            self.section_head("trade", e(t["trade_title"]), e(t["trade_intro"]))
            + f'<div class="sec-body"><p class="trade-status"><span class="status">{self.s(t["trade_status"])}</span></p>'
            f'<dl class="rules">{"".join(rows)}</dl></div>'
        )
        return self.wrap("trade", inner)

    def chart(self) -> str:
        """Inline SVG needs st.markdown (st.html strips SVG), so keep it on one line."""

        t = self.t
        history = (self.snapshot.get("history") or {}).get("ptax") or []
        if len(history) < 2:
            return ""
        r, focus = self.thesis["rules"], self.thesis["evidence"]["focus_fx"]["2026"]
        labels = {k: fill(v, self.values, self.lang) for k, v in t["chart_labels"].items()}
        levels = [
            {"value": r["abandon_above"], "kind": "abandon", "label": labels["abandon"]},
            {"value": r["exit_above"], "kind": "exit", "label": labels["exit"], "nudge": -6},
            {"value": focus, "kind": "prev", "label": labels["prev"], "nudge": 7},
            {"value": r["entry_below"], "kind": "entry", "label": labels["entry"]},
        ]
        events = [{"date": "2026-09-16", "label": labels["event"]}, {"date": self.thesis["election"]["first_round"], "label": labels["vote"]}]
        title = fill(t["chart_title"], {**self.values, "n": str(len(history))}, self.lang)
        desc = fill(t["chart_desc"], {**self.values, "start": f.day(history[0][0], self.lang), "end": f.day(history[-1][0], self.lang),
                                       "latest": f.num(float(history[-1][1]), 4, self.lang)}, self.lang)

        def value(v: float) -> str:
            return f.num(v, 2 if abs(v * 100 - round(v * 100)) < 1e-6 else 4, self.lang)

        wide = ptax_svg(history, levels, events, value, lambda d: f.day(d, self.lang, year=False), title, desc)
        compact = ptax_svg(history, levels, events, value, lambda d: f.day(d, self.lang, year=False), title, desc, compact=True)
        legend = (
            '<p class="legend" aria-hidden="true">'
            f'<span><i></i>PTAX</span><span><i class="entry"></i>{e(labels["entry"])}</span><span><i class="exit"></i>{e(labels["exit"])}</span>'
            f'<span><i class="abandon"></i>{e(labels["abandon"])}</span><span><i class="prev"></i>{e(labels["prev"])}</span></p>'
        )
        rows = "".join(f"<tr><td>{e(f.day(d, self.lang))}</td><td>{e(f.num(float(v), 4, self.lang))}</td></tr>" for d, v in reversed(history))
        table = (
            f'<details><summary>{e(t["chart_table"])}</summary><div class="inner"><div class="table-wrap" tabindex="0" role="region" aria-label="{e(title)}">'
            f'<table><thead><tr><th scope="col">{e(t["chart_cols"][0])}</th><th scope="col">{e(t["chart_cols"][1])}</th></tr></thead><tbody>{rows}</tbody></table></div></div></details>'
        )
        return (
            f'<div class="bm sec-body" lang="{t["html_lang"]}"><figure class="figure" aria-label="{e(title)}"><span class="label">{e(title)}</span>'
            f'<p class="fig-latest">PTAX <strong class="num">{e(f.num(float(history[-1][1]), 4, self.lang))}</strong> <span class="muted">{e(f.day(history[-1][0], self.lang))}</span></p>'
            f"{wide}{compact}{legend}<figcaption class=\"fig-caption\">{e(desc)}</figcaption>{table}</figure></div>"
        )

    def paths(self) -> str:
        t = self.t
        cards = []
        for i, (title, signals, meaning, action) in enumerate(t["paths"]):
            outside = " outside" if i == len(t["paths"]) - 1 else ""
            letter = "ABCD"[i]
            cards.append(
                f'<article class="path{outside}"><h3><span class="n">{letter}</span>{self.s(title)}</h3><dl>'
                f'<div><dt>{e(t["path_fields"][0])}</dt><dd>{self.s(signals)}</dd></div>'
                f'<div><dt>{e(t["path_fields"][1])}</dt><dd>{self.s(meaning)}</dd></div>'
                f'<div><dt>{e(t["path_fields"][2])}</dt><dd class="do">{self.s(action)}</dd></div></dl></article>'
            )
        dates = "".join(
            f'<li><time datetime="{e(item["date"])}">{e(f.day(item["date"], self.lang))}</time>{e(t["calendar"][item["event"]])}</li>'
            for item in self.thesis["calendar"]
        )
        risks = "".join(f"<li>{self.s(item)}</li>" for item in t["trade_risks"])
        return (
            f'<div class="bm sec-body paths-block" lang="{t["html_lang"]}">'
            + self.sub(self.s(t["paths_title"]), e(t["paths_intro"]))
            + f'<div class="paths">{"".join(cards)}</div>'
            f'<div class="calendar-wrap"><span class="label">{e(t["calendar_label"])}</span><ul class="calendar">{dates}</ul></div>'
            f'<details class="more"><summary>{e(t["trade_more"])}</summary><div class="inner">'
            f'<h4>{e(t["trade_risks_label"])}</h4><ul>{risks}</ul>'
            f'<h4>{e(t["trade_change_label"])}</h4><p>{self.s(t["trade_change"])}</p></div></details>'
            "</div>"
        )

    # -- Method, data and about ----------------------------------------------
    def data_table(self) -> str:
        t = self.t
        head = "".join(f'<th scope="col">{e(h)}</th>' for h in t["data_cols"])
        rows = []
        order = ("selic_target", "fed_target_range", "brazil_us_policy_differential", "ptax_usd_brl_midpoint", "us_2_year_treasury",
                 "us_10_year_treasury", "focus_selic", "focus_ipca", "focus_fx")
        for key in order:
            item = self.series.get(key)
            if not item:
                continue
            name = t["series_names"][key].format(year=item.get("selected_reference_year", self.today.year))
            observed = item.get("latest_observation_date")
            frequency = item.get("frequency", "daily")
            _, chip = self.freshness_chip(observed, frequency)
            url = item.get("source_url", "")
            label = t["source_short"]["derived_gap"] if key == "brazil_us_policy_differential" else item.get("source", t["na"])
            source = f'<a href="{e(url)}" target="_blank" rel="noopener">{e(label)}</a>' if url.startswith("https://") else e(label)
            rows.append(f"<tr><th scope=\"row\">{e(name)}</th><td>{e(self.series_value(key, item))}</td><td>{e(f.day(observed, self.lang) if observed else t['na'])}</td>"
                        f"<td>{e(t['freq'].get(frequency, frequency))}</td><td>{source}</td><td>{chip}</td></tr>")
        for key in ("brent", "iron_ore", "soybeans", "sugar"):
            item = self.commodities.get(key)
            if not item:
                continue
            frequency = item.get("frequency", "Daily").lower()
            _, chip = self.freshness_chip(item.get("latest_date"), frequency)
            rows.append(f"<tr><th scope=\"row\">{e(t['series_names'][key])}</th><td>{e(self.commodity_value(key, item))}</td>"
                        f"<td>{e(f.period(item['latest_date'], frequency, self.lang))}</td><td>{e(t['freq'].get(frequency, frequency))}</td>"
                        f"<td>{self.source_link({'brent': 'fred_brent', 'iron_ore': 'fred_iron', 'soybeans': 'fred_soy', 'sugar': 'fred_sugar'}[key])}</td><td>{chip}</td></tr>")
        return (
            f'<div class="table-wrap" tabindex="0" role="region" aria-label="{e(t["data_label"])}"><table class="data">'
            f'<thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
        )

    def method(self) -> str:
        t = self.t
        refresh = self.snapshot.get("refresh") or {}
        failed = [key for key, item in (refresh.get("sources") or {}).items() if item.get("status") != "ok"]
        failed_html = f"<p>{self.s(t['refresh_failed'], names=', '.join(failed))}</p>" if failed else ""
        attempted = refresh.get("attempted_at") or self.snapshot.get("updated_at")
        status_line = self.s(t["refresh_status"], attempted=self.stamp(attempted),
                             ok=str(refresh.get("sources_ok", t["na"])), total=str(refresh.get("sources_total", t["na"])))
        calc = "".join(f"<div><dt>{e(term)}</dt><dd>{self.s(body)}</dd></div>" for term, body in t["method_calc"])
        limits = "".join(f"<li>{self.s(item)}</li>" for item in t["limits"])
        labels = self.t["source_labels"]
        sources = "".join(
            f'<li><a href="{e(src["url"])}" target="_blank" rel="noopener">{e(labels.get(key, src["label"]))}</a> <span class="d">{e(f.day(src["date"], self.lang))}</span></li>'
            for key, src in sorted(self.thesis["sources"].items(), key=lambda item: labels.get(item[0], item[1]["label"]))
        )
        inner = (
            self.section_head("method", e(t["method_title"]))
            + '<div class="sec-body">'
            f'<details><summary>{e(t["method_calc_label"])}</summary><div class="inner"><dl class="defs">{calc}</dl></div></details>'
            f'<details><summary>{e(t["data_label"])}</summary><div class="inner">{self.data_table()}</div></details>'
            f'<details><summary>{e(t["refresh_label"])}</summary><div class="inner"><p>{e(t["refresh_text"])}</p><p>{status_line}</p>{failed_html}<p class="muted">{e(t["refresh_history"])}</p></div></details>'
            f'<details><summary>{e(t["limits_label"])}</summary><div class="inner"><ul>{limits}</ul></div></details>'
            f'<details><summary>{e(t["sources_label"])}</summary><div class="inner"><p class="muted">{e(t["sources_note"])}</p><ul class="sources">{sources}</ul>'
            f'<h4>{e(t["archive_label"])}</h4><p>{e(t["archive"])} <a href="{GITHUB}/tree/main/research" target="_blank" rel="noopener">GitHub</a></p></div></details>'
            "</div>"
        )
        return self.wrap("method", inner)

    def about(self) -> str:
        t = self.t
        return (
            f'<div class="bm" lang="{t["html_lang"]}"><section class="sec" id="about" aria-labelledby="about-title">'
            f'<div class="sec-head"><h2 id="about-title">{e(t["about_title"])}</h2></div>'
            f'<div class="sec-body about"><div><p>{e(t["about"])}</p><p>{e(t["about_build"])}</p><p>{e(LAB_TEXT[self.lang]["about_lab"])}</p></div>'
            f'<div class="links"><a href="{GITHUB}" target="_blank" rel="noopener">{e(t["links"]["code"])}</a>'
            f'<a href="{LINKEDIN}" target="_blank" rel="noopener">{e(t["links"]["linkedin"])}</a></div></div>'
            f'<p class="footer">{self.s(t["footer"])}</p></section></div>'
        )


def _pack(items: list[tuple[str, str]]) -> dict[str, str]:
    """Merge neighbouring HTML blocks and number the blocks: body_1, chart_1, body_2, ..."""

    out: dict[str, str] = {}
    counts = {"body": 0, "chart": 0}
    last = None
    for kind, markup in items:
        if not markup:
            continue
        name = "body" if kind == "html" else "chart"
        if kind == "html" and last == "html":
            out[f"body_{counts['body']}"] += markup
        else:
            counts[name] += 1
            out[f"{name}_{counts[name]}"] = markup
        last = kind
    return out


def render(lang: str, thesis: dict[str, Any], snapshot: dict[str, Any], today: date, lens: str = "quant", risk_report: dict[str, Any] | None = None) -> dict[str, str]:
    """Return the page blocks in display order, keyed by name (``chart_*`` blocks are SVG, the rest HTML)."""

    page = Page(lang, thesis, snapshot, today, lens, risk_report)
    if not thesis:
        message = e(page.t["unavailable"])
        return {"top": page.top_bar(), "hero": f'<div class="bm"><h1>{e(page.t["title"])}</h1><p class="banner">{message}</p></div>'}
    hero, toc = page.hero()
    items: list[tuple[str, str]] = []
    if page.study:
        for key in lens_order(page.lens):
            items += page.quant_blocks() if key == "quant" else page.commodities_blocks()
    items += [("html", page.trade_top()), ("svg", page.chart()), ("html", page.paths() + page.review() + page.evidence() + page.method() + page.about())]
    return {"top": page.top_bar(), "hero": hero, "toc": toc, "lab": page.lab(), "risk": page.risk(), **_pack(items)}
