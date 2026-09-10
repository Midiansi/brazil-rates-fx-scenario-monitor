"""Print-friendly, fully localized research brief. Generation is offline only."""
from pathlib import Path
from html import escape
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from src.editorial import copy_for, format_period, source_url_for
from src.localization import SCENARIO_PT, SCENARIO_FR, TRADE_PT, TRADE_FR, COMMODITY_PT, COMMODITY_FR

INK=colors.HexColor('#102634'); TEAL=colors.HexColor('#087969'); MUTED=colors.HexColor('#425966'); PALE=colors.HexColor('#F0F6F4'); LINE=colors.HexColor('#CBDAD6')


def render_research_pdf(snapshot, commodities, output, language='en'):
    c=copy_for(language); story=[]; width=A4[0]-84
    styles={
      'body':ParagraphStyle('body', fontName='Helvetica', fontSize=9.5, leading=13, textColor=INK, spaceAfter=8),
      'small':ParagraphStyle('small', fontName='Helvetica', fontSize=8.5, leading=12, textColor=MUTED, spaceAfter=6),
      'title':ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=23, leading=27, textColor=INK, spaceAfter=12),
      'heading':ParagraphStyle('heading', fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=TEAL, spaceBefore=10, spaceAfter=8),
      'card':ParagraphStyle('card', fontName='Helvetica', fontSize=9, leading=12.5, textColor=INK, spaceAfter=4),
    }
    def clean(value): return escape(str(value)).replace('–','-').replace('—','-').replace('’',"'")
    def p(value,style='body'): return Paragraph(clean(value), styles[style])
    def heading(key): story.append(p(c[key],'heading'))
    def box(lines):
        t=Table([[p(x, 'card')] for x in lines], colWidths=[width]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE),('BOX',(0,0),(-1,-1),.5,LINE),('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)])); return t
    def pair(label, body): return KeepTogether([p(label,'heading'),p(body)])
    series=snapshot['series']; trade=snapshot['paper_trades'][0]
    dt=TRADE_PT if language=='pt' else TRADE_FR if language=='fr' else trade
    translation=SCENARIO_PT if language=='pt' else SCENARIO_FR if language=='fr' else {}
    story += [p('BRAZIL MACRO / ROMEO MUGNIER DE ALMEIDA','small'),p(c['pdf_title'],'title'),p(c['pdf_subtitle']),p(c['saved']+': '+snapshot['retrieved_at_brasilia']+' · '+language.upper(),'small'),box([c['takeaway']])]
    heading('observations')
    metrics=[]
    for key,label,unit in zip(('ptax_usd_brl_midpoint','selic_target','brazil_us_policy_differential','us_2_year_treasury'),c['metric_names'],('BRL / USD','%', 'pp' if language=='en' else 'p.p.' if language=='pt' else 'points','%')):
        item=series[key]; value=f"{item['value']:.4f}" if 'ptax' in key else f"{item['value']:.3f}" if 'differential' in key else f"{item['value']:.2f}"
        metrics.append(Paragraph(clean(label)+'<br/><font size=14><b>'+clean(value+' '+unit)+'</b></font><br/>'+item['latest_observation_date'], styles['card']))
    mt=Table([metrics[:2],metrics[2:]],colWidths=[width/2]*2)
    mt.setStyle(TableStyle([('BOX',(0,0),(-1,-1),.5,LINE),('INNERGRID',(0,0),(-1,-1),.5,LINE),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),10)]));story.append(mt)
    heading('scenario_heading');story.append(p(c['scenario_note'],'small'))
    for scenario in snapshot['scenarios']:
        sc=translation.get(scenario['name'],scenario); b=sc['brief_summary']
        story.append(KeepTogether([p(sc['name'],'heading'),p('Copom: '+b['copom']+' · FOMC: '+b['fomc'],'card'),p(b['differential']+' · '+b['brl_usd_pressure'],'card'),p(c['watch']+': '+b['confirmation'],'small')]))
    story.append(PageBreak())
    story += [p(c['trade_heading'],'title'),p(c['status'],'small'),box([dt['thesis']])]
    for label,key in (('entry','entry_logic'),('invalidation','invalidation_condition'),('review','profit_taking_logic')):
        story.append(pair(c[label],dt[key]))
    story.append(pair(c['catalyst'],c['meeting']))
    story += [p(c['risk']),p(c['ptax_limit'],'small')]
    heading('commodity_heading')
    ct=COMMODITY_PT if language=='pt' else COMMODITY_FR if language=='fr' else {}
    for i,(key,item) in enumerate(commodities.get('commodities',{}).items()):
        name=ct.get(key,item)['label']; unit=c['units'][item['unit']]; change=(item['latest']/item['previous']-1)*100
        source='EIA / FRED' if key=='brent' else 'IMF / FRED' if language=='en' else 'FMI / FRED'
        story.append(KeepTogether([p(name+' · '+f"{item['latest']:.2f} {unit} · {change:+.1f}%",'card'),p(format_period(item['latest_date'],item['frequency'],language)+' / '+c['comparison'].lower()+' '+format_period(item['previous_date'],item['frequency'],language)+' · '+source,'small'),p(c['channels'][i],'small')]))
    story.append(PageBreak())
    story += [p(c['method_heading'],'title'),p(c['limits']),p(c['horizon']),p(c['pricing_note']),p(c['fx_change'].format(change=f"{series['ptax_usd_brl_midpoint']['one_month_change_percent']:+.2f}"))]
    # Keep the deeper scenario risks visible in the printable record.
    for scenario in snapshot['scenarios']:
        sc=translation.get(scenario['name'],scenario)
        story.append(pair(sc['name'],sc['principal_risk']))
    # Record the original evidence behind the trade, not only the levels.
    from src.brief import build_brief_context
    context = build_brief_context(snapshot)
    if language == 'en':
        changes = context['what_changed']
    elif language == 'pt':
        changes = ['A mediana Focus da Selic de 2026 caiu 0,25 ponto percentual em um mês; a mediana do IPCA caiu 0,0899 ponto.', 'O diferencial de juros caiu 0,25 ponto em um mês. O juro americano de dois anos subiu 0,10 ponto nas últimas cinco observações.']
    else:
        changes = ["La médiane Focus du Selic 2026 a baissé de 0,25 point sur un mois ; celle de l'IPCA a reculé de 0,0899 point.", "L'écart de taux a reculé de 0,25 point sur un mois. Le taux américain à deux ans a augmenté de 0,10 point sur les cinq dernières observations."]
    for change in changes: story.append(p(change,'small'))
    heading('source_heading')
    links=[('BCB · Focus',series['focus_selic']['source_url']),('BCB · PTAX',series['ptax_usd_brl_midpoint']['source_url']),('BCB · Selic / SGS 432',series['selic_target']['source_url']),('Federal Reserve · FOMC',snapshot['event_context']['fomc_september_2026']['source_url']),('BCB · Copom',snapshot['event_context']['copom_september_2026']['source_url']),('FRED · DFEDTARL','https://fred.stlouisfed.org/series/DFEDTARL'),('FRED · DGS2','https://fred.stlouisfed.org/series/DGS2'),('CME FedWatch',snapshot['scenario_label_audit']['fomc']['source_url']),('B3 · DI1',snapshot['scenario_label_audit']['copom']['source_url'])]
    links += [('FRED · DFEDTARU','https://fred.stlouisfed.org/series/DFEDTARU'),('FRED · DGS10','https://fred.stlouisfed.org/series/DGS10')]
    links += [(('EIA' if key=='brent' else 'IMF')+' / FRED · '+item['series_id'],item['source_url']) for key,item in commodities.get('commodities',{}).items()]
    links=[(label,source_url_for(url,series["selic_target"]["latest_observation_date"])) for label,url in links]
    source_cells=[Paragraph('<a href="'+escape(url,quote=True)+'" color="#087969">'+clean(label)+'</a>',styles['small']) for label,url in links]
    if len(source_cells)%2: source_cells.append(p('','small'))
    source_table=Table([source_cells[i:i+2] for i in range(0,len(source_cells),2)],colWidths=[width/2]*2)
    source_table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
    story.append(source_table)
    story += [Spacer(1,8),p(c['disclaimer'],'small')]
    def footer(canvas,doc):
        canvas.setStrokeColor(TEAL);canvas.setLineWidth(2);canvas.line(42,A4[1]-26,A4[0]-42,A4[1]-26)
        canvas.setStrokeColor(LINE);canvas.setLineWidth(.5);canvas.line(42,34,A4[0]-42,34)
        canvas.setFillColor(MUTED);canvas.setFont('Helvetica',8);canvas.drawString(42,22,'BRAZIL MACRO · '+language.upper());canvas.drawRightString(A4[0]-42,22,str(doc.page))
    destination=Path(output);destination.parent.mkdir(parents=True,exist_ok=True)
    doc=SimpleDocTemplate(str(destination),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=42,bottomMargin=48,title=c['pdf_title'],author='Romeo Mugnier de Almeida')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
