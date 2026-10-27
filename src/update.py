"""The 16 October publication, computed only from its frozen inputs.

Archived: the current note is ``src.runoff``. This builder still reproduces
``research/update_2026-10-16.json``, which the 27 October scorecard reads.
"""
from __future__ import annotations

import math
import statistics
from datetime import date
from typing import Any

from src.thesis import survey_path_average

TRADING_DAYS = 252
BREAKEVEN_TENORS = (252, 1512)  # one to six years, in ANBIMA business days


def _forward(curve: dict[str, float], start: int, end: int) -> float:
    """Forward rate between two vertices of an ANBIMA zero curve, in %."""

    growth = (1 + curve[str(end)] / 100) ** (end / TRADING_DAYS) / (1 + curve[str(start)] / 100) ** (start / TRADING_DAYS)
    return (growth ** (TRADING_DAYS / (end - start)) - 1) * 100


def _brl_move(oil: dict[str, float], ptax: dict[str, float], base: str, end: str) -> dict[str, Any]:
    return {'date': base,
            'usd_change_pct': (oil[end] / oil[base] - 1) * 100,
            'fx_change_pct': (ptax[end] / ptax[base] - 1) * 100,
            'brl_change_pct': (oil[end] * ptax[end] / (oil[base] * ptax[base]) - 1) * 100}


