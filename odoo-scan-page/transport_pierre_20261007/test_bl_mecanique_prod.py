# -*- coding: utf-8 -*-
"""Vérifie en production la mécanique Odoo 19 utilisée par la phase 3, sur un transfert interne jetable et sans effet
sur le stock (consommable non suivi, même emplacement source et destination) :
  2 mouvements (5 et 3), on prélève 2 sur le premier (quantity=2, picked=True), on valide avec skip_backorder ->
  attendu : transfert « fait » avec 2 sur le 1er mouvement, et un reliquat créé pour 3 + 3.
Le reliquat est ensuite annulé ; le transfert de test reste (origine « TEST EXPEDITION (à ignorer) »).
  python test_bl_mecanique_prod.py"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)


def x(mo, me, *a, **k):
    ctx = {'allowed_company_ids': [1]}; ctx.update(k.pop('context', {})); k['context'] = ctx
    try:
        return m.execute_kw(D, uid, p, mo, me, list(a), k)
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in str(e):
            return None
        raise


one = lambda v: v[0] if isinstance(v, list) else v
pt = x('stock.picking.type', 'search_read', [['code', '=', 'internal'], ['company_id', '=', 1]], fields=['name', 'default_location_src_id', 'default_location_dest_id'], limit=1)[0]
loc = pt['default_location_src_id'][0] if pt['default_location_src_id'] else x('stock.location', 'search', [['usage', '=', 'internal'], ['company_id', '=', 1]], limit=1)[0]
prod = x('product.product', 'search_read', [['type', '=', 'consu'], ['is_storable', '=', False], ['company_id', 'in', [1, False]], ['sale_ok', '=', False]], fields=['name', 'uom_id'], limit=1)
if not prod:
    prod = x('product.product', 'search_read', [['type', '=', 'consu'], ['is_storable', '=', False], ['company_id', 'in', [1, False]]], fields=['name', 'uom_id'], limit=1)
prod = prod[0]
print('type %s | emplacement %s | article consommable non suivi : %s' % (pt['name'], loc, prod['name']))
pid = one(x('stock.picking', 'create', [{'picking_type_id': pt['id'], 'location_id': loc, 'location_dest_id': loc, 'origin': 'TEST EXPEDITION (à ignorer)',
                                         'move_ids': [(0, 0, {'product_id': prod['id'], 'product_uom_qty': 5, 'product_uom': prod['uom_id'][0], 'location_id': loc, 'location_dest_id': loc}),
                                                      (0, 0, {'product_id': prod['id'], 'product_uom_qty': 3, 'product_uom': prod['uom_id'][0], 'location_id': loc, 'location_dest_id': loc})]}]))
x('stock.picking', 'action_confirm', [pid])
mv = x('stock.move', 'search_read', [['picking_id', '=', pid]], fields=['id', 'product_uom_qty', 'quantity', 'picked', 'state'], order='id')
print('après confirmation :', [(v['product_uom_qty'], v['quantity'], v['picked'], v['state']) for v in mv], '| état', x('stock.picking', 'read', [pid], ['name', 'state'])[0])
x('stock.move', 'write', [mv[0]['id']], {'quantity': 2, 'picked': True})
x('stock.move', 'write', [mv[1]['id']], {'picked': False})
r = x('stock.picking', 'button_validate', [pid], context={'skip_backorder': True, 'skip_sms': True, 'skip_immediate': True})
print('button_validate ->', r if not isinstance(r, dict) else {k: r.get(k) for k in ('type', 'res_model', 'name')})
pk = x('stock.picking', 'read', [pid], ['name', 'state', 'backorder_ids'])[0]
mv2 = x('stock.move', 'search_read', [['picking_id', '=', pid]], fields=['product_uom_qty', 'quantity', 'picked', 'state'], order='id')
print('transfert %s : état %s | mouvements %s | reliquats %s' % (pk['name'], pk['state'], [(v['product_uom_qty'], v['quantity'], v['state']) for v in mv2], pk['backorder_ids']))
for b in pk['backorder_ids']:
    bk = x('stock.picking', 'read', [b], ['name', 'state'])[0]
    mv3 = x('stock.move', 'search_read', [['picking_id', '=', b]], fields=['product_uom_qty', 'quantity', 'state'], order='id')
    print('   reliquat %s (%s) : %s' % (bk['name'], bk['state'], [(v['product_uom_qty'], v['quantity'], v['state']) for v in mv3]))
    x('stock.picking', 'action_cancel', [b]); x('stock.picking', 'unlink', [b]); print('   reliquat annulé et supprimé')
ok = pk['state'] == 'done' and mv2[0]['quantity'] == 2 and mv2[0]['state'] == 'done' and bool(pk['backorder_ids'])
print('MÉCANIQUE :', 'OK (validation partielle + reliquat automatique)' if ok else 'À VÉRIFIER')
