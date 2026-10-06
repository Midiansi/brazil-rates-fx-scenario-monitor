"""The quantitative study: saved results must match the frozen inputs, and the headline
figures are recomputed here by hand (not with ``src/study.py``) so a bug cannot hide behind itself."""
from __future__ import annotations

import json
import math
import statistics
from datetime import date

import pytest

from src import study


def closes(inputs) -> dict[str, float]:
    return {d: v for d, v in inputs["ptax"]}


def log_returns(values: list[float]) -> list[float]:
    return [math.log(b / a) * 100 for a, b in zip(values, values[1:])]


def test_saved_results_match_the_frozen_inputs(thesis, study_inputs) -> None:
    fresh = json.loads(json.dumps(study.build(study_inputs, thesis)))
    assert thesis["study"] == fresh, "research/study_2026-10-06.json is out of date: run python scripts/build_study.py"
    assert thesis["study"]["inputs_file"] == thesis["study_inputs_file"]


def test_inputs_cover_what_the_page_claims(study_inputs, thesis) -> None:
    dates = [d for d, _ in study_inputs["ptax"]]
    assert dates == sorted(set(dates)) and dates[0] <= "2002-01-04" and dates[-1] == thesis["data_as_of"]
    assert all(v > 0 for _, v in study_inputs["ptax"])
    for key, series in study_inputs["commodities_monthly"].items():
        months = [d for d, _ in series]
        assert months == sorted(set(months)) and months[0] <= "2005-01-01" and months[-1] == "2026-07-01", key
    assert set(study_inputs["anbima_ettj"]) >= {"2026-10-02", "2026-10-05"}
    assert study_inputs["exports"]["year"] == 2025


def test_ptax_matches_the_thesis_and_the_frozen_snapshot(study_inputs, thesis, frozen) -> None:
    saved = closes(study_inputs)
    for day, value in frozen["history"]["ptax"]:
        assert saved[day] == pytest.approx(value, abs=1e-4), day
    assert saved[thesis["data_as_of"]] == thesis["evidence"]["ptax"]["value"]


def test_first_monday_by_hand(study_inputs, thesis) -> None:
    saved, windows = closes(study_inputs), {w["year"]: w for w in thesis["study"]["elections"]}
    friday, monday = saved["2026-10-02"], saved["2026-10-05"]
    assert (friday, monday) == (5.2235, 4.9856)
    assert windows[2026]["monday_move"] == pytest.approx((monday / friday - 1) * 100)
    # z: log move over the standard deviation of the 20 daily log returns that end on the Friday
    dates = sorted(saved)
    end = dates.index("2026-10-02")
    sd = statistics.stdev(log_returns([saved[d] for d in dates[end - 20:end + 1]]))
    assert windows[2026]["z"] == pytest.approx(math.log(monday / friday) * 100 / sd)
    # the largest first Monday of the seven, and the only one above 7 sigma
    assert max(abs(w["monday_move"]) for w in windows.values()) == abs(windows[2026]["monday_move"])
    assert sorted(year for year, w in windows.items() if w["surprise"]) == [2014, 2018, 2022, 2026]
    assert all(abs(windows[year]["z"]) < 2 for year in (2002, 2006, 2010))


def test_giveback_agrees_with_the_thesis_event_study(study_inputs, thesis, frozen) -> None:
    windows = {w["year"]: w for w in thesis["study"]["elections"]}
    for saved in frozen["event_study"]["windows"]:
        p0, p1, p2 = (saved["closes"][key][1] for key in ("friday_before", "monday_after", "friday_before_runoff"))
        assert windows[saved["year"]]["giveback_runoff_friday"] == pytest.approx((p2 - p1) / (p0 - p1) * 100, abs=0.1)
        assert windows[saved["year"]]["friday_before"][0] == saved["closes"]["friday_before"][0]
    # the first close after each runoff, by hand for 2022 (Lula won on Sunday 30 Oct)
    saved = closes(study_inputs)
    p0, p1, after = saved["2022-09-30"], saved["2022-10-03"], saved["2022-10-31"]
    assert windows[2022]["giveback_first_close"] == pytest.approx((after - p1) / (p0 - p1) * 100)
    assert windows[2022]["runoff_session_move"] == pytest.approx((after / saved["2022-10-28"] - 1) * 100)
    # a path starts at 100 on the Friday and is only drawn to the Friday before the runoff
    for w in windows.values():
        assert w["path"][0] == [0, 100.0]
        assert w["pending"] if w["year"] == 2026 else w["path"][-1][1] == pytest.approx(w["friday_before_runoff"][1] / w["friday_before"][1] * 100, abs=1e-3)


