"""Shared presentation copy and lightweight saved-data validation. No network imports."""
from __future__ import annotations
from datetime import date, datetime, timezone
from math import isfinite
from urllib.parse import urlsplit

COPY = {
'en': {
 'takeaway_label':'THE VIEW · CONDITIONAL, NOT ACTIVE',
 'takeaway':"A smaller Brazil–U.S. rate gap could weaken the real. My saved view is to wait: consider buying USD only above 5.22, with rates confirmation. Stronger commodity exports could overturn the idea.",
 'age':'Saved {days} days ago · observation periods differ · this page does not track whether the trade has since triggered.',
 'navigation':'Explore the research', 'nav':['Scenarios', 'Paper trade', 'Commodities', 'Evidence'],
 'assumptions':'Assumed decisions', 'watch':'Evidence to watch', 'entry':'Entry / confirmation', 'invalidation':'Invalidation / after entry', 'review':'Review zone / not a target', 'catalyst':'Catalyst / timing',
 'meeting':'Both meetings run on 15–16 September 2026; decisions are scheduled for 16 September. Reassess the idea after the announcements and their guidance.',
 'scenario_note':'Saved September 2026 cases, not forecasts with assigned probabilities. The base case reflects the saved pricing anchors; FX effects are conditional, all else equal. An expected decision alone is not a new trading edge.',
 'pricing_note':'B3: 1 September 2026; about 21.8 basis points of easing estimated from DI futures, not a published Copom probability. CME: 1 September 2026, 02:07 CT; the final refresh failed. These saved inputs are not current pricing. No joint probability is assigned.',
 'fx_change':'USD/BRL changed {change}% over approximately one month in the saved data. A rise means the dollar strengthened against the real; the inverse BRL/USD return has a different magnitude.',
 'ptax_limit':'PTAX is an official daily reference, not a live or executable spot quote. Levels are rounded research rules; 5.22 is slightly below the exact saved high of 5.2233. Costs, slippage and position sizing are not modelled.',
 'forecast_table':'Focus annual median forecasts', 'comparison':'Compared with', 'directions':['higher','lower','unchanged'],
 'units':{'USD per barrel':'USD / barrel','USD per metric ton':'USD / tonne','US cents per pound':'US cents / lb'},
 'download':'Download the research brief · English PDF', 'process':'Research process and project scope',
 'pdf_title':'Brazil macro: one conditional trade', 'pdf_subtitle':'Rates, the real and commodity exports',
 'saved':'Fixed research snapshot', 'observations':'OBSERVED · SAVED DATA', 'interpretation':'INTERPRETATION', 'scenario_heading':'SCENARIOS · ASSUMPTIONS', 'trade_heading':'PAPER TRADE · CONDITIONAL RULES',
 'commodity_heading':'COMMODITIES · A CROSS-CHECK', 'method_heading':'METHOD AND SOURCE LIMITS',
 'disclaimer':'Educational analysis · not investment advice · no actual execution or claimed performance.',
 'status':'No position at the saved snapshot; subsequent activation is not monitored.',
 'limits':'Focus is a survey, not a policy commitment. The policy gap subtracts the Fed target-range midpoint from Selic; it is not an investment return. Commodity prices have different observation periods. The PDF is generated from saved files and does not update automatically.',
 'risk':'Main risks: Brazil keeps rates higher; the Fed does not hike; fiscal improvement, stronger exports or global risk appetite support BRL. Already-priced decisions may produce little reaction.',
 'channels': ['Oil can lift export income but also fuel inflation.', 'Iron ore connects export receipts to steel demand, especially in China.', 'Soybeans bring export dollars; harvest timing and demand shape flows.', 'Sugar competes with ethanol for cane, linking exports to fuel economics.'],
 'metric_names':['USD/BRL PTAX midpoint','Selic target','Brazil–U.S. policy gap','U.S. two-year yield'],
 'source_heading':'Official sources', 'date_label':'Observation', 'rule':'Decision rule',
},
'pt': {
 'takeaway_label':'A VISÃO · CONDICIONAL, SEM POSIÇÃO',
 'takeaway':'Uma diferença menor entre os juros do Brasil e dos EUA pode enfraquecer o real. Minha visão salva é esperar: considerar a compra de dólar só acima de 5.22, com confirmação dos juros. Exportações de commodities mais fortes podem invalidar a ideia.',
 'age':'Dados salvos há {days} dias · os períodos de observação diferem · esta página não acompanha se o gatilho foi atingido depois.',
 'navigation':'Explorar a análise', 'nav':['Cenários','Operação simulada','Commodities','Evidências'],
 'assumptions':'Decisões assumidas', 'watch':'Evidências a acompanhar', 'entry':'Entrada / confirmação', 'invalidation':'Invalidação / após a entrada', 'review':'Zona de reavaliação / não é alvo', 'catalyst':'Catalisador / prazo',
 'meeting':'As duas reuniões ocorrem em 15–16 de setembro de 2026; as decisões estão previstas para 16 de setembro. Reavaliar a ideia após os anúncios e a orientação dos bancos centrais.',
 'scenario_note':'Cenários salvos para setembro de 2026, sem probabilidades atribuídas. O cenário-base reflete as referências de preços salvas; os efeitos no câmbio são condicionais, mantidos os demais fatores. Uma decisão esperada não cria, por si só, uma oportunidade.',
 'pricing_note':'B3: 1 de setembro de 2026; cerca de 21,8 pontos-base de corte estimados pelos futuros de DI, não uma probabilidade publicada do Copom. CME: 1 de setembro de 2026, 02:07 CT; a última atualização falhou. São referências salvas, não preços atuais. Não há probabilidade conjunta.',
 'fx_change':'O USD/BRL variou {change}% em aproximadamente um mês nos dados salvos. Uma alta significa valorização do dólar frente ao real; o retorno inverso, BRL/USD, tem magnitude diferente.',
 'ptax_limit':'A PTAX é uma referência oficial diária, não uma cotação à vista em tempo real ou executável. Os níveis são regras arredondadas; 5.22 fica ligeiramente abaixo da máxima exata de 5.2233. Custos, deslizamento de preço e tamanho da posição não são modelados.',
 'forecast_table':'Medianas anuais da pesquisa Focus', 'comparison':'Comparação com', 'directions':['em alta','em baixa','estável'],
 'units':{'USD per barrel':'USD / barril','USD per metric ton':'USD / tonelada','US cents per pound':'centavos de USD / libra'},
 'download':'Baixar o relatório · PDF em português', 'process':'Método de análise e escopo do projeto',
 'pdf_title':'Brasil macro: uma operação condicional', 'pdf_subtitle':'Juros, real e exportações de commodities',
 'saved':'Dados de pesquisa salvos', 'observations':'OBSERVAÇÕES · DADOS SALVOS', 'interpretation':'INTERPRETAÇÃO', 'scenario_heading':'CENÁRIOS · PREMISSAS', 'trade_heading':'OPERAÇÃO SIMULADA · REGRAS CONDICIONAIS',
 'commodity_heading':'COMMODITIES · TESTE DE COERÊNCIA', 'method_heading':'MÉTODO E LIMITAÇÕES DAS FONTES',
 'disclaimer':'Análise educacional · não é recomendação de investimento · sem execução real ou desempenho alegado.',
 'status':'Sem posição no momento dos dados salvos; a ativação posterior não é acompanhada.',
 'limits':'Focus é uma pesquisa, não um compromisso de política monetária. O diferencial subtrai o ponto médio da faixa americana da Selic; não representa retorno de investimento. As commodities têm períodos de observação diferentes. O PDF é gerado a partir dos arquivos salvos, sem atualização automática.',
 'risk':'Principais riscos: o Brasil mantém juros altos; o Fed não os eleva; melhora fiscal, exportações fortes ou apetite global por risco apoiam o real. Decisões já refletidas nos preços podem gerar pouca reação.',
 'channels':['O petróleo pode elevar receitas de exportação, mas também a inflação dos combustíveis.', 'O minério liga receitas de exportação à demanda por aço, sobretudo na China.', 'A soja gera dólares de exportação; a safra e a demanda influenciam os fluxos.', 'O açúcar disputa a cana com o etanol, conectando exportações aos combustíveis.'],
 'metric_names':['Ponto médio da PTAX USD/BRL','Meta Selic','Diferencial Brasil–EUA','Juro americano de dois anos'],
 'source_heading':'Fontes oficiais', 'date_label':'Observação', 'rule':'Regra de decisão',
},
'fr': {
 'takeaway_label':'LA VUE · CONDITIONNELLE, SANS POSITION',
 'takeaway':"Un écart de taux Brésil–États-Unis plus faible pourrait peser sur le real. Ma position dans cette étude est d'attendre : envisager un achat de dollars seulement au-dessus de 5.22, avec confirmation des taux. Des exportations de matières premières plus fortes pourraient invalider l'idée.",
 'age':"Données enregistrées il y a {days} jours · les périodes d'observation diffèrent · cette page ne suit pas un éventuel déclenchement ultérieur.",
 'navigation':"Explorer l'analyse", 'nav':['Scénarios','Opération fictive','Matières premières','Données'],
 'assumptions':'Décisions supposées', 'watch':'Signaux à suivre', 'entry':'Entrée / confirmation', 'invalidation':"Invalidation / après l'entrée", 'review':"Zone de réexamen / pas un objectif", 'catalyst':'Catalyseur / calendrier',
 'meeting':"Les deux réunions ont lieu les 15–16 septembre 2026 ; les décisions sont prévues le 16 septembre. Réexaminer l'idée après les annonces et les indications des banques centrales.",
 'scenario_note':"Scénarios enregistrés pour septembre 2026, sans probabilités attribuées. Le scénario central reflète les références de prix enregistrées ; les effets de change sont conditionnels, toutes choses égales par ailleurs. Une décision attendue ne crée pas à elle seule une opportunité.",
 'pricing_note':"B3 : 1er septembre 2026 ; environ 21,8 points de base de baisse estimés à partir des contrats DI, pas une probabilité publiée du Copom. CME : 1er septembre 2026, 02:07 CT ; la dernière actualisation a échoué. Ces références ne sont pas des prix actuels. Aucune probabilité conjointe n'est attribuée.",
 'fx_change':"L'USD/BRL a varié de {change}% sur environ un mois dans les données enregistrées. Une hausse signifie que le dollar s'est apprécié face au real ; le rendement inverse, BRL/USD, a une amplitude différente.",
 'ptax_limit':"La PTAX est une référence officielle quotidienne, pas un cours au comptant en direct ou exécutable. Les seuils sont arrondis ; 5.22 est légèrement inférieur au sommet exact de 5.2233. Les coûts, le glissement de prix et la taille de position ne sont pas modélisés.",
 'forecast_table':"Prévisions médianes annuelles Focus", 'comparison':'Comparaison avec', 'directions':['en hausse','en baisse','stable'],
 'units':{'USD per barrel':'USD / baril','USD per metric ton':'USD / tonne','US cents per pound':'cents USD / livre'},
 'download':"Télécharger la note · PDF en français", 'process':"Méthode de recherche et périmètre du projet",
 'pdf_title':'Brésil macro : une opération conditionnelle', 'pdf_subtitle':'Taux, real et exportations de matières premières',
 'saved':'Données de recherche enregistrées', 'observations':'OBSERVATIONS · DONNÉES ENREGISTRÉES', 'interpretation':'INTERPRÉTATION', 'scenario_heading':'SCÉNARIOS · HYPOTHÈSES', 'trade_heading':'OPÉRATION FICTIVE · RÈGLES CONDITIONNELLES',
 'commodity_heading':'MATIÈRES PREMIÈRES · VÉRIFICATION', 'method_heading':'MÉTHODE ET LIMITES DES SOURCES',
 'disclaimer':"Analyse pédagogique · pas un conseil en investissement · aucune exécution réelle ni performance revendiquée.",
 'status':"Aucune position à la date des données ; les déclenchements ultérieurs ne sont pas suivis.",
 'limits':"Focus est une enquête, pas un engagement monétaire. L'écart soustrait le milieu de la fourchette américaine au Selic ; ce n'est pas un rendement d'investissement. Les matières premières ont des périodes d'observation différentes. Le PDF est généré à partir des fichiers enregistrés, sans mise à jour automatique.",
 'risk':"Principaux risques : le Brésil maintient des taux élevés ; la Fed ne les relève pas ; une amélioration budgétaire, des exportations solides ou l'appétit mondial pour le risque soutiennent le real. Des décisions déjà anticipées peuvent susciter peu de réaction.",
 'channels':["Le pétrole peut accroître les recettes d'exportation, mais aussi l'inflation des carburants.", "Le minerai relie les exportations à la demande d'acier, surtout en Chine.", "Le soja apporte des dollars ; les récoltes et la demande influencent les flux.", "Le sucre concurrence l'éthanol pour la canne, reliant exportations et carburants."],
 'metric_names':['Point médian PTAX USD/BRL','Taux directeur Selic','Écart Brésil–États-Unis','Taux américain à deux ans'],
 'source_heading':'Sources officielles', 'date_label':'Observation', 'rule':'Règle de décision',
}}


