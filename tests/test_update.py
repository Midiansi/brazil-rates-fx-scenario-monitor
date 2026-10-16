"""Publication arithmetic, time alignment and preservation of prior research."""
import copy
import json
import re
import string
from datetime import date
from html import unescape

import pytest

from conftest import ROOT
from src.page import render
from src.update import build_update, update_values
from src.update_content import TEXT


@pytest.fixture
def inputs():
    return json.loads((ROOT / 'research/thesis_snapshot_2026-10-16.json').read_text())


@pytest.fixture
def previous():
    return json.loads((ROOT / 'research/thesis_2026-10-06.json').read_text())


def test_publication_reproduces_offline(thesis, inputs, previous):
    assert build_update(inputs, previous) == thesis['current_update']
    assert previous['rules'] == thesis['current_update']['rules'] == thesis['rules']
    for key in ('evidence', 'review', 'previous_file', 'inputs_file', 'study_file'):
        assert thesis[key] == previous[key]
    assert thesis['current_update']['previous_file'] == 'research/thesis_2026-10-06.json'


def test_fx_and_carry_are_independently_recomputed(thesis):
    report = thesis['current_update']
    p, policy = report['ptax'], report['policy']
    assert p['giveback_pct'] == pytest.approx((5.0518 - 4.9856) / (5.2235 - 4.9856) * 100)
    growth = (1.1375 / 1.03875) ** (1 / 12)
    assert policy['monthly_carry_pct'] == pytest.approx((growth - 1) * 100)
    assert policy['one_month_fx_breakeven'] == pytest.approx(5.0518 * growth)
    # At that future exchange rate, the relative USD value of the BRL investment is exactly 1.
    assert growth * p['value'] / policy['one_month_fx_breakeven'] == pytest.approx(1)
    assert policy['monthly_carry_pct'] < p['since_first_day_pct']


def test_carry_is_compared_with_volatility_and_the_event(thesis):
    policy, study = thesis['current_update']['policy'], thesis['study']
    assert policy['annual_carry_pct'] == pytest.approx((1.1375 / 1.03875 - 1) * 100)
    assert policy['annual_carry_pct'] == pytest.approx(study['carry']['annual'])
    # Same 20 pre-vote sessions as the 6 October study; the study's ratio used carry rounded to 0.76%.
    assert policy['prevote_vol_pct'] == pytest.approx(study['volatility']['diffusion_annual'])
    assert policy['carry_to_vol'] == pytest.approx(study['carry']['to_vol_diffusion'], abs=0.01)
    assert 0.9 < policy['carry_to_vol'] < 1.1  # the prose says "roughly equal"
    assert policy['event_move_pct'] == pytest.approx((4.9856 / 5.2235 - 1) * 100)
    assert round(policy['event_carry_months']) == 6


def test_curve_divergence_matches_raw_download(thesis, inputs):
    rows = thesis['current_update']['curve']
    assert [r['date'] for r in rows] == ['2026-10-02', '2026-10-05', '2026-10-15']
    assert rows[-1]['nominal'] == 12.7161
    assert (rows[-1]['nominal'] - rows[1]['nominal']) * 100 == pytest.approx(11.6)
    assert (rows[-1]['breakeven'] - rows[1]['breakeven']) * 100 == pytest.approx(26.82)
    assert (rows[-1]['real'] - rows[1]['real']) * 100 == pytest.approx(-16.19)
    assert '15/10/2026' in inputs['anbima_download']['raw_csv']
    assert '12,7161' in inputs['anbima_download']['raw_csv']
    assert '5,5362' in inputs['anbima_download']['raw_csv']


def test_oil_uses_common_dates_and_compounds_the_shocks(thesis):
    oil = thesis['current_update']['oil']
    assert oil['date'] == '2026-10-14'  # PTAX extends to the 15th; oil does not.
    assert oil['brl_change_pct'] == pytest.approx((126.55 * 5.0438 / (135.51 * 5.2235) - 1) * 100)
    assert oil['brl_change_pct'] != pytest.approx(oil['usd_change_pct'] + oil['fx_change_pct'])


def test_oil_conclusion_is_reported_against_several_base_dates(thesis):
    oil = thesis['current_update']['oil']
    # EIA spot jumped from 114.82 to 135.51 on the pre-vote close itself.
    assert oil['jump_pct'] == pytest.approx((135.51 / 114.82 - 1) * 100)
    bases = {b['date']: b for b in oil['bases']}
    assert list(bases) == ['2026-10-01', '2026-10-02', '2026-10-05']
    assert bases['2026-10-01']['brl_change_pct'] == pytest.approx((126.55 * 5.0438 / (114.82 * 5.2076) - 1) * 100)
    assert bases['2026-10-02']['brl_change_pct'] == pytest.approx(oil['brl_change_pct'])
    assert bases['2026-10-05']['brl_change_pct'] == pytest.approx((126.55 * 5.0438 / (125.51 * 4.9856) - 1) * 100)
    # The sign depends on the start date, which is why the note draws no oil conclusion.
    assert bases['2026-10-01']['brl_change_pct'] > 0 > bases['2026-10-02']['brl_change_pct']
    assert all(b['fx_change_pct'] < 0 for d, b in bases.items() if d < '2026-10-05')


