"""The 27 October publication: the first session after the runoff, computed only from frozen inputs."""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any

from src import formatting as f
from src import risk

AS_OF = '2026-10-27'
FRIDAY = '2026-10-23'  # last session before the 25 October runoff
PRE_FIRST_ROUND, FIRST_DAY = '2026-10-02', '2026-10-05'
CDI_SPREAD = 0.10  # the CDI usually sits 0.10 pp below the Selic target, as in the 6 October study


def path_average(selic_now: float, year_end_medians: dict[int, float], start: date, end: date,
                 cdi_spread: float = CDI_SPREAD) -> float:
    """Annualised average CDI from ``start`` to ``end`` if the Selic follows the economists' path.

    Same convention as ``thesis.survey_path_average``: a straight line from today's
    target through the Focus year-end medians, daily compounding, over any horizon.
    """

    anchors = [(start, selic_now)] + sorted((date(year, 12, 31), value) for year, value in year_end_medians.items()
                                            if date(year, 12, 31) > start)

    def rate(day: date) -> float:
        for (d0, r0), (d1, r1) in zip(anchors, anchors[1:]):
            if d0 <= day <= d1:
                return r0 + (r1 - r0) * (day - d0).days / (d1 - d0).days
        return anchors[-1][1]

    days = (end - start).days
    log_growth = sum(math.log(1 + (rate(start + timedelta(days=i)) - cdi_spread) / 100) for i in range(days))
    return (math.exp(log_growth / days) - 1) * 100


def _daily_moves(ptax: dict[str, float]) -> list[tuple[str, float]]:
    days = sorted(ptax)
    return [(b, math.log(ptax[b] / ptax[a]) * 100) for a, b in zip(days, days[1:])]


