# -*- coding: utf-8 -*-
"""Opérateur par défaut par machine (liste manuscrite de Xavier du 23/09/2026) :
 Atelier : Gracia 1 -> GILLARD Loïc, Gracia 2 -> PIRONNET Thomas, Escande 1 -> GUERIN Frédéric, TC1350 Atelier -> JOLLY Floran,
           Escande 2 -> DESPUJOLS Loïc, Polissoir Thibault -> LANGLOIS Nicolas
 Usine   : TSH 2300 -> CHEVALIER Christophe, TC625 -> LANGLOIS Nicolas, GMM -> JOLLY Floran, TC1350 Usine -> LANGLOIS Nicolas,
           Tour OMAG -> LANGLOIS Nicolas   (Palettisation -> Claude FABRÉ : pas de poste ni d'employé dans Odoo, en attente)
 1. automatisation 57 (opérateur par défaut à la création de l'OT) : nouvelle table par id de poste
 2. automatisation 48 (changement de poste dans le formulaire) : même table, remplace l'opérateur
 3. OT non planifiés (ouverts, sans date de début) sur ces postes : opérateur = défaut du poste
Modes : dry | apply"""
import os, ssl, sys, xmlrpc.client, collections
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U, D = ('https://maquignon.odoo.com', 'maquignon')
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [1], 'active_test': False}))
DEFAULTS = {18: 481, 6: 497, 28: 497, 7: 628, 22: 662, 8: 478, 24: 654, 20: 476, 5: 654, 21: 662, 9: 654, 15: 654}
wc = {w['id']: w['name'] for w in x('mrp.workcenter', 'search_read', [], fields=['name'])}
emp = {e['id']: e['name'] for e in x('hr.employee', 'search_read', [['company_id', '=', 1]], fields=['name'])}
print('employés « Claude » :', [(e['id'], e['name']) for e in x('hr.employee', 'search_read', [['name', 'ilike', 'claude']], fields=['name'])])
print('table :')
for k, v in DEFAULTS.items():
    assert k in wc and v in emp, (k, v)
    print('   %-24s -> %s' % (wc[k], emp[v]))
table = '\n'.join('    %d: %d,   # %s -> %s' % (k, v, wc[k], emp[v]) for k, v in DEFAULTS.items())
CODE57 = """# Opérateur par défaut selon la machine (liste Xavier du 23/09/2026)
# N'écrit que si aucun opérateur n'est déjà assigné
DEFAULTS = {
%s
}
for rec in records:
    if rec.employee_assigned_ids:
        continue
    emp = DEFAULTS.get(rec.workcenter_id.id)
    if emp:
        rec.write({'employee_assigned_ids': [(6, 0, [emp])]})
""" % table
CODE48 = """# Changement de poste dans le formulaire : l'opérateur devient celui par défaut de la nouvelle machine (liste Xavier du 23/09/2026)
DEFAULTS = {
%s
}
emp = DEFAULTS.get(record.workcenter_id.id) if record.workcenter_id else None
if emp:
    record.write({'employee_assigned_ids': [Command.set([emp])]})
""" % table
# ---- OT non planifiés à mettre à jour
wos = x('mrp.workorder', 'search_read', [['production_id.company_id', '=', 1], ['state', 'not in', ['progress', 'done', 'cancel']], ['date_start', '=', False], ['workcenter_id', 'in', list(DEFAULTS)]],
        fields=['workcenter_id', 'employee_assigned_ids', 'state'])
plan = collections.defaultdict(list)
for w in wos:
    d = DEFAULTS[w['workcenter_id'][0]]
    if w['employee_assigned_ids'] != [d]:
        plan[(w['workcenter_id'][1], tuple(emp.get(e, e) for e in w['employee_assigned_ids']), emp[d])].append(w['id'])
print('OT non planifiés sur ces postes :', len(wos), '| à modifier :', sum(len(v) for v in plan.values()))
for (wcn, avant, apres), ids in sorted(plan.items()):
    print('   %-20s %-32s -> %-22s %4d OT' % (wcn, ', '.join(avant) or '(aucun)', apres, len(ids)))
if mode != 'apply':
    sys.exit(0)
a57 = x('base.automation', 'read', [57], fields=['action_server_ids'])[0]
x('ir.actions.server', 'write', a57['action_server_ids'], {'code': CODE57})
a48 = x('base.automation', 'read', [48], fields=['action_server_ids'])[0]
x('ir.actions.server', 'write', a48['action_server_ids'], {'code': CODE48})
print('automatisations 57 et 48 mises à jour')
n = 0
for (wcn, avant, apres), ids in plan.items():
    d = [k for k, v in DEFAULTS.items() if emp[v] == apres and wc[k] == wcn][0]
    for i in range(0, len(ids), 40):
        x('mrp.workorder', 'write', ids[i:i + 40], {'employee_assigned_ids': [[6, 0, [DEFAULTS[d]]]]})
        n += len(ids[i:i + 40])
print('OT mis à jour :', n)
chk = x('mrp.workorder', 'search_read', [['id', 'in', [i for v in plan.values() for i in v]]], fields=['workcenter_id', 'employee_assigned_ids'])
print('contrôle :', collections.Counter((w['workcenter_id'][1], emp.get(w['employee_assigned_ids'][0]) if w['employee_assigned_ids'] else None) for w in chk).most_common())
