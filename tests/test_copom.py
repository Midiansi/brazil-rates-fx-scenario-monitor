"""The 5 November (post-Copom) publication: independent arithmetic, time order and rendering."""
from __future__ import annotations

import copy
import json
import math
import re
import string
from datetime import date
from html import unescape

import numpy as np
import pytest

from src.copom import MID_2027, average_cdi, build_copom, business_days, contract_dv01, contract_value, copom_values, discount, expiry_pnl, forwards, hikes_priced, zero_rate
from src.copom_content import TEXT
from src.page import render
from src.pdf_brief import render_pdf

from conftest import ROOT


def read(name):
    return json.loads((ROOT / 'research' / name).read_text())


@pytest.fixture
def inputs():
    return read('thesis_snapshot_2026-11-05.json')


@pytest.fixture
def study():
    return read('study_2026-10-06.json')


@pytest.fixture
def runoff():
    return read('runoff_2026-10-27.json')


@pytest.fixture
def report(thesis):
    return thesis['current_update']


@pytest.fixture
def risk_report():
    return read('risk_2026-10-07.json')


def test_publication_reproduces_offline(report, inputs, study, runoff):
    assert build_copom(inputs, study, runoff) == report
    assert report['as_of'] == '2026-11-05' and report['data_as_of'] == '2026-11-04'
    assert report['inputs_file'] == 'research/thesis_snapshot_2026-11-05.json'


def test_future_prices_cannot_change_the_publication(inputs, study, runoff):
    altered = copy.deepcopy(inputs)
    altered['history']['ptax'].append(['2026-11-05', 20])
    altered['history']['us_2y'].append(['2026-11-05', 20])
    altered['history']['brent'].append(['2026-11-05', 1])
    altered['anbima_ettj']['curves']['2026-11-05'] = {'fixed_rate': {'21': 1, '504': 1}}
    assert build_copom(altered, study, runoff) == build_copom(inputs, study, runoff)


def test_business_days_match_an_independent_calendar(inputs):
    holidays = [date.fromisoformat(d) for d in inputs['holidays_b3']]
    expected = int(np.busday_count('2026-11-04', '2028-01-03', holidays=[d.isoformat() for d in holidays]))
    assert business_days(date(2026, 11, 4), date(2028, 1, 3), set(holidays)) == expected == 291


def test_interpolation_returns_published_vertices_and_forwards_compound_back(inputs):
    curve = {int(k): v for k, v in inputs['anbima_ettj']['curves']['2026-11-04']['fixed_rate'].items()}
    for vertex, rate in curve.items():
        assert zero_rate(curve, vertex) == pytest.approx(rate, abs=1e-9)
    growth = (1 + curve[21] / 100) ** (21 / 252)
    for row in forwards(curve):
        growth *= (1 + row['forward_cdi'] / 100) ** ((row['to_du'] - row['from_du']) / 252)
    assert growth == pytest.approx(1 / discount(curve, 2520), rel=1e-9)
    assert all(row['selic_equivalent'] - row['forward_cdi'] == pytest.approx(0.10) for row in forwards(curve))


def test_official_curve_agrees_with_the_press_quote(report):
    contract = report['contract']
    assert abs(contract['anbima_interpolated'] - contract['rate']) < 0.10


def test_contract_arithmetic_is_independently_recomputed(report):
    contract, plan = report['contract'], report['plan']
    rate, du = contract['rate'], contract['business_days']
    assert contract_value(rate, du) == pytest.approx(100000 / 1.1439 ** (291 / 252))
    analytic = contract_value(rate, du) * (du / 252) / (1 + rate / 100) * 1e-4
    assert contract_dv01(rate, du) == pytest.approx(analytic, rel=1e-4)
    assert plan['contracts'] == round(1000 / contract['dv01_per_contract'])
    assert plan['stop_loss_brl'] == pytest.approx(plan['stop_bp'] * plan['dv01'])
    assert plan['target_gain_brl'] == pytest.approx(2 * plan['stop_loss_brl'])
    assert plan['jump_loss_brl'] == pytest.approx(194.1 * plan['dv01'])


