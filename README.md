# Brazil Macro

A source-grounded Streamlit research portfolio connecting Brazilian rates, U.S. rates, the real and commodity exports. English, Portuguese and French versions cover the entire page and downloadable brief. Official market observations refresh automatically without putting network calls in the visitor's render path.

Public site: https://brasilmacro.streamlit.app/ — local changes are not deployed automatically by this repository's application code.

## Reading the project

The first screen states the conditional view and its limitations. Navigation leads to three saved scenarios, a disciplined paper trade, commodity transmission channels and the underlying evidence. Detailed scenarios, trade calculations, research process and sources remain available in expanders.

The decision framework is a fixed September 2026 research case, not a live trade recommendation. The prominent market observations are maintained separately in `research/live_snapshot.json` and refreshed from official feeds on weekdays. Commodity observations retain their own dates and frequencies. The page does not claim execution or performance, and the historical paper-trade rules are never silently rewritten by the updater.

The original market thesis and snapshot values are preserved. The paper trade requires a daily PTAX midpoint above the rounded 5.22 reference, with the U.S. two-year yield near/above 4.34% **or** the policy differential not widening. After entry, two consecutive PTAX midpoints below 5.16, **or** a differential that fails to narrow and stays near/above 10.375 percentage points, invalidate the idea. 5.35–5.36 is a review zone. The exact range high is 5.2233; the rounded trigger is slightly lower. PTAX is not an executable spot quote, and costs/position sizing are not modelled.

## Sources and limitations

- BCB: Focus survey, PTAX, Selic and Copom publications.
- Federal Reserve/FRED: policy targets, Treasury yields and FOMC publications.
- EIA/IMF via FRED: Brent, iron ore, soybeans and sugar. Monthly/quarterly dates label observation periods, not publication days.
- B3: saved DI futures decomposition. This is an analytical estimate that ignores term premia and assumes no other policy change in the contract window; it is not a B3-published Copom probability.
- CME: saved 1 September FedWatch observation, retained after the original final refresh failed. The 68.2% figure is historical, not current pricing. No joint probability is assigned.

Official links identify the underlying sources; they do not guarantee that a current webpage reproduces a historical observation. Original B3/CME captures are not bundled, so those historical inputs should be checked against archived exchange evidence before external discussion. The saved research and official-source registry remain in `research/`.

## Local use

Python 3.11 is the Community Cloud/CI target. The production entrypoint is `app.py`.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Open http://127.0.0.1:8501. For production installation, only `requirements.txt` is needed.

## Performance, automatic updates and resilience

Every visit and language change uses local JSON and pre-generated PDF files only. No market-feed request or PDF generation occurs in the production entrypoint. This keeps the page responsive even when BCB or FRED is slow.

`.github/workflows/refresh-market-data.yml` runs after the Brazilian close on weekdays and can also be started manually. It calls `scripts/refresh_market_data.py`, validates each official response and commits `research/live_snapshot.json` only when the result changes. A failed feed retains the last good values rather than breaking the page. The original scenario case remains separate and reviewable.

Missing or malformed snapshots yield localized unavailable states. Invalid individual macro series and commodity records are excluded without suppressing unrelated content. Missing PDFs omit the download button. Standard HTML provides the scenario cards, semantic forecast table and range visual, with no heavy charting dependencies or animation. The forecast table has a keyboard-focusable horizontal scroll area on narrow screens.

Community Cloud hibernation can still delay server startup; application changes cannot remove hosting wake-up time.

## Downloadable research brief

```bash
python scripts/generate_market_brief.py
```

This produces three searchable, print-friendly, three-page PDFs in `outputs/`, one in each language. Page 1 gives the view and scenarios; page 2 covers trade rules and commodities; page 3 preserves limitations, scenario risks and source links. The PDFs are saved outputs and never update themselves. ReportLab and pypdf are development dependencies only. The original English Markdown research companion remains available.

## Validation

```bash
python -m pytest -q
```

Tests cover analytics, source parsing, snapshot research rules, startup without network requests, complete static French translation coverage, language switching, partial/malformed input failures, observation periods and all three PDFs. CI uses Python 3.11. Browser review additionally checks navigation, expanded content, keyboard access and responsive widths in each language.

## Files

- `app.py`: network-free production page, layout and interactions.
- `scripts/refresh_market_data.py`, `src/live_refresh.py`: scheduled official-data refresh and validation.
- `research/live_snapshot.json`: small last-known-good production data file created by the updater.
- `src/editorial.py`: shared localized copy, period formatting and safe snapshot validation.
- `src/localization.py`: detailed English-to-French and Portuguese research translations.
- `src/print_brief.py`: localized print layout.
- `src/brief.py`: preserved research calculations and brief-generation interface.
- `src/data.py`, `src/analytics.py`, `src/research.py`: existing data parsers, calculations and research validation.
- `research/`: original saved inputs and substantive research.
- `tests/`: automated regression checks.

Educational research; not investment advice.
