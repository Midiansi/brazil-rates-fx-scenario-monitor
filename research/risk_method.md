# BRL downside risk: a reproducible one-session diagnostic

Published 7 October 2026. Frozen observations end on 5 October 2026. This is a
retrospective walk-forward diagnostic, with model choices made at publication.
Each reconstructed forecast uses only earlier observations, but these results
were not published prospectively and the evaluation period was not an
independently reserved test set. No window or decay parameter was fitted to
maximise performance in the evaluation period.

## Data and reproducibility

The input is the existing frozen `research/study_inputs_2026-10-06.json`, whose
PTAX series contains 6,221 daily observations from 2 January 2002 through
5 October 2026. The collection script averages the Banco Central do Brasil
buying and selling PTAX rates. USD/BRL is quoted as BRL per USD. PTAX is a daily
fixing benchmark; this exercise does not reconstruct executable bid/ask prices
or intraday exposure. The official source is the
[BCB PTAX dataset and API documentation](https://dadosabertos.bcb.gov.br/dataset/dolar-americano-usd-todos-os-boletins-diarios).

Input SHA-256:
`69d9e6984087d733ad387b8c21f55c6fc944f9f9d52ad0659a7d20b36893af69`.

Run `python scripts/build_risk.py` offline. It writes the compact published
summary `research/risk_2026-10-07.json` and the complete audit download
`research/risk_forecasts.csv`. The CSV has 8,100 rows: one for each of three
models on each of 2,700 evaluation dates. Every row includes previous/current
fixings, realised loss, VaR, ES, breach indicator, and the training start/end
dates and observation count. `src.risk.build` also returns the full timeline.
Tests recompute the files from the input and test same-day/future mutations and
truncated histories to verify that earlier forecasts cannot change.

## Position, loss units and time order

Hold a fixed amount of BRL spot and mark its value in USD. For USD/BRL fixing
`S`, the one-session log return is `r_t = log(S_t / S_(t-1))`, in decimals. The
loss as a percentage of the previous USD value is exactly:

`L_t = 100 * (1 - S_(t-1) / S_t) = 100 * (1 - exp(-r_t))`.

A rise in USD/BRL is a BRL loss; an appreciation is a negative loss. A 10% rise
in USD/BRL produces a 9.0909% USD value loss, rather than a 10% loss. This loss
function increases monotonically in the log return, so an upper-tail log-return
quantile maps directly to an upper-tail loss quantile. Carry, spreads, taxes,
fees and any leverage are absent from this spot diagnostic.

The first 250 observed returns initialise the models (3 January through
27 December 2002). Evaluation starts on the first observed session on or after
1 January 2016: 4 January 2016. All models use the same 2,700 evaluation dates
through 5 October 2026. A forecast for day `t` has training end day `t-1`; the
realised return on `t` enters the model only after that forecast is recorded.
Missing fixing dates are not filled with zero returns. The horizon is the next
observed PTAX session, which can span a weekend or holiday.

## The three fixed model specifications

All three models report one-session 99% VaR and 99% model-implied ES in the
exact percentage-loss units above. VaR is a tail threshold; ES is the average
loss in the model's upper 1% tail. ES is not the average observed evaluation
loss and the coverage test below does not validate ES.

- **Normal, rolling 20:** log returns have mean zero and variance equal to the
  mean of the squared preceding 20 returns. This is RMS volatility under the
  zero-mean assumption, not a demeaned sample standard deviation.
- **Normal, EWMA 0.94:** initialise variance with the mean square of the first
  250 returns, then use `v_(t+1) = 0.94*v_t + 0.06*r_t²`. The variance forecast
  for return `t` is `v_t`, before that return is observed. This uses the daily
  decay convention described in the original
  [RiskMetrics Technical Document, fourth edition, chapter 5](https://www.msci.com/documents/10199/5915b101-4206-4ba0-aee2-3449d5c7e95a).
- **Historical, rolling 250:** equally weight the preceding 250 returns and
  convert every observation to exact loss units. VaR is the inverse empirical
  CDF, `L_(ceil(0.99*n))` in ascending order. At `n=250`, that is rank 248,
  the third-largest loss. ES integrates the upper 1% empirical tail: the two
  largest losses plus half of the third-largest, divided by 2.5. Splitting
  mass at the boundary preserves the chosen tail probability, as discussed in
  [Rockafellar and Uryasev, Conditional Value-at-Risk for General Loss Distributions](https://sites.math.washington.edu/~rtr/papers/rtr187-CVaR2.pdf).

For Normal models, let `sigma = sqrt(v_t)`, `z = Φ⁻¹(0.99)`, and `a = 0.01`.
The implementation integrates the actual spot loss, rather than transforming
the mean tail log return:

`VaR99 = 100 * (1 - exp(-sigma*z))`

`ES99 = 100 * (1 - exp(sigma²/2) * Φ̅(z+sigma) / a)`.

The ES identity follows from completing the square in the truncated Normal
integral for `E[exp(-sigma*Z) | Z>z]`. Transforming `E[r | r>sigma*z]` would
instead introduce a nonlinear approximation. A test checks the closed form
against independent numerical integration of the loss function.

## Coverage result and its limits

A breach occurs only when realised loss is **strictly greater** than that
day's VaR. The nominal expected breach rate is 1%, or 27 of 2,700 sessions.

| Model | Breaches | Observed breach rate | Observed coverage | Kupiec p-value |
|---|---:|---:|---:|---:|
| Normal, rolling 20 | 63 | 2.3333% | 97.6667% | 2.9049e-9 |
| Normal, EWMA 0.94 | 61 | 2.2593% | 97.7407% | 1.6494e-8 |
| Historical, rolling 250 | 36 | 1.3333% | 98.6667% | 0.09765 |

The two Normal specifications underestimate the observed frequency of large
BRL losses in this period. Historical simulation has fewer breaches and is
not rejected against the nominal 1% null at a 5% level by this count test. That
does not establish that the historical model is calibrated, responsive to
regime changes, or suitable for a trading decision. The largest evaluation
loss is 8.0177% on 18 May 2017; all three models breach on that day.

There is finite-window granularity in the historical model. Only two of its
250 training observations lie strictly above rank 248. Under independent,
identically distributed continuous returns, a new observation exceeds this
estimated rank with probability `3/251`, approximately 1.20%, rather than
exactly 1%. The published coverage test deliberately compares every model
with the same **nominal** 1% target; its historical p-value must be read with
this finite-sample qualification. Ties and changing return distributions add
further qualifications.

For `N` evaluation observations, `B` breaches, `q=B/N` and nominal `a=0.01`:

`LR = 2 * [B*log(q/a) + (N-B)*log((1-q)/(1-a))]`

with zero-count terms defined by continuity. Under the asymptotic
chi-square(1) reference, `p = erfc(sqrt(LR/2))`. This is Kupiec's unconditional
coverage statistic. It tests aggregate frequency, not breach independence or
conditional coverage; a comfortable p-value can coexist with clusters of
misses. The distinction and likelihood-ratio test are explained in
[Campbell, A Review of Backtesting and Backtesting Procedures, Federal Reserve FEDS 2005-21, sections 2–3](https://www.federalreserve.gov/pubs/feds/2005/200521/200521pap.pdf).
Serial dependence can weaken the iid-based test interpretation. The audit CSV preserves every breach date so clustering can be inspected
alongside aggregate frequency.

## The separate latest prediction

As of the **5 October 2026** fixing of **4.9856 BRL/USD**, all latest models
include that observed return and predict the next available PTAX session.
They do not have an observed outcome in this frozen dataset. The date of that
next observation is not fabricated.

| Model | VaR99 | ES99 | Latest training window |
|---|---:|---:|---|
| Normal, rolling 20 | 2.7126% | 3.1009% | 8 September–5 October 2026; 20 returns |
| Normal, EWMA 0.94 | 2.8657% | 3.2755% | 3 January 2002–5 October 2026; 6,220 returns |
| Historical, rolling 250 | 1.6678% | 1.7542% | 7 October 2025–5 October 2026; 250 returns |

These are conditional thresholds under explicit model assumptions. They are
not forecasts of the election outcome, probabilities of a political scenario,
position-size recommendations, or claimed investment returns.

## Scenario-lab arithmetic

The lab's calculations are deterministic scenarios, distinct from the risk
model. Public rate inputs are annual effective **decimals** (`0.13` means 13%),
rate shocks are basis points (`100 bp = 0.01`), FX and commodity shocks are
percentages (`10` means 10%), and time is integer business days with 252 per
year. Domain checks reject non-finite inputs, rates at or below −100%, negative
time, and non-positive FX conversion rates.

**Zero-coupon rate exposure.** `P = face * (1+y)^(-T)`, where `T=days/252`.
Apply `shock_bp/10000` to the annual effective yield and reprice exactly at the
same remaining maturity. P&L is the shocked price minus the initial price.
Modified duration is `T/(1+y)`. Positive DV01 is the average of the two
symmetric one-basis-point price changes:
`[P(y-0.0001)-P(y+0.0001)]/2`. This is currency value per 1 bp, not a derivative
per one percentage point. The face amount is a redemption amount, not an
assumed invested market value. This illustrates a zero-coupon exposure; it
does not reproduce a coupon bond or a DI future's contract settlement.

**Carry and FX.** The relative terminal return versus USD cash is
`[((1+BR_rate)/(1+US_rate))^(days/252)/(1+FX_change_pct/100)-1]*100`.
A positive FX change means BRL depreciation. This normalises terminal USD
asset value by terminal USD cash benchmark value; it is not dollar P&L or a
return on an unspecified leveraged equity amount. Rates are held constant
through the scenario. The break-even USD/BRL increase equals the compounded
carry ratio minus one.

**Commodity producer revenue.** Given baseline USD receipts `R`, USD/BRL spot
`S`, commodity percentage shock `c`, FX percentage shock `f`, hedge fraction
`h=hedge_pct/100`, and supplied forward conversion rate `F`:

`scenario_USD = R*(1+c/100)`

`baseline_BRL = R*S`

`unhedged_BRL = scenario_USD*S*(1+f/100)`

`hedged_BRL = scenario_USD*[h*F+(1-h)*S*(1+f/100)]`.

The hedge fraction applies to actual scenario receipts, so a commodity shock
also changes the assumed amount converted forward. This is a revenue
conversion illustration, not a fixed-notional derivative payoff or profit
model. Production costs, volume changes, basis, forward pricing, collateral,
and transaction costs are not estimated. Tests verify the 0%/100% hedge limits
and independently recompute mixed shocks.
