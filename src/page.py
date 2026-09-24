"""Build the page as a handful of HTML strings.

Pure functions (no Streamlit import) so the whole page can be rendered and
checked in tests.  All prose comes from ``src.content``; every value comes from
``research/thesis.json`` (dated) or ``research/live_snapshot.json`` (refreshed).
"""
from __future__ import annotations

from datetime import date
from html import escape
from typing import Any

from src import formatting as f
from src.chart import ptax_svg
from src.content import TEXT
from src.freshness import run_age_days, status as fresh_status
from src.thesis import fill, placeholders, rule_status

GITHUB = "https://github.com/Midiansi/brazil-rates-fx-scenario-monitor"
LINKEDIN = "https://www.linkedin.com/in/romeomugnier"
SECTIONS = ("view", "review", "evidence", "paths", "trade", "commodities", "method")
TAPE = ("selic_target", "fed_target_range", "brazil_us_policy_differential", "ptax_usd_brl_midpoint", "us_2_year_treasury", "brent")
EVIDENCE_SOURCES = {
    "fact": (("copom_281",), ("fomc_statement",), ("derived_gap",), ("datafolha_0917", "tse"), ("ifi_ploa2027",)),
    "pricing": (("bcb_ptax",), ("treasury",), ("anbima_ettj",), ("fred_brent", "advfn_estadao_0923")),
    "survey": (("bcb_focus",), ("fomc_sep",), ("eia_steo", "aljazeera_pipeline")),
    "interpretation": ((), (), ()),
}
VERDICT_ICONS = {"confirmed": "✓", "partly": "~", "unresolved": "?", "not_triggered": "–", "underweighted": "!"}


def e(text: Any) -> str:
    return escape(str(text), quote=True)


