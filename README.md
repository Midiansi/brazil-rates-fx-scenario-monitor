# Brazil Macro

A student research log on how Brazilian and U.S. interest rates, the Brazilian real and Brazil's main commodity exports move together. Each view is dated, backed by official data, and paired with the rules that would make me act or change my mind — and each old view is reviewed after the fact.

Public site: https://brasilmacro.streamlit.app/ (English, `?lang=pt` Português, `?lang=fr` Français)

Educational research, not investment advice. No real positions and no claimed performance.

![First screen of the site: the dated view, why, and what would make me act or change my mind](assets/dashboard.png)

## Current thesis (24 September 2026)

**The real is held up by its large interest-rate cushion; the 4 October election will decide the next move. No position until the market shows its hand.**

- Both 16 September decisions matched the previous thesis: the Copom cut the Selic to 13.75%, the Fed raised its range to 3.75–4.00%. The rate gap narrowed from 10.38 to 9.88 points, yet USD/BRL rose only 1.7% and never reached the 5.22 trigger — no paper position was opened.
- Brazil's two-year rate (13.76%, ANBIMA) sits about 1.5 points above the average implied by economists' own Selic forecasts (12.29%), which I read mostly as a fiscal and political risk premium.
- Conditional paper trade: after the first round, buy the real (short USD/BRL) only on two PTAX closes below 5.10 with the U.S. two-year yield at or below 5.00%. Drop the idea on any close above 5.30; exit on two closes above 5.20; review at 4.97–5.00 or on 4 November.

The full reasoning — review of the 13 September call, evidence sorted into facts, market pricing, surveys and interpretation, four post-election paths, commodity channels and sources — is on the site and in the printable briefs in `outputs/`. The previous case is preserved unchanged in `research/data_snapshot.json` and `research/scenario_trade.md`.

## How it works

```
GitHub Actions (weekdays, 22:17 UTC)                      Streamlit Community Cloud
scripts/refresh_market_data.py                            app.py
  ├─ BCB: PTAX, Selic (SGS 432), Focus survey               reads research/thesis.json      (dated thesis, numbers only)
  ├─ New York Fed → Fed target range  (FRED fallback)       reads research/live_snapshot.json (refreshed data)
  ├─ U.S. Treasury → 2y/10y yields   (FRED fallback)        renders cached HTML per language; no network, no pandas
  └─ FRED: Brent (EIA), iron ore / soy / sugar (IMF)
        │ each source validated independently
        ▼
research/live_snapshot.json  ──commit──▶  redeploy  ──▶  page shows every value with its own date and freshness
scripts/check_freshness.py   ──▶ run fails (owner notified) if key figures are > 1 week old
```

- **Visitors never trigger a data request.** The page reads two small JSON files and pre-generated PDFs. HTML is built once per language and data version and cached in memory.
- **One failed feed never blanks or freezes the others.** Each source keeps its last good value, original date and an error message in `refresh.sources`; the page flags delayed or stale values instead of hiding them.
- **Honest refresh claims.** The page states when the job last ran and how many sources updated. Until 24 September 2026 the job reported success while every FRED request timed out on GitHub's runners, and the all-or-nothing build also discarded valid BCB data; the page kept showing 13 September figures. Sources are now independent, U.S. data has official fallbacks, and staleness turns the run red.
- **The thesis is never rewritten by the updater.** Prose lives in `src/content.py` (EN/PT/FR); every number comes from `research/thesis.json`, and the data frozen at the thesis date is in `research/thesis_snapshot_2026-09-24.json`, so tests can recompute each figure. The only automatic element is a mechanical check of the pre-committed rules against new PTAX closes.

## Run locally

Python 3.11 is the Community Cloud and CI target (3.9+ works).

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m streamlit run app.py
```

Open http://localhost:8501 (add `?lang=pt` or `?lang=fr`).

```bash
python -m pytest -q                                   # 107 tests
python scripts/refresh_market_data.py                 # fetch official data (network)
python scripts/check_freshness.py                     # exit 1 if key data is stale
python scripts/generate_market_brief.py               # regenerate the three PDFs + Markdown brief
```

Production installs only `requirements.txt` (Streamlit). The refresh job installs `requirements-refresh.txt` (pandas, requests); PDF generation and tests use `requirements-dev.txt`.

## Updating the thesis

1. Save the data as of the new date: copy `research/live_snapshot.json` to `research/thesis_snapshot_<date>.json`.
2. Write the new numbers, rules, review verdicts and sources in `research/thesis.json` (point `inputs_file` and `previous_file` at the right files).
3. Edit the prose in `src/content.py` in all three languages — placeholders only, no literal figures.
4. `python scripts/generate_market_brief.py`, then `python -m pytest -q`. The tests fail if a number cannot be reproduced from the saved inputs, a language is missing a string, or the committed PDFs are out of date.

## Tests

Refresh behaviour (independent sources, fallbacks, malformed data, total outage), freshness thresholds and the CI gate, thesis consistency (every figure recomputed from saved inputs; verdicts checked against the data), the rule monitor, EN/PT/FR structure and placeholder parity, French typography, "commodities" in Portuguese, page completeness and robustness to missing or malformed data, network isolation of the production render, PDF content/localization/searchability and that the committed PDFs match the current content, and static responsive-layout checks. Browser review covers 1440×900, 1280×720 and 375×812 in all three languages.

## Files

- `app.py` — production entrypoint (Streamlit shell, caching, language switch).
- `src/page.py`, `src/chart.py`, `src/style.css` — HTML sections, the one inline-SVG chart, the design system.
- `static/fonts/` — self-hosted Geist and Geist Mono (SIL Open Font License), registered in `.streamlit/config.toml`.
- `src/content.py` — every visible sentence in English, Portuguese and French.
- `src/thesis.py`, `src/formatting.py`, `src/freshness.py` — thesis loading, rule check, calculations, locale formatting, freshness rules.
- `src/live_refresh.py`, `src/data.py`, `src/analytics.py` — scheduled refresh, source parsers, calculations (refresh job only).
- `src/pdf_brief.py` — printable brief and Markdown companion (offline only).
- `research/thesis.json`, `research/thesis_snapshot_2026-09-24.json`, `research/live_snapshot.json` — dated thesis, its frozen inputs, refreshed data.
- `research/data_snapshot.json`, `research/commodity_snapshot.json`, `research/scenario_trade.md` — archived 13 September case.
- `outputs/` — the three PDFs. `tests/` — automated checks.

## Limits

PTAX is the central bank's daily reference rate, not an executable price; costs, spreads and sizing are not modelled. ANBIMA's curve and oil futures are dated manual observations. Focus is a survey. The market-vs-economists gap mixes expectations and risk premium. No probabilities are assigned and no rule has been back-tested. Community Cloud can still take a few seconds to wake a sleeping app.

AI tools (OpenAI Codex/ChatGPT and Anthropic Claude) helped write the code, draft research text and translate. The question, the rules and the final judgement are mine; every figure links to its source.
