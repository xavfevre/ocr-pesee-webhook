# -*- coding: utf-8 -*-
"""Ménage des opérateurs assignés (SARL MAQUIGNON) : PIRONNET Thomas (497) a été ajouté mécaniquement aux OT par le compte
tablette « Atelier » (uid 9) à chaque Démarrer/Terminer. Règle : OT (tous états sauf annulé) avec >= 2 opérateurs assignés
dont 497, ET au moins un pointage de 497 fait par l'utilisateur Atelier -> on retire 497, l'opérateur prévu reste.
Les pointages ne sont pas touchés.   Modes : dry | apply"""
import os, ssl, sys, xmlrpc.client, collections
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U, D = ('https://maquignon.odoo.com', 'maquignon')
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [1]}))
PIR, ATELIER = 497, 9
wos = x('mrp.workorder', 'search_read', [['production_id.company_id', '=', 1], ['state', '!=', 'cancel'], ['employee_assigned_ids', 'in', [PIR]]],
        fields=['state', 'employee_assigned_ids', 'time_ids', 'workcenter_id', 'date_finished', 'production_id'])
multi = [w for w in wos if len(w['employee_assigned_ids']) > 1]
print('OT avec PIRONNET assigné :', len(wos), '| dont avec d\'autres opérateurs :', len(multi), '| par état :', dict(collections.Counter(w['state'] for w in multi)))
tids = [t for w in multi for t in w['time_ids']]
tl = {}
for i in range(0, len(tids), 2000):
    for t in x('mrp.workcenter.productivity', 'read', tids[i:i + 2000], fields=['employee_id', 'user_id']):
        tl[t['id']] = t
cible, sans_preuve = [], []
for w in multi:
    logs = [tl[t] for t in w['time_ids'] if t in tl]
    meca = any(t['employee_id'] and t['employee_id'][0] == PIR and t['user_id'] and t['user_id'][0] == ATELIER for t in logs)
    (cible if meca else sans_preuve).append(w)
emp = {e['id']: e['name'] for e in x('hr.employee', 'search_read', [['company_id', '=', 1]], fields=['name'])}
print('à nettoyer (pointage PIRONNET par Atelier) :', len(cible), '| par état :', dict(collections.Counter(w['state'] for w in cible)))
print('   autres opérateurs conservés :', collections.Counter(emp.get(e, e) for w in cible for e in w['employee_assigned_ids'] if e != PIR).most_common())
print('   par mois de fin :', sorted(collections.Counter((w['date_finished'] or '')[:7] for w in cible).items()))
print('laissés (PIRONNET + autres, sans pointage Atelier) :', len(sans_preuve), [(w['id'], w['state'], [emp.get(e, e) for e in w['employee_assigned_ids']]) for w in sans_preuve[:10]])
if mode != 'apply':
    sys.exit(0)
ids = [w['id'] for w in cible]
for i in range(0, len(ids), 40):
    x('mrp.workorder', 'write', ids[i:i + 40], {'employee_assigned_ids': [[3, PIR]]})
    print('   %d / %d' % (min(i + 40, len(ids)), len(ids)))
reste = x('mrp.workorder', 'search_read', [['id', 'in', ids]], fields=['employee_assigned_ids'])
print('contrôle : OT encore avec PIRONNET :', sum(1 for w in reste if PIR in w['employee_assigned_ids']), '| OT sans opérateur :', sum(1 for w in reste if not w['employee_assigned_ids']), '| avec 2+ :', sum(1 for w in reste if len(w['employee_assigned_ids']) > 1))
