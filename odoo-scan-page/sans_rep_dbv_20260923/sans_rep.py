# -*- coding: utf-8 -*-
"""DISTRI BETON VIENNE : position fiscale « SANS REP » (17) inefficace (elle mappe seulement 20% G -> 20% G).
En Odoo 19 une position fiscale remplace une taxe par une autre via la taxe de DESTINATION (original_tax_ids +
fiscal_position_ids). Pour exonérer, on crée deux taxes à 0 € « REP Béton exonérée (SANS REP) » et « REP Granulats
exonérée (SANS REP) » qui remplacent REP Béton (203) et REP Granulats (205) sous la position 17.
  test : création sur la base de test + rejeu du calcul des taxes sur les devis Colas en brouillon
  prod : idem en production + liste des factures Colas validées portant encore de la REP"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'test').lower()
U, D = ('https://testmaq230926.odoo.com', 'testmaq230926') if mode == 'test' else ('https://maquignon.odoo.com', 'maquignon')
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)


def x(mo, me, *a, **k):
    k['context'] = dict({'allowed_company_ids': [2, 1, 3, 4, 13]}, **k.get('context', {}))
    return m.execute_kw(D, uid, p, mo, me, list(a), k)


FP = 17
SRC = {203: 'REP Béton exonérée (SANS REP)', 205: 'REP Granulats exonérée (SANS REP)'}
fp = x('account.fiscal.position', 'read', [FP], fields=['name', 'company_id', 'tax_ids'])[0]
assert fp['name'] == 'SANS REP' and fp['company_id'][0] == 2, fp
new_ids = {}
for src, name in SRC.items():
    t = x('account.tax', 'read', [src], fields=['name', 'amount', 'amount_type', 'tax_group_id', 'type_tax_use', 'company_id', 'price_include_override' if 'price_include_override' in x('account.tax', 'fields_get', attributes=['type']) else 'name'])[0]
    assert t['company_id'][0] == 2 and t['amount_type'] == 'fixed', t
    ex = x('account.tax', 'search', [['name', '=', name], ['company_id', '=', 2]], context={'active_test': False})
    if ex:
        new_ids[src] = ex[0]
        x('account.tax', 'write', ex, {'active': True, 'original_tax_ids': [[6, 0, [src]]], 'fiscal_position_ids': [[4, FP]]})
        print('taxe existante réutilisée :', name, ex[0])
        continue
    vals = {'name': name, 'amount': 0.0, 'amount_type': 'fixed', 'type_tax_use': 'sale', 'company_id': 2, 'tax_group_id': t['tax_group_id'][0],
            'description': 'Exonération REP (client déclarant)', 'original_tax_ids': [[6, 0, [src]]], 'fiscal_position_ids': [[6, 0, [FP]]]}
    r = x('account.tax', 'create', [vals])
    new_ids[src] = r[0] if isinstance(r, list) else r
    print('taxe créée :', name, new_ids[src])
print('position SANS REP, taxes de destination :', x('account.fiscal.position', 'read', [FP], fields=['tax_ids'])[0]['tax_ids'])
# lignes des commandes Colas non encore facturées : remplacement direct des taxes REP par les taxes exonérées
colas = x('res.partner', 'search', [['name', '=ilike', 'colas%'], ['property_account_position_id', '=', FP]], context={'allowed_company_ids': [2]})
print('partenaires Colas avec la position SANS REP :', colas)
lines = x('sale.order.line', 'search_read', [['company_id', '=', 2], ['order_id.partner_id', 'in', colas], ['order_id.state', 'in', ['draft', 'sent', 'sale']], ['tax_ids', 'in', list(SRC)], ['display_type', '=', False]], fields=['order_id', 'tax_ids', 'invoice_lines', 'name'])
n = 0; skipped = 0
for l in lines:
    if l['invoice_lines'] and any(i['parent_state'] == 'posted' for i in x('account.move.line', 'read', l['invoice_lines'], fields=['parent_state'])):
        skipped += 1; continue
    newtax = [new_ids.get(t, t) for t in l['tax_ids']]
    x('sale.order.line', 'write', [l['id']], {'tax_ids': [[6, 0, newtax]]}); n += 1
orders = sorted({l['order_id'][1] for l in lines})
print('lignes de commandes Colas corrigées :', n, '| déjà facturées (laissées) :', skipped, '| commandes :', orders[:30])
chk = x('sale.order.line', 'search_count', [['company_id', '=', 2], ['order_id.partner_id', 'in', colas], ['order_id.state', 'in', ['draft', 'sent', 'sale']], ['tax_ids', 'in', list(SRC)], ['display_type', '=', False], ['invoice_lines', '=', False]])
print('contrôle : lignes non facturées portant encore une taxe REP :', chk)
if mode == 'prod':
    inv = x('account.move.line', 'search_read', [['company_id', '=', 2], ['partner_id', 'in', colas], ['parent_state', '=', 'posted'], ['display_type', '=', 'tax'], ['tax_line_id', 'in', [203, 205]], ['date', '>=', '2026-01-01']], fields=['move_name', 'date', 'balance', 'tax_line_id'], order='date')
    tot = {}
    for l in inv:
        tot.setdefault(l['move_name'], [l['date'], 0.0]); tot[l['move_name']][1] += -l['balance']
    print('factures Colas validées avec de la REP en 2026 :', len(tot), '| total REP facturée %.2f € HT' % sum(v[1] for v in tot.values()))
    for k, v in sorted(tot.items(), key=lambda kv: kv[1][0]): print('   ', k, v[0], '%.2f' % v[1])