def test_the_jump_is_the_eighth_largest_fall_since_2002(study_inputs, thesis) -> None:
    values = [v for _, v in sorted(study_inputs["ptax"])]
    returns = log_returns(values)
    vol = thesis["study"]["volatility"]
    assert vol["event_return"] == pytest.approx(returns[-1])
    assert sum(r < returns[-1] for r in returns) + 1 == vol["event_rank"] == 8
    assert vol["observations"] == len(returns)


def test_volatility_estimators_by_hand(study_inputs, thesis) -> None:
    values = [v for _, v in sorted(study_inputs["ptax"])]
    returns = log_returns(values)
    vol = thesis["study"]["volatility"]
    before, window = returns[-21:-1], returns[-20:]
    assert vol["diffusion_daily"] == pytest.approx(statistics.stdev(before)) == pytest.approx(thesis["evidence"]["volatility"]["daily_sd"], abs=0.001)
    assert vol["diffusion_annual"] == pytest.approx(statistics.stdev(before) * math.sqrt(252))
    rv = math.sqrt(sum(r * r for r in window) / 20)
    bv = math.sqrt(math.pi / 2 * sum(abs(a) * abs(b) for a, b in zip(window, window[1:])) / 19)
    assert vol["with_jump_daily"] == pytest.approx(rv) and vol["bipower_daily"] == pytest.approx(bv)
    assert vol["jump_share"] == pytest.approx((1 - bv * bv / (rv * rv)) * 100)
    # one jump dominates the realised variance but barely moves the jump-robust estimate
    assert vol["with_jump_annual"] > 1.6 * vol["bipower_annual"] and vol["jump_share"] > 50
    dates = sorted(d for d, _ in study_inputs["ptax"])
    since_2003 = log_returns([v for d, v in sorted(study_inputs["ptax"]) if d >= "2002-12-30"])
    assert vol["long_run_daily"] == pytest.approx(statistics.stdev(since_2003), rel=0.01)
    assert dates[-1] == thesis["data_as_of"]


def test_curve_forward_and_decomposition_by_hand(study_inputs, thesis, frozen) -> None:
    curve, ettj = thesis["study"]["curve"], study_inputs["anbima_ettj"]
    for day, key in (("2026-10-02", "previous"), ("2026-10-05", None)):
        block = frozen["anbima_ettj"][key] if key else frozen["anbima_ettj"]
        assert ettj[day]["fixed_rate"]["252"] == block["fixed_rate"]["252"] and ettj[day]["fixed_rate"]["504"] == block["fixed_rate"]["504"]
        assert ettj[day]["implied_inflation"]["504"] == block["implied_inflation"]["504"]
    z1, z2 = (ettj["2026-10-05"]["fixed_rate"][v] / 100 for v in ("252", "504"))
    assert curve["forward_1y1y"]["after"] == pytest.approx(((1 + z2) ** 2 / (1 + z1) - 1) * 100)
    # the curve sloped up between one and two years before the vote (forward above the two-year zero) and down after it
    before2 = ettj["2026-10-02"]["fixed_rate"]["504"]
    assert curve["forward_1y1y"]["before"] > before2 and curve["forward_1y1y"]["after"] < z2 * 100
    d_breakeven = ettj["2026-10-05"]["implied_inflation"]["504"] - ettj["2026-10-02"]["implied_inflation"]["504"]
    d_real = ettj["2026-10-05"]["real_rate"]["504"] - ettj["2026-10-02"]["real_rate"]["504"]
    assert curve["breakeven_share"] == pytest.approx(d_breakeven / (d_breakeven + d_real) * 100)
    two_year = next(row for row in curve["rows"] if row["vertex"] == "504")
    assert two_year["change_bp"] == pytest.approx((ettj["2026-10-05"]["fixed_rate"]["504"] - ettj["2026-10-02"]["fixed_rate"]["504"]) * 100)
    # Fisher: (1 + nominal) = (1 + real)(1 + breakeven), within rounding of ANBIMA's published figures
    for day in ("2026-10-02", "2026-10-05"):
        nominal = ettj[day]["fixed_rate"]["504"] / 100
        real, breakeven = ettj[day]["real_rate"]["504"] / 100, ettj[day]["implied_inflation"]["504"] / 100
        assert (1 + real) * (1 + breakeven) - 1 == pytest.approx(nominal, abs=1e-4)
    assert curve["history_2y"][-1] == ["2026-10-05", ettj["2026-10-05"]["fixed_rate"]["504"]]