def copy_for(language):
    return COPY[language]


def safe_url(value):
    if isinstance(value, str) and urlsplit(value).scheme == 'https' and urlsplit(value).netloc:
        return value.replace('"', '%22').replace('<', '%3C').replace('>', '%3E')
    return ''


def snapshot_age(value, today=None):
    try:
        observed = datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc).date()
        age = ((today or datetime.now(timezone.utc).date()) - observed).days
        return age if age >= 0 else None
    except (ValueError, TypeError, AttributeError):
        return None


def format_period(value, frequency, language):
    observed = date.fromisoformat(value)
    if frequency == 'Quarterly':
        return f'{"Q" if language == "en" else "T"}{(observed.month-1)//3+1} {observed.year}'
    if frequency == 'Monthly':
        return observed.strftime('%Y-%m')
    return observed.isoformat()


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def _valid_series(key, item):
    try:
        date.fromisoformat(item['latest_observation_date'])
        if not all(isinstance(item[x], str) for x in ('label', 'unit')):
            return False
        if key.startswith('focus_'):
            return _number(item['selected_value']) and _number(item['selected_1_month_change_pp']) and bool(item['values_by_reference_year']) and all(_number(v) for v in item['values_by_reference_year'].values())
        if key == 'fed_target_range':
            return all(_number(item[x]) for x in ('lower','upper','midpoint'))
        if not _number(item['value']):
            return False
        if key == 'ptax_usd_brl_midpoint':
            rr=item['twenty_observation_range']
            return _number(item['one_month_change_percent']) and all(_number(rr[x]) for x in ('low','high','midpoint','width')) and rr['high'] > rr['low']
        return True
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def sanitize_snapshot(name, payload):
    if not isinstance(payload, dict):
        return {}
    result = dict(payload)
    if name == 'commodity_snapshot.json':
        result['commodities'] = {}
        items=payload.get('commodities', {})
        if not isinstance(items, dict): return result
        for key,item in items.items():
            try:
                if not all(isinstance(item[x], str) for x in ('label','benchmark','frequency','unit','channel','source_url')): continue
                date.fromisoformat(item['latest_date']); date.fromisoformat(item['previous_date'])
                if not (_number(item['latest']) and _number(item['previous']) and item['previous'] > 0): continue
                result['commodities'][key]=item
            except (KeyError, ValueError, TypeError): continue
        return result
    raw=payload.get('series', {})
    result['series']={k:v for k,v in raw.items() if _valid_series(k,v)} if isinstance(raw,dict) else {}
    for key in ('scenarios','paper_trades','source_registry'):
        raw=payload.get(key, [])
        result[key]=[x for x in raw if isinstance(x,dict)] if isinstance(raw,list) else []
    for key in ('scenario_label_audit','trade_threshold_calculations'):
        if not isinstance(result.get(key),dict): result[key]={}
    if not all(isinstance(x.get('brief_summary'),dict) and isinstance(x.get('confirmation_signals'),list) for x in result['scenarios']): result['scenarios']=[]
    if not all(all(isinstance(x.get(k),str) for k in ('thesis','entry_logic','invalidation_condition','profit_taking_logic')) for x in result['paper_trades']): result['paper_trades']=[]
    return result

