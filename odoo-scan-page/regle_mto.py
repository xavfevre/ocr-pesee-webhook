# -*- coding: utf-8 -*-
"""Règle de réapprovisionnement 5 (route « Replenish on Order (MTO) », Maq/Stock -> Clients) :
« mts_else_mto » (prendre en stock si disponible, sinon fabriquer) -> « make_to_order » (toujours fabriquer / acheter).
Ainsi chaque vente d'un article MTO génère son OF (ou son achat), quel que soit le stock.
Usage : python regle_mto.py dry | apply"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
mto = x('stock.route', 'search', [['name', 'ilike', 'Replenish on Order']])
buy = x('stock.route', 'search', [['name', '=', 'Buy']])
manuf = x('stock.route', 'search', [['name', '=', 'Manufacture']])
tm = x('product.template', 'search_read', [['sale_ok', '=', True], ['company_id', 'in', [1, False]], ['route_ids', 'in', mto]],
       fields=['name', 'default_code', 'route_ids', 'qty_available'])
print('articles sur la route MTO :', len(tm))
print('  MTO + Achat (créeront un achat à chaque vente en MTO strict) :',
      [(t['default_code'] or '', t['name'][:40], 'stock %.2f' % t['qty_available']) for t in tm if set(buy) & set(t['route_ids'])])
print('  MTO + Fabrication avec stock > 0 (aujourd\'hui : pas d\'OF généré) :',
      [(t['default_code'] or '', t['name'][:40], '%.2f' % t['qty_available']) for t in tm if set(manuf) & set(t['route_ids']) and t['qty_available'] > 0])
r = x('stock.rule', 'read', [5], fields=['name', 'procure_method', 'route_id'])[0]
print('règle 5 :', r['name'], '|', r['route_id'] and r['route_id'][1], '| méthode actuelle :', r['procure_method'])
if mode == 'apply':
    x('stock.rule', 'write', [5], {'procure_method': 'make_to_order'})
    print('règle 5 après :', x('stock.rule', 'read', [5], fields=['procure_method'])[0]['procure_method'],
          '-> chaque vente d\'un article MTO crée son OF (ou son achat), quel que soit le stock')
