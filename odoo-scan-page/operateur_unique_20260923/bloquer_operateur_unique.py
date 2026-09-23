# -*- coding: utf-8 -*-
"""Règle « un seul opérateur assigné par OT » (automatisation 95 réécrite) :
 - toute écriture qui laisse >= 2 opérateurs assignés est refusée (message d'erreur), formulaire OF, liste OT, imports…
 - exception : le compte Atelier (uid 9) dont l'employé lié est ajouté automatiquement par l'écran standard d'Odoo -> retiré
   silencieusement (comportement précédent conservé).
  test : base de test — écriture de 2 opérateurs refusée, 1 opérateur acceptée, ajout automatique retiré (uid de test)
  prod : pose en production (uid 9) + essai « 2 opérateurs refusés » sur l'OT 19021 puis remise en l'état"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'test').lower()
U, D = ('https://testmaq230926.odoo.com', 'testmaq230926') if mode == 'test' else ('https://maquignon.odoo.com', 'maquignon')
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)


def x(mo, me, *a, **k):
    k['context'] = dict({'allowed_company_ids': [1]}, **k.get('context', {}))
    return m.execute_kw(D, uid, p, mo, me, list(a), k)


def essai(fn):
    try:
        fn(); return 'accepté'
    except xmlrpc.client.Fault as e:
        s = str(e)
        if 'cannot marshal None' in s:
            return 'accepté'
        return 'REFUSÉ : ' + s.strip().split('\n')[-1][:160]


NOM = 'OT : un seul opérateur assigné'
CODE = """# Regle : un seul operateur assigne par ordre de travail.
# Exception : le compte Atelier (ecran standard d'Odoo) fait ajouter son employe lie automatiquement -> on le retire.
ATELIER_UID = %d
for rec in records:
    emps = rec.employee_assigned_ids
    if len(emps) <= 1:
        continue
    auto = env.user.employee_id if env.user.id == ATELIER_UID else env['hr.employee']
    if auto and auto in emps:
        rec.write({'employee_assigned_ids': [Command.unlink(auto.id)]})
        continue
    raise UserError("Un seul opérateur par ordre de travail. %%s a %%d opérateurs assignés (%%s) : n'en gardez qu'un." %% (rec.display_name, len(emps), ', '.join(emps.mapped('name'))))
"""
MODEL_WO = x('ir.model', 'search', [['model', '=', 'mrp.workorder']])[0]
F_ASSIGN = x('ir.model.fields', 'search', [['model', '=', 'mrp.workorder'], ['name', '=', 'employee_assigned_ids']])[0]


def poser(atelier_uid):
    ex = x('base.automation', 'search', ['|', ['name', '=', NOM], ['name', '=', 'OT : un seul opérateur assigné (compte Atelier)']])
    vals = {'name': NOM, 'model_id': MODEL_WO, 'trigger': 'on_create_or_write', 'trigger_field_ids': [[6, 0, [F_ASSIGN]]], 'active': True}
    if ex:
        a = x('base.automation', 'read', ex[:1], fields=['action_server_ids'])[0]
        x('base.automation', 'write', ex[:1], vals)
        x('ir.actions.server', 'write', a['action_server_ids'], {'name': NOM, 'code': CODE % atelier_uid})
        return ex[0]
    vals['action_server_ids'] = [[0, 0, {'name': NOM, 'model_id': MODEL_WO, 'state': 'code', 'code': CODE % atelier_uid, 'usage': 'base_automation'}]]
    r = x('base.automation', 'create', [vals])
    return r[0] if isinstance(r, list) else r


WO = 19021
lire = lambda: x('mrp.workorder', 'read', [WO], fields=['employee_assigned_ids', 'state'])[0]
if mode == 'prod':
    aid = poser(9)
    print('automatisation en production :', aid, x('base.automation', 'read', [aid], fields=['name', 'active', 'trigger_field_ids'])[0])
    avant = lire()
    print('OT 19021 avant :', avant)
    print('essai 2 opérateurs :', essai(lambda: x('mrp.workorder', 'write', [WO], {'employee_assigned_ids': [[6, 0, [654, 481]]]})))
    print('essai 1 opérateur :', essai(lambda: x('mrp.workorder', 'write', [WO], {'employee_assigned_ids': [[6, 0, [654]]]})))
    x('mrp.workorder', 'write', [WO], {'employee_assigned_ids': [[6, 0, avant['employee_assigned_ids']]]})
    print('OT 19021 remis :', lire())
    sys.exit(0)
# ---------- base de test
aid = poser(uid)   # l'uid du compte de test joue le rôle du compte Atelier
print('automatisation (test, uid %d) :' % uid, aid)
x('mrp.workorder', 'write', [WO], {'employee_assigned_ids': [[6, 0, [654]]]})
print('écriture 2 opérateurs [654, 481] :', essai(lambda: x('mrp.workorder', 'write', [WO], {'employee_assigned_ids': [[6, 0, [654, 481]]]})), '->', lire()['employee_assigned_ids'])
print('ajout d\'un 2e opérateur [4, 481] :', essai(lambda: x('mrp.workorder', 'write', [WO], {'employee_assigned_ids': [[4, 481]]})), '->', lire()['employee_assigned_ids'])
print('écriture 1 opérateur [481] :', essai(lambda: x('mrp.workorder', 'write', [WO], {'employee_assigned_ids': [[6, 0, [481]]]})), '->', lire()['employee_assigned_ids'])
print('mécanisme Atelier (button_start ajoute l\'employé du compte) :', essai(lambda: x('mrp.workorder', 'button_start', [WO])), '->', lire())
print('fin (button_finish) :', essai(lambda: x('mrp.workorder', 'button_finish', [WO])), '->', lire())
# remise en état de l'OT de test
essai(lambda: x('ir.actions.server', 'run', [1940], context={'active_model': 'mrp.workorder', 'active_ids': [WO]}))
w = x('mrp.workorder', 'read', [WO], fields=['time_ids'])[0]
if w['time_ids']:
    essai(lambda: x('mrp.workcenter.productivity', 'unlink', w['time_ids']))
x('mrp.workorder', 'write', [WO], {'state': 'ready', 'employee_ids': [[6, 0, []]], 'employee_assigned_ids': [[6, 0, []]]})
print('OT de test remis :', lire())
