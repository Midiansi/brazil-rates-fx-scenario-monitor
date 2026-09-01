# Brazil Rates & FX Scenario Monitor

A compact Streamlit dashboard for monitoring Brazilian survey expectations, USD/BRL PTAX and the Brazil–US policy-rate backdrop. The project is designed to demonstrate careful market interpretation: every statement is generated from a displayed calculation, units are explicit, and each external source can fail without taking down the rest of the dashboard.

The secondary **Scenario Lab** adds a fixed, reviewable September 2026 Copom/FOMC scenario framework and exactly one conditional paper trade. Its narrative is loaded from `research/data_snapshot.json`; it is not generated dynamically and does not replace the three primary live-data views. The full research note is in `research/scenario_trade.md`.

## One-page trade brief

[Download the generated Brazil Rates & FX Trade Brief](outputs/Brazil_Rates_FX_Trade_Brief.pdf).

The brief uses the fixed snapshot retrieved **1 September 2026 at 18:24:02 UTC** and the exchange-pricing audit completed the same day. Regenerate both the PDF and its Markdown companion with:

```bash
python scripts/generate_market_brief.py
```

Refresh the underlying official data, CME FedWatch view and B3 DI curve before discussing or publishing the trade; the saved brief does not update itself silently.

## Screenshot

_Placeholder: add a screenshot of the deployed Streamlit dashboard here._

## Data sources

| Data | Official source | Series or dataset |
|---|---|---|
| Selic and IPCA expectations | [Banco Central do Brasil Focus Expectations OData](https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/) | `ExpectativasMercadoAnuais`, `baseCalculo = 0` |
| USD/BRL PTAX | [Banco Central do Brasil PTAX OData](https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/) | `CotacaoDolarPeriodo` buying and selling rates |
| Selic target | [Banco Central do Brasil SGS series 432 API](https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json) | SGS series 432 |
| Federal-funds target range | [FRED DFEDTARL](https://fred.stlouisfed.org/series/DFEDTARL) and [FRED DFEDTARU](https://fred.stlouisfed.org/series/DFEDTARU) | Lower and upper target-range limits |
| U.S. Treasury yields | [FRED DGS2](https://fred.stlouisfed.org/series/DGS2) and [FRED DGS10](https://fred.stlouisfed.org/series/DGS10) | 2-year and 10-year constant-maturity yields |
| September FOMC pricing | [CME FedWatch](https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html) | ZQU6-implied 16 September target-range probabilities |
| September Copom pricing | [B3 daily files](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/boletins-diarios/pesquisa-por-pregao/pesquisa-por-pregao/) | BVBG.187.01 DI1U26 and DI1V26 settlement unit prices |

The BCB Expectations and PTAX entity and field names were selected from each service's official OData metadata.

## Metric definitions

- **Focus median:** the median in the BCB annual expectations dataset for each reference calendar year. Selic is a percent-per-year policy-rate expectation; IPCA is the expected calendar-year inflation rate in percent. `baseCalculo = 0` selects the standard aggregate calculation base returned by the service.
- **Five-business-day change:** latest valid observation minus the observation five sorted, valid business-day observations earlier (t versus t−5). Rate and expectation changes are percentage-point changes. PTAX is a relative percentage change.
- **Approximately one-month change:** latest valid value compared with the last valid observation on or before the calendar date one month earlier.
- **USD/BRL PTAX midpoint:** `(cotacaoCompra + cotacaoVenda) / 2`, in BRL per USD. A rise means BRL weakened against USD; a fall means BRL strengthened.
- **Fed target-range midpoint:** `(DFEDTARL + DFEDTARU) / 2`. This is a calculated policy-rate measure, not a bond yield and not the effective federal funds rate.
- **Brazil–US policy-rate differential:** BCB Selic target minus the Fed target-range midpoint, in percentage points.
- **U.S. 2s10s:** 10-year constant-maturity Treasury yield minus the 2-year yield, in percentage points. A positive change is a steepening; a negative change is a flattening.

All series are explicitly converted to dates and numeric values, invalid observations are removed, duplicate dates are resolved, and data are sorted before changes are calculated. Policy-rate history uses only dates common to the source series; no synthetic market observations are inserted.

## Install and run

Python 3.11 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

Run the automated checks with:

```bash
python -m pytest -q
```

## Reliability and known limitations

- The dashboard depends on live BCB and FRED availability and their publication calendars. It warns on individual source failures and keeps unaffected views usable.
- Focus figures are survey medians, not realized outcomes or executable market prices, and can be revised by the source.
- PTAX is an official reference rate, not a continuously traded spot quote.
- Treasury series are published for U.S. business days; Brazilian and U.S. holiday calendars do not always coincide.
- “One month” is a calendar-month comparison to the latest available observation on or before the cutoff, so the exact day gap varies around holidays and weekends.
- Streamlit's in-memory cache reduces repeat calls but is not a persistent database.
- The B3 Copom figure is a DI-curve decomposition with an explicit business-day split, not a B3-published probability; it ignores term premia and other possible changes inside the contract window.

## Public deployment

Push the repository to GitHub, sign in to [Streamlit Community Cloud](https://share.streamlit.io/), choose the repository and branch, and set the entry point to `app.py`. The platform installs `requirements.txt` automatically. No API secrets are required.

## Disclaimer

This is an educational market-monitoring project and is not investment advice. AI assisted development of the application; source definitions, units and calculations were manually checked against the official BCB OData metadata and official series descriptions.