def test_gap_to_the_economists_matches_the_thesis(thesis) -> None:
    gap, sp = thesis["study"]["survey_gap"], thesis["evidence"]["survey_path_average"]
    assert gap["survey_1y"] == pytest.approx(sp["one_year"], abs=0.005) and gap["survey_2y"] == pytest.approx(sp["two_year"], abs=0.005)
    assert gap["gap_2y_after"] == pytest.approx(sp["two_year_gap"], abs=0.005) and gap["gap_1y_after"] == pytest.approx(sp["one_year_gap"], abs=0.005)
    assert gap["gap_2y_before"] == pytest.approx(sp["two_year_gap_before"], abs=0.005)
    # the economists' second-year average: (1 + 2y)^2 / (1 + 1y) - 1
    assert gap["survey_fwd_1y1y"] == pytest.approx(((1 + gap["survey_2y"] / 100) ** 2 / (1 + gap["survey_1y"] / 100) - 1) * 100)


def test_basket_regression_by_hand(study_inputs, thesis) -> None:
    prices = {k: {d: v for d, v in series} for k, series in study_inputs["commodities_monthly"].items()}
    by_month: dict[str, list[float]] = {}
    for day, value in study_inputs["ptax"]:
        by_month.setdefault(day[:7] + "-01", []).append(value)
    fx = {m: sum(v) / len(v) for m, v in by_month.items()}
    months = [m for m in sorted(prices["brent"]) if "2005-01-01" <= m <= "2026-07-01"]
    exports = study_inputs["exports"]
    codes = {"brent": "2709", "soybeans": "1201", "iron_ore": "2601", "coffee": "0901", "sugar": "1701", "maize": "1005"}
    assert exports["hs"] == codes
    total = sum(exports["usd"][k] for k in codes)
    weights = {k: exports["usd"][k] / total for k in codes}
    basket = [sum(weights[k] * math.log(prices[k][b] / prices[k][a]) for k in codes) for a, b in zip(months, months[1:])]
    change = [math.log(fx[b] / fx[a]) for a, b in zip(months, months[1:])]
    slope, intercept = statistics.linear_regression(basket, change)
    saved = thesis["study"]["basket"]
    assert saved["n"] == len(change) == 258
    assert saved["slope"] == pytest.approx(slope) and saved["intercept"] == pytest.approx(intercept)
    assert saved["r2"] == pytest.approx(statistics.correlation(basket, change) ** 2)
    assert saved["slope"] < 0 and 0.2 < saved["r2"] < 0.4  # commodities matter, but explain well under half
    assert saved["early"]["r2"] > saved["late"]["r2"] > 0.15 and abs(saved["early"]["slope"] - saved["late"]["slope"]) < 0.1
    shares = thesis["study"]["weights"]
    assert shares["covered"] == pytest.approx(sum(exports["usd"][k] for k in codes) / exports["total_usd"] * 100)
    assert sum(shares["relative"].values()) == pytest.approx(100)
    assert len(saved["scatter"]) == 258 and saved["scatter"][-1][0] == pytest.approx(basket[-1] * 100, abs=0.01)


