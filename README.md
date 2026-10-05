# Brazil Macro

A student research log on how Brazilian and U.S. interest rates, the Brazilian real and Brazil's main commodity exports move together. Each view is dated, backed by official data, and paired with the rules that would make me act or change my mind — and each old view is reviewed after the fact.

Public site: https://brasilmacro.streamlit.app/ (English, `?lang=pt` Português, `?lang=fr` Français)

Educational research, not investment advice. No real positions and no claimed performance.

![First screen of the site: the dated view, why, and what would make me act or change my mind](assets/dashboard.png)

## Current thesis (5 October 2026)

**Flávio Bolsonaro's first-round lead is a surprise, not a verdict. In two of the last three elections the real gave back most of its post-vote rally before the runoff, so I stay out until 25 October and act only if prices confirm.**

- Flávio Bolsonaro took 47.1% of valid votes to Lula's 45.0% (99.5% of ballot boxes counted), with 7.8% going to other candidates: to reach 50% he needs 37% of them, Lula 63%. The final Datafolha and Quaest polls had Lula ahead and missed the margin by 5.1 and 3.1 points.
- On the first Monday after the 2014, 2018 and 2022 first rounds USD/BRL fell 2.9–3.8%; by the Friday before the runoff it had given back 85% (2014) and 70% (2022) of the move, while 2018 extended it. At recent volatility (9% a year) the entry level is 1.1 standard deviations below Friday's close and the drop level 0.7 above it, so a single session can jump both.
- Conditional paper trade: from 26 October, the first PTAX after the runoff, buy the real (short USD/BRL) only on two PTAX closes below 5.10 with the U.S. two-year yield at or below 5.00%. Drop the idea on any close above 5.30; exit on two closes above 5.22 or a U.S. two-year yield above 5.10%; review at 4.94–5.00 or on 4 November.

Market prices are from 2 October, the last session before the vote. The full reasoning (review of the 24 September call, evidence sorted into facts, market pricing, surveys and interpretation, paths around the runoff, commodity channels and sources) is on the site and in the printable briefs in `outputs/`. The previous thesis is preserved unchanged in `research/thesis_2026-09-24.json` and `research/thesis_snapshot_2026-09-24.json`; the 13 September case is in `research/data_snapshot.json` and `research/scenario_trade.md`.

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
- **The thesis is never rewritten by the updater.** Prose lives in `src/content.py` (EN/PT/FR); every number comes from `research/thesis.json`, and the data frozen at the thesis date is in `research/thesis_snapshot_2026-10-05.json`, so tests can recompute each figure. The only automatic element is a mechanical check of the pre-committed rules against new PTAX closes.

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
python -m pytest -q                                   # 114 tests
python scripts/refresh_market_data.py                 # fetch official data (network)
python scripts/check_freshness.py                     # exit 1 if key data is stale
python scripts/generate_market_brief.py               # regenerate the three PDFs + Markdown brief
```

Production installs only `requirements.txt` (Streamlit). The refresh job installs `requirements-refresh.txt` (pandas, requests); PDF generation and tests use `requirements-dev.txt`.

## Keeping the app awake

[Keep Streamlit Awake](.github/workflows/keep-streamlit-awake.yml) opens the public site in headless Chromium through Playwright at **00:23, 08:23 and 16:23 UTC every day**. The eight-hour cadence leaves a four-hour buffer against [Community Cloud's 12-hour inactivity window](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app#app-hibernation). It clicks the wake-up button if needed, waits for the actual dashboard to render (including inside Streamlit's iframe), holds the browser session open for 15 seconds and retries one failed visit. No secrets or changes to the app's dependencies are needed.

The workflow also runs when its file is pushed to `main`, and can be started from **Actions → Keep Streamlit Awake → Run workflow**. It must be on the default branch for scheduled visits. A failed visit produces a failed Actions run; inspect that run's logs.

This is best-effort availability: [GitHub can delay or drop scheduled runs and disables schedules in public repositories after 60 days without repository activity](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule). If disabled, re-enable the workflow in Actions. The existing market-data refresh remains separate.

## Updating the thesis

1. Archive the old thesis (`cp research/thesis.json research/thesis_<its date>.json`), then save the data as of the new date: copy `research/live_snapshot.json` to `research/thesis_snapshot_<date>.json`.
2. Write the new numbers, rules, review verdicts and sources in `research/thesis.json` (point `inputs_file` and `previous_file` at the right files; when markets have not yet reopened on the thesis date, set `data_as_of` to the last session so the rule monitor still checks the first close).
3. Edit the prose in `src/content.py` in all three languages — placeholders only, no literal figures.
4. `python scripts/generate_market_brief.py`, then `python -m pytest -q`. The tests fail if a number cannot be reproduced from the saved inputs, a language is missing a string, or the committed PDFs are out of date.

## Tests

Refresh behaviour (independent sources, fallbacks, malformed data, total outage), freshness thresholds and the CI gate, thesis consistency (every figure recomputed from saved inputs, including vote shares, runoff arithmetic, poll misses, the first-round event study and volatility bands; verdicts checked against the data), the rule monitor, EN/PT/FR structure and placeholder parity, French typography, "commodities" in Portuguese, page completeness and robustness to missing or malformed data, network isolation of the production render, PDF content/localization/searchability and that the committed PDFs match the current content, and static responsive-layout checks. Browser review covers 1440×900, 1280×720 and 375×812 in all three languages.

## Files

- `app.py` — production entrypoint (Streamlit shell, caching, language switch).
- `src/page.py`, `src/chart.py`, `src/style.css` — HTML sections, the one inline-SVG chart, the design system.
- `src/content.py` — every visible sentence in English, Portuguese and French.
- `src/thesis.py`, `src/formatting.py`, `src/freshness.py` — thesis loading, rule check, calculations, locale formatting, freshness rules.
- `src/live_refresh.py`, `src/data.py`, `src/analytics.py` — scheduled refresh, source parsers, calculations (refresh job only).
- `src/pdf_brief.py` — printable brief and Markdown companion (offline only).
- `research/thesis.json`, `research/thesis_snapshot_2026-10-05.json`, `research/live_snapshot.json` — dated thesis, its frozen inputs (refreshed data plus the election count, final polls, ANBIMA curve and the 2014/2018/2022 PTAX windows), refreshed data.
- `research/thesis_2026-09-24.json`, `research/thesis_snapshot_2026-09-24.json` — the previous thesis and its inputs, preserved unchanged.
- `research/data_snapshot.json`, `research/commodity_snapshot.json`, `research/scenario_trade.md` — archived 13 September case.
- `outputs/` — the three PDFs. `tests/` — automated checks.

## Limits

PTAX is the central bank's daily reference rate, not an executable price; costs, spreads and sizing are not modelled. ANBIMA's curve is a dated manual observation. Focus is a survey. The market-vs-economists gap mixes expectations and risk premium. No probabilities are assigned and no rule has been back-tested; the first-round study covers only three elections. Community Cloud can still take a few seconds to wake a sleeping app.

AI tools (OpenAI Codex/ChatGPT and Anthropic Claude) helped write the code, draft research text and translate. The question, the rules and the final judgement are mine; every figure links to its source.