def build_update(snapshot: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    """``baseline`` is the 6 October thesis this publication reviews; its rules and survey are not altered."""

    rules, before = baseline['rules'], baseline['evidence']
    ptax = dict(snapshot['history']['ptax'])
    oil = dict(snapshot['history']['brent'])
    curves = snapshot['anbima_ettj']
    latest = snapshot['market_cutoff']
    as_of = '2026-10-16'
    p0, p1, spot = (ptax[d] for d in ('2026-10-02', '2026-10-05', latest))
    series = snapshot['series']
    selic = series['selic_target']['value']
    fed = series['fed_target_range']['midpoint']
    relative_growth = (1 + selic / 100) / (1 + fed / 100)
    monthly = relative_growth ** (1 / 12) - 1
    # Match the two series by date, rather than multiplying each feed's latest observation.
    common = sorted(d for d in set(ptax) & set(oil) if d <= latest)
    oil_date = common[-1]
    oil_base = '2026-10-02'
    fx_shocks, commodity_shocks = (-0.05, 0.0, 0.05), (-0.10, 0.0, 0.10)
    # Volatility of the 20 sessions to the pre-vote close, as in the 6 October study.
    dates = sorted(ptax)
    window = dates[dates.index(oil_base) - 20:dates.index(oil_base) + 1]
    returns = [math.log(ptax[b] / ptax[a]) for a, b in zip(window, window[1:])]
    prevote_vol = statistics.stdev(returns) * math.sqrt(TRADING_DAYS) * 100
    event_move = (p1 / p0 - 1) * 100
    # Breakevens across the curve, and the two-to-five-year forward, first post-vote session to cutoff.
    inflation = {d: curves[d]['implied_inflation'] for d in ('2026-10-05', latest)}
    shifts = [(inflation[latest][t] - inflation['2026-10-05'][t]) * 100
              for t in inflation[latest] if BREAKEVEN_TENORS[0] <= int(t) <= BREAKEVEN_TENORS[1]]
    fwd_before, fwd_after = (_forward(inflation[d], 504, 1260) for d in ('2026-10-05', latest))
    # Two-year zero rate minus the economists' Selic path, measured as in the 6 October study.
    medians_before = {int(y): v for y, v in before['focus_selic'].items() if y.isdigit()}
    medians_after = {int(y): v for y, v in series['focus_selic']['values_by_reference_year'].items()}
    path_before = survey_path_average(before['selic']['value'], medians_before, date.fromisoformat(baseline['as_of']), 2)
    path_after = survey_path_average(selic, medians_after, date.fromisoformat(as_of), 2)
    jump_from = common[common.index(oil_base) - 1]
    result = {
        'schema_version': 1, 'id': as_of, 'as_of': as_of,
        'data_as_of': latest, 'status': 'no_position',
        'inputs_file': 'research/thesis_snapshot_2026-10-16.json',
        'previous_file': 'research/thesis_2026-10-06.json',
        'historical_study_date': '2026-10-06',
        'rules': rules,
        'ptax': {'date': latest, 'value': spot, 'pre_vote': p0, 'first_day': p1,
                 'giveback_pct': (spot - p1) / (p0 - p1) * 100,
                 'since_first_day_pct': (spot / p1 - 1) * 100},
        'curve': [{'date': d, 'nominal': curves[d]['fixed_rate']['504'],
                   'breakeven': curves[d]['implied_inflation']['504'],
                   'real': curves[d]['real_rate']['504']} for d in sorted(curves)],
        'breakevens': {'from': '2026-10-05', 'to': latest, 'tenors': list(BREAKEVEN_TENORS),
                       'min_change_bp': min(shifts), 'max_change_bp': max(shifts),
                       'forward_2y5y_before': fwd_before, 'forward_2y5y_after': fwd_after,
                       'forward_2y5y_change_bp': (fwd_after - fwd_before) * 100},
        'survey': {'previous_date': before['focus_ipca']['date'],
                   'ipca_2026': [before['focus_ipca']['2026'], series['focus_ipca']['values_by_reference_year']['2026']],
                   'ipca_2027': [before['focus_ipca']['2027'], series['focus_ipca']['values_by_reference_year']['2027']],
                   'selic_2026': [before['focus_selic']['2026'], medians_after[2026]],
                   'path_2y': [path_before, path_after],
                   'gap_2y': [curves['2026-10-05']['fixed_rate']['504'] - path_before,
                              curves[latest]['fixed_rate']['504'] - path_after]},
        'policy': {'selic': selic, 'fed_midpoint': fed,
                   'monthly_carry_pct': monthly * 100,
                   'annual_carry_pct': (relative_growth - 1) * 100,
                   'prevote_vol_pct': prevote_vol,
                   'carry_to_vol': (relative_growth - 1) * 100 / prevote_vol,
                   'event_move_pct': event_move,
                   'event_carry_months': abs(event_move) / (monthly * 100),
                   'one_month_fx_breakeven': spot * (1 + monthly),
                   'us2y': series['us_2_year_treasury']['value'],
                   'us2y_date': series['us_2_year_treasury']['latest_observation_date']},
        'focus': {key: {'date': series[key]['latest_observation_date'],
                        'values': series[key]['values_by_reference_year']}
                  for key in ('focus_selic', 'focus_ipca', 'focus_fx')},
        'oil': {'date': oil_date, 'base_date': oil_base,
                'usd_now': oil[oil_date], 'usd_base': oil[oil_base],
                'fx_now': ptax[oil_date], 'fx_base': ptax[oil_base],
                'usd_change_pct': (oil[oil_date] / oil[oil_base] - 1) * 100,
                'fx_change_pct': (ptax[oil_date] / ptax[oil_base] - 1) * 100,
                'brl_change_pct': (oil[oil_date] * ptax[oil_date] / (oil[oil_base] * ptax[oil_base]) - 1) * 100,
                # One spot print moves the answer: show the day before, the pre-vote close and the first post-vote session.
                'jump_date': oil_base, 'jump_pct': (oil[oil_base] / oil[jump_from] - 1) * 100,
                'bases': [_brl_move(oil, ptax, base, oil_date) for base in (jump_from, oil_base, '2026-10-05')]},
        'producer': {'commodity_shocks': list(commodity_shocks), 'fx_shocks': list(fx_shocks),
                     'revenue_change_pct': [[((1 + c) * (1 + x) - 1) * 100 for x in fx_shocks] for c in commodity_shocks],
                     'offset_commodity_pct': (1 / (1 - 0.05) - 1) * 100},
        'sources': [
            {'key': 'ptax', 'label': 'BCB · PTAX midpoint', 'date': latest,
             'url': series['ptax_usd_brl_midpoint']['source_url']},
            {'key': 'curve', 'label': 'ANBIMA · ETTJ, 2 / 5 / 15 Oct', 'date': latest,
             'url': 'https://www.anbima.com.br/informacoes/est-termo/CZ.asp'},
            {'key': 'focus', 'label': 'BCB · Focus survey', 'date': series['focus_selic']['latest_observation_date'],
             'url': series['focus_selic']['source_url']},
            {'key': 'treasury', 'label': 'U.S. Treasury · Par yields', 'date': series['us_2_year_treasury']['latest_observation_date'],
             'url': series['us_2_year_treasury']['source_url']},
            {'key': 'oil', 'label': 'EIA / FRED · Brent spot', 'date': oil_date,
             'url': snapshot['commodities']['brent']['source_url']},
            {'key': 'selic', 'label': 'BCB · Selic target', 'date': '2026-09-17',
             'url': series['selic_target']['source_url']},
            {'key': 'policy', 'label': 'New York Fed · EFFR and target range', 'date': '2026-10-14',
             'url': 'https://www.newyorkfed.org/markets/reference-rates/effr'},
            {'key': 'runoff', 'label': 'TSE · Election calendar', 'date': '2026-10-16',
             'url': 'https://www.tse.jus.br/eleicoes/eleicoes-2026/calendario-eleitoral'},
            {'key': 'fomc', 'label': 'Federal Reserve · FOMC calendar', 'date': '2026-10-16',
             'url': 'https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm'},
            {'key': 'copom', 'label': 'BCB · Copom calendar', 'date': '2026-10-16',
             'url': 'https://www.bcb.gov.br/detalhenoticia/20739/nota'},
        ],
    }
    return result

