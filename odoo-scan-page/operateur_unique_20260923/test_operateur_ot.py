# -*- coding: utf-8 -*-
"""Test contrôlé : comment Odoo 19 gère l'opérateur quand on démarre un OT par RPC.
Sur un OT « prêt » (OF déjà en cours, assigné à LANGLOIS 654, sans pointage) :
  A. button_start avec context employee_id=654  -> pointage ? assignés ? état ?  puis button_pending (même contexte)
  B. start_employee(654)                        -> idem, puis stop_employee([654])
Nettoyage : suppression des pointages créés, restauration assignés / travaillant / état / date_start."""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
BASE = {'allowed_company_ids': [1]}


def x(mo, me, *a, **k):
    ctx = dict(BASE, **k.pop('ctx', {}))
    k['context'] = ctx
    return m.execute_kw(D, uid, p, mo, me, list(a), k)


def sur(fn):
    try:
        return fn()
    except xmlrpc.client.Fault as e:
        s = str(e)
        if 'cannot marshal None' in s:
            return None
        print('   ERREUR :', s.strip().split('\n')[-1][:200])
        return 'ERR'


def etat(wid, lab):
    w = x('mrp.workorder', 'read', [wid], fields=['state', 'employee_assigned_ids', 'employee_ids', 'time_ids', 'date_start', 'production_id'])[0]
    tl = x('mrp.workcenter.productivity', 'read', w['time_ids'], fields=['employee_id', 'user_id', 'date_start', 'date_end']) if w['time_ids'] else []
    print('   [%s] état %s | assignés %s | travaillant %s | date_start %s | pointages %s' % (lab, w['state'], w['employee_assigned_ids'], w['employee_ids'], w['date_start'], [(t['employee_id'] and t['employee_id'][1], t['user_id'] and t['user_id'][1], t['date_end'] and 'fermé' or 'ouvert') for t in tl]))
    return w


# méthodes existantes ?
for meth, args in (('stop_employee', [[654]]), ('button_start', []), ('button_pending', []), ('button_finish', [])):
    try:
        x('mrp.workorder', meth, [], *args); print(meth, ': OK sur recordset vide')
    except xmlrpc.client.Fault as e:
        print(meth, ':', str(e).strip().split('\n')[-1][:140])
print('employé du compte RPC (Isabelle) :', x('res.users', 'read', [uid], fields=['employee_id'])[0]['employee_id'])
cand = x('mrp.workorder', 'search_read', [['production_id.company_id', '=', 1], ['state', '=', 'ready'], ['production_id.state', '=', 'progress'], ['employee_assigned_ids', '=', 654], ['time_ids', '=', False], ['workcenter_id', '!=', 27]], fields=['id', 'name', 'production_id', 'workcenter_id', 'employee_assigned_ids', 'date_start'], limit=1)
assert cand, 'pas de candidat'
w0 = cand[0]; wid = w0['id']
print('OT test :', wid, w0['name'], w0['production_id'][1], w0['workcenter_id'][1], 'date_start', w0['date_start'])
prod0 = x('mrp.production', 'read', [w0['production_id'][0]], fields=['state', 'date_start'])[0]
avant = etat(wid, 'avant')
# A. button_start + context employee_id
print('A. button_start(context employee_id=654)')
r = sur(lambda: x('mrp.workorder', 'button_start', [wid], ctx={'employee_id': 654}))
a1 = etat(wid, 'après start')
print('   button_pending(context employee_id=654)')
sur(lambda: x('mrp.workorder', 'button_pending', [wid], ctx={'employee_id': 654}))
a2 = etat(wid, 'après pending')
# nettoyage intermédiaire des pointages
if a2['time_ids']:
    sur(lambda: x('mrp.workcenter.productivity', 'unlink', a2['time_ids']))
x('mrp.workorder', 'write', [wid], {'employee_assigned_ids': [[6, 0, avant['employee_assigned_ids']]], 'employee_ids': [[6, 0, avant['employee_ids']]]})
etat(wid, 'nettoyé A')
# B. start_employee / stop_employee
print('B. start_employee(654)')
sur(lambda: x('mrp.workorder', 'start_employee', [wid], 654))
b1 = etat(wid, 'après start_employee')
print('   stop_employee([654])')
sur(lambda: x('mrp.workorder', 'stop_employee', [wid], [654]))
b2 = etat(wid, 'après stop_employee')
# nettoyage final
if b2['time_ids']:
    sur(lambda: x('mrp.workcenter.productivity', 'unlink', b2['time_ids']))
vals = {'employee_assigned_ids': [[6, 0, avant['employee_assigned_ids']]], 'employee_ids': [[6, 0, avant['employee_ids']]]}
if avant['date_start'] != b2['date_start']:
    vals['date_start'] = avant['date_start']
x('mrp.workorder', 'write', [wid], vals)
fin = etat(wid, 'final')
if fin['state'] != avant['state']:
    print('   état différent (%s -> %s) : tentative de remise' % (avant['state'], fin['state']))
    sur(lambda: x('mrp.workorder', 'write', [wid], {'state': avant['state']}))
    etat(wid, 'final 2')
prod1 = x('mrp.production', 'read', [w0['production_id'][0]], fields=['state', 'date_start'])[0]
print('OF avant/après :', prod0, prod1)
