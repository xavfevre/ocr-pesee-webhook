# -*- coding: utf-8 -*-
"""Tableau de bord 23 v3 : CA HT = écritures comptables des factures clients validées sur comptes de produits
(lignes d'article ET lignes de taxe : TGAP, REP en taxe), via les champs stockés account.move.line.x_ca_ht /
x_activite. Tuile, graphiques, tableau par activité et évolution mensuelle passent sur ce modèle ; le tableau
« CA par article » (lignes d'article) et le bloc par compte restent. Usage : python dash23_v3.py dry|apply"""
import os, ssl, sys, json, io, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
assert x('ir.model.fields', 'search_count', [['model', '=', 'account.move.line'], ['name', 'in', ['x_ca_ht', 'x_activite']]]) == 2
js = json.loads(io.open('audit/dash23.AFTER_v2.json', encoding='utf-8').read())
sh = js['sheets'][0]
DOM = ['&', '&', '&', ['parent_state', '=', 'posted'], ['move_id.move_type', 'in', ['out_invoice', 'out_refund']],
       ['account_id.account_type', 'in', ['income', 'income_other']], ['display_type', 'in', ['product', 'tax']]]
FM = {'flt_period': {'chain': 'date', 'type': 'date', 'offset': 0},
      'flt_company': {'chain': 'company_id', 'type': 'many2one'},
      'flt_categ': {'chain': 'product_id.categ_id', 'type': 'many2one'}}
# pivot 2 (activité) et pivot 3 (mensuel) : sur les écritures
js['pivots']['2'] = {'type': 'ODOO', 'model': 'account.move.line', 'name': 'CA par activité (écritures)', 'formulaId': '2',
                     'rows': [{'fieldName': 'company_id'}, {'fieldName': 'x_activite'}], 'columns': [],
                     'measures': [{'id': 'x_ca_ht', 'fieldName': 'x_ca_ht', 'aggregator': 'sum', 'userDefinedName': 'CA HT Net'},
                                  {'id': 'quantity', 'fieldName': 'quantity', 'aggregator': 'sum', 'userDefinedName': 'Qté'}],
                     'domain': DOM, 'context': {}, 'sortedColumn': None, 'fieldMatching': FM}
js['pivots']['3'] = {'type': 'ODOO', 'model': 'account.move.line', 'name': 'CA par mois (écritures)', 'formulaId': '3',
                     'rows': [{'fieldName': 'company_id'}, {'fieldName': 'x_activite'}],
                     'columns': [{'fieldName': 'date', 'granularity': 'year'}, {'fieldName': 'date', 'granularity': 'month'}],
                     'measures': [{'id': 'x_ca_ht', 'fieldName': 'x_ca_ht', 'aggregator': 'sum', 'userDefinedName': 'CA HT Net'}],
                     'domain': DOM, 'context': {}, 'sortedColumn': None, 'fieldMatching': FM}
# tuile
sh['cells']['A5'] = '=PIVOT.VALUE(2,"x_ca_ht")'
sh['cells']['A2'] = 'Écritures des factures clients validées, ventes + contributions TGAP/REP · filtres Période / Société / Catégorie en haut'
sh['cells']['A40'] = 'DÉTAIL PAR SOCIÉTÉ ET ACTIVITÉ (CA HT + quantités, contributions incluses)'
sh['cells']['A165'] = "CA PAR ARTICLE — Société › Activité › Article (lignes d'article, hors contributions en taxe)"
# graphiques Odoo : même présentation, modèle écritures, mesure x_ca_ht
for fg in sh['figures']:
    d = fg['data']
    gb = {'chart-ca-soc': ['company_id'], 'chart-ca-cat': ['x_activite'], 'chart-ca-mois': ['date:month']}[fg['id']]
    d['metaData'].update({'groupBy': gb, 'measure': 'x_ca_ht', 'resModel': 'account.move.line'})
    d['searchParams'].update({'domain': DOM, 'groupBy': gb})
    d['fieldMatching'] = FM
data = json.dumps(js, ensure_ascii=False)
io.open('audit/dash23.AFTER_v3.json', 'w', encoding='utf-8').write(data)
print('pivots :', {k: (v['name'], v['model']) for k, v in js['pivots'].items()})
print('figures :', [(fg['id'], fg['data']['metaData']['resModel'], fg['data']['metaData']['measure'], fg['data']['metaData']['groupBy']) for fg in sh['figures']])
if mode == 'apply':
    x('spreadsheet.dashboard', 'write', [23], {'spreadsheet_data': data})
    print('tableau de bord 23 mis à jour (v3)')