class Page:
    """Everything needed to render one language, computed once."""

    def __init__(self, lang: str, thesis: dict[str, Any], snapshot: dict[str, Any], today: date):
        self.lang = lang if lang in TEXT else "en"
        self.t = TEXT[self.lang]
        self.thesis = thesis
        self.snapshot = snapshot if isinstance(snapshot, dict) else {}
        self.series = self.snapshot.get("series") if isinstance(self.snapshot.get("series"), dict) else {}
        self.commodities = self.snapshot.get("commodities") if isinstance(self.snapshot.get("commodities"), dict) else {}
        self.today = today
        self.values = placeholders(thesis, self.lang) if thesis else {}

    # -- helpers -----------------------------------------------------------
    def s(self, text: str, **extra: str) -> str:
        """Fill placeholders, apply French spacing, escape for HTML."""

        return e(fill(text, {**self.values, **extra}, self.lang))

    def source_link(self, key: str) -> str:
        source = self.thesis.get("sources", {}).get(key)
        if not source:
            return ""
        short = self.t["source_short"].get(key, source["label"].split(" · ")[0])
        return f'<a href="{e(source["url"])}" target="_blank" rel="noopener">{e(short)}</a>'

    def section_head(self, index: int, key: str, title: str, intro: str = "") -> str:
        intro_html = f'<p class="intro">{intro}</p>' if intro else ""
        return (
            f'<div class="sec-head"><span class="n">{index:02d}</span><h2 id="{key}-title">{title}</h2>{intro_html}</div>'
        )

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

    # -- sections ----------------------------------------------------------
    def top_bar(self) -> str:
        t = self.t
        return (
            '<div class="bm"><div class="bm-top"><strong>Romeo Mugnier de Almeida</strong>'
            f'<span class="byline">{e(t["byline"])}</span><span class="links">'
            f'<a href="{GITHUB}" target="_blank" rel="noopener">GitHub</a>'
            f'<a href="{LINKEDIN}" target="_blank" rel="noopener">LinkedIn</a></span></div></div>'
        )

    def monitor(self) -> str:
        t = self.t
        result = rule_status(self.thesis, self.snapshot, self.today)
        state = result.get("state", "unavailable")
        extra = {}
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
            when = f.day(observed, self.lang, year=False) if observed else "—"
            cells.append(
                f'<div><dt>{e(t["tape"][key])}</dt><dd><span class="v num">{e(value)}</span>'
                f'<span class="m">{e(when)} · {e(source)}</span><span class="m">{chip}</span></dd></div>'
            )
        banner = ""
        run_age = run_age_days((self.snapshot.get("refresh") or {}).get("attempted_at"), self.today)
        attempted = (self.snapshot.get("refresh") or {}).get("attempted_at") or self.snapshot.get("updated_at")
        if run_age is None or run_age > 4:
            when = f.day(attempted[:10], self.lang) if isinstance(attempted, str) and len(attempted) >= 10 else "—"
            banner = f'<p class="banner" role="status">{self.s(t["refresh_banner"], date=when)}</p>'
        elif any(state in ("stale", "unknown") for state in states):
            banner = f'<p class="banner" role="status">{e(t["stale_banner"])}</p>'
        caption = self.s(t["refresh_status"], attempted=f.timestamp(attempted, self.lang) if attempted else "—",
                         ok=str((self.snapshot.get("refresh") or {}).get("sources_ok", "—")),
                         total=str((self.snapshot.get("refresh") or {}).get("sources_total", "—")))
        return (
            f'<h2 class="sr-only">{e(t["tape_label"])}</h2><dl class="tape" aria-label="{e(t["tape_label"])}">{"".join(cells)}</dl>'
            f'<div class="tape-caption"><span>{e(t["tape_label"])}</span><span>{caption}</span></div>{banner}'
        )

    def hero(self) -> str:
        t = self.t
        why = "".join(
            f'<div><h3><span class="n">{i}</span>{self.s(title)}</h3><p>{self.s(body)}</p></div>'
            for i, (title, body) in enumerate(t["why"], 1)
        )
        nav = "".join(
            f'<a href="#{key}"><span class="n">{i:02d}</span>{e(t["nav"][key])}</a>' for i, key in enumerate(SECTIONS, 1)
        )
        return (
            f'<div class="bm" lang="{t["html_lang"]}"><section class="hero" id="view" aria-labelledby="view-title">'
            f'<p class="kicker">{e(t["kicker"])}</p><div class="hero-head"><h1>{e(t["title"])}</h1><p class="lede">{e(t["intro"])}</p></div>'
            f'<article class="view" aria-labelledby="view-title"><div class="view-meta">'
            f'<h2 class="label" id="view-title">{e(t["view_label"])}</h2>'
            f'<span class="status">{e(t["status_no_position"])}</span>'
            f'<time datetime="{e(self.thesis["as_of"])}">{e(self.values["as_of"])}</time></div>'
            f'<p class="view-headline">{self.s(t["view_headline"])}</p>'
            f'<div class="why" aria-label="{e(t["why_label"])}">{why}</div>'
            f'<div class="decide"><div class="act"><h3>{e(t["act_label"])}</h3><p>{self.s(t["act"])}</p></div>'
            f'<div class="change"><h3>{e(t["change_label"])}</h3><p>{self.s(t["change"])}</p></div></div>'
            f'{self.monitor()}</article>{self.tape()}</section></div>'
        ), f'<div class="bm"><nav class="toc" aria-label="{e(t["nav_label"])}">{nav}</nav></div>'

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
        return (
            f'<div class="bm" lang="{t["html_lang"]}"><section class="sec" id="review" aria-labelledby="review-title">'
            + self.section_head(2, "review", e(t["review_title"]), self.s(t["review_intro"]))
            + f'<div class="sec-body"><div class="table-wrap" tabindex="0" role="region" aria-labelledby="review-title">'
            f'<table class="review"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            f'<div class="lesson"><span class="label">{e(t["review_lesson_label"])}</span><p>{e(t["review_lesson"])}</p></div>'
            "</div></section></div>"
        )

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
                    cells.append("<td>—</td>")
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
        return (
            f'<div class="bm" lang="{t["html_lang"]}"><section class="sec" id="evidence" aria-labelledby="evidence-title">'
            + self.section_head(3, "evidence", e(t["evidence_title"]), self.s(t["evidence_intro"]))
            + f'<div class="sec-body"><div class="kinds">{"".join(blocks)}</div>{self.focus_table()}</div></section></div>'
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
        return (
            f'<div class="bm" lang="{t["html_lang"]}"><section class="sec" id="paths" aria-labelledby="paths-title">'
            + self.section_head(4, "paths", self.s(t["paths_title"]), e(t["paths_intro"]))
            + f'<div class="sec-body"><div class="paths">{"".join(cards)}</div>'
            f'<div class="calendar-wrap"><span class="label">{e(t["calendar_label"])}</span><ul class="calendar">{dates}</ul></div>'
            "</div></section></div>"
        )

    def trade_top(self) -> str:
        t = self.t
        rows = []
        for i, (term, body) in enumerate(t["trade_rows"]):
            key = " key" if i in (4, 5, 6) else ""
            rows.append(f'<div class="{key.strip()}"><dt>{e(term)}</dt><dd>{self.s(body)}</dd></div>')
        return (
            f'<div class="bm" lang="{t["html_lang"]}"><section class="sec" id="trade" aria-labelledby="trade-title">'
            + self.section_head(5, "trade", e(t["trade_title"]))
            + f'<div class="sec-body"><p class="trade-status"><span class="status">{self.s(t["trade_status"])}</span></p>'
            f'<dl class="rules">{"".join(rows)}</dl></div></section></div>'
        )

    def chart(self) -> str:
        """Inline SVG needs st.markdown (st.html strips SVG), so keep it on one line."""

        t = self.t
        history = (self.snapshot.get("history") or {}).get("ptax") or []
        if len(history) < 2:
            return ""
        r, p = self.thesis["rules"], self.thesis["previous_rules"]
        labels = {k: fill(v, self.values, self.lang) for k, v in t["chart_labels"].items()}
        levels = [
            {"value": r["abandon_above"], "kind": "abandon", "label": labels["abandon"]},
            {"value": p["trigger"], "kind": "prev", "label": labels["prev"], "nudge": -6},
            {"value": r["exit_above"], "kind": "exit", "label": labels["exit"], "nudge": 7},
            {"value": r["entry_below"], "kind": "entry", "label": labels["entry"]},
        ]
        events = [{"date": "2026-09-16", "label": labels["event"]}]
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

    def trade_bottom(self) -> str:
        t = self.t
        risks = "".join(f"<li>{self.s(item)}</li>" for item in t["trade_risks"])
        return (
            f'<div class="bm sec-body more" lang="{t["html_lang"]}"><details><summary>{e(t["trade_more"])}</summary><div class="inner">'
            f'<h4>{e(t["trade_risks_label"])}</h4><ul>{risks}</ul>'
            f'<h4>{e(t["trade_change_label"])}</h4><p>{self.s(t["trade_change"])}</p>'
            f'<h4>{e(t["trade_channels_label"])}</h4><p>{self.s(t["trade_channels"])}</p>'
            f'<h4>{e(t["trade_math_label"])}</h4><p class="num">{self.s(t["trade_math"])}</p>'
            "</div></details></div>"
        )

    def commodities_section(self) -> str:
        t = self.t
        head = "".join(f'<th scope="col">{e(h)}</th>' for h in t["commodity_cols"])
        rows = []
        for key in ("brent", "iron_ore", "soybeans", "sugar"):
            item = self.commodities.get(key)
            verdict, reason = t["commodity_verdicts"][key]
            if not item:
                rows.append(f'<tr><th scope="row">{e(t["commodity_names"][key])}</th><td colspan="2">{e(t["unavailable"])}</td>'
                            f"<td><strong>{e(verdict)}</strong>{self.s(reason)}</td></tr>")
                continue
            frequency = item.get("frequency", "Daily")
            try:
                change = (float(item["latest"]) / float(item["previous"]) - 1) * 100
                change_text = f.pct(change, 1, self.lang, signed=True)
            except (KeyError, TypeError, ValueError, ZeroDivisionError):
                change_text = "—"
            state, chip = self.freshness_chip(item.get("latest_date"), frequency)
            period = f.period(item["latest_date"], frequency, self.lang)
            previous = f.period(item["previous_date"], frequency, self.lang)
            rows.append(
                f'<tr><th scope="row">{e(t["commodity_names"][key])}<span class="sub">{self.source_link({"brent": "fred_brent", "iron_ore": "fred_iron", "soybeans": "fred_soy", "sugar": "fred_sugar"}[key])}</span></th>'
                f'<td>{e(self.commodity_value(key, item))}<span class="sub">{e(period)} · {e(t["freq"].get(frequency.lower(), frequency))}</span><span class="sub">{chip}</span></td>'
                f'<td>{e(change_text)}<span class="sub">{e(t["vs"])} {e(previous)}</span></td>'
                f"<td><strong>{e(verdict)}</strong>{self.s(reason)}</td></tr>"
            )
        return (
            f'<div class="bm" lang="{t["html_lang"]}"><section class="sec" id="commodities" aria-labelledby="commodities-title">'
            + self.section_head(6, "commodities", e(t["commodities_title"]), e(t["commodities_intro"]))
            + f'<div class="sec-body"><div class="table-wrap" tabindex="0" role="region" aria-labelledby="commodities-title">'
            f'<table class="commodities"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            + self.equity()
            + "</div></section></div>"
        )

    def equity(self) -> str:
        t = self.t
        steps = "".join(f"<div><h3>{e(title)}</h3><p>{e(body)}</p></div>" for title, body in t["equity_steps"])
        return (
            f'<h3 style="margin:3rem 0 0.5rem;font-size:1.15rem">{e(t["equity_title"])}</h3><p class="muted" style="max-width:68ch">{e(t["equity_intro"])}</p>'
            f'<div class="steps">{steps}</div><p class="examples"><span class="label">{e(t["equity_examples_label"])}</span>{e(t["equity_examples"])}</p>'
        )

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
            label = t["source_short"]["derived_gap"] if key == "brazil_us_policy_differential" else item.get("source", "—")
            source = f'<a href="{e(url)}" target="_blank" rel="noopener">{e(label)}</a>' if url.startswith("https://") else e(label)
            rows.append(f"<tr><th scope=\"row\">{e(name)}</th><td>{e(self.series_value(key, item))}</td><td>{e(f.day(observed, self.lang) if observed else '—')}</td>"
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
        status_line = self.s(t["refresh_status"], attempted=f.timestamp(attempted, self.lang) if attempted else "—",
                             ok=str(refresh.get("sources_ok", "—")), total=str(refresh.get("sources_total", "—")))
        calc = "".join(f"<div><dt>{e(term)}</dt><dd>{self.s(body)}</dd></div>" for term, body in t["method_calc"])
        limits = "".join(f"<li>{e(item)}</li>" for item in t["limits"])
        labels = self.t["source_labels"]
        sources = "".join(
            f'<li><a href="{e(src["url"])}" target="_blank" rel="noopener">{e(labels.get(key, src["label"]))}</a> <span class="d">{e(f.day(src["date"], self.lang))}</span></li>'
            for key, src in sorted(self.thesis["sources"].items(), key=lambda item: labels.get(item[0], item[1]["label"]))
        )
        return (
            f'<div class="bm" lang="{t["html_lang"]}"><section class="sec" id="method" aria-labelledby="method-title">'
            + self.section_head(7, "method", e(t["method_title"]))
            + '<div class="sec-body">'
            f'<details><summary>{e(t["method_calc_label"])}</summary><div class="inner"><dl class="defs">{calc}</dl></div></details>'
            f'<details><summary>{e(t["data_label"])}</summary><div class="inner">{self.data_table()}</div></details>'
            f'<details><summary>{e(t["refresh_label"])}</summary><div class="inner"><p>{e(t["refresh_text"])}</p><p>{status_line}</p>{failed_html}<p class="muted">{e(t["refresh_history"])}</p></div></details>'
            f'<details><summary>{e(t["limits_label"])}</summary><div class="inner"><ul>{limits}</ul></div></details>'
            f'<details><summary>{e(t["sources_label"])}</summary><div class="inner"><p class="muted">{e(t["sources_note"])}</p><ul class="sources">{sources}</ul>'
            f'<h4>{e(t["archive_label"])}</h4><p>{e(t["archive"])} <a href="{GITHUB}/blob/main/research/data_snapshot.json" target="_blank" rel="noopener">GitHub</a></p></div></details>'
            "</div></section></div>"
        )

    def about(self) -> str:
        t = self.t
        return (
            f'<div class="bm" lang="{t["html_lang"]}"><section class="sec" id="about" aria-labelledby="about-title">'
            f'<div class="sec-head"><span class="n">—</span><h2 id="about-title">{e(t["about_title"])}</h2></div>'
            f'<div class="sec-body about"><div><p>{e(t["about"])}</p><p>{e(t["about_build"])}</p></div>'
            f'<div class="links"><a href="{GITHUB}" target="_blank" rel="noopener">{e(t["links"]["code"])}</a>'
            f'<a href="{LINKEDIN}" target="_blank" rel="noopener">{e(t["links"]["linkedin"])}</a></div></div>'
            f'<p class="footer">{self.s(t["footer"])}</p></section></div>'
        )


def render(lang: str, thesis: dict[str, Any], snapshot: dict[str, Any], today: date) -> dict[str, str]:
    """Return the page blocks in display order, keyed by name."""

    page = Page(lang, thesis, snapshot, today)
    if not thesis:
        message = e(page.t["unavailable"])
        return {"top": page.top_bar(), "hero": f'<div class="bm"><h1>{e(page.t["title"])}</h1><p class="banner">{message}</p></div>'}
    hero, toc = page.hero()
    return {
        "top": page.top_bar(),
        "hero": hero,
        "body_1": toc + page.review() + page.evidence() + page.paths() + page.trade_top(),
        "chart": page.chart(),
        "body_2": page.trade_bottom() + page.commodities_section() + page.method() + page.about(),
    }
