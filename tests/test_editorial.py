import ast
import re
import io
import json
from datetime import date
from pathlib import Path

import pytest
from pypdf import PdfReader
from streamlit.testing.v1 import AppTest
from src.editorial import COPY, format_period, snapshot_age, sanitize_snapshot, safe_url
from src.localization import UI_FR
from src.brief import generate_market_brief


def test_all_static_labels_have_french_translations():
    tree=ast.parse(Path('app.py').read_text())
    missing=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='ui' and len(node.args)==2 and isinstance(node.args[0],ast.Constant):
            if node.args[0].value not in UI_FR: missing.append(node.args[0].value)
    assert not missing
    assert COPY['en'].keys()==COPY['pt'].keys()==COPY['fr'].keys()
    assert 'matérias-primas' not in str(COPY['pt'])


def test_periods_and_age_are_honest():
    assert format_period('2026-04-01','Quarterly','en')=='Q2 2026'
    assert format_period('2026-04-01','Quarterly','pt')=='T2 2026'
    assert format_period('2026-07-01','Monthly','fr')=='2026-07'
    assert snapshot_age('2026-09-02T00:40:27Z',date(2026,9,10))==8
    assert snapshot_age('bad',date(2026,9,10)) is None
    assert snapshot_age('2026-09-12T00:00:00Z',date(2026,9,10)) is None
    assert safe_url('javascript:alert(1)')==''


@pytest.mark.parametrize('key',list(json.loads(Path('research/data_snapshot.json').read_text())['series']))
def test_partial_macro_outage_keeps_other_sections(monkeypatch,key):
    original=Path.open
    payload=json.loads(Path('research/data_snapshot.json').read_text())
    payload['series'][key]={'value':float('nan')}
    def read(path,*args,**kwargs):
        if path.name=='data_snapshot.json': return io.StringIO(json.dumps(payload))
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',read)
    app=AppTest.from_file('app.py').run(timeout=10)
    assert not app.exception
    assert any('Oil' in m.value for m in app.markdown)
    assert not any(re.search(r'\bnan\b', m.value.lower()) for m in app.markdown)


@pytest.mark.parametrize('filename',['data_snapshot.json','commodity_snapshot.json'])
@pytest.mark.parametrize('raw',['{invalid', 'null', '{"series":null,"commodities":null,"scenarios":null,"paper_trades":null}'])
def test_broken_optional_snapshot_does_not_crash(monkeypatch,filename,raw):
    original=Path.open
    def read(path,*args,**kwargs):
        if path.name==filename: return io.StringIO(raw)
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',read)
    app=AppTest.from_file('app.py').run(timeout=10)
    assert not app.exception
    assert len(app.title)==1


def test_bad_commodity_does_not_suppress_good_ones():
    payload=json.loads(Path('research/commodity_snapshot.json').read_text())
    payload['commodities']['brent']['previous']=0
    result=sanitize_snapshot('commodity_snapshot.json',payload)
    assert set(result['commodities'])=={'iron_ore','soybeans','sugar'}


@pytest.mark.parametrize('language',['en','pt','fr'])
def test_localized_pdf_complete_and_searchable(tmp_path,language):
    pdf=tmp_path/f'{language}.pdf'
    generate_market_brief('research/data_snapshot.json',pdf,tmp_path/'note.md',language)
    reader=PdfReader(pdf); text='\n'.join(p.extract_text() for p in reader.pages)
    assert len(reader.pages)==3
    assert COPY[language]['pdf_title'] in text
    assert '5.2233' in text.replace(',', '.') and '5.3613' in text.replace(',', '.') and '2026-09-11' in text
    assert len(text)>4500
    assert len(reader.pages[-1].get('/Annots'))>=13
    if language!='en':
        assert 'No position at the saved snapshot' not in text
        assert 'Entry / confirmation' not in text


def test_selic_link_is_bounded_to_observed_day():
    from src.editorial import source_url_for
    from urllib.parse import parse_qs,urlsplit
    url=source_url_for('https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json','2026-09-01')
    query=parse_qs(urlsplit(url).query)
    assert query['dataInicial']==['01/09/2026']==query['dataFinal']


def test_french_trade_preserves_alternative_confirmation():
    from src.localization import TRADE_FR
    assert "ou une baisse effective de l'écart de taux" in TRADE_FR['entry_logic']
    assert 'deux clôtures PTAX quotidiennes' in TRADE_FR['invalidation_condition']
    assert "ne diminue pas" in TRADE_FR['invalidation_condition']
