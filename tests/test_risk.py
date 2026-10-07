"""Independent checks of loss units, tail arithmetic and time ordering."""
from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import math
import statistics
from pathlib import Path

import pytest

from src import risk

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def inputs() -> dict:
    return json.loads((ROOT / "research/study_inputs_2026-10-06.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def saved_report() -> dict:
    return json.loads((ROOT / "research/risk_2026-10-07.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report(inputs) -> dict:
    return risk.build(inputs)


def test_generated_report_and_csv_reproduce_offline(inputs, report, saved_report, no_network) -> None:
    computed = risk.build(inputs)
    raw = (ROOT / "research/study_inputs_2026-10-06.json").read_bytes()
    computed["input_sha256"] = hashlib.sha256(raw).hexdigest()
    assert {key: value for key, value in computed.items() if key != "timeline"} == saved_report
    assert "timeline" not in saved_report
    assert (ROOT / "research/risk_forecasts.csv").read_text(encoding="utf-8") == risk.forecast_csv(report).replace("\r\n", "\n")
    assert no_network == []


def test_fixed_spot_long_brl_loss_is_not_the_usd_brl_percentage_change() -> None:
    # 100 BRL is worth 20 USD at 5 and 18.1818 USD at 5.5: a 9.0909% loss.
    assert risk.spot_loss(5, 5.5) == pytest.approx((20 - 100 / 5.5) / 20 * 100)
    assert risk.spot_loss(5, 5.5) == pytest.approx(100 / 11)
    assert risk.spot_loss(5, 4.5) < 0
    assert risk.loss_from_log_return(math.log(5.5 / 5)) == pytest.approx(risk.spot_loss(5, 5.5))


def test_normal_var_and_es_against_independent_tail_integration() -> None:
    sigma = 0.2
    result = risk.normal_tail(sigma)
    z = statistics.NormalDist().inv_cdf(0.99)
    assert result["var_pct"] == pytest.approx((1 - math.exp(-sigma * z)) * 100)
    # Simpson integration of the actual loss, rather than the closed-form ES.
    count, right = 4000, 12.0
    step = (right - z) / count

    def integrand(x: float) -> float:
        return 100 * (1 - math.exp(-sigma * x)) * math.exp(-x * x / 2) / math.sqrt(2 * math.pi)

    total = integrand(z) + integrand(right)
    total += sum((4 if i % 2 else 2) * integrand(z + i * step) for i in range(1, count))
    es_integral = total * step / 3 / 0.01
    assert result["es_pct"] == pytest.approx(es_integral, abs=1e-7)
    conditional_log_mean = sigma * math.exp(-z * z / 2) / math.sqrt(2 * math.pi) / 0.01
    assert result["es_pct"] < (1 - math.exp(-conditional_log_mean)) * 100
    assert result["es_pct"] > result["var_pct"]
    assert risk.normal_tail(0) == {"var_pct": 0, "es_pct": 0, "sigma_daily_pct": 0}


def test_historical_var_and_exact_fractional_tail_by_hand() -> None:
    returns = [i / 10000 for i in range(250)]
    result = risk.historical_tail(list(reversed(returns)))
    losses = [(1 - math.exp(-r)) * 100 for r in returns]
    assert result["var_pct"] == pytest.approx(losses[247])
    assert result["tail_observation_mass"] == pytest.approx(2.5)
    assert result["es_pct"] == pytest.approx((losses[249] + losses[248] + 0.5 * losses[247]) / 2.5)
    assert result["es_pct"] > result["var_pct"]
    # A tied threshold still produces the correct tail mean; no empty tail.
    tied = risk.historical_tail([math.log(1.05)] * 250)
    assert tied["var_pct"] == pytest.approx(100 * (1 - 1 / 1.05))
    assert tied["es_pct"] == pytest.approx(tied["var_pct"])
    integer_mass = risk.historical_tail(returns[:100])
    assert integer_mass["es_pct"] == pytest.approx(losses[99])


def test_rolling_normal_uses_prior_twenty_returns_and_zero_mean_rms(inputs, report) -> None:
    row = report["timeline"][0]
    closes = inputs["ptax"]
    index = next(i for i, (day, _) in enumerate(closes) if day == row["date"])
    training = closes[index - 21:index]
    returns = [math.log(b[1] / a[1]) for a, b in zip(training, training[1:])]
    sigma = math.sqrt(sum(r * r for r in returns) / 20)
    model = row["models"]["rolling_normal"]
    assert model["sigma_daily_pct"] == pytest.approx(sigma * 100)
    assert model["training_start"] == training[1][0]
    assert model["training_end"] == training[-1][0] == row["previous_date"]
    assert model["training_observations"] == 20


def test_ewma_variance_is_updated_after_forecasting(inputs, report) -> None:
    closes = inputs["ptax"]
    returns = [(day, math.log(after / before)) for (_, before), (day, after) in zip(closes, closes[1:])]
    row = report["timeline"][0]
    variance = sum(value * value for _, value in returns[:250]) / 250
    for day, value in returns[250:]:
        if day == row["date"]:
            break
        variance = 0.94 * variance + 0.06 * value * value
    model = row["models"]["ewma_normal"]
    assert model["sigma_daily_pct"] == pytest.approx(math.sqrt(variance) * 100)
    assert model["training_start"] == returns[0][0]
    assert model["training_end"] == row["previous_date"]


def test_changing_forecast_day_and_future_cannot_change_earlier_forecasts(inputs, report) -> None:
    mutated = copy.deepcopy(inputs)
    target = "2020-03-18"
    for row in mutated["ptax"]:
        if row[0] >= target:
            row[1] *= 1.7
    changed = risk.build(mutated)
    before = [row for row in report["timeline"] if row["date"] <= target]
    after = [row for row in changed["timeline"] if row["date"] <= target]
    assert len(before) == len(after)
    for original, new in zip(before, after):
        for key in risk.MODEL_KEYS:
            assert {k: v for k, v in original["models"][key].items() if k != "breach"} == {
                k: v for k, v in new["models"][key].items() if k != "breach"}
    assert before[-1]["loss_pct"] != after[-1]["loss_pct"]


@pytest.mark.parametrize("target", ["2016-02-01", "2020-03-18", "2026-10-05"])
def test_truncating_history_at_previous_day_reproduces_forecast(inputs, report, target) -> None:
    truncated = dict(inputs, ptax=[row for row in inputs["ptax"] if row[0] < target])
    prefix = risk.build(truncated)
    original = next(row for row in report["timeline"] if row["date"] == target)
    for key in risk.MODEL_KEYS:
        assert prefix["latest"]["models"][key] == {k: v for k, v in original["models"][key].items() if k != "breach"}


def test_all_training_dates_precede_forecast_date_and_latest_uses_cutoff(report) -> None:
    assert report["evaluation"]["start"] == "2016-01-04"
    assert report["evaluation"]["end"] == "2026-10-05"
    assert report["evaluation"]["n"] == len(report["timeline"]) == 2700
    assert report["publication_date"] == "2026-10-07"
    assert report["evaluation"]["parameters_tuned_on_evaluation"] is False
    for row in report["timeline"]:
        for model in row["models"].values():
            assert model["training_start"] <= model["training_end"] == row["previous_date"] < row["date"]
            assert model["es_pct"] >= model["var_pct"]
    assert report["latest"]["forecast_date"] is None
    for model in report["latest"]["models"].values():
        assert model["training_end"] == report["data_as_of"] == "2026-10-05"


def test_kupiec_likelihood_and_boundary_cases_by_hand() -> None:
    n, breaches, alpha = 250, 10, 0.01
    q = breaches / n
    expected_lr = 2 * ((n - breaches) * math.log((1 - q) / (1 - alpha)) + breaches * math.log(q / alpha))
    result = risk.kupiec_coverage(n, breaches, alpha)
    assert result["lr"] == pytest.approx(expected_lr)
    assert 12.94 < result["lr"] < 12.96
    assert result["p_value"] == pytest.approx(math.erfc(math.sqrt(expected_lr / 2)))
    assert risk.kupiec_coverage(1000, 10)["p_value"] == pytest.approx(1)
    assert risk.kupiec_coverage(250, 0)["lr"] == pytest.approx(-500 * math.log(0.99))
    assert risk.kupiec_coverage(250, 250)["lr"] == pytest.approx(-500 * math.log(0.01))


def test_breach_counts_coverage_and_extreme_days_recompute(report) -> None:
    for model in report["models"]:
        key = model["key"]
        dates = [row["date"] for row in report["timeline"] if row["loss_pct"] > row["models"][key]["var_pct"]]
        assert model["breach_dates"] == dates
        assert model["breaches"] == len(dates)
        assert model["breach_rate_pct"] == pytest.approx(len(dates) / 2700 * 100)
        assert model["observed_coverage_pct"] + model["breach_rate_pct"] == pytest.approx(100)
        assert model["expected_breaches"] == pytest.approx(27)
        assert model["expected_breach_rate_pct"] == pytest.approx(1)
        assert model["kupiec_p"] == pytest.approx(risk.kupiec_coverage(2700, len(dates))["p_value"])
    worst = sorted(report["timeline"], key=lambda row: row["loss_pct"], reverse=True)[:10]
    assert [row["date"] for row in report["largest_losses"]] == [row["date"] for row in worst]
    assert report["largest_losses"][0]["loss_pct"] == max(row["loss_pct"] for row in report["timeline"])


def test_download_has_one_row_per_model_per_day_and_audit_columns(report) -> None:
    rows = list(csv.DictReader(io.StringIO(risk.forecast_csv(report))))
    assert len(rows) == 8100
    assert len({(row["date"], row["model"]) for row in rows}) == 8100
    assert all(row["training_end"] < row["date"] for row in rows)
    assert set(rows[0]) >= {"previous_spot", "spot", "loss_pct", "var99_pct", "es99_pct", "breach", "training_start", "training_end"}


def test_zero_coupon_mark_rate_shock_sign_and_exact_repricing() -> None:
    face, rate, days = 1_000_000, 0.13, 504
    initial = face / (1 + rate) ** 2
    assert risk.zero_coupon_price(face, rate, days) == pytest.approx(initial)
    rise = risk.zero_coupon_stress(face, rate, days, 100)
    fall = risk.zero_coupon_stress(face, rate, days, -100)
    assert rise["shocked_price"] == pytest.approx(face / 1.14 ** 2)
    assert rise["pnl"] == pytest.approx(face / 1.14 ** 2 - initial)
    assert rise["pnl_pct"] == pytest.approx(((1.13 / 1.14) ** 2 - 1) * 100)
    assert rise["pnl"] < 0 < fall["pnl"]
    assert fall["pnl"] > abs(rise["pnl"])  # convexity matters at finite shocks
    unchanged = risk.zero_coupon_stress(face, rate, days, 0)
    assert unchanged["pnl"] == unchanged["pnl_pct"] == 0


def test_duration_dv01_units_and_business_day_convention() -> None:
    result = risk.zero_coupon_stress(100_000, 0.12, 252, 1)
    assert result["years"] == 1
    assert result["modified_duration"] == pytest.approx(1 / 1.12)
    # Independently differentiate price at a much smaller yield increment.
    y, tiny = 0.12, 1e-7
    derivative = ((100_000 / (1 + y - tiny)) - (100_000 / (1 + y + tiny))) / (2 * tiny)
    assert result["dv01"] == pytest.approx(derivative * 0.0001, rel=1e-7)
    assert abs(result["pnl"]) == pytest.approx(result["dv01"], rel=1e-4)
    maturity = risk.zero_coupon_stress(100_000, 0.12, 0, 100)
    assert maturity["price"] == maturity["shocked_price"] == 100_000
    assert maturity["dv01"] == maturity["modified_duration"] == 0


def test_carry_exact_funding_fx_conversion_and_break_even() -> None:
    factor = (1.15 / 1.04) ** (63 / 252)
    result = risk.carry_stress(0.15, 0.04, 63, 10)
    assert result["net_return_pct"] == pytest.approx((factor / 1.10 - 1) * 100)
    assert result["carry_before_fx_pct"] == pytest.approx((factor - 1) * 100)
    assert result["fx_only_return_pct"] == pytest.approx((1 / 1.10 - 1) * 100)
    assert result["years"] == 0.25
    assert risk.carry_stress(0.15, 0.04, 63, result["break_even_fx_change_pct"])["net_return_pct"] == pytest.approx(0)
    assert risk.carry_stress(0.15, 0.04, 63, -10)["net_return_pct"] > 0
    assert risk.carry_stress(0.15, 0.04, 0, 0)["net_return_pct"] == 0
    assert risk.carry_stress(0.05, 0.05, 252, 0)["net_return_pct"] == 0


def test_producer_revenue_shocks_and_actual_receipts_hedge_by_hand() -> None:
    # 1m USD receipts, a 20% commodity fall, and a 10% BRL depreciation.
    result = risk.producer_stress(1_000_000, 5, -20, 10, 40, 5.2)
    assert result["scenario_receipts_usd"] == 800_000
    assert result["baseline_brl"] == 5_000_000
    assert result["shocked_spot"] == pytest.approx(5.5)
    assert result["unhedged_brl"] == pytest.approx(800_000 * 5.5)
    assert result["hedged_brl"] == pytest.approx(800_000 * (0.4 * 5.2 + 0.6 * 5.5))
    assert result["unhedged_change_pct"] == pytest.approx((0.8 * 1.1 - 1) * 100)
    assert result["hedged_change_pct"] == pytest.approx((800_000 * (0.4 * 5.2 + 0.6 * 5.5) / 5_000_000 - 1) * 100)
    none = risk.producer_stress(1_000_000, 5, -20, 10, 0, 5.2)
    full = risk.producer_stress(1_000_000, 5, -20, 10, 100, 5.2)
    assert none["hedged_brl"] == none["unhedged_brl"]
    assert full["hedged_brl"] == pytest.approx(800_000 * 5.2)
    # FX cannot change fully converted revenue, but commodity receipts still do.
    assert risk.producer_stress(1_000_000, 5, -20, -20, 100, 5.2)["hedged_brl"] == full["hedged_brl"]
    assert risk.producer_stress(1_000_000, 5, -100, 10, 100, 5.2)["hedged_brl"] == 0
    assert risk.producer_stress(1_000_000, 5, 0, 10, 0, 5.2)["unhedged_change_pct"] > 0


@pytest.mark.parametrize("call", [
    lambda: risk.spot_loss(0, 5), lambda: risk.spot_loss(5, -1), lambda: risk.normal_tail(-0.1),
    lambda: risk.historical_tail([]), lambda: risk.historical_tail([0.1], 1),
    lambda: risk.kupiec_coverage(0, 0), lambda: risk.kupiec_coverage(100, 101),
    lambda: risk.zero_coupon_price(0, 0.1, 252), lambda: risk.zero_coupon_price(float("nan"), 0.1, 252),
    lambda: risk.zero_coupon_price(100, -1, 252), lambda: risk.zero_coupon_price(100, 0.1, -1),
    lambda: risk.zero_coupon_price(100, 0.1, 252.0), lambda: risk.zero_coupon_stress(100, 0.1, 252, -12000),
    lambda: risk.carry_stress(0.1, -1, 252, 0), lambda: risk.carry_stress(0.1, 0.1, 252, -100),
    lambda: risk.carry_stress(0.1, 0.1, 1.5, 0), lambda: risk.carry_stress(0.1, 0.1, 252, float("inf")),
    lambda: risk.producer_stress(1000, 5, -101, 0, 50, 5),
    lambda: risk.producer_stress(1000, 5, 0, -100, 50, 5),
    lambda: risk.producer_stress(1000, 5, 0, 0, 101, 5),
    lambda: risk.producer_stress(1000, 5, 0, 0, -1, 5),
    lambda: risk.producer_stress(1000, 5, 0, 0, 50, 0),
])
def test_invalid_units_and_domains_fail_clearly(call) -> None:
    with pytest.raises(ValueError):
        call()


def test_duplicate_dates_non_positive_prices_and_short_history_fail(inputs) -> None:
    with pytest.raises(ValueError, match="unique"):
        risk.build(dict(inputs, ptax=inputs["ptax"] + [inputs["ptax"][0]]))
    with pytest.raises(ValueError, match="positive"):
        risk.build(dict(inputs, ptax=[["2020-01-01", -1], ["2020-01-02", 5]]))
    with pytest.raises(ValueError, match="warmup"):
        risk.build(dict(inputs, ptax=inputs["ptax"][:250]))
    with pytest.raises(ValueError, match="evaluation start"):
        risk.build(inputs, evaluation_start="2030-01-01")
