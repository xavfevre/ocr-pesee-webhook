# -*- coding: utf-8 -*-
"""Test chronométré de confirmation d'une commande Pierres de N lignes (OF par ligne), puis suppression complète
(OF, transferts, commande, messages, pièces jointes). Le compteur de numéros (S0…, WH/OF/…) avance : c'est le seul résidu.
  python perf_test_confirm.py <étiquette> [N]"""
import os, ssl, sys, time, xmlrpc.client
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
lab = sys.argv[1] if len(sys.argv) > 1 else 'test'
N = int(sys.argv[2]) if len(sys.argv) > 2 else 25
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
CTX = {'allowed_company_ids': [1], 'default_company_id': 1}


def x(mo, me, *a, **k):
    ctx = dict(CTX); ctx.update(k.pop('context', {})); k['context'] = ctx
    try:
        return m.execute_kw(D, uid, p, mo, me, list(a), k)
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in str(e):
            return None
        raise


PARTNER = 15893   # LEFÈVRE CENTRE OUEST (AGENCE 44)
pid = x('product.product', 'search', [['default_code', '=', 'TUF0000-PS']], limit=1)[0]
print('=== %s : %d lignes, produit %s, client %s' % (lab, N, pid, PARTNER))
lignes = [(0, 0, {'product_id': pid, 'product_uom_qty': 1, 'x_studio_ref_pierre': 'TEST-%02d' % (i + 1), 'x_studio_nbr': 1,
                  'x_studio_long': 0.5, 'x_studio_larg': 0.3, 'x_studio_epais': 0.2}) for i in range(N)]
t = time.time()
so_id = x('sale.order', 'create', [{'partner_id': PARTNER, 'company_id': 1, 'origin': 'TEST PERF', 'client_order_ref': 'TEST PERF (à supprimer)', 'order_line': lignes}])
so_id = so_id[0] if isinstance(so_id, list) else so_id
so = x('sale.order', 'read', [so_id], ['name', 'state', 'amount_total'])[0]
print('commande %s créée (%d) en %.1f s, total %.2f' % (so['name'], so_id, time.time() - t, so['amount_total']))
mos = pk = []
try:
    t = time.time()
    x('sale.order', 'action_confirm', [so_id])
    dt = time.time() - t
    so = x('sale.order', 'read', [so_id], ['name', 'state', 'picking_ids', 'message_ids', 'x_studio_fab_encours', 'x_studio_of_non_planifies', 'x_studio_of_liste', 'x_studio_pierres_faites'])[0]
    mos = x('mrp.production', 'search_read', [['origin', '=', so['name']]], fields=['name', 'state', 'workorder_ids', 'sale_line_id', 'x_studio_ref_pierre', 'x_studio_nom_du_client', 'log_note', 'product_qty', 'message_ids'], order='id')
    wos = x('mrp.workorder', 'search_read', [['production_id', 'in', [o['id'] for o in mos]]], fields=['state', 'employee_assigned_ids', 'workcenter_id'])
    pk = x('stock.picking', 'read', so['picking_ids'], ['name', 'state', 'move_ids', 'picking_type_id'])
    att = x('ir.attachment', 'search_count', [['res_model', '=', 'mrp.production'], ['res_id', 'in', [o['id'] for o in mos]]])
    print('CONFIRMATION : %.1f s  (%.2f s par ligne)' % (dt, dt / N))
    print('   état %s | OF %d %s | OT %d %s | transferts %s | pièces jointes OF %d | messages commande %d, messages OF %d'
          % (so['state'], len(mos), dict(Counter(o['state'] for o in mos)), len(wos), dict(Counter(w['state'] for w in wos)),
             [(k['name'], k['state'], len(k['move_ids'])) for k in pk], att, len(so['message_ids']), sum(len(o['message_ids']) for o in mos)))
    print('   Fab en cours : %s | OF non planifiés %s | liste %s | pierres faites %s' % (so['x_studio_fab_encours'], so['x_studio_of_non_planifies'], so['x_studio_of_liste'], so['x_studio_pierres_faites']))
    if mos:
        o = mos[0]
        print('   1er OF : %s ligne %s réf %s client %s qté %s | note : %s' % (o['name'], o['sale_line_id'] and o['sale_line_id'][1][:40], o['x_studio_ref_pierre'], o['x_studio_nom_du_client'], o['product_qty'], (o['log_note'] or '').replace('\n', ' / ')[:80]))
        print('   OF -> lignes distinctes : %d / %d' % (len({o['sale_line_id'] and o['sale_line_id'][0] for o in mos}), len(mos)))
        print('   opérateurs OT :', Counter(tuple(w['employee_assigned_ids']) for w in wos).most_common(3), '| postes', Counter(w['workcenter_id'][1] for w in wos).most_common(3))
