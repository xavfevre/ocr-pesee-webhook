# -*- coding: utf-8 -*-
"""Mesure différentielle de la confirmation d'une commande Pierres de N lignes : les automatisations sont exclues
pour LA SEULE commande de test (filtre « origin != S0xxxx » ajouté le temps du test, puis retiré), les autres
enregistrements ne sont pas concernés. Nettoyage complet ensuite (OF, transferts, commande, messages).
  python perf_diff_confirm.py <base|sans_mrp|sans_auto> [N]
    base      : toutes les automatisations actives (référence)
    sans_mrp  : automatisations sur OF et OT exclues
    sans_auto : toutes les automatisations personnalisées exclues (OF, OT, commande, lignes, transfert)"""
import ast, os, ssl, sys, time, xmlrpc.client
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'base').lower()
N = int(sys.argv[2]) if len(sys.argv) > 2 else 40
assert mode in ('base', 'sans_mrp', 'sans_auto') or mode.startswith('sans='), mode
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


# automatisations à exclure : id -> chemin vers le nom de la commande
MRP = {7: 'origin', 11: 'origin', 12: 'origin', 13: 'origin', 39: 'origin', 47: 'origin', 61: 'origin', 67: 'origin', 71: 'origin', 76: 'origin', 81: 'origin',
       57: 'production_id.origin', 64: 'production_id.origin', 77: 'production_id.origin', 95: 'production_id.origin'}
AUTRES = {53: 'order_id.name', 55: 'order_id.name', 68: 'order_id.name', 78: 'order_id.name',
          14: 'name', 54: 'name', 60: 'name', 62: 'name', 93: 'name', 52: 'name', 51: 'origin'}
TOUTES = {**MRP, **AUTRES}
if mode == 'base':
    EXCL = {}
elif mode == 'sans_mrp':
    EXCL = dict(MRP)
elif mode == 'sans_auto':
    EXCL = dict(TOUTES)
else:   # sans=7,13 : liste d'ids d'automatisations à exclure
    ids = [int(i) for i in mode[5:].split(',') if i.strip()]
    assert all(i in TOUTES for i in ids), [i for i in ids if i not in TOUTES]
    EXCL = {i: TOUTES[i] for i in ids}
PARTNER = 15893
pid = x('product.product', 'search', [['default_code', '=', 'TUF0000-PS']], limit=1)[0]
# lignes comme en production : quantité = volume arrondi à 3 décimales (volume calculé 0,03224 -> 0,032 m³)
lignes = [(0, 0, {'product_id': pid, 'product_uom_qty': 0.032, 'x_studio_ref_pierre': 'TEST-%02d' % (i + 1), 'x_studio_nbr': 1,
                  'x_studio_long': 0.52, 'x_studio_larg': 0.31, 'x_studio_epais': 0.2}) for i in range(N)]
so_id = x('sale.order', 'create', [{'partner_id': PARTNER, 'company_id': 1, 'origin': 'TEST PERF', 'client_order_ref': 'TEST PERF (à supprimer)', 'order_line': lignes}])
so_id = so_id[0] if isinstance(so_id, list) else so_id
nom = x('sale.order', 'read', [so_id], ['name'])[0]['name']
print('=== mode %s : commande %s (%d), %d lignes, %d automatisations exclues pour cette commande' % (mode, nom, so_id, N, len(EXCL)))
sauv = {}
try:
    if EXCL:
        for a in x('base.automation', 'read', list(EXCL), ['filter_domain', 'model_name', 'active']):
            if not a['active']:
                continue
            sauv[a['id']] = a['filter_domain']
            terme = (EXCL[a['id']], '!=', nom)
            if a['filter_domain']:
                try:
                    dom = ['&', terme] + list(ast.literal_eval(a['filter_domain']))
                    nouveau = repr(dom)
                except Exception:
                    nouveau = "['&', %r] + (%s)" % (terme, a['filter_domain'])
            else:
                nouveau = repr([terme])
            x('base.automation', 'write', [a['id']], {'filter_domain': nouveau})
        print('filtres posés sur', sorted(sauv))
    t = time.time()
    x('sale.order', 'action_confirm', [so_id])
    dt = time.time() - t
    mos = x('mrp.production', 'search_read', [['origin', '=', nom]], fields=['state', 'x_studio_nom_du_client', 'product_qty', 'workorder_ids', 'log_note'])
    wos = x('mrp.workorder', 'search_read', [['production_id', 'in', [o['id'] for o in mos]]], fields=['state', 'employee_assigned_ids'])
    print('CONFIRMATION : %.1f s  (%.2f s par ligne)' % (dt, dt / N))
    print('   OF %d %s | client renseigné sur %d OF | qté OF %s | OT %d, opérateur assigné sur %d' % (
        len(mos), dict(Counter(o['state'] for o in mos)), len([o for o in mos if o['x_studio_nom_du_client']]),
        dict(Counter(o['product_qty'] for o in mos)), len(wos), len([w for w in wos if w['employee_assigned_ids']])))
finally:
    for aid, dom in sauv.items():
        x('base.automation', 'write', [aid], {'filter_domain': dom or False})
    if sauv:
        verif = x('base.automation', 'read', list(sauv), ['filter_domain'])
        print('filtres restaurés :', all((v['filter_domain'] or False) == (sauv[v['id']] or False) for v in verif))
    print('--- nettoyage')
    mo_ids = [o['id'] for o in x('mrp.production', 'search_read', [['origin', '=', nom]], fields=['id'])]
    if mo_ids:
        x('mrp.production', 'action_cancel', mo_ids); x('mrp.production', 'unlink', mo_ids)
    so2 = x('sale.order', 'read', [so_id], ['state', 'picking_ids'])[0]
    if so2['state'] not in ('cancel', 'draft'):
        x('sale.order', 'action_cancel', [so_id], context={'disable_cancel_warning': True})
    pk_ids = so2['picking_ids']
    if pk_ids:
        stp = x('stock.picking', 'read', pk_ids, ['state'])
        todo = [k['id'] for k in stp if k['state'] != 'cancel']
        if todo:
            x('stock.picking', 'action_cancel', todo)
        x('stock.picking', 'unlink', pk_ids)
    x('sale.order', 'unlink', [so_id])
    for model, ids in (('mrp.production', mo_ids), ('sale.order', [so_id]), ('stock.picking', pk_ids)):
        if ids:
            msg = x('mail.message', 'search', [['model', '=', model], ['res_id', 'in', ids]])
            if msg:
                x('mail.message', 'unlink', msg)
            at = x('ir.attachment', 'search', [['res_model', '=', model], ['res_id', 'in', ids]])
            if at:
                x('ir.attachment', 'unlink', at)
    print('   OF %d, transferts %d, commande supprimés ; restes : commandes %d, OF %d' % (len(mo_ids), len(pk_ids), x('sale.order', 'search_count', [['id', '=', so_id]]), x('mrp.production', 'search_count', [['origin', '=', nom]])))
