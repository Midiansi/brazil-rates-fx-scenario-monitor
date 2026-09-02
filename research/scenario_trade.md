# September 2026 Copom/FOMC Scenario Framework

**Snapshot retrieved:** 2 September 2026 at 00:40:27 UTC (1 September 2026 at 21:40:27 Brasília time)

**Status:** Fixed educational research snapshot; not investment advice and not an execution recommendation.

The scenario labels describe Brazil's stance **relative to the US and to the saved exchange-pricing anchors**. They do not imply that both central banks must move in the same hawkish or dovish direction. CME's published FOMC probabilities are recorded below; no Copom probability or joint scenario probability is assigned.

## Verified event context

- The September 2026 Copom meeting is scheduled for **15–16 September 2026**, according to the [BCB's official 2026 calendar](https://www.bcb.gov.br/detalhenoticia/20739/nota).
- The September 2026 FOMC meeting is scheduled for **15–16 September 2026** and includes a Summary of Economic Projections, according to the [Federal Reserve's official calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm).
- At its latest meeting on 4–5 August, Copom unanimously cut Selic by 0.25 pp to **14.00%**. The [statement](https://www.bcb.gov.br/controleinflacao/comunicadoscopom/21215) and [minutes](https://www.bcb.gov.br/en/publications/copomminutes/05082026) retained a cautious, restrictive and data-dependent stance because inflation and expectations remained elevated.
- At its latest meeting on 28–29 July, the FOMC held **3.50%–3.75%** by a 9–3 vote; three voters preferred a 0.25 pp hike. The [statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20260729a.htm) said inflation remained elevated and the Committee would deliver price stability. The [minutes](https://www.federalreserve.gov/monetarypolicy/fomcminutes20260729.htm) said most favored holding and several favored hiking. Their description of market pricing refers to conditions around 29 July; current pricing is audited separately below.

## Scenario-label and exchange-pricing audit

**Result:** The three labels are retained. The middle row remains **Base case** because meeting-specific primary-exchange evidence was obtained for both September decisions. B3 is current to 1 September; CME's saved 1 September observation is stale after a failed final refresh. It is a market-aligned analytical scenario, not a joint-probability forecast.

- **FOMC:** The saved official [CME FedWatch](https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html) view for 16 September showed **68.2% for a 25 bp hike, 31.8% for no change and 0.0% for easing**, using ZQU6 at a 96.2913 mid-price. CME timestamped the observation **1 September 2026 at 02:07:02 CT**. FedWatch uses 30-Day Federal Funds futures under its published [methodology](https://www.cmegroup.com/articles/2023/understanding-the-cme-group-fedwatch-tool-methodology.html). A final refresh attempt at 21:40 Brasília time failed because the official interactive tool returned protocol errors and timed out, so the saved probabilities are explicitly stale and may have changed.
- **Copom:** B3's official [BVBG.187.01 derivatives report](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/boletins-diarios/pesquisa-por-pregao/pesquisa-por-pregao/) for **1 September 2026** reported a 13.900% adjusted-quote rate for the maturing DI1U26 and a **98,929.53** settlement unit price for DI1V26. Applying the [DI1 contract convention](https://www.b3.com.br/pt_br/produtos-e-servicos/negociacao/juros/futuro-de-taxa-media-de-depositos-interfinanceiros-de-um-dia.htm), `rate = (100000 / PU)^(252 / business days) - 1`, gives 13.785953% for DI1V26. Splitting the contract into 10 business days before and 11 after the 16 September decision implies a post-meeting DI rate of 13.682463%, or about **21.8 bp of easing**.

The B3 calculation is a transparent curve decomposition, not an exchange-published Copom probability. It assumes no other rate change within the contract window and ignores term premia; the same-day file was published at 20:35 Brasília time. All automated BCB and FRED requests succeeded; lagged Focus and Treasury dates are recorded explicitly rather than filled. The CME refresh failure is recorded rather than hidden.

## Timestamped market snapshot

| Measure | Latest value | Observation date | Change context | Status |
|---|---:|---|---|---|
| Focus Selic median, 2026 | 13.75% p.a. | 28 Aug 2026 | 0.00 pp / 5 obs; −0.25 pp / 1 month | Latest returned, but no 31 Aug or 1 Sep observation was available |
| Focus IPCA median, 2026 | 5.0062% | 28 Aug 2026 | −0.0102 pp / 5 obs; −0.0899 pp / 1 month | Latest returned, with the same reporting lag |
| USD/BRL PTAX midpoint | 5.1567 | 1 Sep 2026, 13:06 BRT | +0.16% / 5 obs; +1.57% / 1 month | Current same-day observation |
| Selic target | 14.00% p.a. | 1 Sep 2026 | — | Current same-day target |
| Fed target midpoint | 3.625% p.a. | 1 Sep 2026 | Range 3.50%–3.75% | Current same-day target |
| Brazil–US policy differential | 10.375 pp | 1 Sep 2026 | 0.00 pp / 5 business days; −0.25 pp / 1 month | Derived from same-day official targets |
| US 2-year Treasury | 4.34% | 31 Aug 2026 | +0.10 pp / 5 obs; +0.06 pp / 1 month | Latest published; 1 Sep observation not yet available |
| US 10-year Treasury | 4.75% | 31 Aug 2026 | +0.05 pp / 5 obs; 0.00 pp / 1 month | Latest published; 1 Sep observation not yet available |
| US 2s10s | +0.41 pp | 31 Aug 2026 | −0.05 pp / 5 obs | Latest common Treasury observation |

Focus values use the [BCB Expectations OData service](https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/); PTAX uses the [BCB PTAX OData service](https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/); Selic uses [BCB SGS 432](https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json); Fed policy targets and Treasury yields use [DFEDTARL](https://fred.stlouisfed.org/series/DFEDTARL), [DFEDTARU](https://fred.stlouisfed.org/series/DFEDTARU), [DGS2](https://fred.stlouisfed.org/series/DGS2) and [DGS10](https://fred.stlouisfed.org/series/DGS10).

## Three scenarios

| Scenario | Copom outcome and guidance | FOMC outcome and guidance | Difference from saved expectations | Likely initial BRL/USD direction | Brazil front-end | US 2-year | Brazil–US differential | Two confirmation signals | Principal risk |
|---|---|---|---|---|---|---|---|---|---|
| **Hawkish relative to expectations** | Hold 14.00%; require clearer re-anchoring before more easing and retain restrictive guidance. | Hold 3.50%–3.75%, but retain firm price-stability language and tightening optionality. | Copom is hawkish to roughly 21.8 bp of B3-implied easing; the Fed does not deliver the saved CME observation's highest-weight hike outcome. Relative carry is 0.50 pp wider than the base path. | Likely initial BRL strength / USD/BRL lower, all else equal; subject to risk sentiment. | Likely upward pressure as easing is removed. | Likely downward pressure unless guidance offsets the no-hike surprise. | Mechanically unchanged near 10.38 pp; 0.50 pp wider than the base path. | (1) Focus Selic revises toward 14.00%; (2) PTAX breaks below the saved 5.09 range low while US 2Y falls from 4.34%. | Global risk-off or a commodity shock weakens BRL despite the rate outcome. |
| **Base case** | Cut 0.25 pp to 13.75%; retain cautious, restrictive and data-dependent guidance. | Hike 0.25 pp to 3.75%–4.00%; avoid pre-committing beyond the meeting. | The Copom cut is consistent with roughly 21.8 bp of B3-implied easing. The FOMC hike is the highest-weight outcome in the saved CME observation at 68.2%; no joint probability is inferred. | Likely mild BRL depreciation / USD/BRL higher, all else equal; the reaction may be limited if anticipated. | Limited downward pressure if the path is validated. | Limited upward pressure; guidance matters after the recent 0.10 pp rise. | Narrows 0.50 pp to about 9.88 pp. | (1) Official targets produce a differential near 9.88 pp; (2) PTAX closes above the saved 5.22 range high while US 2Y remains near or above 4.34%. | The moves are already reflected in markets and global risk, commodities or fiscal news dominates. |
| **Dovish relative to expectations** | Cut 0.50 pp to 13.50%; signal further gradual easing if expectations improve. | Hike 0.25 pp to 3.75%–4.00%; retain a firmer tightening bias. | Copom delivers about 28 bp more easing than the B3 curve embeds and ends below the Focus median while the Fed follows the saved CME-aligned hike anchor. | Likely initial BRL depreciation / USD/BRL higher, all else equal; subject to the inflation rationale and risk sentiment. | Likely downward pressure if the larger cut is credible. | Likely upward pressure under the hike and firm guidance. | Narrows 0.75 pp to about 9.63 pp. | (1) Focus Selic revises below 13.75% without renewed IPCA deterioration; (2) PTAX clears 5.22 and US 2Y rises from 4.34%. | A larger cut is read as a credibility error, lifting local risk premia and front-end rates instead. |

## One conditional paper trade

### Long USD / short BRL — conditional, no position at the snapshot

**Thesis:** Enter only on a confirmed upside break in USD/BRL because the exchange-aligned base case narrows the Brazil–US policy differential while recent PTAX, Focus Selic and US 2-year moves already lean in the same direction.

**Supporting evidence**

1. USD/BRL PTAX rose 1.57% over approximately one month and 0.16% over five observations to 5.1567.
2. The policy differential narrowed 0.25 pp over one month to 10.375 pp and narrows another 0.50 pp in the base scenario.
3. The 2026 Focus Selic median is 13.75%, 0.25 pp below the current target, and fell 0.25 pp over one month.
4. The US 2-year yield rose 0.10 pp over five observations to 4.34%, while 2s10s flattened 0.05 pp.

**Catalyst:** The coincident 15–16 September Copom and FOMC decisions, especially a Brazilian cut alongside a US hike or firm US guidance.

**Entry logic:** No paper position at 5.1567. Enter only after a daily PTAX midpoint closes above approximately **5.22**, calculated by rounding the saved 20-observation high of 5.2233 to two decimals, with the US 2-year still near or above 4.34% or the policy differential not widening.

**Invalidation:** After entry, invalidate on two consecutive PTAX midpoints below approximately **5.16**, the rounded midpoint of the saved 20-observation range, or if the policy differential fails to narrow and remains near or above 10.375 pp because Copom does not ease and the FOMC does not hike.

**Profit-taking:** The unrounded saved high plus one unrounded saved range width is `5.2233 + 0.1328 = 5.3561`. Bracketing that measured move to its adjacent cents gives the reproducible **5.35–5.36** review zone. Take profit earlier if post-meeting data reverse the differential or US 2-year confirmation.

**Expected holding period:** Two to four weeks, spanning the decisions and initial repricing.

**Principal risks:** (1) a Copom hold or materially hawkish guidance; (2) an FOMC hold or dovish guidance; (3) improved global risk appetite, stronger commodity terms of trade or favorable Brazilian fiscal news.

**Evidence that changes the view:** Focus Selic revising back toward 14.00%, a failure of the differential to narrow, a material decline in US 2-year yields from 4.34%, or a failed PTAX breakout followed by a move below the saved 5.09 range low.

**Supporting scenario:** Base case.  
**Invalidating scenario:** Hawkish relative to expectations.

> This is one educational conditional paper trade, not investment advice, actual execution, or a claim of past performance.
