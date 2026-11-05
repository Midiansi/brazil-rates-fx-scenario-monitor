# 5 November 2026 publication: definitions and decision record

The first note after the Copom's 282nd meeting (4 November, decision after the close). Market observations end on 4 November, so nothing here reflects the first session after the decision. Each series keeps its own date: PTAX, Treasury yields and the ANBIMA curve through 4 November, Focus dated 30 October (published 3 November), Brent spot through 3 November.

## Inputs and reproduction

`thesis_snapshot_2026-11-05.json` freezes the official snapshot committed at `44f12fa`. It adds labelled blocks:

- `anbima_ettj`: the official zero curves of 27 to 30 October and 3 and 4 November, downloaded from ANBIMA's CSV service and parsed with `parse_ettj` from `scripts/collect_study_inputs.py`. ANBIMA no longer served 23 and 26 October when this note was built, so those two days have no curve.
- `copom`: the decision, the vote, the inflation projections, the FX assumption and the wording used in the note, from the official statement.
- `fed`: the 28 October decision and the two dissents in favour of a hike, from the official statement.
- `press`: figures no official feed in this repository provides (B3 DI rates, the Ibovespa, front-month Brent, surveys and option pricing) and budget reporting. Each carries the URL and date of the report it was copied from, and the note labels them as press-reported.
- `holidays_b3`: the national holidays used to count business days.

Run `python scripts/build_copom.py` to reproduce `copom_2026-11-05.json`, then `python scripts/generate_market_brief.py` for the PDFs and Markdown note. `current_update_file` in `thesis.json` selects this report and `previous_update_file` the 27 October note, which stays on the page under the scorecard. Its briefs are in `outputs/archive/2026-10-27/`.

## What is priced

A DI rate compounds over business days to the contract's maturity. January 2028 (DI1F28) matures on 3 January 2028, 291 business days from 4 November.

**Hikes priced.** `hikes_priced` solves for the size of a straight-line rise in the Selic from today to 30 June 2027, flat afterwards, such that the average overnight rate (Selic minus 0.10 pp, daily compounding) equals the DI rate. The result is 103 bp; the note says "about 100 bp". This is a one-parameter reading of one contract: other paths give the same average, and the DI rate also contains a risk premium.

**Economists' path.** The same convention as the 6 and 27 October notes: a straight line from today's Selic through the Focus year-end medians. To January 2028 it averages 12.98%. The gap to the contract is 1.41 pp. The 0.3 pp and 2.3 pp comparisons are the saved 27 October figures, which used the 23 October survey; economists have since moved up, so part of the narrowing comes from the survey, not from the market. The note says so under "What would prove me wrong?".

**Market line in the chart.** Forward CDI between consecutive ANBIMA vertices, plotted at the midpoint of each interval, plus 0.10 pp to make it comparable with the Selic. The 5 October line uses the study's saved curve with the same method. Forward rates contain term and risk premia and are not expectations.

**Decomposition.** The share of the 2-year rise that comes from implied inflation is `d_breakeven / (d_breakeven + d_real)`, the formula used for the 5 October fall in the study, with 5 October as the base and 4 November as the end. ANBIMA's implied inflation contains inflation-risk and liquidity premia.

The official curve interpolated flat-forward to 291 business days gives 14.43%, against the press-reported 14.39% close. The two are different measurements at different times; the test only requires them to agree within 10 bp.

## The rule test

The 27 October note published this branch before the meeting: if the Copom holds, sounds firm on inflation and the 2027 budget target is confirmed, prepare a bet that January 2028 falls, with dated levels.

| Condition | Status on 5 November | Evidence |
| --- | --- | --- |
| Holds | Met | 13.75%, 7-0 |
| Firm on inflation | Met | Projections raised to 5.6%, 4.7% and 3.5%; upward asymmetry; "manter a restrição adequada"; no signal of a cut |
| Budget target confirmed | Not met | Minister Durigan says the centre of the target (R$73.2 bn, 0.5% of GDP) will be pursued formally through a complementary bill; none is filed, and press reports put the budget room needed at R$39.8 bn or more |

"Firm on inflation" is a judgment on the statement's wording, recorded here so it can be challenged. "Confirmed" is defined from now on as a filed bill, because a speech cannot be checked. The conditions were not changed after the decision; only the third was given this operational definition.

## The paper plan

Written before the first session after the decision. Nothing has been entered, and no result is claimed.

- **Instrument:** receive January 2028, equivalent to being long the contract's PU.
- **Size:** R$1,000 per bp, 116 contracts. One contract's DV01 is R$8.64, by exact repricing of `100000 / (1 + r)^(du/252)` for a 1 bp move centred on the quote.
- **Why this size:** on 26 October this contract moved 194 bp in a session. At this DV01 a repeat costs about R$195,000, the limit of the paper plan. The size comes from the worst observed day because a stop cannot protect against a gap.
- **Entry:** first settlement after the trigger, only at 14.00% or above. At 14.00% the market would still price some hikes, and the 100 bp target would land on the economists' average of about 13.0%.
- **Stop and target:** 50 bp above and 100 bp below entry. A Copom hike or an explicit hike signal closes the plan at once. The target also triggers if the gap to the economists' path falls under 0.5 pp.
- **Expiry:** the 9 December Copom. If no bill is filed by then, the idea closes without a trade and is scored.

**Carry and roll.** Over 21 business days: carry is `(DI − CDI) × 21/252` of notional, expressed in rate terms by dividing by modified duration (6 bp). Roll is the zero rate at 291 business days minus the zero rate at 270 on the same curve (7 bp). Both assume the curve does not move. Note that the two use different measurements of the contract, the press quote for carry and the ANBIMA curve for roll.

**Result at expiry.** `contracts × (100000 − PU0 × (1 + average CDI)^(du/252))`, before costs and margin. Calendar-day path compounding and 252-day DI quoting differ slightly, as in the earlier notes.

## Facts used in the argument

- The Copom's reference scenario uses the Focus Selic path and starts from R$5.20 per dollar. PTAX on the decision day was 5.4775, 5.3% weaker. The statement says the FX value came from "the usual procedure"; this note does not try to reconstruct it and only reports the gap.
- Copom expectations before the meeting differed by source: 39 of 75 institutions expected a cut in the Broadcast survey, while B3 options priced about 70% for a hold. The scorecard therefore records the 27 October call as confirmed but not as an edge.
- Brent spot (EIA via FRED) is the series used for reais per barrel, multiplied by same-day PTAX. Front-month futures are a different contract and are reported separately, labelled as press-reported.

## Limits

DI rates are press-reported closes and not settlements; the 3 November comparison is a settlement. ANBIMA's curve is a fitted model. The hikes-priced figure depends on the assumed path shape. Forward rates and breakevens contain premia and cannot be read as forecasts. No position was opened, and the paper plan ignores costs, margin, liquidity and execution. The budget condition rests on press reporting of statements by officials, and the note will be scored against a filed bill.
