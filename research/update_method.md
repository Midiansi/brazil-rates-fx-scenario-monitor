# 16 October 2026 publication: definitions and decision record

The current publication uses market observations through 15 October. Each series retains its own observation date. Brent ends on 14 October; Focus is dated 9 October. Publication is before the 16 October PTAX close. No intraday or executable prices are implied.

## Inputs and reproduction

`thesis_snapshot_2026-10-16.json` freezes the official-source snapshot committed at `04f8fd1` plus the ANBIMA curve downloaded specifically for 15 October. The raw ANBIMA CSV, encoding, URL and POST parameters are included. Curves for 2 and 5 October come from the original frozen study inputs. The old study and its risk forecasts are not extended or refitted.

Run `python scripts/build_update.py` to reproduce `update_2026-10-16.json`, then `python scripts/generate_market_brief.py` to regenerate the PDFs and Markdown note. Page visits do neither and make no network requests. The current report is selected by `current_update_file` in `thesis.json`; a missing follow-up leaves the original study available. The app cache includes the follow-up report and its prose/calculation modules.

## FX and carry

PTAX is the mean of official buying and selling reference rates. The first-round move uses the 2 October and 5 October observations. Reversal at 15 October is `(S15 − S5) / (S2 − S5)`. Its complement is the fraction retained **in USD/BRL quote units**, not a BRL total return or a trading P&L. Reciprocating the quote would change the percentages.

For an illustrative comparison with USD cash, relative one-month investment growth is `G = [(1 + Selic/100) / (1 + Fed midpoint/100)]^(1/12)`. The policy-rate proxy is `(G − 1) × 100`; the future exchange rate that makes relative USD wealth unchanged is `S × G`. Annual carry is `G¹² − 1`. It is compared with pre-vote volatility: the sample standard deviation of the 20 daily log PTAX changes to 2 October, times √252, as in the 6 October study. The study's ratio (1.05) used carry rounded to 0.76% a month; unrounded, the ratio is 1.045. The first-round move, `S5/S2 − 1`, is also expressed in months of carry: `|move| / (G − 1)`. Annual policy targets are treated as constant effective rates for this illustration. This is not the actual BRL or USD funding convention, a CDI accumulation, a covered-interest-parity estimate, or an executable forward. Curves, calendars, basis, margin and costs are omitted. The calculation deliberately does not extrapolate a short realised FX move into an expected return.

## Curve and survey

The table compares ANBIMA fitted nominal, inflation-implied and real zero rates at 504 business days, across the same three dates. Changes in basis points use the underlying unrounded percentage yields. Nominal rates are multiplicative in real rates and breakevens; the changes in the last two columns are not an exact additive attribution. Breakevens contain inflation-risk and liquidity premia as well as expectations.

To check whether the breakeven rise is confined to the front end, the report records the smallest and largest 5→15 October change across the ANBIMA implied-inflation vertices from 252 to 1,512 business days (one to six years), and the change in the forward breakeven between 504 and 1,260 business days, `[(1 + BE₅)⁵ / (1 + BE₂)²]^(1/3) − 1`. A one-off inflation print would mainly affect near vertices; a rise in the two-to-five-year forward is harder to attribute to it.

Focus medians are identified by survey date and reference year. The note compares the 2 October survey saved with the 6 October thesis against the 9 October survey, year by year. The 2026 and 2027 inflation medians are not compared directly with the two-year breakeven as if their maturities or compounding conventions matched. The two-year gap over the economists' Selic path uses `survey_path_average` exactly as in the 6 October study (straight-line path from the current target through the year-end medians, CDI 0.10 pp below target, start at the publication date). Recomputed from the 6 October inputs, the first-round gap equals the study's saved value. The current note does not label a survey/curve difference as a pure fiscal premium or claim to identify the cause of a market move.

## Commodities and revenue

The Brent/FX calculation uses the intersection of observation dates, ending on 14 October. Both comparisons begin on 2 October: `(Brent14 × S14) / (Brent2 × S2) − 1`. It does **not** combine the latest Brent with the 15 October PTAX, compare futures with spot, or compare a lagged September observation with an October endpoint.

The EIA spot print on 2 October is 18% above 1 October (114.82 to 135.51). Because one observation moves the result, the report also computes the same matched-date change from 1 October and from 5 October. The sign of the oil and BRL-revenue change depends on the start date, so the note draws no oil conclusion from it; the USD/BRL leg is negative from both pre-vote bases.

The scenario table holds physical volume constant and computes `(1 + commodity shock) × (1 + FX shock) − 1`. The cross term matters. The dollar-price increase needed to offset a five-percent fall in USD/BRL is `1/0.95 − 1`, not five percent. This describes unhedged benchmark gross receipts, not EBITDA, profit, a fixed-notional forward payoff or a company valuation. A producer may have USD costs and liabilities, product differentials, uncertain volumes and pre-existing hedges. No hedge fraction or transaction is recommended.

## Decision standard adopted on 16 October

The original thresholds are preserved without alteration in `thesis_2026-10-06.json` and copied into the new publication for audit. The original `rule_status` computation remains a mechanical replay of those recorded criteria. It may later report a hypothetical legacy entry, exit or review state; that is not a newly approved position.

The **new decision** is to remain flat before the runoff and require a fresh, separately dated review before any paper entry. This is a change in how a future trigger is used, adopted on 16 October, not a claim that discretion was part of every earlier rule. No paper position has been opened by this publication. Brazilian two-year yields and the proposed credibility checks are analytical review conditions, not additional backtested filters silently inserted into the legacy replay.

Waiting avoided exposure but did not demonstrate predictive skill. No strategy return, execution, position sizing, scenario probability or out-of-sample edge is claimed. The risk-model evidence remains the retrospective 7 October diagnostic, with its original coverage-test limitations. Calendar dates are linked to TSE, Federal Reserve and BCB publications and were checked on 16 October.

## Same-day revision (16 October)

The first version of this note reported the oil comparison from the 2 October base only (Brent −6.6%, −9.8% in reais), and set the 1.33% rise in USD/BRL since 5 October against the one-month carry cushion. The revised note reports the base-date range, and states carry relative to pre-vote volatility and to the first-round move. It also adds the breakeven term structure, Focus revisions and the survey gap. Inputs, rules and the decision are unchanged; the earlier figures remain in the saved report.
