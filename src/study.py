"""The quantitative study behind the 6 October 2026 thesis.

Pure standard library, like the rest of the production code.  Every function
takes the frozen inputs saved by ``scripts/collect_study_inputs.py`` and returns
plain numbers, so ``tests/test_study.py`` can recompute each figure on the page
and ``scripts/build_study.py`` can write them to ``research/study_2026-10-06.json``.

Conventions: PTAX is the midpoint of the central bank's buying and selling
rates; returns are daily log returns in percent; zero rates are ANBIMA's
pre-fixed curve in % a year with vertices in business days (252 = one year).
"""
from __future__ import annotations

import math
import statistics
from datetime import date
from typing import Any

from src.thesis import survey_path_average

# First round and runoff of every presidential election since PTAX data start to
# cover a market that floats (2002 onward).  2026 is still in progress.
ELECTIONS: dict[int, tuple[str, str]] = {
    2002: ("2002-10-06", "2002-10-27"), 2006: ("2006-10-01", "2006-10-29"), 2010: ("2010-10-03", "2010-10-31"),
    2014: ("2014-10-05", "2014-10-26"), 2018: ("2018-10-07", "2018-10-28"), 2022: ("2022-10-02", "2022-10-30"),
    2026: ("2026-10-04", "2026-10-25"),
}
SURPRISE_Z = 2.0  # a first Monday counts as a surprise when it moves more than twice the usual daily range
VERTICES = ("21", "42", "63", "126", "252", "504", "756", "1008", "1260", "2520")
TRADING_DAYS = 252
COMMODITIES = ("brent", "soybeans", "iron_ore", "coffee", "sugar", "maize")


# ---------------------------------------------------------------------------
# Small numerical helpers (no numpy in production).


def _log_returns(closes: list[float]) -> list[float]:
    return [math.log(b / a) * 100 for a, b in zip(closes, closes[1:])]


def _normal_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _corr(a: list[float], b: list[float]) -> float:
    ma, mb = statistics.fmean(a), statistics.fmean(b)
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))


def _ols(y: list[float], x: list[float]) -> dict[str, float]:
    """Simple regression of y on x with an intercept: slope, its standard error, R², n."""

    mx, my = statistics.fmean(x), statistics.fmean(y)
    sxx = sum((a - mx) ** 2 for a in x)
    slope = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx
    intercept = my - slope * mx
    residuals = [c - (intercept + slope * a) for a, c in zip(x, y)]
    sse = sum(r * r for r in residuals)
    return {
        "slope": slope, "intercept": intercept, "se": math.sqrt(sse / (len(x) - 2) / sxx),
        "r2": 1 - sse / sum((c - my) ** 2 for c in y), "n": len(x),
    }


def ptax_closes(inputs: dict[str, Any]) -> tuple[list[str], list[float]]:
    rows = sorted((str(d), float(v)) for d, v in inputs["ptax"])
    return [d for d, _ in rows], [v for _, v in rows]


# ---------------------------------------------------------------------------
# 1. Event study: the first Monday after each first round, and what followed.


