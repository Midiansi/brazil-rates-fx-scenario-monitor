"""Trailing one-session BRL downside diagnostics and transparent stress arithmetic.

Production uses only the Python standard library. Log returns are decimals inside
the models; all public ``*_pct`` outputs are percentage points. USD/BRL is BRL
per USD, so a higher fixing produces a loss on a fixed spot holding of BRL.
"""
from __future__ import annotations

import csv
import io
import math
import statistics
from datetime import date
from typing import Any

BUSINESS_DAYS = 252
CONFIDENCE = 0.99
MODEL_KEYS = ("rolling_normal", "ewma_normal", "historical")


def _finite(value: float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def _rate(value: float, name: str) -> float:
    number = _finite(value, name)
    if number <= -1:
        raise ValueError(f"{name} is a decimal annual rate and must exceed -1")
    return number


def _days(value: int, name: str = "business days") -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def loss_from_log_return(log_return: float) -> float:
    """USD loss (%) on a fixed BRL spot holding: 100 * (1 - exp(-r))."""
    return -100 * math.expm1(-_finite(log_return, "log return"))


def spot_loss(previous_spot: float, current_spot: float) -> float:
    """Exact USD value loss (%) when USD/BRL changes between two fixings."""
    before, after = _finite(previous_spot, "previous spot"), _finite(current_spot, "current spot")
    if before <= 0 or after <= 0:
        raise ValueError("USD/BRL fixings must be positive")
    return (1 - before / after) * 100


def normal_tail(sigma: float, confidence: float = CONFIDENCE) -> dict[str, float]:
    """Zero-mean Normal log-return VaR and exact conditional loss ES.

    With r = sigma*Z, ES integrates 1-exp(-r) over Z > z. Transforming
    E[r | r > VaR(r)] would instead be an approximation (Jensen's inequality).
    """
    sigma = _finite(sigma, "daily sigma")
    if sigma < 0 or not 0 < confidence < 1:
        raise ValueError("sigma must be non-negative and confidence must lie between 0 and 1")
    if sigma == 0:
        return {"var_pct": 0.0, "es_pct": 0.0, "sigma_daily_pct": 0.0}
    z = statistics.NormalDist().inv_cdf(confidence)
    tail = 1 - confidence
    conditional_inverse_fx = math.exp(sigma * sigma / 2) * (math.erfc((z + sigma) / math.sqrt(2)) / 2) / tail
    return {"var_pct": loss_from_log_return(sigma * z), "es_pct": (1 - conditional_inverse_fx) * 100,
            "sigma_daily_pct": sigma * 100}


def historical_tail(log_returns: list[float], confidence: float = CONFIDENCE) -> dict[str, Any]:
    """Inverse-empirical-CDF VaR and exact upper-tail mean in loss units.

    ES includes a fractional boundary observation: a 1% tail of 250 equally
    weighted observations is the two largest losses plus half the third,
    divided by 2.5. This avoids silently turning a 1% tail into a 1.2% tail.
    """
    if not log_returns or not 0 < confidence < 1:
        raise ValueError("historical returns must be non-empty and confidence must lie between 0 and 1")
    losses = sorted(loss_from_log_return(r) for r in log_returns)
    n = len(losses)
    var = losses[math.ceil(confidence * n) - 1]
    mass = (1 - confidence) * n
    # Remove floating-point noise at integer tail sizes (e.g. 100 * 0.01).
    if math.isclose(mass, round(mass), abs_tol=1e-12):
        mass = float(round(mass))
    whole = math.floor(mass)
    partial = mass - whole
    weighted_sum = sum(losses[n - whole:]) if whole else 0.0
    if partial:
        weighted_sum += partial * losses[n - whole - 1]
    return {"var_pct": var, "es_pct": weighted_sum / mass, "sigma_daily_pct": None,
            "tail_observation_mass": mass}


def kupiec_coverage(n: int, breaches: int, tail_probability: float = 0.01) -> dict[str, float]:
    """Unconditional coverage LR and asymptotic chi-square(1) survival p-value."""
    if not isinstance(n, int) or not isinstance(breaches, int) or n <= 0 or not 0 <= breaches <= n:
        raise ValueError("coverage needs a positive observation count and 0 <= breaches <= n")
    if not 0 < tail_probability < 1:
        raise ValueError("tail probability must lie between 0 and 1")
    observed = breaches / n
    null_ll = breaches * math.log(tail_probability) + (n - breaches) * math.log1p(-tail_probability)
    fitted_ll = 0.0
    if breaches:
        fitted_ll += breaches * math.log(observed)
    if breaches < n:
        fitted_ll += (n - breaches) * math.log1p(-observed)
    lr = max(0.0, 2 * (fitted_ll - null_ll))
    return {"lr": lr, "p_value": math.erfc(math.sqrt(lr / 2))}


def _observations(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[tuple[str, float]] = []
    for raw_day, raw_spot in inputs["ptax"]:
        day = date.fromisoformat(str(raw_day)).isoformat()
        spot = _finite(raw_spot, "PTAX")
        if spot <= 0:
            raise ValueError("PTAX must be positive")
        rows.append((day, spot))
    rows.sort()
    if len({day for day, _ in rows}) != len(rows):
        raise ValueError("PTAX dates must be unique")
    return [{"date": day, "previous_date": previous_day, "previous_spot": previous,
             "spot": spot, "log_return": math.log(spot / previous), "loss_pct": spot_loss(previous, spot)}
            for (previous_day, previous), (day, spot) in zip(rows, rows[1:])]


def build(inputs: dict[str, Any], *, publication_date: str = "2026-10-07", evaluation_start: str = "2016-01-01",
          warmup: int = 250, rolling_window: int = 20, historical_window: int = 250,
          decay: float = 0.94, confidence: float = CONFIDENCE) -> dict[str, Any]:
    """Reconstruct daily forecasts without observing the forecast day's return.

    The first ``warmup`` returns initialise EWMA; its variance is updated only
    *after* forecasting each subsequent observation. All three models use the
    identical evaluation dates. The separate latest forecast includes the last
    observed return and refers to the next available PTAX session (date unknown).
    """
    date.fromisoformat(publication_date)
    date.fromisoformat(evaluation_start)
    for value in (warmup, rolling_window, historical_window):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("warmup and model windows must be positive integers")
    if warmup < max(rolling_window, historical_window) or not 0 < decay < 1 or not 0.5 < confidence < 1:
        raise ValueError("warmup must cover both windows; decay must lie in (0,1) and confidence in (0.5,1)")
    observations = _observations(inputs)
    if len(observations) <= warmup:
        raise ValueError("PTAX history needs more returns than the warmup")
    returns = [row["log_return"] for row in observations]
    ewma_variance = statistics.fmean(r * r for r in returns[:warmup])

    def forecast(end: int, variance: float) -> dict[str, dict[str, Any]]:
        # end is exclusive: realised return at observations[end] is absent.
        last_day = observations[end - 1]["date"]
        rolling = normal_tail(math.sqrt(statistics.fmean(r * r for r in returns[end - rolling_window:end])), confidence)
        ewma = normal_tail(math.sqrt(variance), confidence)
        historical = historical_tail(returns[end - historical_window:end], confidence)
        for result, start, count in ((rolling, end - rolling_window, rolling_window),
                                     (ewma, 0, end), (historical, end - historical_window, historical_window)):
            result.update({"training_start": observations[start]["date"], "training_end": last_day,
                           "training_observations": count})
        return dict(zip(MODEL_KEYS, (rolling, ewma, historical)))

    timeline = []
    for i in range(warmup, len(observations)):
        observation = observations[i]
        if observation["date"] >= evaluation_start:
            predictions = forecast(i, ewma_variance)
            for prediction in predictions.values():
                prediction["breach"] = observation["loss_pct"] > prediction["var_pct"]
            timeline.append({key: observation[key] for key in ("date", "previous_date", "previous_spot", "spot", "loss_pct")} |
                            {"log_return_pct": observation["log_return"] * 100, "models": predictions})
        # The return enters EWMA only once the forecast and breach are recorded.
        ewma_variance = decay * ewma_variance + (1 - decay) * returns[i] * returns[i]
    if not timeline:
        raise ValueError("evaluation start lies after the available history")

    labels = (f"Normal · {rolling_window} sessions", f"Normal · EWMA λ {decay:g}", f"Historical · {historical_window} sessions")
    training = (f"Trailing {rolling_window} log returns; zero-mean RMS volatility",
                f"Expanding trailing EWMA; λ={decay:g}; initial variance from first {warmup} returns",
                f"Trailing {historical_window} returns; equal weights; inverse empirical CDF")
    n, tail = len(timeline), 1 - confidence
    models = []
    for key, label, method in zip(MODEL_KEYS, labels, training):
        breaches = [row["date"] for row in timeline if row["models"][key]["breach"]]
        coverage = kupiec_coverage(n, len(breaches), tail)
        models.append({"key": key, "label": label, "training": method, "n": n, "breaches": len(breaches),
                       "breach_dates": breaches, "breach_rate_pct": len(breaches) / n * 100,
                       "observed_coverage_pct": (1 - len(breaches) / n) * 100,
                       "expected_breach_rate_pct": tail * 100, "expected_breaches": n * tail,
                       "kupiec_lr": coverage["lr"], "kupiec_p": coverage["p_value"],
                       "average_var_pct": statistics.fmean(row["models"][key]["var_pct"] for row in timeline),
                       "average_es_pct": statistics.fmean(row["models"][key]["es_pct"] for row in timeline)})
    largest = sorted(timeline, key=lambda row: row["loss_pct"], reverse=True)[:10]
    return {
        "schema_version": 1, "publication_date": publication_date, "data_as_of": observations[-1]["date"],
        "input_file": "research/study_inputs_2026-10-06.json", "csv_file": "research/risk_forecasts.csv",
        "method_file": "research/risk_method.md",
        "conventions": {"position": "Fixed spot BRL holding, marked in USD; carry and costs excluded",
                        "quote": "USD/BRL: BRL per USD", "loss_formula": "100 * (1 - S_previous / S_current)",
                        "confidence": confidence, "horizon_sessions": 1, "return_unit": "decimal log returns internally",
                        "risk_unit": "percentage of previous USD spot value", "business_days_per_year": BUSINESS_DAYS,
                        "normal_mean": 0.0, "ewma_decay": decay, "rolling_window": rolling_window,
                        "historical_window": historical_window, "historical_quantile": "inverse empirical CDF (nearest rank)",
                        "historical_es": "mean of upper tail in exact loss units, fractional boundary weight"},
        "evaluation": {"requested_start": evaluation_start, "start": timeline[0]["date"], "end": timeline[-1]["date"],
                       "n": n, "warmup_returns": warmup, "warmup_start": observations[0]["date"],
                       "warmup_end": observations[warmup - 1]["date"],
                       "status": "Retrospective walk-forward diagnostic; model choices set on 7 October 2026",
                       "parameters_tuned_on_evaluation": False,
                       "coverage_test_scope": "Unconditional exceedance frequency only; no independence or ES calibration test"},
        "models": models,
        "latest": {"as_of": observations[-1]["date"], "forecast_date": None,
                   "horizon": "Next observed PTAX session after the data cutoff", "spot": observations[-1]["spot"],
                   "models": forecast(len(observations), ewma_variance)},
        "largest_losses": [{"date": row["date"], "previous_date": row["previous_date"], "loss_pct": row["loss_pct"],
                            "usd_brl_change_pct": (row["spot"] / row["previous_spot"] - 1) * 100,
                            "breaches": [key for key in MODEL_KEYS if row["models"][key]["breach"]]} for row in largest],
        "timeline": timeline,
    }


def forecast_csv(report: dict[str, Any]) -> str:
    """One row per evaluation date and model, preserving audit training dates."""
    output = io.StringIO(newline="")
    fields = ("date", "previous_date", "previous_spot", "spot", "log_return_pct", "loss_pct", "model", "var99_pct",
              "es99_pct", "sigma_daily_pct", "breach", "training_start", "training_end", "training_observations")
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for row in report["timeline"]:
        for key in MODEL_KEYS:
            model = row["models"][key]
            record = {name: row[name] for name in fields[:6]}
            record.update({"model": key, "var99_pct": model["var_pct"], "es99_pct": model["es_pct"],
                           "sigma_daily_pct": model["sigma_daily_pct"], "breach": int(model["breach"]),
                           **{name: model[name] for name in fields[-3:]}})
            writer.writerow(record)
    return output.getvalue()


def zero_coupon_price(principal: float, annual_yield_decimal: float, maturity_business_days: int) -> float:
    """BRL zero-coupon present value, annual effective yield and 252-day year."""
    principal = _finite(principal, "principal")
    if principal <= 0:
        raise ValueError("principal must be positive")
    rate, days = _rate(annual_yield_decimal, "yield"), _days(maturity_business_days, "maturity business days")
    return principal * (1 + rate) ** (-days / BUSINESS_DAYS)


def zero_coupon_stress(principal: float, annual_yield_decimal: float, maturity_business_days: int, shock_bp: float) -> dict[str, float]:
    """Exact instantaneous repricing and positive DV01 per 1 bp rate decline.

    Principal is the fixed face value, not invested market value. Maturity stays
    fixed during the shock. This is a zero-coupon illustration, not a DI future.
    """
    rate, shock = _rate(annual_yield_decimal, "yield"), _finite(shock_bp, "rate shock (bp)")
    days = _days(maturity_business_days, "maturity business days")
    price = zero_coupon_price(principal, rate, days)
    shocked = zero_coupon_price(principal, rate + shock / 10000, days)
    if rate - 0.0001 <= -1:
        raise ValueError("yield must exceed -0.9999 to compute symmetric 1 bp DV01")
    dv01 = (zero_coupon_price(principal, rate - 0.0001, days) - zero_coupon_price(principal, rate + 0.0001, days)) / 2
    return {"price": price, "shocked_price": shocked, "pnl": shocked - price, "pnl_pct": (shocked / price - 1) * 100,
            "dv01": dv01, "modified_duration": (days / BUSINESS_DAYS) / (1 + rate),
            "years": days / BUSINESS_DAYS, "shock_bp": shock, "shocked_yield_decimal": rate + shock / 10000}


def carry_stress(br_rate_decimal: float, us_rate_decimal: float, days_business: int, fx_change_pct: float) -> dict[str, float]:
    """BRL asset return relative to a USD cash benchmark, with constant rates.

    Positive FX change means USD/BRL rises (BRL weakens). The result is
    ((1+BR rate)/(1+US rate))**(days/252)/(1+FX change/100)-1.
    This ratio normalises terminal USD asset value by terminal USD cash value;
    it is not dollar P&L or a return on an unspecified leveraged equity amount.
    """
    br, us = _rate(br_rate_decimal, "BR annual rate"), _rate(us_rate_decimal, "USD annual funding rate")
    days, fx = _days(days_business, "holding business days"), _finite(fx_change_pct, "USD/BRL change (%)")
    if fx <= -100:
        raise ValueError("USD/BRL change must exceed -100%")
    carry_factor = ((1 + br) / (1 + us)) ** (days / BUSINESS_DAYS)
    fx_factor = 1 + fx / 100
    return {"net_return_pct": (carry_factor / fx_factor - 1) * 100,
            "carry_before_fx_pct": (carry_factor - 1) * 100, "fx_only_return_pct": (1 / fx_factor - 1) * 100,
            "break_even_fx_change_pct": (carry_factor - 1) * 100,
            "carry_factor": carry_factor, "fx_factor": fx_factor, "years": days / BUSINESS_DAYS}


def producer_stress(receipts_usd: float, spot_brl_per_usd: float, commodity_pct: float,
                    fx_pct: float, hedge_pct: float, forward_rate: float) -> dict[str, float]:
    """Translate shocked commodity export receipts to BRL revenue, not profit.

    The hedge covers a fraction of the *actual scenario* USD receipts at a
    supplied forward conversion rate. This is not a fixed-notional derivative
    payoff: changing receipts also changes the assumed amount converted forward.
    """
    receipts, spot = _finite(receipts_usd, "USD receipts"), _finite(spot_brl_per_usd, "USD/BRL spot")
    commodity, fx = _finite(commodity_pct, "commodity change (%)"), _finite(fx_pct, "USD/BRL change (%)")
    hedge, forward = _finite(hedge_pct, "hedge share (%)"), _finite(forward_rate, "forward USD/BRL rate")
    if receipts <= 0 or spot <= 0 or forward <= 0:
        raise ValueError("USD receipts, USD/BRL spot and forward conversion rate must be positive")
    if commodity < -100 or fx <= -100 or not 0 <= hedge <= 100:
        raise ValueError("commodity change must be >= -100%, FX change > -100%, and hedge share in [0,100]%")
    scenario = receipts * (1 + commodity / 100)
    shocked_spot = spot * (1 + fx / 100)
    h = hedge / 100
    baseline, unhedged = receipts * spot, scenario * shocked_spot
    hedged = scenario * (h * forward + (1 - h) * shocked_spot)
    return {"baseline_brl": baseline, "unhedged_brl": unhedged, "hedged_brl": hedged,
            "unhedged_change_pct": (unhedged / baseline - 1) * 100,
            "hedged_change_pct": (hedged / baseline - 1) * 100,
            "scenario_receipts_usd": scenario, "shocked_spot": shocked_spot, "hedge_fraction": h}
