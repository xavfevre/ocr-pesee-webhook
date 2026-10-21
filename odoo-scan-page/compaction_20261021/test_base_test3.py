# -*- coding: utf-8 -*-
"""Essais réels base de test tesmaq211026, série 3 : 1911 (tâche créée), 1904 (commande écrite), 1905 (OF confirmé).
Ancien puis nouveau code, l'étape de la tâche est remise à « Nouveau » (113) avant chaque essai."""
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
def ids(x):
    return x if isinstance(x, list) else [x]
def chrono(fn):
    t0 = time.time(); r = fn(); return r, round((time.time() - t0) * 1000)
def stage(tid):
    return call('project.task', 'read', [tid], fields=['stage_id'], **CTX)[0]['stage_id']
STAGES = [113, 119, 114, 115, 116, 117, 118]
bilan = {}

print('== 1911 tâche créée ==')
ok = True
for nom, dom in (('commande confirmée livrée facturée', [['state', '=', 'sale'], ['delivery_status', '=', 'full'], ['invoice_status', '=', 'invoiced']]), ('commande confirmée en cours', [['state', '=', 'sale'], ['invoice_status', '=', 'to invoice']]), ('devis', [['state', '=', 'draft']])):
    so = call('sale.order', 'search', dom + [['company_id', '=', 1]], order='id desc', limit=1, **CTX)
    if not so: print('  pas de commande pour', nom); continue
    def essai(version):
        installer(1911, version)
        tid, t = chrono(lambda: ids(call('project.task', 'create', [{'name': 'ESSAI COMPACTION', 'project_id': 13, 'x_studio_devis_commandes_1': [(6, 0, so)]}], **CTX))[0])
        st = stage(tid); call('project.task', 'unlink', [tid], **CTX)
        return st, t
    r1, t1 = essai('avant'); r2, t2 = essai('apres')
    same = r1 == r2; ok &= same
    print('  %s -> étape %s : %s | %d ms -> %d ms' % (nom, r1 and r1[1], 'identique' if same else 'DIFFÉRENT %s / %s' % (r1, r2), t1, t2))
bilan['1911'] = ok

print('\n== 1904 commande écrite ==')
ok = True
sos = call('sale.order', 'search_read', [['x_studio_tache', '!=', False], ['x_studio_tache.project_id', '=', 13], ['company_id', '=', 1]], fields=['name', 'x_studio_tache'], order='id desc', limit=3, **CTX)
for so in sos:
    tid = so['x_studio_tache'][0]; avant_stage = stage(tid)
    def essai(version):
        installer(1904, version)
        call('project.task', 'write', [tid], {'stage_id': 113}, **CTX)                 # remise à Nouveau
        call('sale.order', 'write', [so['id']], {'x_studio_tache': False}, **CTX)
        _, t = chrono(lambda: call('sale.order', 'write', [so['id']], {'x_studio_tache': tid}, **CTX))
        return stage(tid), t
    r1, t1 = essai('avant'); r2, t2 = essai('apres')
    same = r1 == r2; ok &= same
    print('  %s -> étape %s : %s | %d ms -> %d ms (étape initiale %s)' % (so['name'], r1 and r1[1], 'identique' if same else 'DIFFÉRENT %s / %s' % (r1, r2), t1, t2, avant_stage and avant_stage[1]))
    if avant_stage and r1 and avant_stage[0] != r1[0]:
        call('project.task', 'write', [tid], {'stage_id': avant_stage[0]}, **CTX)       # on remet l'étape d'origine
bilan['1904'] = ok

print('\n== 1905 OF confirmé ==')
ok = True
brouillons = call('mrp.production', 'search_read', [['state', '=', 'draft'], ['x_studio_tche_commande_pierre', '!=', False], ['company_id', '=', 1]], fields=['name', 'x_studio_tche_commande_pierre'], order='id desc', limit=60, **CTX)
par_tache = {}
for o in brouillons:
    par_tache.setdefault(o['x_studio_tche_commande_pierre'][0], []).append(o)
paires = [(t, l) for t, l in par_tache.items() if len(l) >= 2][:2]
if not paires:
    print('  aucune tâche avec deux OF brouillon sur la base de test : essai sauté (logique couverte par le harnais)')
for tid, lst in paires:
    avant_stage = stage(tid)
    def essai(version, of):
        installer(1905, version)
        call('project.task', 'write', [tid], {'stage_id': 113}, **CTX)
        _, t = chrono(lambda: call('mrp.production', 'action_confirm', [of['id']], **CTX))
        return stage(tid), t
    r1, t1 = essai('avant', lst[0]); r2, t2 = essai('apres', lst[1])
    same = r1 == r2; ok &= same
    print('  tâche %d : %s confirmé -> %s | %s confirmé -> %s : %s | %d ms -> %d ms' % (tid, lst[0]['name'], r1 and r1[1], lst[1]['name'], r2 and r2[1], 'identique' if same else 'DIFFÉRENT', t1, t2))
    if avant_stage and r2 and avant_stage[0] != r2[0]:
        call('project.task', 'write', [tid], {'stage_id': avant_stage[0]}, **CTX)
bilan['1905'] = ok
for n in (1911, 1904, 1905):
    installer(n, 'apres')
print('\nBILAN :', bilan, '| nouveau code installé sur la base de test')
