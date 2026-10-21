# -*- coding: utf-8 -*-
"""Essai réel base de test, uniquement 1979 / 1980 (Fab en cours) : extrait de test_base_test2.py."""
import os, sys, io, time, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
ICI = os.path.dirname(os.path.abspath(__file__))
HOST = 'https://tesmaq211026.odoo.com'; DB = 'tesmaq211026'
U = os.environ['ODOO_USER']; P = os.environ['ODOO_PWD']
uid = xmlrpc.client.ServerProxy(HOST + '/xmlrpc/2/common').authenticate(DB, U, P, {})
m = xmlrpc.client.ServerProxy(HOST + '/xmlrpc/2/object', allow_none=True)
def call(model, meth, *a, **k):
    return m.execute_kw(DB, uid, P, model, meth, list(a), k)
CTX = {'context': {'allowed_company_ids': [1, 3, 4], 'active_test': False}}
assert call('ir.config_parameter', 'get_param', 'web.base.url') == HOST
def code(num, version):
    return io.open(os.path.join(ICI, 'action_%d_%s.py' % (num, version)), encoding='utf-8').read()
def installer(num, version):
    call('ir.actions.server', 'write', [num], {'code': code(num, version)})
def chrono(fn):
    t0 = time.time(); r = fn(); return r, round((time.time() - t0) * 1000)
CH_SO = ['x_studio_fab_encours', 'x_studio_of_non_planifies', 'x_studio_of_non_programmes', 'x_studio_of_tranches', 'x_studio_vol_of', 'x_studio_vol_reste', 'x_studio_produits_fab', 'x_studio_of_liste', 'x_studio_pierres_faites', 'x_studio_date_planif']
ouverts = call('mrp.production', 'search_read', [['state', 'in', ['confirmed', 'progress']], ['company_id', '=', 1], ['origin', '=like', 'S%'], ['workorder_ids', '!=', False]], fields=['name', 'origin', 'workorder_ids'], order='id desc', limit=40, **CTX)
vus, choix = set(), []
for o in ouverts:
    if o['origin'] not in vus:
        vus.add(o['origin']); choix.append(o)
    if len(choix) >= 3: break
ok = True
for of in choix:
    so = call('sale.order', 'search_read', [['name', '=', of['origin']]], fields=['name'] + CH_SO, limit=1, **CTX)
    if not so: continue
    so = so[0]
    def essai(num, version):
        installer(num, version)
        if num == 1979:
            call('mrp.production', 'write', [of['id']], {'origin': 'ESSAI-COMPACTION'}, **CTX)
            call('sale.order', 'write', [so['id']], {'x_studio_of_liste': 'A RECALCULER', 'x_studio_produits_fab': '?'}, **CTX)
            _, t = chrono(lambda: call('mrp.production', 'write', [of['id']], {'origin': of['origin']}, **CTX))
        else:
            wo = of['workorder_ids'][0]
            emp = call('mrp.workorder', 'read', [wo], fields=['employee_assigned_ids'], **CTX)[0]['employee_assigned_ids']
            autre = call('hr.employee', 'search', [['id', 'not in', emp], ['company_id', '=', 1]], limit=1, **CTX)
            call('mrp.workorder', 'write', [wo], {'employee_assigned_ids': [(6, 0, autre)]}, **CTX)
            call('sale.order', 'write', [so['id']], {'x_studio_of_liste': 'A RECALCULER', 'x_studio_produits_fab': '?'}, **CTX)
            _, t = chrono(lambda: call('mrp.workorder', 'write', [wo], {'employee_assigned_ids': [(6, 0, emp)]}, **CTX))
        return call('sale.order', 'read', [so['id']], fields=CH_SO, **CTX)[0], t
    for num in (1979, 1980):
        r1, t1 = essai(num, 'avant'); r2, t2 = essai(num, 'apres')
        same = r1 == r2 and r1['x_studio_of_liste'] != 'A RECALCULER'
        ok &= same
        print('  %d %s (%s) : %s | %d ms -> %d ms' % (num, so['name'], r1['x_studio_of_liste'], 'identique' if same else 'DIFFÉRENT ou non recalculé', t1, t2))
        if r1 != r2:
            for k in r1:
                if r1[k] != r2[k]: print('     ', k, r1[k], '|', r2[k])
print('BILAN fab :', ok, '| code final base de test :', all(call('ir.actions.server', 'read', [n], fields=['code'])[0]['code'] == code(n, 'apres') for n in (1979, 1980)))