def build_runoff(snapshot: dict[str, Any], study_inputs: dict[str, Any], baseline: dict[str, Any],
                 previous: dict[str, Any]) -> dict[str, Any]:
    """``baseline`` is the 6 October thesis (rules, fiscal and first-round facts); ``previous`` the 16 October note."""

    latest = snapshot['market_cutoff']
    series, press, election = snapshot['series'], snapshot['press'], snapshot['election']
    ptax = {d: v for d, v in snapshot['history']['ptax'] if d <= latest}
    us2y = {d: v for d, v in snapshot['history']['us_2y'] if d <= latest}
    # The long PTAX history comes from the frozen study inputs; later closes from this snapshot.
    full = {d: v for d, v in study_inputs['ptax']}
    full.update({d: v for d, v in ptax.items() if d > max(full)})
    fri, mon = ptax[FRIDAY], ptax[latest]
    move = (mon / fri - 1) * 100
    moves = _daily_moves(full)
    this = dict(moves)[latest]
    larger = [(d, m) for d, m in moves if m > this]

    selic, fed = series['selic_target']['value'], series['fed_target_range']['midpoint']
    monthly_carry = (((1 + selic / 100) / (1 + fed / 100)) ** (1 / 12) - 1) * 100
    # The site's own one-day 99% VaR models, fed only with closes up to the Friday before the vote.
    var = risk.build({'ptax': sorted((d, v) for d, v in full.items() if d <= FRIDAY)})['latest']
    loss = risk.spot_loss(fri, mon)

    votes = election['runoff']['votes']
    total = sum(votes.values())
    first = baseline['evidence']['election_first_round']

    focus = {key: series[key]['values_by_reference_year'] for key in ('focus_selic', 'focus_ipca', 'focus_fx')}
    medians = {int(y): v for y, v in focus['focus_selic'].items()}
    di = press['di_futures']
    jan28, jan27 = di['jan28'], di['jan27']
    end28, end27 = date.fromisoformat(jan28['maturity']), date.fromisoformat(jan27['maturity'])
    path_fri = path_average(selic, medians, date.fromisoformat(FRIDAY), end28)
    path_mon = path_average(selic, medians, date.fromisoformat(latest), end28)
    path_27 = path_average(selic, medians, date.fromisoformat(latest), end27)

    ibov = press['ibovespa']
    spot = press['spot_usd_brl']
    fiscal = baseline['evidence']['fiscal_2027']
    rules = baseline['rules']
    brent = snapshot['commodities']['brent']
    first_round_move = (ptax[FIRST_DAY] / ptax[PRE_FIRST_ROUND] - 1) * 100
    old = previous['policy']
    return {
        'schema_version': 1, 'id': AS_OF, 'as_of': AS_OF, 'data_as_of': latest, 'status': 'no_position',
        'inputs_file': 'research/thesis_snapshot_2026-10-27.json',
        'history_file': 'research/study_inputs_2026-10-06.json',
        'previous_file': 'research/update_2026-10-16.json',
        'baseline_file': 'research/thesis_2026-10-06.json',
        'election': {'date': election['runoff']['date'], 'votes': votes,
                     'lula_pct': votes['lula'] / total * 100, 'flavio_pct': votes['flavio'] / total * 100,
                     'margin_pts': (votes['lula'] - votes['flavio']) / total * 100,
                     'margin_votes': votes['lula'] - votes['flavio'],
                     'first_round': {'flavio_pct': first['flavio'], 'lula_pct': first['lula'],
                                     'reporting_pct': first['reporting_pct']},
                     'final_poll': election['final_poll']},
        'fx': {'friday': fri, 'monday': mon, 'friday_date': FRIDAY, 'date': latest,
               'move_pct': move, 'log_move_pct': this,
               'rank_since': moves[0][0][:4], 'rank': len(larger) + 1, 'larger': [d for d, _ in larger],
               'pre_first_round': ptax[PRE_FIRST_ROUND], 'first_day': ptax[FIRST_DAY],
               'first_round_move_pct': first_round_move,
               'friday_vs_pre_first_pct': (fri / ptax[PRE_FIRST_ROUND] - 1) * 100,
               'monday_vs_pre_first_pct': (mon / ptax[PRE_FIRST_ROUND] - 1) * 100,
               'asymmetry': abs(move / first_round_move),
               'spot_close': spot[latest]['close'], 'spot_change_pct': spot[latest]['change_pct'],
               'spot_intraday_above': spot[latest]['intraday_high_above'],
               'next_day_ptax': (spot['2026-10-27']['ptax_buy'] + spot['2026-10-27']['ptax_sell']) / 2},
        'carry': {'selic': selic, 'fed_midpoint': fed, 'monthly_pct': monthly_carry,
                  'months_lost': move / monthly_carry,
                  'first_round_months': old['event_carry_months']},
        'risk': {'loss_pct': loss, 'var_date': var['as_of'],
                 'var_pct': {key: model['var_pct'] for key, model in var['models'].items()},
                 'min_ratio': loss / max(m['var_pct'] for m in var['models'].values()),
                 'max_ratio': loss / min(m['var_pct'] for m in var['models'].values())},
        'us2y': {'friday': us2y[FRIDAY], 'monday': us2y[latest], 'change_bp': (us2y[latest] - us2y[FRIDAY]) * 100},
        'rates': {'jan28_friday': jan28[FRIDAY], 'jan28_monday': jan28[latest],
                  'jan28_change_bp': (jan28[latest] - jan28[FRIDAY]) * 100,
                  'jan27_monday': jan27[latest], 'jan29_monday': di['jan29'][latest], 'jan31_monday': di['jan31'][latest],
                  'cdi': selic - CDI_SPREAD,
                  'path_jan28_friday': path_fri, 'path_jan28_monday': path_mon, 'path_jan27_monday': path_27,
                  'gap_jan28_friday': jan28[FRIDAY] - path_fri, 'gap_jan28_monday': jan28[latest] - path_mon,
                  'cuts_expected_2026_bp': (selic - medians[2026]) * 100},
        'equity': {'friday': ibov[FRIDAY], 'monday': ibov[latest], 'change_pct': (ibov[latest] / ibov[FRIDAY] - 1) * 100,
                   'circuit_breaker': ibov['circuit_breaker']},
        'focus': {'date': series['focus_selic']['latest_observation_date'], 'selic': focus['focus_selic'],
                  'ipca': focus['focus_ipca'], 'fx': focus['focus_fx'], 'ipca_ceiling': 4.5, 'ipca_target': 3.0},
        'fiscal': {'government_2027': fiscal['government'], 'ifi_2027': fiscal['ifi'], 'date': fiscal['date']},
        'exporters': {'brl_per_usd_change_pct': move, 'brent_date': brent['latest_date'], 'brent': brent['latest']},
        'previous_view': {'kept_pct': 100 - previous['ptax']['giveback_pct'],
                          'breakeven_before': previous['curve'][1]['breakeven'],
                          'breakeven_after': previous['curve'][-1]['breakeven']},
        'rule': {'date': latest, 'value': mon, 'abandon_above': rules['abandon_above'],
                 'earliest_entry': rules['earliest_entry'],
                 'state': 'abandoned' if mon > rules['abandon_above'] else 'open'},
        'calendar': [{'date': '2026-10-28', 'event': 'fomc'}, {'date': '2026-11-04', 'event': 'copom'},
                     {'date': '2026-12-09', 'event': 'both'}],
        'sources': [
            {'key': 'tse', **election['runoff']['source']},
            {'key': 'ptax', 'label': 'BCB · PTAX', 'date': latest, 'url': series['ptax_usd_brl_midpoint']['source_url']},
            {'key': 'treasury', 'label': 'U.S. Treasury · Par yields', 'date': latest,
             'url': series['us_2_year_treasury']['source_url']},
            {'key': 'focus', 'label': 'BCB · Focus', 'date': series['focus_selic']['latest_observation_date'],
             'url': series['focus_selic']['source_url']},
            {'key': 'selic', 'label': 'BCB · Selic target', 'date': series['selic_target']['effective_since'],
             'url': series['selic_target']['source_url']},
            {'key': 'ifi', 'label': 'Senate IFI · 2027 budget', 'date': fiscal['date'],
             'url': baseline['sources']['ifi_ploa2027']['url']},
            *({'key': key, **source} for key in ('di_futures', 'ibovespa', 'spot_usd_brl', 'treasury_auctions', 'central_bank')
              for source in press[{'treasury_auctions': 'treasury'}.get(key, key)]['sources']),
            {'key': 'poll', **election['final_poll']['source']},
            {'key': 'calendar', 'label': 'BCB · Copom calendar', 'date': AS_OF, 'url': baseline['sources']['copom_calendar']['url']},
        ],
    }


