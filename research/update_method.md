# 16 October 2026 publication: definitions and decision record

The current publication uses market observations through 15 October. Each series retains its own observation date. Brent ends on 14 October; Focus is dated 9 October. Publication is before the 16 October PTAX close. No intraday or executable prices are implied.

## Inputs and reproduction

`thesis_snapshot_2026-10-16.json` freezes the official-source snapshot committed at `04f8fd1` plus the ANBIMA curve downloaded specifically for 15 October. The raw ANBIMA CSV, encoding, URL and POST parameters are included. Curves for 2 and 5 October come from the original frozen study inputs. The old study and its risk forecasts are not extended or refitted.

Run `python scripts/build_update.py` to reproduce `update_2026-10-16.json`, then `python scripts/generate_market_brief.py` to regenerate the PDFs and Markdown note. Page visits do neither and make no network requests. The current report is selected by `current_update_file` in `thesis.json`; a missing follow-up leaves the original study available. The app cache includes the follow-up report and its prose/calculation modules.

## FX and carry

PTAX is the mean of official buying and selling reference rates. The first-round move uses the 2 October and 5 October observations. Reversal at 15 October is `(S15 − S5) / (S2 − S5)`. Its complement is the fraction retained **in USD/BRL quote units**, not a BRL total return or a trading P&L. Reciprocating the quote would change the percentages.

For an illustrative comparison with USD cash, relative one-month investment growth is `G = [(1 + Selic/100) / (1 + Fed midpoint/100)]^(1/12)`. The policy-rate proxy is `(G − 1) × 100`; the future exchange rate that makes relative USD wealth unchanged is `S × G`. Annual policy targets are treated as constant effective rates for this illustration. This is not the actual BRL or USD funding convention, a CDI accumulation, a covered-interest-parity estimate, or an executable forward. Curves, calendars, basis, margin and costs are omitted. The calculation deliberately does not extrapolate a short realised FX move into an expected return.

## Curve and survey

The table compares ANBIMA fitted nominal, inflation-implied and real zero rates at 504 business days, across the same three dates. Changes in basis points use the underlying unrounded percentage yields. Nominal rates are multiplicative in real rates and breakevens; the changes in the last two columns are not an exact additive attribution. Breakevens contain inflation-risk and liquidity premia as well as expectations.

Focus medians are identified by survey date and reference year. The 2026 and 2027 inflation medians are not compared directly with the two-year breakeven as if their maturities or compounding conventions matched. The current note does not label a survey/curve difference as a pure fiscal premium or claim to identify the cause of a market move.

## Commodities and revenue

The Brent/FX calculation uses the intersection of observation dates, ending on 14 October. Both comparisons begin on 2 October: `(Brent14 × S14) / (Brent2 × S2) − 1`. It does **not** combine the latest Brent with the 15 October PTAX, compare futures with spot, or compare a lagged September observation with an October endpoint.

The scenario table holds physical volume constant and computes `(1 + commodity shock) × (1 + FX shock) − 1`. The cross term matters. The dollar-price increase needed to offset a five-percent fall in USD/BRL is `1/0.95 − 1`, not five percent. This describes unhedged benchmark gross receipts, not EBITDA, profit, a fixed-notional forward payoff or a company valuation. A producer may have USD costs and liabilities, product differentials, uncertain volumes and pre-existing hedges. No hedge fraction or transaction is recommended.

## Decision standard adopted on 16 October

The original thresholds are preserved without alteration in `thesis_2026-10-06.json` and copied into the new publication for audit. The original `rule_status` computation remains a mechanical replay of those recorded criteria. It may later report a hypothetical legacy entry, exit or review state; that is not a newly approved position.

The **new decision** is to remain flat before the runoff and require a fresh, separately dated review before any paper entry. This is a change in how a future trigger is used, adopted on 16 October, not a claim that discretion was part of every earlier rule. No paper position has been opened by this publication. Brazilian two-year yields and the proposed credibility checks are analytical review conditions, not additional backtested filters silently inserted into the legacy replay.

Waiting avoided exposure but did not demonstrate predictive skill. No strategy return, execution, position sizing, scenario probability or out-of-sample edge is claimed. The risk-model evidence remains the retrospective 7 October diagnostic, with its original coverage-test limitations. Calendar dates are linked to TSE, Federal Reserve and BCB publications and were checked on 16 October.