def test_breakevens_rose_along_the_curve_not_just_the_front(thesis, inputs):
    shift, curves = thesis['current_update']['breakevens'], inputs['anbima_ettj']
    after, before = curves['2026-10-15']['implied_inflation'], curves['2026-10-05']['implied_inflation']
    moves = [(after[t] - before[t]) * 100 for t in after if 252 <= int(t) <= 1512]
    assert len(moves) == 11
    assert (shift['min_change_bp'], shift['max_change_bp']) == (pytest.approx(min(moves)), pytest.approx(max(moves)))
    assert round(shift['min_change_bp']) == 27 and round(shift['max_change_bp']) == 30

    def forward(curve):  # independent of src.update: compound to five years, discount two
        return (((1 + curve['1260'] / 100) ** 5 / (1 + curve['504'] / 100) ** 2) ** (1 / 3) - 1) * 100
    assert shift['forward_2y5y_change_bp'] == pytest.approx((forward(after) - forward(before)) * 100)
    assert shift['forward_2y5y_change_bp'] > shift['min_change_bp']


def test_survey_moved_less_than_the_curve(thesis):
    survey, study = thesis['current_update']['survey'], thesis['study']
    assert survey['previous_date'] == '2026-10-02'
    assert survey['ipca_2026'] == [5.0129, 5.2245] and survey['selic_2026'] == [13.5, 13.25]
    assert round(survey['ipca_2027'][0], 2) == round(survey['ipca_2027'][1], 2) == 4.30
    # The first-round gap is recomputed exactly as the 6 October study measured it.
    assert survey['gap_2y'][0] == pytest.approx(study['survey_gap']['gap_2y_after'])
    assert survey['gap_2y'][1] == pytest.approx(12.7161 - survey['path_2y'][1])
    assert 0 < survey['gap_2y'][0] < survey['gap_2y'][1]  # the prose says "above ... up from"


def test_future_prices_cannot_change_the_publication(inputs, previous):
    altered = copy.deepcopy(inputs)
    altered['history']['ptax'].append(['2026-10-16', 20])
    altered['history']['brent'].append(['2026-10-16', 1])
    altered['history']['us_2y'].append(['2026-10-16', 20])
    assert build_update(altered, previous) == build_update(inputs, previous)


def test_producer_shocks_include_the_cross_term(thesis):
    producer = thesis['current_update']['producer']
    assert producer['revenue_change_pct'][0][0] == pytest.approx(-14.5)
    assert producer['revenue_change_pct'][0][2] == pytest.approx(-5.5)
    assert producer['revenue_change_pct'][2][0] == pytest.approx(4.5)
    offset = producer['offset_commodity_pct'] / 100
    assert (1 + offset) * .95 == pytest.approx(1)


@pytest.mark.parametrize('lang', ['en', 'pt', 'fr'])
def test_current_note_resolves_and_precedes_archived_studies(thesis, inputs, lang):
    blocks = render(lang, thesis, inputs, date(2026, 10, 16))
    page = ''.join(blocks.values())
    text = unescape(re.sub(r'<[^>]+>', ' ', page))
    assert not re.search(r'\{[a-z_0-9]+\}', text)
    assert page.index('id="update"') < page.index('id="quant"')
    assert 'datetime="2026-10-16"' in blocks['hero']
    assert ('5.0518' if lang == 'en' else '5,0518') in blocks['hero']
    assert TEXT[lang]['archive'] in unescape(page)
    assert TEXT[lang]['monitor_note'] in unescape(blocks['hero'])


def test_languages_have_matching_fields_and_placeholders(thesis):
    def fields(value):
        if isinstance(value, str):
            return {field for _, field, _, _ in string.Formatter().parse(value) if field}
        if isinstance(value, dict):
            return {key: fields(item) for key, item in value.items()}
        return [fields(item) for item in value]
    assert fields(TEXT['en']) == fields(TEXT['pt']) == fields(TEXT['fr'])
    assert set(update_values(thesis['current_update'], 'en')) == set(update_values(thesis['current_update'], 'pt'))


def test_missing_followup_keeps_original_page_available(thesis, inputs):
    old = copy.deepcopy(thesis)
    old.pop('current_update')
    page = render('en', old, inputs, date(2026, 10, 16))
    assert page['update'] == ''
    assert 'datetime="2026-10-06"' in page['hero']