def runoff_values(report: dict[str, Any], lang: str) -> dict[str, str]:
    fx, carry, rk, us, rates, eq = (report[k] for k in ('fx', 'carry', 'risk', 'us2y', 'rates', 'equity'))
    vote, focus, fiscal, prev = report['election'], report['focus'], report['fiscal'], report['previous_view']
    n = lambda v, digits=2: f.num(v, digits, lang)
    pct = lambda v, digits=2: f.pct(v, digits, lang)
    signed = lambda v, digits=1: f.pct(v, digits, lang, signed=True)
    bp = lambda v: f.num(v, 0, lang, signed=True)
    var = sorted(rk['var_pct'].values())
    return {
        'r_date': f.day(report['as_of'], lang, long=True),
        'r_cutoff': f.day(report['data_as_of'], lang, year=False, long=True),
        'r_vote_day': f.day(vote['date'], lang, year=False, long=True),
        'r_friday': f.day(fx['friday_date'], lang, year=False),
        'r_monday': f.day(fx['date'], lang, year=False),
        'r_lula': pct(vote['lula_pct']), 'r_flavio': pct(vote['flavio_pct']),
        'r_fr_flavio': pct(vote['first_round']['flavio_pct'], 1), 'r_fr_lula': pct(vote['first_round']['lula_pct'], 1),
        'r_poll': str(vote['final_poll']['valid_votes']['lula']),
        'r_ptax_fri': n(fx['friday'], 4), 'r_ptax': n(fx['monday'], 4), 'r_move': signed(fx['move_pct']),
        'r_move_abs': pct(fx['move_pct'], 1),
        'r_rank_since': fx['rank_since'], 'r_larger': f.day(fx['larger'][0], lang, long=True) if fx['larger'] else '',
        'r_pre_first': n(fx['pre_first_round'], 4), 'r_vs_pre_first': pct(fx['monday_vs_pre_first_pct'], 1),
        'r_fri_vs_pre_first': pct(abs(fx['friday_vs_pre_first_pct']), 1),
        'r_first_move': pct(abs(fx['first_round_move_pct']), 1),
        'r_first_day': n(fx['first_day'], 2),
        'r_spot_close': n(fx['spot_close'], 4), 'r_spot_move': signed(fx['spot_change_pct']),
        'r_spot_high': n(fx['spot_intraday_above'], 2), 'r_next_ptax': n(fx['next_day_ptax'], 2),
        'r_next_day': f.day(report['as_of'], lang, year=False, long=True),
        'r_carry': pct(carry['monthly_pct']), 'r_months': n(carry['months_lost'], 0),
        'r_first_months': n(carry['first_round_months'], 0),
        'r_loss': pct(rk['loss_pct'], 1), 'r_var_low': pct(var[0], 1), 'r_var_high': pct(var[-1], 1),
        'r_ratio_low': n(math.floor(rk['min_ratio']), 0), 'r_ratio_high': n(math.floor(rk['max_ratio']), 0),
        'r_us_fri': pct(us['friday']), 'r_us': pct(us['monday']), 'r_us_bp': bp(us['change_bp']),
        'r_di28_fri': pct(rates['jan28_friday']), 'r_di28': pct(rates['jan28_monday']), 'r_di28_bp': bp(rates['jan28_change_bp']),
        'r_di28_pp': f.pp(rates['jan28_change_bp'] / 100, 2, lang, signed=True),
        'r_di27': pct(rates['jan27_monday']), 'r_di29': pct(rates['jan29_monday']), 'r_di31': pct(rates['jan31_monday']),
        'r_cdi': pct(rates['cdi']), 'r_path28': pct(rates['path_jan28_monday'], 1), 'r_path27': pct(rates['path_jan27_monday'], 1),
        'r_gap_fri': f.pp(rates['gap_jan28_friday'], 1, lang), 'r_gap_mon': f.pp(rates['gap_jan28_monday'], 1, lang),
        'r_cuts': n(rates['cuts_expected_2026_bp'], 0),
        'r_selic': pct(carry['selic']), 'r_selic26': pct(float(focus['selic']['2026'])),
        'r_selic27': pct(float(focus['selic']['2027'])),
        'r_ibov_fri': n(eq['friday'], 0), 'r_ibov': n(eq['monday'], 0), 'r_ibov_move': signed(eq['change_pct']),
        'r_focus_date': f.day(focus['date'], lang, year=False),
        'r_ipca26': pct(float(focus['ipca']['2026']), 1), 'r_ipca27': pct(float(focus['ipca']['2027']), 1),
        'r_ceiling': pct(focus['ipca_ceiling'], 1), 'r_target': pct(focus['ipca_target'], 0),
        'r_fiscal_gov': f.brl_bn(fiscal['government_2027'], lang), 'r_fiscal_ifi': f.brl_bn(fiscal['ifi_2027'], lang),
        'r_brent_date': f.day(report['exporters']['brent_date'], lang, year=False, long=True),
        'r_kept': pct(prev['kept_pct'], 0), 'r_be_before': pct(prev['breakeven_before']), 'r_be_after': pct(prev['breakeven_after']),
        'r_abandon': n(report['rule']['abandon_above'], 2),
        'r_fomc': f.day(report['calendar'][0]['date'], lang, year=False, long=True),
        'r_copom': f.day(report['calendar'][1]['date'], lang, year=False, long=True),
        'r_december': f.day(report['calendar'][2]['date'], lang, year=False, long=True),
    }
