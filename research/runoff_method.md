# 27 October 2026 publication: definitions and decision record

The first note after the 25 October runoff. Market observations end on 26 October, the first session after the vote. Each series keeps its own date: PTAX and Treasury yields through 26 October, Focus dated 23 October, Brent through 20 October.

## Inputs and reproduction

`thesis_snapshot_2026-10-27.json` freezes the official-source snapshot committed at `3dc4714`. It adds three labelled blocks:

- `election`: the TSE runoff count (Lula 64,256,232 votes, Flávio Bolsonaro 59,826,041) and the last Datafolha poll before the vote (50–50 of valid votes).
- `press`: market figures that no official feed in this repository provides (B3 DI futures, the Ibovespa, the spot dollar close, the 27 October PTAX before the next refresh) and policy announcements (Treasury auction cancellations and buybacks, the central bank's stated FX stance). Each carries the URL and date of the report it was copied from. The note labels these press-reported wherever it uses them.
- No ANBIMA curve is saved for 26 October, so this note does not report breakevens or real yields.

The long PTAX history (since January 2002) is the frozen 6 October study input; later closes come from the new snapshot. The two agree on all 76 overlapping dates.

Run `python scripts/build_runoff.py` to reproduce `runoff_2026-10-27.json`, then `python scripts/generate_market_brief.py` for the PDFs and Markdown note. `current_update_file` in `thesis.json` selects this report. The 16 October note is preserved in `update_2026-10-16.json` (still reproducible with `scripts/build_update.py`) and its briefs in `outputs/archive/2026-10-16/`.

## FX

The move is `S26/S23 − 1` on PTAX (5.0374 → 5.50025, +9.19%). A fixed holding of reais marked in dollars loses `1 − S23/S26` (8.42%), the loss convention of the 7 October risk study. The rank compares daily log changes over the joined official history since 2002; only 8 October 2008 is larger.

PTAX is the average of four fixing windows between 10:00 and 13:00 Brasília time. On 26 October the spot dollar peaked above R$5.60 in the morning and closed at 5.4029 (+8.21%, press-reported), so PTAX overstates the close-to-close move. The note says so rather than switching series.

Carry uses the 16 October formula: `[(1 + Selic) / (1 + Fed midpoint)]^(1/12) − 1`, an illustrative policy-rate proxy, not a forward. "Months of carry" is `move / monthly carry`.

## The VaR comparison

`risk.build` runs on PTAX closes up to and including 23 October, with the same three models and parameters as the 7 October diagnostic (Normal on 20 sessions, EWMA λ = 0.94, historical 250 sessions, 99%). Its `latest` forecast is the next session, 26 October. The ratio is the realised loss divided by each model's VaR. This is a single observation used to illustrate jump risk; it is not a re-evaluation of the diagnostic, whose sample and conclusions are unchanged.

## Rates

DI futures are B3 contracts quoted as annual rates over 252 business days. The 23 October January 2028 rate (12.859%) is a settlement; the 26 October rate (14.80%) is a late-afternoon quote reported with its +194 bp change. The January 2027, 2029 and 2031 rates are 26 October settlements.

The economists' path follows `survey_path_average` from the 6 October study (straight line from today's 13.75% Selic through the Focus year-end medians, CDI 0.10 pp below target, daily compounding), extended to an arbitrary end date: the contract maturity (3 January 2028; 4 January 2027). Friday's and Monday's gaps use the same 23 October survey, so the change isolates the market move. Calendar-day path compounding and 252-day DI quoting differ slightly; the gap mixes expected policy and risk premia and cannot separate them.

"No further cut is priced this year" rests on the January 2027 settlement (13.696%) sitting above the 13.65% CDI and above the 13.39% the survey path implies to that date.

## Facts used in the argument

- Vote shares are of valid votes. Since 1989 every runoff was won by the first-round leader (Collor 1989, Lula 2002 and 2006, Dilma Rousseff 2010 and 2014, Bolsonaro 2018, Lula 2022); 1994 and 1998 were decided in the first round.
- Fiscal figures are the 6 October inputs: the government's 2027 budget bill projects a R$18.6 bn primary surplus; the Senate IFI (17 September) projects an R$86.1 bn deficit.
- Inflation figures are the 23 October Focus medians against the 3% target and 4.5% ceiling.

## Decision record

The 6 October rule allowed entry from 26 October and dropped the idea on any pre-entry close above 5.30. PTAX printed 5.50025 on 26 October, so the idea closed without an entry. No paper position was opened by any publication.

The new view is a judgement, not a model output: the Copom cutting cycle is over. The rates trade being prepared (receiving the January 2028 DI) is conditional on the 4 November Copom pausing rather than hiking and on the 2027 fiscal target being reaffirmed; it would need its own dated entry and stop levels. No scenario probabilities, position sizes or returns are claimed.
