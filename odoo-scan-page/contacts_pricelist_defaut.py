# -*- coding: utf-8 -*-
"""Liste de prix « par défaut » de chaque société (celle qu'Odoo affiche quand le contact n'en a pas de spécifique) et
valeur par défaut (ir.default) du champ specific_property_product_pricelist, pour que le regroupement ne montre pas
« Aucun » mais la vraie liste. Usage : dry | apply"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
F = 'specific_property_product_pricelist'
for cid in (4, 1, 2, 3, 13):
    ctx = {'allowed_company_ids': [cid]}
    soc = x('res.company', 'read', [cid], fields=['name'])[0]['name']
    sans = x('res.partner', 'search_read', [[F, '=', False], ['customer_rank', '>', 0]], fields=['name', 'property_product_pricelist'], limit=3, context=ctx)
    defaut = {(s['property_product_pricelist'] and s['property_product_pricelist'][1]) for s in sans}
    dflt_id = sans[0]['property_product_pricelist'][0] if sans and sans[0]['property_product_pricelist'] else None
    n_sans = x('res.partner', 'search_count', [[F, '=', False], ['customer_rank', '>', 0]], context=ctx)
    cur = x('ir.default', 'search_read', [['field_id.model', '=', 'res.partner'], ['field_id.name', '=', F], ['company_id', '=', cid]], fields=['json_value', 'company_id'])
    print('%-24s clients sans liste spécifique : %4d -> affichés « %s » (id %s) | ir.default actuel : %s' % (soc[:24], n_sans, ', '.join(sorted(defaut)) or '-', dflt_id, [d['json_value'] for d in cur] or 'aucun'))
    if mode == 'apply':
        if dflt_id and not cur:
            x('ir.default', 'set', 'res.partner', F, dflt_id, company_id=cid); print('   valeur par défaut posée')
        g = x('res.partner', 'read_group', [['customer_rank', '>', 0]], ['id:count'], [F], context=ctx)
        print('   regroupement :', [((r[F] and r[F][1]) or 'Aucun', r.get('__count', r.get(F + '_count'))) for r in g])
