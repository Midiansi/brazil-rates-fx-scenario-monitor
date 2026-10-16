"""The 16 October publication, computed only from its frozen inputs."""
from __future__ import annotations

from typing import Any

from src import formatting as f


def build_update(snapshot: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    ptax = dict(snapshot['history']['ptax'])
    oil = dict(snapshot['history']['brent'])
    curves = snapshot['anbima_ettj']
    latest = snapshot['market_cutoff']
    p0, p1, spot = (ptax[d] for d in ('2026-10-02', '2026-10-05', latest))
    series = snapshot['series']
    selic = series['selic_target']['value']
    fed = series['fed_target_range']['midpoint']
    relative_growth = (1 + selic / 100) / (1 + fed / 100)
    monthly = relative_growth ** (1 / 12) - 1
    # Match the two series by date, rather than multiplying each feed's latest observation.
    oil_date = max(d for d in set(ptax) & set(oil) if d <= latest)
    oil_base = '2026-10-02'
    fx_shocks, commodity_shocks = (-0.05, 0.0, 0.05), (-0.10, 0.0, 0.10)
    result = {
        'schema_version': 1, 'id': '2026-10-16', 'as_of': '2026-10-16',
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
        'policy': {'selic': selic, 'fed_midpoint': fed,
                   'monthly_carry_pct': monthly * 100,
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
                'brl_change_pct': (oil[oil_date] * ptax[oil_date] / (oil[oil_base] * ptax[oil_base]) - 1) * 100},
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


def update_values(report: dict[str, Any], lang: str) -> dict[str, str]:
    p, policy, oil, rows = (report[k] for k in ('ptax', 'policy', 'oil', 'curve'))
    before, after = rows[1], rows[-1]
    n = lambda v, digits=2: f.num(v, digits, lang)
    pct = lambda v, digits=2: f.pct(v, digits, lang)
    return {
        'update_date': f.day(report['as_of'], lang, long=True),
        'cutoff': f.day(report['data_as_of'], lang, year=False, long=True),
        'u_ptax': n(p['value'], 4), 'u_giveback': pct(p['giveback_pct'], 0),
        'u_kept': pct(100 - p['giveback_pct'], 0), 'u_fx_rise': pct(p['since_first_day_pct']),
        'u_nominal': pct(after['nominal']), 'u_be': pct(after['breakeven']),
        'u_real': pct(after['real']), 'u_be_old': pct(before['breakeven']),
        'u_nominal_bp': n((after['nominal'] - before['nominal']) * 100, 0),
        'u_be_bp': n((after['breakeven'] - before['breakeven']) * 100, 0),
        'u_real_bp': n(abs(after['real'] - before['real']) * 100, 0),
        'u_carry': pct(policy['monthly_carry_pct']),
        'u_fx_breakeven': n(policy['one_month_fx_breakeven'], 4),
        'u_us2y': pct(policy['us2y']),
        'u_focus_ipca': pct(report['focus']['focus_ipca']['values']['2026']),
        'u_focus_ipca27': pct(report['focus']['focus_ipca']['values']['2027']),
        'u_focus_selic': pct(report['focus']['focus_selic']['values']['2026']),
        'u_focus_date': f.day(report['focus']['focus_selic']['date'], lang, year=False),
        'u_oil_date': f.day(oil['date'], lang, year=False),
        'u_oil_usd': pct(abs(oil['usd_change_pct']), 1),
        'u_oil_fx': pct(abs(oil['fx_change_pct']), 1),
        'u_oil_brl': pct(abs(oil['brl_change_pct']), 1),
        'u_offset': pct(report['producer']['offset_commodity_pct']),
    }