finally:
    print('--- nettoyage')
    mo_ids = [o['id'] for o in x('mrp.production', 'search_read', [['origin', '=', so['name']]], fields=['id'])]
    if mo_ids:
        try:
            x('mrp.production', 'action_cancel', mo_ids)
            x('mrp.production', 'unlink', mo_ids)
            print('   OF annulés et supprimés :', len(mo_ids))
        except Exception as e:
            print('   OF : échec annulation/suppression standard (%s) -> purge SQL via action temporaire' % str(e)[:120])
            mid = x('ir.model', 'search', [['model', '=', 'mrp.production']])[0]
            code = """ids = tuple(records.ids)
env.cr.execute("DELETE FROM mrp_workcenter_productivity WHERE workorder_id IN (SELECT id FROM mrp_workorder WHERE production_id IN %s)", (ids,))
env.cr.execute("UPDATE mrp_workorder SET state='cancel' WHERE production_id IN %s", (ids,))
env.cr.execute("DELETE FROM stock_move_line WHERE move_id IN (SELECT id FROM stock_move WHERE production_id IN %s OR raw_material_production_id IN %s)", (ids, ids))
env.cr.execute("UPDATE stock_move SET state='cancel', quantity=0, picked=false WHERE production_id IN %s OR raw_material_production_id IN %s", (ids, ids))
env.cr.execute("UPDATE mrp_production SET state='cancel', qty_producing=0 WHERE id IN %s", (ids,))
env.invalidate_all()
records.with_context(force_delete=True).unlink()"""
            aid = x('ir.actions.server', 'create', [{'name': 'TEST purge OF (à supprimer)', 'model_id': mid, 'state': 'code', 'code': code}])
            aid = aid[0] if isinstance(aid, list) else aid
            try:
                x('ir.actions.server', 'run', [aid], context={'active_model': 'mrp.production', 'active_ids': mo_ids, 'active_id': mo_ids[0]})
            finally:
                x('ir.actions.server', 'unlink', [aid])
            print('   OF purgés :', len(mo_ids))
    so2 = x('sale.order', 'read', [so_id], ['state', 'picking_ids'])[0]
    if so2['state'] not in ('cancel', 'draft'):
        x('sale.order', 'action_cancel', [so_id], context={'disable_cancel_warning': True})
    pk_ids = so2['picking_ids']
    if pk_ids:
        st = x('stock.picking', 'read', pk_ids, ['state'])
        todo = [k['id'] for k in st if k['state'] != 'cancel']
        if todo:
            x('stock.picking', 'action_cancel', todo)
        x('stock.picking', 'unlink', pk_ids)
        print('   transferts supprimés :', len(pk_ids))
    x('sale.order', 'unlink', [so_id])
    for model, ids in (('mrp.production', mo_ids), ('sale.order', [so_id]), ('stock.picking', pk_ids)):
        if not ids:
            continue
        msg = x('mail.message', 'search', [['model', '=', model], ['res_id', 'in', ids]])
        if msg:
            x('mail.message', 'unlink', msg)
        at = x('ir.attachment', 'search', [['res_model', '=', model], ['res_id', 'in', ids]])
        if at:
            x('ir.attachment', 'unlink', at)
    print('   commande supprimée ; restes : commandes %d, OF %d, messages %d' % (
        x('sale.order', 'search_count', [['id', '=', so_id]]), x('mrp.production', 'search_count', [['origin', '=', so['name']]]),
        x('mail.message', 'search_count', [['model', '=', 'sale.order'], ['res_id', '=', so_id]])))