COPY['en']['horizon'] = 'Research horizon: approximately two to four weeks around the September meetings. The base case supports the idea; the more restrictive relative-rate case invalidates it.'
COPY['pt']['horizon'] = 'Horizonte da análise: aproximadamente duas a quatro semanas ao redor das reuniões de setembro. O cenário-base apoia a ideia; o cenário de juros relativos mais restritivos a invalida.'
COPY['fr']['horizon'] = "Horizon de recherche : environ deux à quatre semaines autour des réunions de septembre. Le scénario central soutient l'idée ; le scénario de taux relatifs plus restrictifs l'invalide."

COPY['en'].update({
 'takeaway_label':'THE VIEW · NO POSITION AT THE SAVED SNAPSHOT',
 'entry_short':'Wait for a daily PTAX midpoint above 5.22, with the U.S. two-year yield near or above 4.34% OR the policy gap not widening. No position at the saved 5.1567 reference.',
 'invalidation_short':'After entry: exit after two consecutive daily PTAX midpoints below 5.16, OR if the policy gap fails to narrow and stays near or above 10.375 percentage points.',
 'review_short':'Reassess around 5.35–5.36, or sooner if rates confirmation reverses. This is a review zone, not a guaranteed target.',
 'brazil_bank':'Brazil / Copom','us_bank':'U.S. / FOMC',
 'units_note':'25 basis points (bp) = 0.25 percentage point (pp). The rate gap compares annual policy rates, not investment returns.',
 'pricing_method':'The B3 estimate compounds DI futures over the meeting window. It ignores term premia and assumes no other rate change within that window. A Focus year-end median is not a meeting-specific forecast.',
})
COPY['pt'].update({
 'takeaway_label':'A VISÃO · SEM POSIÇÃO NOS DADOS SALVOS',
 'entry_short':'Esperar a PTAX diária fechar acima de 5,22, com o juro americano de dois anos perto ou acima de 4,34% OU sem abertura do diferencial de juros. Sem posição na referência salva de 5,1567.',
 'invalidation_short':'Após a entrada: sair após duas PTAX diárias consecutivas abaixo de 5,16, OU se o diferencial não diminuir e permanecer perto ou acima de 10,375 pontos percentuais.',
 'review_short':'Reavaliar perto de 5,35–5,36, ou antes se os juros deixarem de confirmar a tese. É uma zona de reavaliação, não um alvo garantido.',
 'brazil_bank':'Brasil / Copom','us_bank':'EUA / FOMC',
 'units_note':'25 pontos-base = 0,25 ponto percentual (p.p.). O diferencial compara juros anuais de política monetária, não retornos de investimento.',
 'pricing_method':'A estimativa da B3 usa capitalização dos futuros de DI na janela da reunião. Ignora prêmios de prazo e pressupõe que não haja outra mudança de juros nessa janela. A mediana Focus de fim de ano não é uma previsão específica para a reunião.',
})
COPY['fr'].update({
 'takeaway_label':'LA VUE · SANS POSITION À LA DATE DES DONNÉES',
 'entry_short':"Attendre un point médian PTAX quotidien au-dessus de 5,22, avec le taux américain à deux ans proche ou au-dessus de 4,34 % OU un écart de taux qui ne s'élargit pas. Aucune position au niveau enregistré de 5,1567.",
 'invalidation_short':"Après l'entrée : sortir après deux points médians PTAX quotidiens consécutifs sous 5,16, OU si l'écart ne diminue pas et reste proche ou au-dessus de 10,375 points.",
 'review_short':"Réexaminer vers 5,35–5,36, ou plus tôt si les taux ne confirment plus la thèse. Il s'agit d'une zone de réexamen, pas d'un objectif garanti.",
 'brazil_bank':'Brésil / Copom','us_bank':'États-Unis / FOMC',
 'units_note':"25 points de base = 0,25 point de pourcentage. L'écart compare les taux directeurs annuels, pas les rendements d'investissement.",
 'pricing_method':"L'estimation B3 utilise la capitalisation des contrats DI sur la période de la réunion. Elle ignore les primes de terme et suppose aucun autre changement de taux sur cette période. La médiane Focus de fin d'année n'est pas une prévision propre à cette réunion.",
})


def source_url_for(url, observation_date):
    """Bound SGS links to the cited day; unbounded history requests can return 406."""
    from urllib.parse import urlencode
    if isinstance(url,str) and url.startswith('https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados'):
        try:
            observed=date.fromisoformat(observation_date).strftime('%d/%m/%Y')
        except (ValueError,TypeError):
            return safe_url(url)
        return url.split('?')[0]+'?'+urlencode({'formato':'json','dataInicial':observed,'dataFinal':observed})
    return safe_url(url)