def test_expiry_result_is_zero_at_the_contract_rate_and_falls_with_the_overnight_rate(report):
    contract, plan = report['contract'], report['plan']
    rate, du, n = contract['rate'], contract['business_days'], plan['contracts']
    assert expiry_pnl(rate, du, n, rate) == pytest.approx(0, abs=1e-6)
    rows = {row['key']: row for row in plan['scenarios']}
    assert rows['focus']['pnl_brl'] > rows['hold']['pnl_brl'] > rows['hike_100']['pnl_brl'] > rows['hike_200']['pnl_brl']
    assert rows['hold']['average_cdi'] == pytest.approx(13.65, abs=1e-6)
    # About what is priced: a 100 bp path leaves the position near flat, and that is what the note says.
    assert abs(rows['hike_100']['pnl_brl']) < 0.05 * rows['hold']['pnl_brl']


def test_hikes_priced_solve_for_the_contract_rate(report):
    start, end = date(2026, 11, 4), date(2028, 1, 3)
    selic, rate = report['decision']['selic'], report['contract']['rate']
    hikes = hikes_priced(rate, selic, start, end)
    assert hikes == pytest.approx(report['priced']['hikes_bp_by_mid_2027'])
    path = [(start, selic), (MID_2027, selic + hikes / 100), (end, selic + hikes / 100)]
    assert average_cdi(path, start, end) == pytest.approx(rate, abs=1e-6)
    assert 75 < hikes < 125  # the note rounds this to "about 100"


def test_survey_gap_uses_the_economists_path(report):
    focus = report['focus']['selic']
    start, end = date(2026, 11, 4), date(2028, 1, 3)
    path = average_cdi([(start, 13.75), (date(2026, 12, 31), focus['2026']), (date(2027, 12, 31), focus['2027']), (date(2028, 12, 31), focus['2028'])], start, end)
    assert report['priced']['survey_path_average'] == pytest.approx(path)
    assert report['priced']['gap_pp'] == pytest.approx(report['contract']['rate'] - path)


def test_breakeven_share_is_recomputed_from_the_raw_curves(report, inputs, study):
    today = inputs['anbima_ettj']['curves']['2026-11-04']
    d_be = today['implied_inflation']['504'] - study['curve']['breakeven_2y']['after']
    d_real = today['real_rate']['504'] - study['curve']['real_2y']['after']
    assert report['curve']['breakeven_share'] == pytest.approx(d_be / (d_be + d_real) * 100)
    assert report['curve']['two_year_since_first_round_bp'] == pytest.approx((14.8272 - 12.6001) * 100)


def test_reais_per_barrel_use_the_same_day_for_both_series(report, inputs):
    ptax, brent = dict(inputs['history']['ptax']), dict(inputs['history']['brent'])
    assert report['oil']['date'] == '2026-11-03'
    assert report['oil']['brl_barrel']['before'] == pytest.approx(ptax['2026-10-23'] * brent['2026-10-23'])
    assert report['oil']['brl_barrel']['latest'] == pytest.approx(ptax['2026-11-03'] * brent['2026-11-03'])
    assert report['oil']['brl_barrel']['latest'] < report['oil']['brl_barrel']['before'] < report['oil']['brl_barrel']['after']


def test_rule_says_wait_while_the_budget_condition_is_open(report, thesis, inputs):
    assert report['rule']['conditions'] == {'copom_holds': True, 'firm_on_inflation': True, 'budget_target_in_law': False}
    assert report['status'] == 'waiting_for_trigger'
    assert report['rule']['written'] == '2026-10-27'  # the conditions predate the decision


def test_every_source_is_dated_and_linked(report):
    assert len(report['sources']) >= 10
    for source in report['sources']:
        assert source['url'].startswith('https://') and source['label'] and date.fromisoformat(source['date'])
        assert source['date'] <= report['as_of']


