"""The 27 October (post-runoff) publication: independent arithmetic, time order and rendering."""
import copy
import json
import math
import re
import statistics
import string
from datetime import date
from html import unescape

import pytest

from conftest import ROOT
from src.page import render
from src.runoff import build_runoff, path_average, runoff_values
from src.runoff_content import TEXT
from src.thesis import survey_path_average


def read(name):
    return json.loads((ROOT / 'research' / name).read_text())


@pytest.fixture
def inputs():
    return read('thesis_snapshot_2026-10-27.json')


@pytest.fixture
def history():
    return read('study_inputs_2026-10-06.json')


@pytest.fixture
def baseline():
    return read('thesis_2026-10-06.json')


@pytest.fixture
def previous():
    return read('update_2026-10-16.json')


@pytest.fixture
def report(thesis):
    return thesis['current_update']


def test_publication_reproduces_offline(report, inputs, history, baseline, previous):
    built = build_runoff(inputs, history, baseline, previous)
    expected = copy.deepcopy(report)
    # Day-by-day sums over the survey path can differ in the last bits across Python versions.
    for key in ('path_jan28_friday', 'path_jan28_monday', 'path_jan27_monday', 'gap_jan28_friday', 'gap_jan28_monday'):
        expected['rates'][key] = pytest.approx(expected['rates'][key], rel=1e-12, abs=1e-12)
    assert built == expected
    assert report['previous_file'] == 'research/update_2026-10-16.json'
    assert report['inputs_file'] == 'research/thesis_snapshot_2026-10-27.json'


def test_fx_move_and_loss_are_independently_recomputed(report):
    fx, carry, risk = report['fx'], report['carry'], report['risk']
    assert (fx['friday'], fx['monday']) == (5.0374, 5.50025)
    assert fx['move_pct'] == pytest.approx((5.50025 / 5.0374 - 1) * 100)
    # A long-real position marked in dollars loses 1 - S_fri / S_mon, not the USD/BRL change.
    assert risk['loss_pct'] == pytest.approx((1 - 5.0374 / 5.50025) * 100)
    assert risk['loss_pct'] < fx['move_pct']
    growth = (1.1375 / 1.03875) ** (1 / 12)
    assert carry['monthly_pct'] == pytest.approx((growth - 1) * 100)
    assert round(carry['months_lost']) == 12  # "a year of carry"
    assert round(carry['first_round_months']) == 6
    assert fx['first_round_move_pct'] == pytest.approx((4.9856 / 5.2235 - 1) * 100)
    assert round(fx['asymmetry']) == 2  # the prose says "about twice as much"
    assert fx['friday_vs_pre_first_pct'] < 0 < fx['monday_vs_pre_first_pct']


def test_rank_since_2002_uses_the_full_official_history(report, history, inputs):
    ptax = dict(history['ptax'])
    ptax.update({d: v for d, v in inputs['history']['ptax'] if d > max(ptax)})
    days = sorted(ptax)
    moves = sorted(((math.log(ptax[b] / ptax[a]), b) for a, b in zip(days, days[1:])), reverse=True)
    assert days[0].startswith('2002')
    assert [d for _, d in moves[:2]] == ['2008-10-08', '2026-10-26']
    assert report['fx']['rank'] == 2 and report['fx']['larger'] == ['2008-10-08']


def test_var_uses_only_closes_up_to_friday(report, inputs, history, baseline, previous):
    risk = report['risk']
    assert risk['var_date'] == '2026-10-23'
    # Independent rolling-Normal check: zero-mean RMS of the 20 log returns to Friday.
    ptax = dict(history['ptax'])
    ptax.update({d: v for d, v in inputs['history']['ptax'] if d > max(ptax)})
    window = [d for d in sorted(ptax) if d <= '2026-10-23'][-21:]
    returns = [math.log(ptax[b] / ptax[a]) for a, b in zip(window, window[1:])]
    sigma = math.sqrt(statistics.fmean(r * r for r in returns))
    z = statistics.NormalDist().inv_cdf(0.99)
    assert risk['var_pct']['rolling_normal'] == pytest.approx(-100 * math.expm1(-sigma * z))
    # Changing Monday's close changes the loss but none of Friday's forecasts.
    altered = copy.deepcopy(inputs)
    altered['history']['ptax'][-1][1] = 6.0
    rebuilt = build_runoff(altered, history, baseline, previous)['risk']
    assert rebuilt['var_pct'] == risk['var_pct'] and rebuilt['loss_pct'] != risk['loss_pct']
    assert math.floor(risk['min_ratio']) == 3 and math.floor(risk['max_ratio']) == 5  # "3 to 5 times"


