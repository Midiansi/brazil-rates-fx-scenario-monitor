# Brazil Macro

A source-grounded Streamlit market brief connecting Brazilian rates, BRL and commodities. The public site is designed for a fast first read: synthesis first, evidence second, methodology third.

**Live site:** https://brasilmacro.streamlit.app/

## What changed

The production entrypoint now renders entirely from checked-in, reviewable snapshots. No BCB or FRED request sits on the first-paint path. A visitor sees the full brief immediately after the Streamlit session connects; live source checks are an optional action in the deeper-data section.

The opening view answers four questions in plain English: what Brazilian rates imply, what BRL has done, where inflation expectations stand, and whether the latest available commodity observations are broadly supportive or mixed. Exact values, dates, frequencies and source detail remain available below.

## Commodities

The portfolio adds four economically relevant Brazil exposures: Brent crude, iron ore, soybeans and sugar. Their publication frequencies are labelled explicitly rather than forcing daily, monthly and quarterly observations into a misleading synchronized dashboard. The section explains the transmission channels to export receipts, BRL, inflation and monetary policy.

The reviewable commodity input is `research/commodity_snapshot.json`. The macro/scenario input remains `research/data_snapshot.json`.

## Performance architecture

1. `app.py` imports the production portfolio view in `portfolio_app.py`.
2. Local JSON snapshots are parsed before any network-capable code is invoked.
3. `src/portfolio.py` converts those snapshots into presentation data and deterministic plain-language synthesis.
4. Live BCB/FRED requests are isolated behind an explicit **Check official sources now** button.
5. When requested, the eight independent macro feeds run concurrently with `ThreadPoolExecutor` and remain cached for one hour.
6. Production dependencies are limited to pandas, Plotly, Requests and Streamlit; test/report packages are no longer installed by Streamlit Community Cloud.

This removes the previous `Loading official market data…` spinner and the sequential eight-request critical path. Streamlit Community Cloud hibernation can still delay the server/session itself; application code cannot eliminate that hosting-level wake-up latency.

## Source discipline

Primary macro data comes from Banco Central do Brasil and Federal Reserve/FRED series. Commodity benchmarks use EIA/IMF series distributed through FRED. Every commodity observation records its source, date, unit and frequency. The UI does not imply that differently timed observations are contemporaneous, and deterministic copy avoids unsupported causal claims.

## Run locally

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

## Tests

```bash
python -m pip install pytest
python -m pytest -q
```

CI is defined in `.github/workflows/test.yml`. The resilience tests assert that first render makes zero HTTP requests and still displays the market brief and commodities section.

## Project structure

- `app.py` — production Streamlit entrypoint
- `portfolio_app.py` — portfolio-first UI and optional concurrent refresh
- `src/portfolio.py` — local-first snapshot conversion and deterministic synthesis
- `src/data.py` — validated BCB/FRED parsers and fetchers
- `src/analytics.py` — rate, curve and change calculations
- `research/data_snapshot.json` — reviewable macro/scenario snapshot
- `research/commodity_snapshot.json` — reviewable commodity snapshot
- `tests/` — calculation, parsing, resilience and portfolio tests

**Educational analysis — not investment advice.**
