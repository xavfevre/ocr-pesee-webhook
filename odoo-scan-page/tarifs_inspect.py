# -*- coding: utf-8 -*-
"""État des lieux des listes de prix de SARL MAQUIGNON : listes, règles, clients rattachés, articles vendables."""
import os, ssl, sys, xmlrpc.client, collections
sys.stdout.reconfigure(encoding='utf-8')
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
ctx = {'allowed_company_ids': [1], 'active_test': False}
fpl = x('ir.model.fields', 'search_read', [['model', '=', 'product.pricelist']], fields=['name'])
fpl = {f['name'] for f in fpl}
fields_pl = [f for f in ('name', 'company_id', 'active', 'currency_id', 'item_ids', 'sequence', 'discount_policy', 'country_group_ids', 'create_date', 'write_date') if f in fpl]
pls = x('product.pricelist', 'search_read', [['company_id', 'in', [1, False]]], fields=fields_pl, order='sequence,id', context=ctx)
print('listes de prix (société 1 ou toutes) :', len(pls))
fit = {f['name'] for f in x('ir.model.fields', 'search_read', [['model', '=', 'product.pricelist.item']], fields=['name'])}
fields_it = [f for f in ('pricelist_id', 'applied_on', 'product_tmpl_id', 'product_id', 'categ_id', 'compute_price', 'fixed_price', 'percent_price', 'base', 'base_pricelist_id', 'price_discount', 'price_surcharge', 'price_round', 'price_min_margin', 'price_max_margin', 'min_quantity', 'date_start', 'date_end', 'name', 'price') if f in fit]
items = x('product.pricelist.item', 'search_read', [['pricelist_id', 'in', [pl['id'] for pl in pls]]], fields=fields_it, limit=20000, context=ctx)
byp = collections.defaultdict(list)
for it in items:
    byp[it['pricelist_id'][0]].append(it)
part = collections.Counter()
for r in x('res.partner', 'read_group', [['specific_property_product_pricelist', 'in', [pl['id'] for pl in pls]]], ['id:count'], ['specific_property_product_pricelist'], context=ctx):
    part[r['specific_property_product_pricelist'][0]] = r.get('__count', r.get('specific_property_product_pricelist_count'))
print('%5s %-45s %-8s %-6s %5s %6s  détail des règles' % ('id', 'liste', 'société', 'active', 'règl', 'clients'))
for pl in pls:
    its = byp[pl['id']]
    det = collections.Counter('%s/%s%s' % (it['applied_on'][2:], it['compute_price'], ('→' + it['base_pricelist_id'][1][:14]) if it.get('base_pricelist_id') else '') for it in its)
    print('%5d %-45s %-8s %-6s %5d %6d  %s' % (pl['id'], pl['name'][:45], (pl['company_id'] and 'Maq') or 'toutes', pl['active'], len(its), part.get(pl['id'], 0), dict(det.most_common(4))))
# articles vendables Maquignon
tm = x('product.template', 'search_read', [['sale_ok', '=', True], ['company_id', 'in', [1, False]], ['active', '=', True]], fields=['name', 'list_price', 'categ_id', 'type', 'product_variant_count', 'uom_id'], limit=5000, context=ctx)
print('\narticles vendables actifs (société 1 ou toutes) :', len(tm), '| variantes :', sum(t['product_variant_count'] for t in tm))
cat = collections.Counter(t['categ_id'][1].split(' / ')[0] for t in tm)
print('par catégorie racine :', dict(cat.most_common(12)))
print('prix public à 0 :', sum(1 for t in tm if not t['list_price']), '| par type :', dict(collections.Counter(t['type'] for t in tm)))
# exemples de règles des listes clients
for pl in pls:
    if part.get(pl['id'], 0) <= 5 and byp[pl['id']] and pl['active']:
        print('\n--', pl['name'], ':', len(byp[pl['id']]), 'règles')
        for it in byp[pl['id']][:8]:
            print('     %-22s %-12s %-45s fixe %8.2f  %%%6.2f base=%s%s minq %s' % (it['applied_on'][2:], it['compute_price'], ((it.get('product_tmpl_id') or it.get('product_id') or it.get('categ_id') or [0, 'tous'])[1])[:45], it.get('fixed_price') or 0, it.get('percent_price') or 0, it.get('base'), ('→' + it['base_pricelist_id'][1]) if it.get('base_pricelist_id') else '', it.get('min_quantity')))
# paramètres de vente : mode des listes de prix
for k in ('product.product_pricelist_setting', 'sale.group_discount_per_so_line'):
    v = x('ir.config_parameter', 'search_read', [['key', '=', k]], fields=['value'])
    print('param', k, ':', v)
print('groupes tarifs :', x('res.groups', 'search_read', [['name', 'ilike', 'pricelist']], fields=['name', 'full_name'] if 'full_name' in {f['name'] for f in x('ir.model.fields', 'search_read', [['model', '=', 'res.groups']], fields=['name'])} else ['name']))