def test_languages_have_matching_fields_and_placeholders(report):
    def fields(value):
        if isinstance(value, str):
            return {field for _, field, _, _ in string.Formatter().parse(value) if field}
        if isinstance(value, dict):
            return {key: fields(item) for key, item in value.items()}
        return [fields(item) for item in value]
    assert fields(TEXT['en']) == fields(TEXT['pt']) == fields(TEXT['fr'])
    assert set(copom_values(report, 'en')) == set(copom_values(report, 'pt')) == set(copom_values(report, 'fr'))


def test_note_copy_has_no_em_dashes():
    source = (ROOT / 'src' / 'copom_content.py').read_text(encoding='utf-8')
    assert '—' not in source


@pytest.mark.parametrize('lang', ['en', 'pt', 'fr'])
def test_the_first_screen_states_the_call_and_the_trade(thesis, inputs, risk_report, lang):
    blocks = render(lang, thesis, inputs, date(2026, 11, 5), 'quant', risk_report)
    page = ''.join(blocks.values())
    text = unescape(re.sub(r'<[^>]+>', ' ', page))
    assert not re.search(r'\{[a-z_0-9]+\}', text)
    hero = unescape(blocks['hero'])
    assert 'datetime="2026-11-05"' in hero
    assert ('14.39' if lang == 'en' else '14,39') in hero and ('14.00' if lang == 'en' else '14,00') in hero
    assert TEXT[lang]['status'] in hero and TEXT[lang]['ticket_label'] in hero
    assert list(blocks).index('chart_pricing') < list(blocks).index('update')
    assert page.index('id="view"') < page.index('id="update"') < page.index('id="scorecard"') < page.index('id="lab"') < page.index('id="quant"') < page.index('id="archive"')


def test_track_record_counts_every_scored_call(thesis, inputs, risk_report):
    proof = unescape(re.sub(r'<[^>]+>', ' ', render('en', thesis, inputs, date(2026, 11, 5), 'quant', risk_report)['proof']))
    assert '11 dated calls checked so far.' in proof
    numbers = re.findall(r'<dt>([^<]+)</dt><dd>(\d+)</dd>', render('en', thesis, inputs, date(2026, 11, 5), 'quant', risk_report)['proof'])
    assert numbers == [('Confirmed', '5'), ('Partly right', '5'), ('Missed', '1'), ('Paper trades entered', '0')]


def test_every_cv_claim_stays_on_the_page(thesis, inputs, risk_report):
    """Recruiters check the CV against the site, so these figures must stay visible and reachable."""

    page = ''.join(render('en', thesis, inputs, date(2026, 11, 5), 'quant', risk_report).values())
    text = unescape(re.sub(r'<[^>]+>', ' ', page))
    for claim in ('2,700', '2.3%', '1.3%', 'Kupiec', '−4.55%', '8.1σ', '61%', '28%', '11 official data feeds', 'six commodities', 'Seven first-round elections'):
        assert claim in text, claim
    for section in ('update', 'scorecard', 'lab', 'risk', 'quant', 'commodities', 'archive', 'methods'):
        assert f'id="{section}"' in page, section


def test_the_market_chart_is_labelled_and_has_two_variants(thesis, inputs):
    blocks = render('en', thesis, inputs, date(2026, 11, 5))
    chart = blocks['chart_pricing']
    assert chart.count('<svg') == 2 and 'Economists (Focus)' in chart and 'Selic today' in chart
    assert '<title' in chart and '<figcaption' in chart and '\n\n' not in chart


def test_a_missing_previous_note_does_not_break_the_page(thesis, inputs):
    old = copy.deepcopy(thesis)
    old.pop('previous_update')
    page = ''.join(render('en', old, inputs, date(2026, 11, 5)).values())
    assert 'id="update"' in page and 'class="previous-note"' not in page


def test_pdf_states_the_trade(thesis, inputs, tmp_path):
    from pypdf import PdfReader
    path = render_pdf(thesis, inputs, tmp_path / 'brief.pdf', 'en')
    text = re.sub(r'\s+', ' ', ' '.join(page.extract_text() for page in PdfReader(path).pages))
    assert 'Receive DI January 2028' in text and 'Paper only' in text