def election_windows(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    """Per election: the four closes that matter, the first-Monday move in plain and
    volatility-scaled terms, the giveback by the runoff, and the first post-runoff session.

    ``giveback`` is 100 when the real is back at its pre-vote level and negative when the
    move was extended; it is only defined for surprise-sized Mondays (|z| above 2).
    """

    dates, closes = ptax_closes(inputs)
    position = {d: i for i, d in enumerate(dates)}

    def last_before(day: str) -> int:
        return max(i for i, d in enumerate(dates) if d < day)

    def first_after(day: str) -> int:
        return min(i for i, d in enumerate(dates) if d > day)

    out = []
    for year, (first_round, runoff) in ELECTIONS.items():
        i0, i1 = last_before(first_round), first_after(first_round)
        p0, p1 = closes[i0], closes[i1]
        daily = _log_returns(closes[i0 - 20:i0 + 1])
        sd = statistics.stdev(daily)
        move = (p1 / p0 - 1) * 100
        z = math.log(p1 / p0) * 100 / sd
        item: dict[str, Any] = {
            "year": year, "first_round": first_round, "runoff": runoff,
            "friday_before": [dates[i0], p0], "monday_after": [dates[i1], p1],
            "monday_move": move, "daily_sd": sd, "z": z, "surprise": abs(z) > SURPRISE_Z,
        }
        if year < 2026:
            ir, ia = last_before(runoff), first_after(runoff)
            pr, pa = closes[ir], closes[ia]
            item.update({
                "friday_before_runoff": [dates[ir], pr], "first_after_runoff": [dates[ia], pa],
                "runoff_session_move": (pa / pr - 1) * 100,
                "giveback_runoff_friday": (pr - p1) / (p0 - p1) * 100 if abs(z) > SURPRISE_Z else None,
                "giveback_first_close": (pa - p1) / (p0 - p1) * 100 if abs(z) > SURPRISE_Z else None,
                "path": [[k, round(closes[i0 + k] / p0 * 100, 3)] for k in range(0, ir - i0 + 1)],
            })
        else:
            last = len(closes) - 1
            item.update({"pending": True, "path": [[k, round(closes[i0 + k] / p0 * 100, 3)] for k in range(0, last - i0 + 1)]})
        out.append(item)
    return out


def runoff_session_rms(windows: list[dict[str, Any]]) -> float:
    """Root-mean-square move of the first PTAX after each completed runoff, in percent."""

    moves = [w["runoff_session_move"] for w in windows if "runoff_session_move" in w]
    return math.sqrt(sum(m * m for m in moves) / len(moves))


# ---------------------------------------------------------------------------
# 2. Volatility: diffusion and jump.


def volatility(inputs: dict[str, Any], sessions: int = 20) -> dict[str, float]:
    """Realised volatility of PTAX around the 5 October jump.

    ``diffusion`` is the 20 sessions before the jump (what the 5 October note used);
    ``with_jump`` includes it; ``bipower`` is the jump-robust estimator
    (pi/2 times the mean product of adjacent absolute returns), which a single
    outsized day barely moves; ``long_run`` is the sample standard deviation since 2003.
    """

    dates, closes = ptax_closes(inputs)
    returns = _log_returns(closes)
    event = returns[-1]
    before, window = returns[-sessions - 1:-1], returns[-sessions:]
    ann = math.sqrt(TRADING_DAYS)
    rv = math.sqrt(statistics.fmean(r * r for r in window))
    bipower = math.sqrt(math.pi / 2 * statistics.fmean(abs(a) * abs(b) for a, b in zip(window, window[1:])))
    first_2003 = next(i for i, d in enumerate(dates[1:]) if d >= "2003-01-01")
    long_run = statistics.stdev(returns[first_2003:])
    ewma = statistics.pvariance(returns[:60])
    for r in returns[:-1]:
        ewma = 0.94 * ewma + 0.06 * r * r
    diffusion = statistics.stdev(before)
    return {
        "event_date": dates[-1], "event_return": event, "event_rank": sorted(returns).index(event) + 1, "observations": len(returns),
        "diffusion_daily": diffusion, "diffusion_annual": diffusion * ann, "event_z": event / diffusion,
        "with_jump_daily": rv, "with_jump_annual": rv * ann,
        "bipower_daily": bipower, "bipower_annual": bipower * ann,
        "jump_share": max(0.0, 1 - bipower ** 2 / rv ** 2) * 100,
        "ewma_diffusion_daily": math.sqrt(ewma), "long_run_daily": long_run, "long_run_annual": long_run * ann,
    }


# ---------------------------------------------------------------------------
# 3. The curve.


def _zero(curve: dict[str, Any], vertex: str) -> float:
    return float(curve["fixed_rate"][vertex])


def forward(curve: dict[str, Any], start: str, end: str) -> float:
    """Forward rate between two vertices (business days) implied by the zero curve, in %."""

    a, b = int(start), int(end)
    za, zb = _zero(curve, start) / 100, _zero(curve, end) / 100
    growth = (1 + zb) ** (b / TRADING_DAYS) / (1 + za) ** (a / TRADING_DAYS)
    return (growth ** (TRADING_DAYS / (b - a)) - 1) * 100


def curve_shift(inputs: dict[str, Any], before: str, after: str) -> dict[str, Any]:
    ettj = inputs["anbima_ettj"]
    a, b = ettj[before], ettj[after]
    vertices = [v for v in VERTICES if v in a["fixed_rate"] and v in b["fixed_rate"]]
    rows = [{"vertex": v, "years": int(v) / TRADING_DAYS, "before": _zero(a, v), "after": _zero(b, v),
             "change_bp": (_zero(b, v) - _zero(a, v)) * 100} for v in vertices]
    be_a, be_b = a["implied_inflation"]["504"], b["implied_inflation"]["504"]
    real_a, real_b = a["real_rate"]["504"], b["real_rate"]["504"]
    d_be, d_real = (be_b - be_a) * 100, (real_b - real_a) * 100
    return {
        "before": before, "after": after, "rows": rows,
        "forward_1y1y": {"before": forward(a, "252", "504"), "after": forward(b, "252", "504")},
        "breakeven_1y": {"before": a["implied_inflation"]["252"], "after": b["implied_inflation"]["252"]},
        "breakeven_2y": {"before": be_a, "after": be_b},
        "real_2y": {"before": real_a, "after": real_b},
        "two_year_change_bp": (_zero(b, "504") - _zero(a, "504")) * 100,
        "breakeven_share": d_be / (d_be + d_real) * 100,
        "history_2y": [[d, ettj[d]["fixed_rate"]["504"]] for d in sorted(ettj)],
        "history_1y": [[d, ettj[d]["fixed_rate"]["252"]] for d in sorted(ettj)],
    }


def survey_gap(focus_selic: dict[str, float], selic_now: float, start: date, curve_after: dict[str, Any], curve_before: dict[str, Any]) -> dict[str, float]:
    """Market zero rates minus the rate implied by the economists' own Selic path (Focus)."""

    medians = {int(year): value for year, value in focus_selic.items() if year.isdigit()}
    one, two = (survey_path_average(selic_now, medians, start, years) for years in (1, 2))
    survey_forward = ((1 + two / 100) ** 2 / (1 + one / 100) - 1) * 100  # the economists' own second-year average
    return {
        "survey_1y": one, "survey_2y": two, "survey_fwd_1y1y": survey_forward,
        "gap_fwd_before": forward(curve_before, "252", "504") - survey_forward, "gap_fwd_after": forward(curve_after, "252", "504") - survey_forward,
        "gap_1y_before": _zero(curve_before, "252") - one, "gap_2y_before": _zero(curve_before, "504") - two,
        "gap_1y_after": _zero(curve_after, "252") - one, "gap_2y_after": _zero(curve_after, "504") - two,
    }


# ---------------------------------------------------------------------------
# 4. Commodities and the real (monthly, 2005 to July 2026).


def _monthly_fx(inputs: dict[str, Any]) -> dict[str, float]:
    by_month: dict[str, list[float]] = {}
    for day, value in inputs["ptax"]:
        by_month.setdefault(str(day)[:7] + "-01", []).append(float(value))
    return {month: statistics.fmean(values) for month, values in by_month.items()}


def export_weights(inputs: dict[str, Any]) -> dict[str, dict[str, float]]:
    exports = inputs["exports"]
    share = {key: exports["usd"][key] / exports["total_usd"] * 100 for key in COMMODITIES}
    total = sum(share.values())
    return {"share_of_exports": share, "relative": {key: value / total * 100 for key, value in share.items()}, "covered": total}


def _aligned(inputs: dict[str, Any], start: str = "2005-01-01") -> tuple[list[str], dict[str, dict[str, float]], dict[str, float]]:
    prices = {key: {str(d): float(v) for d, v in inputs["commodities_monthly"][key]} for key in COMMODITIES}
    fx = _monthly_fx(inputs)
    months = sorted(set.intersection(*(set(series) for series in prices.values())) & set(fx))
    return [m for m in months if m >= start], prices, fx


def basket_vs_real(inputs: dict[str, Any]) -> dict[str, Any]:
    months, prices, fx = _aligned(inputs)
    weights = export_weights(inputs)["relative"]
    returns = {key: [math.log(prices[key][b] / prices[key][a]) for a, b in zip(months, months[1:])] for key in COMMODITIES}
    fx_returns = [math.log(fx[b] / fx[a]) for a, b in zip(months, months[1:])]
    basket = [sum(weights[key] / 100 * returns[key][i] for key in COMMODITIES) for i in range(len(fx_returns))]
    full = _ols(fx_returns, basket)

    def sub(first: str, last: str) -> dict[str, float]:
        idx = [i for i, month in enumerate(months[1:]) if first <= month[:4] <= last]
        return _ols([fx_returns[i] for i in idx], [basket[i] for i in idx])

    return {
        "months": [months[0][:7], months[-1][:7]], "slope": full["slope"], "intercept": full["intercept"], "se": full["se"], "r2": full["r2"], "n": full["n"],
        "corr": _corr(fx_returns, basket), "early": sub("2005", "2014"), "late": sub("2015", "2026"),
        "scatter": [[round(x * 100, 2), round(y * 100, 2)] for x, y in zip(basket, fx_returns)],
    }


def natural_hedge(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    """Volatility of each benchmark in dollars and in reais, and how it co-moves with USD/BRL."""

    months, prices, fx = _aligned(inputs)
    fx_returns = [math.log(fx[b] / fx[a]) for a, b in zip(months, months[1:])]
    out = []
    for key in COMMODITIES:
        usd = [math.log(prices[key][b] / prices[key][a]) for a, b in zip(months, months[1:])]
        brl = [u + f for u, f in zip(usd, fx_returns)]
        vu, vb = statistics.stdev(usd) * math.sqrt(12) * 100, statistics.stdev(brl) * math.sqrt(12) * 100
        out.append({"key": key, "vol_usd": vu, "vol_brl": vb, "corr_fx": _corr(usd, fx_returns), "hedge": (1 - vb / vu) * 100})
    return out


def year_on_year(inputs: dict[str, Any], latest: str = "2026-07-01", base: str = "2025-07-01") -> dict[str, Any]:
    """What a producer saw over twelve months: the same benchmark in dollars and in reais."""

    _, prices, fx = _aligned(inputs)
    rows = []
    for key in COMMODITIES:
        usd = (prices[key][latest] / prices[key][base] - 1) * 100
        brl = (prices[key][latest] * fx[latest] / (prices[key][base] * fx[base]) - 1) * 100
        rows.append({"key": key, "usd": usd, "brl": brl})
    return {"latest": latest, "base": base, "fx_base": fx[base], "fx_latest": fx[latest], "fx_change": (fx[latest] / fx[base] - 1) * 100, "rows": rows}


# ---------------------------------------------------------------------------
# 5. The rule, restated in the units of the first Monday.


def rule_geometry(p0: float, p1: float, rules: dict[str, Any], diffusion_daily: float, long_run_daily: float,
                  runoff_rms: float, sessions_to_runoff_close: int = 14) -> dict[str, Any]:
    """Express the pre-committed levels as a giveback of Monday's move, and compare them with a random walk.

    ``p0`` is the last close before the first round, ``p1`` the first Monday's close.  The random-walk
    benchmark has zero drift, diffusion volatility for every session but the first one after the runoff,
    and that session's variance taken from past runoffs (``runoff_rms``).  It is a benchmark, not a forecast.
    """

    def giveback(level: float) -> float:
        return (level - p1) / (p0 - p1) * 100

    def share_below(level: float, daily: float) -> float:
        variance = daily ** 2 * (sessions_to_runoff_close - 1) + runoff_rms ** 2
        return _normal_cdf(math.log(level / p1) * 100 / math.sqrt(variance)) * 100

    levels = {"entry": rules["entry_below"], "exit": rules["exit_above"], "abandon": rules["abandon_above"],
              "review_low": rules["review_low"], "review_high": rules["review_high"]}
    benchmark = {}
    for label, daily in (("diffusion", diffusion_daily), ("long_run", long_run_daily)):
        benchmark[label] = {
            "daily_sd": daily,
            "below_entry": share_below(levels["entry"], daily),
            "above_exit": 100 - share_below(levels["exit"], daily),
            "above_abandon": 100 - share_below(levels["abandon"], daily),
        }
    entry_distance = (levels["entry"] / p1 - 1) * 100
    return {
        "p0": p0, "p1": p1, "move": (p1 / p0 - 1) * 100,
        "giveback": {key: giveback(value) for key, value in levels.items()},
        "distance_pct": {key: (value / p1 - 1) * 100 for key, value in levels.items()},
        "sessions": sessions_to_runoff_close, "runoff_rms": runoff_rms, "random_walk": benchmark,
        "entry_distance_pct": entry_distance,
    }


def carry_to_vol(carry_per_month: float, daily_sd: float) -> float:
    """Annualised carry (compounded) over annualised volatility."""

    return ((1 + carry_per_month / 100) ** 12 - 1) * 100 / (daily_sd * math.sqrt(TRADING_DAYS))


# ---------------------------------------------------------------------------


def build(inputs: dict[str, Any], thesis: dict[str, Any]) -> dict[str, Any]:
    """Every figure of the study, in one JSON-ready dictionary."""

    ev, rules = thesis["evidence"], thesis["rules"]
    windows = election_windows(inputs)
    vol = volatility(inputs)
    shift = curve_shift(inputs, "2026-10-02", "2026-10-05")
    ettj = inputs["anbima_ettj"]
    focus = {year: value for year, value in ev["focus_selic"].items() if year.isdigit()}
    gap = survey_gap(focus, ev["selic"]["value"], date.fromisoformat(thesis["as_of"]), ettj["2026-10-05"], ettj["2026-10-02"])
    current = next(w for w in windows if w["year"] == 2026)
    rms = runoff_session_rms(windows)
    geometry = rule_geometry(current["friday_before"][1], current["monday_after"][1], rules, vol["diffusion_daily"], vol["long_run_daily"], rms)
    fed_mid = (ev["fed_range"]["lower"] + ev["fed_range"]["upper"]) / 2
    carry = (1 + ev["selic"]["value"] / 100) / (1 + fed_mid / 100)
    return {
        "schema_version": 1,
        "inputs_file": thesis["study_inputs_file"],
        "elections": windows, "volatility": vol, "curve": shift, "survey_gap": gap,
        "basket": basket_vs_real(inputs), "weights": export_weights(inputs), "hedge": natural_hedge(inputs),
        "year_on_year": year_on_year(inputs), "rule_geometry": geometry,
        "carry": {"annual": (carry - 1) * 100, "to_vol_diffusion": carry_to_vol(ev["carry_per_month"]["value"], vol["diffusion_daily"]),
                  "to_vol_long_run": carry_to_vol(ev["carry_per_month"]["value"], vol["long_run_daily"])},
    }