def test_vote_shares_come_from_the_tse_count(report, baseline):
    vote = report['election']
    assert vote['votes'] == {'lula': 64256232, 'flavio': 59826041}
    assert round(vote['lula_pct'], 2) == 51.79 and round(vote['flavio_pct'], 2) == 48.21
    first = baseline['evidence']['election_first_round']
    assert first['flavio'] > first['lula']  # the runner-up won the runoff


def test_rates_compare_the_curve_with_the_same_survey_path(report, inputs):
    rates = report['rates']
    medians = {int(y): v for y, v in inputs['series']['focus_selic']['values_by_reference_year'].items()}
    # The arbitrary-horizon helper matches the 6 October convention over two whole years.
    start = date(2026, 10, 26)
    assert path_average(13.75, medians, start, date(2028, 10, 25)) == pytest.approx(survey_path_average(13.75, medians, start, 2), abs=1e-9)
    assert rates['jan28_change_bp'] == pytest.approx((14.80 - 12.859) * 100)
    assert rates['gap_jan28_friday'] == pytest.approx(12.859 - rates['path_jan28_friday'])
    assert rates['gap_jan28_monday'] == pytest.approx(14.80 - rates['path_jan28_monday'])
    assert 0 < rates['gap_jan28_friday'] < 0.5 < 2 < rates['gap_jan28_monday']
    # "No further cut is priced this year": the January 2027 contract is above today's CDI and the survey path.
    assert rates['jan27_monday'] > rates['cdi'] > rates['path_jan27_monday']
    assert rates['jan28_monday'] > report['carry']['selic']
    assert rates['cuts_expected_2026_bp'] == pytest.approx(50)


def test_the_shock_was_domestic(report):
    assert report['us2y']['monday'] <= report['us2y']['friday']
    assert report['equity']['change_pct'] == pytest.approx((176608.23 / 205082.56 - 1) * 100)


def test_original_rule_was_dropped_on_the_first_eligible_day(report, baseline):
    rule = report['rule']
    assert rule['date'] == baseline['rules']['earliest_entry'] == '2026-10-26'
    assert rule['value'] > baseline['rules']['abandon_above'] and rule['state'] == 'abandoned'


def test_future_prices_cannot_change_the_publication(inputs, history, baseline, previous):
    altered = copy.deepcopy(inputs)
    altered['history']['ptax'].append(['2026-10-27', 20])
    altered['history']['us_2y'].append(['2026-10-27', 20])
    assert build_runoff(altered, history, baseline, previous) == build_runoff(inputs, history, baseline, previous)


def test_every_source_is_dated_and_linked(report):
    assert len(report['sources']) >= 12
    for source in report['sources']:
        assert source['url'].startswith('https://') and source['label'] and date.fromisoformat(source['date'])


@pytest.mark.parametrize('lang', ['en', 'pt', 'fr'])
def test_current_note_resolves_and_precedes_archived_studies(thesis, inputs, lang):
    blocks = render(lang, thesis, inputs, date(2026, 10, 27))
    page = ''.join(blocks.values())
    text = unescape(re.sub(r'<[^>]+>', ' ', page))
    assert not re.search(r'\{[a-z_0-9]+\}', text)
    assert page.index('id="update"') < page.index('id="quant"')
    assert 'datetime="2026-10-27"' in blocks['hero']
    assert ('5.5003' if lang == 'en' else '5,5003') in blocks['hero']
    assert TEXT[lang]['archive'] in unescape(page)
    assert TEXT[lang]['monitor_note'] in unescape(blocks['hero'])
    assert unescape(TEXT[lang]['title']) in unescape(blocks['update'])


def test_languages_have_matching_fields_and_placeholders(report):
    def fields(value):
        if isinstance(value, str):
            return {field for _, field, _, _ in string.Formatter().parse(value) if field}
        if isinstance(value, dict):
            return {key: fields(item) for key, item in value.items()}
        return [fields(item) for item in value]
    assert fields(TEXT['en']) == fields(TEXT['pt']) == fields(TEXT['fr'])
    assert set(runoff_values(report, 'en')) == set(runoff_values(report, 'pt')) == set(runoff_values(report, 'fr'))
    for lang in TEXT:
        assert {row[2] for row in TEXT[lang]['review_rows']} <= set(TEXT[lang]['verdicts'])


def test_missing_followup_keeps_original_page_available(thesis, inputs):
    old = copy.deepcopy(thesis)
    old.pop('current_update')
    page = render('en', old, inputs, date(2026, 10, 27))
    assert page['update'] == ''
    assert 'datetime="2026-10-06"' in page['hero']
