# -*- coding: utf-8 -*-
"""Lignes de commande « figées » : article aujourd'hui facturé sur quantités COMMANDÉES, ligne confirmée, rien de facturé,
mais statut « rien à facturer » (calcul fait quand l'article était sur quantités LIVRÉES ; Odoo ne recalcule qu'au
prochain changement de livré/facturé, d'où « obligé de valider le BL »). Historique des changements de politique.
Usage : python lignes_figees.py dry | apply   (apply = recalcul des lignes figées par réécriture du livré à l'identique)"""
import os, ssl, sys, xmlrpc.client, collections
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
ctx = {'allowed_company_ids': [1, 2, 3, 4, 13], 'active_test': False}
# 1) historique des changements de politique de facturation (suivi chatter)
fid = x('ir.model.fields', 'search', [['model', '=', 'product.template'], ['name', '=', 'invoice_policy']])
tv = x('mail.tracking.value', 'search_read', [['field_id', 'in', fid]], fields=['mail_message_id', 'old_value_char', 'new_value_char', 'create_date'], order='create_date desc', limit=40, context=ctx) if fid else []
print('changements de politique de facturation tracés :', len(tv))
msgs = {mm['id']: mm for mm in x('mail.message', 'read', [t['mail_message_id'][0] for t in tv], fields=['res_id', 'author_id', 'date', 'model'], context=ctx)} if tv else {}
tmpl_ids = sorted({msgs[t['mail_message_id'][0]]['res_id'] for t in tv if t['mail_message_id'][0] in msgs})
tmpls = {t['id']: t['name'] for t in x('product.template', 'read', tmpl_ids, fields=['name'], context=ctx)} if tmpl_ids else {}
for t in tv:
    mm = msgs.get(t['mail_message_id'][0], {})
    print('   %s  %-55s %-22s -> %-22s par %s' % (t['create_date'][:16], tmpls.get(mm.get('res_id'), '?')[:55], t['old_value_char'], t['new_value_char'], (mm.get('author_id') or [0, '?'])[1]))
# 2) lignes figées
dom = [['state', '=', 'sale'], ['invoice_status', '=', 'no'], ['display_type', '=', False], ['is_downpayment', '=', False],
       ['product_id.invoice_policy', '=', 'order'], ['product_uom_qty', '>', 0]]
ls = x('sale.order.line', 'search_read', dom, fields=['order_id', 'product_id', 'product_uom_qty', 'qty_delivered', 'qty_invoiced', 'qty_to_invoice', 'price_subtotal', 'company_id', 'create_date', 'product_type'], limit=20000, context=ctx)
fig = [l for l in ls if l['qty_invoiced'] < l['product_uom_qty'] - 1e-6]
print('\nlignes figées (politique commandée, statut « rien à facturer », quantité non facturée) : %d, %.2f € HT' % (len(fig), sum(l['price_subtotal'] for l in fig)))
par_soc = collections.defaultdict(lambda: [0, 0.0])
par_prod = collections.defaultdict(lambda: [0, 0.0])
par_an = collections.Counter()
for l in fig:
    par_soc[l['company_id'][1]][0] += 1; par_soc[l['company_id'][1]][1] += l['price_subtotal']
    par_prod[l['product_id'][1]][0] += 1; par_prod[l['product_id'][1]][1] += l['price_subtotal']
    par_an[l['create_date'][:7]] += 1
print('par société :', {k: (v[0], round(v[1], 2)) for k, v in par_soc.items()})
print('par mois de création :', dict(sorted(par_an.items())))
print('par article (20 premiers) :')
for k, v in sorted(par_prod.items(), key=lambda kv: -kv[1][1])[:20]:
    print('   %4d  %10.2f  %s' % (v[0], v[1], k[:80]))
loc = [l for l in fig if 'Location de mat' in l['product_id'][1]]
print('dont Location de matériel Transport : %d lignes, %.2f € HT, commandes %s' % (len(loc), sum(l['price_subtotal'] for l in loc), sorted({l['order_id'][1] for l in loc})[:30]))
if mode == 'apply':
    n = 0
    for l in fig:
        try:
            x('sale.order.line', 'write', [l['id']], {'qty_delivered': l['qty_delivered']}, context=ctx); n += 1
        except Exception as e:  # noqa: BLE001
            print('   ligne', l['id'], l['order_id'][1], str(e).strip().splitlines()[-1][:120])
    apres = x('sale.order.line', 'read', [l['id'] for l in fig], fields=['invoice_status'], context=ctx)
    print('recalculées : %d -> %s' % (n, dict(collections.Counter(a['invoice_status'] for a in apres))))
    oids = sorted({l['order_id'][0] for l in fig})
    print('commandes concernées :', dict(collections.Counter(o['invoice_status'] for o in x('sale.order', 'read', oids, fields=['invoice_status'], context=ctx))))
