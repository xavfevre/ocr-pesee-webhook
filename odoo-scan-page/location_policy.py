# -*- coding: utf-8 -*-
"""Articles transport / location encore facturés sur « quantités livrées » (obligent à valider le BL) -> « quantités
commandées », puis recalcul des lignes de commande ouvertes concernées. Usage : python location_policy.py dry | apply"""
import os, ssl, sys, xmlrpc.client, collections
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
ctx = {'allowed_company_ids': [1, 2, 3, 4, 13], 'active_test': False}
dom = ['&', ['invoice_policy', '=', 'delivery'], '|', '|', '|', ['name', 'ilike', 'transport'], ['name', 'ilike', 'location de mat'], ['name', 'ilike', 'transfert'], ['name', 'ilike', 'livraison']]
tm = x('product.template', 'search_read', dom, fields=['name', 'type', 'invoice_policy', 'active', 'company_id', 'sale_ok', 'product_variant_count', 'categ_id'], order='name', context=ctx)
print('modèles transport/location/transfert/livraison en « quantités livrées » :', len(tm))
for t in tm:
    print('  %5d %-70s %-6s %-8s actif=%-5s %-22s %s' % (t['id'], t['name'][:70], t['type'], t['invoice_policy'], t['active'], (t['company_id'] and t['company_id'][1][:22]) or 'toutes', t['categ_id'][1][:30]))
cible = [t for t in tm if 'Location de mat' in t['name'] or 'Semi Fond' in t['name']]
print('\nvisé par la demande (Location de matériel Transport…) :', [(t['id'], t['name']) for t in cible])
# lignes de commande ouvertes portées par ces modèles
tids = [t['id'] for t in tm]
lines = x('sale.order.line', 'search_read', [['product_id.product_tmpl_id', 'in', tids], ['state', '=', 'sale'], ['invoice_status', 'in', ['no', 'to invoice']], ['product_uom_qty', '>', 0]],
          fields=['order_id', 'product_id', 'product_uom_qty', 'qty_delivered', 'qty_invoiced', 'invoice_status', 'price_subtotal'], limit=5000, context=ctx) if tids else []
bloq = [l for l in lines if l['invoice_status'] == 'no' and l['qty_invoiced'] < l['product_uom_qty']]
print('\nlignes ouvertes sur ces articles : %d, dont %d « rien à facturer » faute de BL validé (%.2f € HT)' % (len(lines), len(bloq), sum(l['price_subtotal'] for l in bloq)))
par = collections.Counter(l['product_id'][1] for l in bloq)
for k, v in par.most_common(15):
    print('   %4d  %s' % (v, k[:80]))
if mode == 'apply':
    if tids:
        x('product.template', 'write', tids, {'invoice_policy': 'order'}, context=ctx)
        print('\n%d modèles passés en « quantités commandées »' % len(tids))
    # recalcul des lignes ouvertes : réécriture de la quantité à l'identique (déclenche qty_to_invoice / invoice_status)
    n = 0
    for l in lines:
        try:
            x('sale.order.line', 'write', [l['id']], {'product_uom_qty': l['product_uom_qty']}, context=ctx); n += 1
        except Exception as e:  # noqa: BLE001
            print('   ligne', l['id'], l['order_id'][1], str(e).strip().splitlines()[-1][:120])
    apres = x('sale.order.line', 'read', [l['id'] for l in lines], fields=['invoice_status', 'order_id'], context=ctx) if lines else []
    print('lignes recalculées : %d -> statuts %s' % (n, dict(collections.Counter(a['invoice_status'] for a in apres))))
    oids = sorted({l['order_id'][0] for l in lines})
    if oids:
        print('commandes : %s' % dict(collections.Counter(o['invoice_status'] for o in x('sale.order', 'read', oids, fields=['invoice_status'], context=ctx))))
