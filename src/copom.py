"""The 5 November publication: the first note after the Copom, computed only from frozen inputs.

Everything here is arithmetic on ``research/thesis_snapshot_2026-11-05.json`` and earlier
saved reports, so the note reproduces offline and later prices cannot change it.
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any

from src import formatting as f

AS_OF = '2026-11-05'
BEFORE_VOTE, AFTER_VOTE = '2026-10-23', '2026-10-26'
FIRST_ROUND = '2026-10-05'
CDI_SPREAD = 0.10  # the CDI usually sits 0.10 pp below the Selic target, as in the earlier notes
MID_2027 = date(2027, 6, 30)

# The paper-trade plan, written before the first session after the decision.
TRADE = {
    'contract': 'DI1F28',
    'dv01_brl': 1000.0,      # R$ per basis point
    'entry_floor': 14.0,     # below this too little of the gap is left to be paid for
    'stop_bp': 50.0,
    'target_bp': 100.0,
    'carry_horizon_du': 21,  # about one month
}


def business_days(start: date, end: date, holidays: set[date]) -> int:
    """Business days in [start, end): the DI convention counts the start date, not the maturity."""

    days, day = 0, start
    while day < end:
        if day.weekday() < 5 and day not in holidays:
            days += 1
        day += timedelta(days=1)
    return days


def discount(curve: dict[int, float], du: float) -> float:
    """Discount factor from a zero curve, flat-forward between published vertices."""

    vertices = sorted(curve)
    if du <= vertices[0]:
        return (1 + curve[vertices[0]] / 100) ** (-du / 252)
    for a, b in zip(vertices, vertices[1:]):
        if a <= du <= b:
            log_a = -a / 252 * math.log(1 + curve[a] / 100)
            log_b = -b / 252 * math.log(1 + curve[b] / 100)
            return math.exp(log_a + (log_b - log_a) * (du - a) / (b - a))
    raise ValueError('maturity is outside the curve')


def zero_rate(curve: dict[int, float], du: float) -> float:
    return (discount(curve, du) ** (-252 / du) - 1) * 100


def forwards(curve: dict[int, float]) -> list[dict[str, float]]:
    """Forward CDI between consecutive vertices, plus the spread that makes it comparable to the Selic."""

    vertices = sorted(curve)
    rows = []
    for a, b in zip(vertices, vertices[1:]):
        forward = ((discount(curve, a) / discount(curve, b)) ** (252 / (b - a)) - 1) * 100
        rows.append({'from_du': a, 'to_du': b, 'forward_cdi': forward, 'selic_equivalent': forward + CDI_SPREAD})
    return rows


def average_cdi(anchors: list[tuple[date, float]], start: date, end: date, spread: float = CDI_SPREAD) -> float:
    """Annualised average overnight rate along a straight-line Selic path through ``anchors``."""

    points = [(start, anchors[0][1])] + [point for point in anchors if point[0] > start]

    def selic(day: date) -> float:
        for (d0, r0), (d1, r1) in zip(points, points[1:]):
            if d0 <= day <= d1:
                return r0 + (r1 - r0) * (day - d0).days / (d1 - d0).days
        return points[-1][1]

    days = (end - start).days
    growth = sum(math.log(1 + (selic(start + timedelta(days=i)) - spread) / 100) for i in range(days))
    return (math.exp(growth / days) - 1) * 100


def hikes_priced(di_rate: float, selic: float, start: date, end: date, by: date = MID_2027) -> float:
    """Hikes, in bp, that make the average overnight rate equal the DI rate.

    The Selic rises in a straight line from today to ``by`` and then stays flat.
    Solved by bisection; the function is monotonic in the size of the hikes.
    """

    def gap(bp: float) -> float:
        return average_cdi([(start, selic), (by, selic + bp / 100), (end, selic + bp / 100)], start, end) - di_rate

    low, high = -500.0, 1000.0
    for _ in range(60):
        mid = (low + high) / 2
        if gap(mid) > 0:
            high = mid
        else:
            low = mid
    return (low + high) / 2


def contract_value(rate: float, du: int) -> float:
    """B3 DI future price (PU): R$100,000 at maturity discounted at the quoted rate."""

    return 100000 / (1 + rate / 100) ** (du / 252)


def contract_dv01(rate: float, du: int) -> float:
    """R$ gained per contract when the rate falls 1 bp, by exact repricing around the quote."""

    return (contract_value(rate - 0.005, du) - contract_value(rate + 0.005, du))


def expiry_pnl(rate: float, du: int, contracts: int, average: float) -> float:
    """Receiving ``rate`` until maturity while paying the overnight average: R$ at expiry, before costs."""

    return contracts * (100000 - contract_value(rate, du) * (1 + average / 100) ** (du / 252))


def build_copom(snapshot: dict[str, Any], study: dict[str, Any], runoff: dict[str, Any]) -> dict[str, Any]:
    """``study`` is the saved 6 October study; ``runoff`` the saved 27 October note."""

    cutoff = snapshot['market_cutoff']
    start = date.fromisoformat(cutoff)
    series, press, copom = snapshot['series'], snapshot['press'], snapshot['copom']
    curves = {d: curve for d, curve in snapshot['anbima_ettj']['curves'].items() if d <= cutoff}
    today = curves[cutoff]
    fixed = {int(k): v for k, v in today['fixed_rate'].items()}

    # -- Policy and survey ---------------------------------------------------
    selic = copom['selic']
    cdi = selic - CDI_SPREAD
    focus = {key: {int(y): v for y, v in series[key]['values_by_reference_year'].items()} for key in ('focus_selic', 'focus_ipca', 'focus_fx')}
    previous_focus = runoff['focus']['selic']

    # -- The contract --------------------------------------------------------
    di_today = press['di_futures'][cutoff]
    settled = press['di_futures']['2026-11-03_settlement']
    rate = di_today['jan28']
    maturity = date.fromisoformat(press['di_futures']['maturity_jan28'])
    holidays = {date.fromisoformat(d) for d in snapshot['holidays_b3']}
    du = business_days(start, maturity, holidays)
    per_contract = contract_dv01(rate, du)
    contracts = round(TRADE['dv01_brl'] / per_contract)
    dv01 = contracts * per_contract

    # -- What is priced ------------------------------------------------------
    path_anchors = [(date(year, 12, 31), value) for year, value in sorted(focus['focus_selic'].items()) if date(year, 12, 31) > start]
    survey_points = [(start, selic), *path_anchors]
    path = average_cdi(survey_points, start, maturity)
    hikes = hikes_priced(rate, selic, start, maturity)
    end_2027 = (date(2027, 12, 31) - start).days / 365.25
    market_points = [(0.0, selic)] + [((row['from_du'] + row['to_du']) / 2 / 252, row['selic_equivalent']) for row in forwards(fixed)]
    market_end_2027 = next(r0 + (r1 - r0) * (end_2027 - t0) / (t1 - t0) for (t0, r0), (t1, r1) in zip(market_points, market_points[1:]) if t0 <= end_2027 <= t1)

    # -- Curve decomposition since the first-round rally (same method as the study) ------
    be, real = today['implied_inflation'], today['real_rate']
    study_curve = study['curve']
    first_round_2y = next(row['after'] for row in study_curve['rows'] if row['vertex'] == '504')
    be_change = be['504'] - study_curve['breakeven_2y']['after']
    real_change = real['504'] - study_curve['real_2y']['after']
    previous_day = curves[sorted(curves)[-2]]

    # -- Carry and roll for one month if the curve does not move --------------
    horizon = TRADE['carry_horizon_du']
    duration = du / 252 / (1 + rate / 100)
    carry_bp = (rate - cdi) * horizon / 252 * 100 / duration
    roll_bp = (zero_rate(fixed, du) - zero_rate(fixed, du - horizon)) * 100

    # -- Paper plan ----------------------------------------------------------
    jump_bp = runoff['rates']['jan28_change_bp']
    scenarios = []
    for key, anchors in (
        ('focus', survey_points),
        ('hold', [(start, selic), (maturity, selic)]),
        ('hike_100', [(start, selic), (MID_2027, selic + 1.0), (maturity, selic + 1.0)]),
        ('hike_200', [(start, selic), (MID_2027, selic + 2.0), (maturity, selic + 2.0)]),
    ):
        average = average_cdi(anchors, start, maturity)
        scenarios.append({'key': key, 'average_cdi': average, 'pnl_brl': expiry_pnl(rate, du, contracts, average)})

    # -- Reais per barrel, one spot series against official PTAX ------------
    ptax = dict(snapshot['history']['ptax'])
    brent = {d: v for d, v in snapshot['history']['brent'] if d <= cutoff}
    brent_day = max(brent)
    brl_barrel = {
        'before': brent[BEFORE_VOTE] * ptax[BEFORE_VOTE],
        'after': brent[AFTER_VOTE] * ptax[AFTER_VOTE],
        'latest': brent[brent_day] * ptax[brent_day],
    }
    us2y = dict(snapshot['history']['us_2y'])
    fed = series['fed_target_range']['midpoint']
    monthly_carry = (((1 + selic / 100) / (1 + fed / 100)) ** (1 / 12) - 1) * 100

    return {
        'schema_version': 1, 'id': AS_OF, 'as_of': AS_OF, 'data_as_of': cutoff, 'status': 'waiting_for_trigger',
        'inputs_file': 'research/thesis_snapshot_2026-11-05.json',
        'previous_file': 'research/runoff_2026-10-27.json',
        'study_file': 'research/study_2026-10-06.json',
        'decision': {'meeting': copom['meeting'], 'date': copom['decision_date'], 'selic': selic, 'cdi': cdi,
                     'vote_for': copom['vote_for'], 'vote_against': copom['vote_against'],
                     'cuts_before': copom['consecutive_cuts_before'], 'cut_size_bp': copom['cut_size_bp'],
                     'cycle_start': copom['cycle_start_selic'], 'projections': copom['projections'],
                     'fx_assumption': copom['fx_assumption'], 'target': copom['target'], 'ceiling': copom['ceiling'],
                     'next_meeting': copom['next_meeting'], 'minutes': copom['minutes'],
                     'broadcast_cut': press['expectations']['broadcast_cut'], 'broadcast_total': press['expectations']['broadcast_total'],
                     'b3_hold_pct': press['expectations']['b3_options_hold_pct']},
        'fed': {'date': snapshot['fed']['decision_date'], 'lower': snapshot['fed']['lower'], 'upper': snapshot['fed']['upper'],
                'dissents_for_hike': snapshot['fed']['dissents_for_hike']},
        'contract': {'ticker': TRADE['contract'], 'maturity': maturity.isoformat(), 'business_days': du, 'rate': rate,
                     'previous_settlement': settled['jan28'], 'day_change_bp': (rate - settled['jan28']) * 100,
                     'anbima_interpolated': zero_rate(fixed, du), 'jan29': di_today['jan29'], 'jan31': di_today['jan31'],
                     'before_vote': runoff['rates']['jan28_friday'], 'after_vote': runoff['rates']['jan28_monday'],
                     'fall_since_vote_bp': (runoff['rates']['jan28_monday'] - rate) * 100,
                     'dv01_per_contract': per_contract},
        'priced': {'hikes_bp_by_mid_2027': hikes, 'survey_path_average': path, 'gap_pp': rate - path,
                   'market_end_2027': market_end_2027, 'gap_end_2027_pp': market_end_2027 - focus['focus_selic'][2027],
                   'gap_before_vote_pp': runoff['rates']['gap_jan28_friday'], 'gap_after_vote_pp': runoff['rates']['gap_jan28_monday'],
                   'forwards': forwards(fixed),
                   'forwards_first_round': forwards({int(row['vertex']): row['after'] for row in study_curve['rows']}),
                   'survey_path': [[d.isoformat(), v] for d, v in survey_points]},
        'curve': {'date': cutoff, 'previous_date': sorted(curves)[-2],
                  'fixed': today['fixed_rate'], 'two_year': fixed[504], 'two_year_first_round': first_round_2y,
                  'two_year_since_first_round_bp': (fixed[504] - first_round_2y) * 100,
                  'two_year_day_change_bp': (fixed[504] - previous_day['fixed_rate']['504']) * 100,
                  'breakeven_2y': be['504'], 'breakeven_2y_first_round': study_curve['breakeven_2y']['after'],
                  'real_2y': real['504'], 'real_2y_first_round': study_curve['real_2y']['after'],
                  'breakeven_share': be_change / (be_change + real_change) * 100,
                  'first_round_breakeven_share': study_curve['breakeven_share']},
        'focus': {'date': series['focus_selic']['latest_observation_date'], 'selic': series['focus_selic']['values_by_reference_year'],
                  'ipca': series['focus_ipca']['values_by_reference_year'], 'fx': series['focus_fx']['values_by_reference_year'], 'previous_selic_2027': float(previous_focus['2027'])},
        'fx': {'before_vote': ptax[BEFORE_VOTE], 'after_vote': ptax[AFTER_VOTE], 'latest': ptax[cutoff], 'date': cutoff,
               'since_vote_pct': (ptax[cutoff] / ptax[BEFORE_VOTE] - 1) * 100,
               'vs_copom_assumption_pct': (ptax[cutoff] / copom['fx_assumption'] - 1) * 100,
               'monthly_carry_pct': monthly_carry},
        'oil': {'date': brent_day, 'before_vote': brent[BEFORE_VOTE], 'after_vote': brent[AFTER_VOTE], 'latest': brent[brent_day],
                'fall_since_vote_pct': (1 - brent[brent_day] / brent[AFTER_VOTE]) * 100, 'brl_barrel': brl_barrel,
                'brl_vs_before_pct': (brl_barrel['latest'] / brl_barrel['before'] - 1) * 100,
                'front_month': press['brent_front_month'][cutoff], 'front_month_change_pct': press['brent_front_month']['change_pct']},
        'us2y': {'after_vote': us2y[AFTER_VOTE], 'before_vote': us2y[BEFORE_VOTE], 'latest': us2y[cutoff], 'change_bp': (us2y[cutoff] - us2y[AFTER_VOTE]) * 100},
        'equity': {'before_vote': runoff['equity']['friday'], 'after_vote': runoff['equity']['monday'], 'latest': press['ibovespa'][cutoff]},
        'fiscal': {'target_bn': press['fiscal']['target_2027_bn'], 'target_pct_gdp': press['fiscal']['target_2027_pct_gdp'],
                   'floor_bn': press['fiscal']['floor_2027_bn'], 'room_needed_bn': press['fiscal']['room_needed_min_bn'],
                   'bill_filed': press['fiscal']['bill_filed'], 'speech': press['fiscal']['speech_date']},
        'rule': {'written': runoff['as_of'], 'conditions': {'copom_holds': selic == series['selic_target']['value'], 'firm_on_inflation': True,
                                                            'budget_target_in_law': press['fiscal']['bill_filed']},
                 'expires': copom['next_meeting']},
        'plan': {**TRADE, 'contracts': contracts, 'dv01': dv01, 'stop_loss_brl': TRADE['stop_bp'] * dv01, 'target_gain_brl': TRADE['target_bp'] * dv01,
                 'jump_bp': jump_bp, 'jump_loss_brl': jump_bp * dv01, 'carry_bp_per_month': carry_bp, 'roll_bp_per_month': roll_bp,
                 'carry_roll_bp_per_month': carry_bp + roll_bp, 'carry_roll_brl_per_month': (carry_bp + roll_bp) * dv01,
                 'waiting_cost_bp': (runoff['rates']['jan28_monday'] - rate) * 100, 'scenarios': scenarios},
        'sources': [
            {'key': 'copom', **copom['source']},
            {'key': 'ptax', 'label': 'BCB · PTAX', 'date': cutoff, 'url': series['ptax_usd_brl_midpoint']['source_url']},
            {'key': 'anbima', 'label': 'ANBIMA · Term structure, 3 and 4 November', 'date': cutoff, 'url': snapshot['anbima_ettj']['url']},
            {'key': 'focus', 'label': 'BCB · Focus', 'date': series['focus_selic']['latest_observation_date'], 'url': series['focus_selic']['source_url']},
            {'key': 'treasury', 'label': 'U.S. Treasury · Par yields', 'date': cutoff, 'url': series['us_2_year_treasury']['source_url']},
            {'key': 'fed', **snapshot['fed']['source']},
            {'key': 'brent', 'label': 'EIA · Brent spot, via FRED', 'date': brent_day, 'url': snapshot['commodities']['brent']['source_url']},
            *({'key': key, **source} for key in ('di_futures', 'ibovespa', 'brent_front_month', 'expectations', 'fiscal') for source in press[key]['sources']),
        ],
    }


def copom_values(report: dict[str, Any], lang: str) -> dict[str, str]:
    """Text placeholders for the note, all prefixed ``c_`` so the archived note keeps its own."""

    n = lambda v, digits=2: f.num(v, digits, lang)
    pct = lambda v, digits=2: f.pct(v, digits, lang)
    prefix = {'en': 'R$', 'pt': 'R$ ', 'fr': 'R$ '}[lang]  # same spacing as the budget figures in each language
    money = lambda v, digits=0: f'{prefix}{f.num(abs(v), digits, lang)}'
    brl = lambda v, signed=False: f'{"+" if signed and v > 0 else "−" if v < 0 else ""}{money(v)}'
    thousand = lambda v: round(v, -3)
    decision, contract, priced, curve, focus = (report[k] for k in ('decision', 'contract', 'priced', 'curve', 'focus'))
    fx, oil, us, plan, fiscal, eq = (report[k] for k in ('fx', 'oil', 'us2y', 'plan', 'fiscal', 'equity'))
    scenario = {row['key']: row for row in plan['scenarios']}
    selic_focus = {str(k): v for k, v in focus['selic'].items()}
    ipca_focus = {str(k): v for k, v in focus['ipca'].items()}
    projections = decision['projections']
    bp = lambda v: f.num(v, 0, lang)
    return {
        'c_date': f.day(report['as_of'], lang, long=True),
        'c_cutoff': f.day(report['data_as_of'], lang, year=False, long=True),
        'c_decision_day': f.day(decision['date'], lang, year=False, long=True),
        'c_short_before': f.day('2026-10-23', lang, year=False),
        'c_short_after': f.day('2026-10-26', lang, year=False),
        'c_short_now': f.day(report['data_as_of'], lang, year=False),
        'c_selic': pct(decision['selic']), 'c_cdi': pct(decision['cdi']),
        'c_cuts': str(decision['cuts_before']), 'c_cut_size': bp(decision['cut_size_bp']),
        'c_cycle_start': pct(decision['cycle_start'], 0),
        'c_vote': f"{decision['vote_for']}-{decision['vote_against']}",
        'c_broadcast_cut': str(decision['broadcast_cut']), 'c_broadcast_total': str(decision['broadcast_total']),
        'c_b3_hold': pct(decision['b3_hold_pct'], 0),
        'c_ipca26': pct(projections['2026'], 1), 'c_ipca27': pct(projections['2027'], 1), 'c_ipca_h': pct(projections['2028Q2'], 1),
        'c_ipca26_old': pct(projections['previous_2026'], 1), 'c_ipca27_old': pct(projections['previous_2027'], 1),
        'c_target': pct(decision['target'], 0), 'c_ceiling': pct(decision['ceiling'], 1),
        'c_minutes': f.day(decision['minutes'], lang, year=False, long=True),
        'c_expiry': f.day(decision['next_meeting'], lang, year=False, long=True),
        'c_speech': f.day(fiscal['speech'], lang, year=False, long=True),
        'c_fomc': f.day(report['fed']['date'], lang, year=False, long=True),
        'c_fed_range': f.rate_range(report['fed']['lower'], report['fed']['upper'], lang),
        'c_dissents': str(report['fed']['dissents_for_hike']),
        'c_di28': pct(contract['rate']), 'c_di28_settle': pct(contract['previous_settlement']),
        'c_di28_day': bp(abs(contract['day_change_bp'])), 'c_di28_peak': pct(contract['after_vote']),
        'c_di28_pre': pct(contract['before_vote']), 'c_di28_fall': bp(contract['fall_since_vote_bp']),
        'c_di28_anbima': pct(contract['anbima_interpolated']), 'c_di29': pct(contract['jan29']), 'c_di31': pct(contract['jan31']),
        'c_du': str(contract['business_days']), 'c_dv01_contract': money(contract['dv01_per_contract'], 2),
        'c_slope_front': bp((contract['rate'] - decision['cdi']) * 100), 'c_slope_mid': bp((contract['jan29'] - contract['rate']) * 100),
        'c_slope_long': bp((contract['jan31'] - contract['jan29']) * 100),
        'c_hikes': f.num(25 * round(priced['hikes_bp_by_mid_2027'] / 25), 0, lang),
        'c_gap27': f.pp(priced['gap_end_2027_pp'], 1, lang), 'c_focus_date': f.day(focus['date'], lang, year=False, long=True),
        'c_path': pct(priced['survey_path_average'], 1), 'c_gap': f.pp(priced['gap_pp'], 1, lang),
        'c_gap_pre': f.pp(priced['gap_before_vote_pp'], 1, lang), 'c_gap_post': f.pp(priced['gap_after_vote_pp'], 1, lang),
        'c_selic26': pct(selic_focus['2026']), 'c_selic27': pct(selic_focus['2027']), 'c_selic28': pct(selic_focus['2028']),
        'c_selic27_old': pct(focus['previous_selic_2027']), 'c_focus_ipca27': pct(ipca_focus['2027'], 1), 'c_focus_ipca26': pct(ipca_focus['2026'], 1),
        'c_2y': pct(curve['two_year']), 'c_2y_first': pct(curve['two_year_first_round']),
        'c_2y_since': bp(curve['two_year_since_first_round_bp']), 'c_2y_day': bp(abs(curve['two_year_day_change_bp'])),
        'c_be_share': pct(curve['breakeven_share'], 0), 'c_be_first_share': pct(curve['first_round_breakeven_share'], 0),
        'c_be': pct(curve['breakeven_2y']), 'c_be_first': pct(curve['breakeven_2y_first_round']), 'c_real': pct(curve['real_2y'], 1),
        'c_ptax': n(fx['latest'], 4), 'c_ptax_before': n(fx['before_vote'], 4), 'c_ptax_after': n(fx['after_vote'], 4),
        'c_fx_since': pct(fx['since_vote_pct'], 1), 'c_fx_copom': money(decision['fx_assumption'], 2), 'c_fx_gap': pct(fx['vs_copom_assumption_pct'], 1),
        'c_fx_carry': pct(fx['monthly_carry_pct']),
        'c_brent_before': n(oil['before_vote'], 2), 'c_brent_after': n(oil['after_vote'], 2), 'c_brent': n(oil['latest'], 2),
        'c_brent_fall': pct(oil['fall_since_vote_pct'], 0), 'c_brent_date': f.day(oil['date'], lang, year=False, long=True),
        'c_brent_short': f.day(oil['date'], lang, year=False),
        'c_brent_front': n(oil['front_month'], 2), 'c_brent_front_move': f.pct(oil['front_month_change_pct'], 1, lang, signed=True),
        'c_rb_before': brl(oil['brl_barrel']['before']), 'c_rb_after': brl(oil['brl_barrel']['after']), 'c_rb': brl(oil['brl_barrel']['latest']),
        'c_rb_change': pct(abs(oil['brl_vs_before_pct']), 0),
        'c_us_before': pct(us['before_vote']), 'c_us_after': pct(us['after_vote']), 'c_us': pct(us['latest']), 'c_us_chg': bp(abs(us['change_bp'])),
        'c_ibov_before': n(eq['before_vote'], 0), 'c_ibov_after': n(eq['after_vote'], 0), 'c_ibov': n(eq['latest'], 0),
        'c_fiscal_target': f.brl_bn(fiscal['target_bn'], lang), 'c_fiscal_pct': pct(fiscal['target_pct_gdp'], 1),
        'c_fiscal_room': f.brl_bn(fiscal['room_needed_bn'], lang),
        'c_floor': pct(plan['entry_floor']), 'c_stop': bp(plan['stop_bp']), 'c_goal': bp(plan['target_bp']),
        'c_dv01': money(plan['dv01_brl']), 'c_contracts': str(plan['contracts']),
        'c_stop_loss': brl(thousand(plan['stop_loss_brl'])), 'c_goal_gain': brl(thousand(plan['target_gain_brl'])),
        'c_jump': bp(plan['jump_bp']), 'c_jump_loss': brl(thousand(plan['jump_loss_brl'])),
        'c_carry': bp(plan['carry_bp_per_month']), 'c_roll': bp(plan['roll_bp_per_month']), 'c_cr': bp(plan['carry_roll_bp_per_month']),
        'c_cr_brl': brl(thousand(plan['carry_roll_brl_per_month'])), 'c_wait_cost': bp(plan['waiting_cost_bp']),
        'c_wait_cost_brl': brl(thousand(plan['waiting_cost_bp'] * plan['dv01'])),
        'c_pnl_focus': brl(thousand(scenario['focus']['pnl_brl']), True), 'c_pnl_hold': brl(thousand(scenario['hold']['pnl_brl']), True),
        'c_pnl_100': brl(thousand(scenario['hike_100']['pnl_brl']), True), 'c_pnl_200': brl(thousand(scenario['hike_200']['pnl_brl']), True),
        'c_avg_focus': pct(scenario['focus']['average_cdi'], 1), 'c_avg_hold': pct(scenario['hold']['average_cdi'], 1),
        'c_avg_100': pct(scenario['hike_100']['average_cdi'], 1), 'c_avg_200': pct(scenario['hike_200']['average_cdi'], 1),
    }