def test_natural_hedge_and_twelve_month_change_by_hand(study_inputs, thesis) -> None:
    prices = {k: {d: v for d, v in series} for k, series in study_inputs["commodities_monthly"].items()}
    by_month: dict[str, list[float]] = {}
    for day, value in study_inputs["ptax"]:
        by_month.setdefault(day[:7] + "-01", []).append(value)
    fx = {m: sum(v) / len(v) for m, v in by_month.items()}
    months = [m for m in sorted(prices["soybeans"]) if "2005-01-01" <= m <= "2026-07-01"]
    usd = [math.log(prices["soybeans"][b] / prices["soybeans"][a]) for a, b in zip(months, months[1:])]
    brl = [u + math.log(fx[b] / fx[a]) for u, (a, b) in zip(usd, zip(months, months[1:]))]
    soy = next(item for item in thesis["study"]["hedge"] if item["key"] == "soybeans")
    assert soy["vol_usd"] == pytest.approx(statistics.stdev(usd) * math.sqrt(12) * 100)
    assert soy["hedge"] == pytest.approx((1 - statistics.stdev(brl) / statistics.stdev(usd)) * 100)
    assert soy["corr_fx"] == pytest.approx(statistics.correlation(usd, [math.log(fx[b] / fx[a]) for a, b in zip(months, months[1:])]))
    yoy = thesis["study"]["year_on_year"]
    assert yoy["fx_change"] == pytest.approx((fx["2026-07-01"] / fx["2025-07-01"] - 1) * 100)
    sugar = next(row for row in yoy["rows"] if row["key"] == "sugar")
    assert sugar["usd"] == pytest.approx((prices["sugar"]["2026-07-01"] / prices["sugar"]["2025-07-01"] - 1) * 100)
    assert sugar["brl"] == pytest.approx(((1 + sugar["usd"] / 100) * fx["2026-07-01"] / fx["2025-07-01"] - 1) * 100)
    # the real appreciated, so every benchmark did worse in reais than in dollars
    assert yoy["fx_change"] < 0 and all(row["brl"] < row["usd"] for row in yoy["rows"])
    # the latest benchmarks agree with the figures on the page
    assert prices["sugar"]["2026-07-01"] == pytest.approx(thesis["evidence"]["sugar"]["value"], abs=0.01)
    assert prices["soybeans"]["2026-07-01"] == pytest.approx(thesis["evidence"]["soybeans"]["value"], abs=0.01)


def test_rule_geometry_by_hand(thesis) -> None:
    geometry, rules = thesis["study"]["rule_geometry"], thesis["rules"]
    p0, p1 = 5.2235, 4.9856
    for key, level in (("entry", rules["entry_below"]), ("exit", rules["exit_above"]), ("abandon", rules["abandon_above"]),
                       ("review_low", rules["review_low"]), ("review_high", rules["review_high"])):
        assert geometry["giveback"][key] == pytest.approx((level - p1) / (p0 - p1) * 100)
        assert geometry["distance_pct"][key] == pytest.approx((level / p1 - 1) * 100)
    assert 40 < geometry["giveback"]["entry"] < 55  # the entry level is now a test of keeping about half the move
    walk = geometry["random_walk"]["diffusion"]
    sd = math.sqrt(walk["daily_sd"] ** 2 * (geometry["sessions"] - 1) + geometry["runoff_rms"] ** 2)
    z = math.log(rules["entry_below"] / p1) * 100 / sd
    assert walk["below_entry"] == pytest.approx(0.5 * (1 + math.erf(z / math.sqrt(2))) * 100)
    assert geometry["random_walk"]["long_run"]["below_entry"] < walk["below_entry"]  # more volatility, less certainty
    assert walk["above_exit"] > walk["above_abandon"] > 0
    # root mean square of the six completed first post-runoff sessions
    moves = [w["runoff_session_move"] for w in thesis["study"]["elections"] if "runoff_session_move" in w]
    assert len(moves) == 6 and geometry["runoff_rms"] == pytest.approx(math.sqrt(sum(m * m for m in moves) / 6))
    assert geometry["sessions"] == thesis["evidence"]["volatility"]["horizon_sessions"]


def test_carry_to_volatility(thesis) -> None:
    ev, study_carry, vol = thesis["evidence"], thesis["study"]["carry"], thesis["study"]["volatility"]
    mid = (ev["fed_range"]["lower"] + ev["fed_range"]["upper"]) / 2
    annual = ((1 + ev["selic"]["value"] / 100) / (1 + mid / 100) - 1) * 100
    assert study_carry["annual"] == pytest.approx(annual)
    assert study_carry["to_vol_diffusion"] == pytest.approx(annual / (vol["diffusion_daily"] * math.sqrt(252)), rel=0.01)
    assert study_carry["to_vol_long_run"] < study_carry["to_vol_diffusion"]


def test_the_study_is_dated_and_forward_looking(thesis) -> None:
    assert date.fromisoformat(thesis["data_as_of"]) < date.fromisoformat(thesis["as_of"]) < date.fromisoformat(thesis["election"]["runoff"])
    assert thesis["study"]["elections"][-1]["year"] == 2026 and thesis["study"]["elections"][-1]["pending"]
