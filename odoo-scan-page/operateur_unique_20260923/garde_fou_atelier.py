# -*- coding: utf-8 -*-
"""Garde-fou « un seul opérateur assigné par OT » pour l'écran Atelier standard d'Odoo (non utilisé, mais au cas où).
Mécanisme : quand le compte Atelier (uid 9, employé lié PIRONNET) déclenche button_start/button_finish, Odoo ajoute
PIRONNET aux opérateurs assignés. Une automatisation sur mrp.workorder (écriture de employee_assigned_ids) retire
l'employé du compte Atelier dès qu'il se retrouve en plus d'un autre opérateur.
  test  : sur la base de test (testmaq230926) — 1) comportement de button_start pour un utilisateur SANS employé lié,
          2) automatisation posée avec l'uid du compte de test, button_start -> l'ajout est annulé ; tout est remis en état
  prod  : pose/mise à jour de l'automatisation en production avec uid 9 (Atelier)"""
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


def sur(fn):
    try:
        return fn()
    except xmlrpc.client.Fault as e:
        s = str(e)
        if 'cannot marshal None' in s:
            return None
        msg = s.strip().split('\n')[-1][:300]
        print('   ERREUR :', msg)
        return 'ERR'


NOM = 'OT : un seul opérateur assigné (compte Atelier)'
CODE = """# Garde-fou : quand le compte Atelier demarre/termine un OT depuis l'ecran standard d'Odoo, Odoo ajoute
# l'employe lie au compte (PIRONNET) aux operateurs assignes. On le retire s'il n'est pas seul.
ATELIER_UID = %d
if env.user.id == ATELIER_UID:
    auto = env.user.employee_id
    for rec in records:
        if auto and len(rec.employee_assigned_ids) > 1 and auto in rec.employee_assigned_ids:
            rec.write({'employee_assigned_ids': [Command.unlink(auto.id)]})
"""
MODEL_WO = x('ir.model', 'search', [['model', '=', 'mrp.workorder']])[0]
F_ASSIGN = x('ir.model.fields', 'search', [['model', '=', 'mrp.workorder'], ['name', '=', 'employee_assigned_ids']])[0]


def poser(atelier_uid):
    ex = x('base.automation', 'search', [['name', '=', NOM]])
    vals = {'name': NOM, 'model_id': MODEL_WO, 'trigger': 'on_create_or_write', 'trigger_field_ids': [[6, 0, [F_ASSIGN]]], 'active': True}
    if ex:
        a = x('base.automation', 'read', ex, fields=['action_server_ids'])[0]
        x('base.automation', 'write', ex, vals)
        x('ir.actions.server', 'write', a['action_server_ids'], {'code': CODE % atelier_uid})
        return ex[0]
    vals['action_server_ids'] = [[0, 0, {'name': NOM, 'model_id': MODEL_WO, 'state': 'code', 'code': CODE % atelier_uid, 'usage': 'base_automation'}]]
    r = x('base.automation', 'create', [vals])
    return r[0] if isinstance(r, list) else r


if mode == 'prod':
    aid = poser(9)
    a = x('base.automation', 'read', [aid], fields=['name', 'trigger', 'trigger_field_ids', 'active', 'action_server_ids'])[0]
    print('automatisation en production :', aid, a)
    sys.exit(0)

# ---------- TEST sur la base de test
WO = 19021
def etat(lab):
    w = x('mrp.workorder', 'read', [WO], fields=['state', 'employee_assigned_ids', 'employee_ids', 'time_ids'])[0]
    tl = x('mrp.workcenter.productivity', 'read', w['time_ids'], fields=['employee_id', 'user_id']) if w['time_ids'] else []
    print('   [%s] état %s | assignés %s | travaillant %s | pointages %s' % (lab, w['state'], w['employee_assigned_ids'], w['employee_ids'], [(t['employee_id'] and t['employee_id'][1], t['user_id'] and t['user_id'][1]) for t in tl]))
    return w


def nettoyer(assign):
    w = x('mrp.workorder', 'read', [WO], fields=['time_ids'])[0]
    if w['time_ids']:
        sur(lambda: x('mrp.workcenter.productivity', 'unlink', w['time_ids']))
    x('mrp.workorder', 'write', [WO], {'state': 'ready', 'employee_ids': [[6, 0, []]], 'employee_assigned_ids': [[6, 0, assign]]})


me = x('res.users', 'read', [uid], fields=['name', 'employee_id', 'employee_ids'])[0]
print('compte de test :', me)
emp_me = me['employee_id'] and me['employee_id'][0]
x('mrp.workorder', 'write', [WO], {'employee_assigned_ids': [[6, 0, [654]]]})
etat('départ (assigné LANGLOIS)')
print('1) button_start avec un utilisateur SANS employé lié')
if emp_me:
    x('hr.employee', 'write', [emp_me], {'user_id': False})
print('   employé du compte maintenant :', x('res.users', 'read', [uid], fields=['employee_id'])[0]['employee_id'])
r = sur(lambda: x('mrp.workorder', 'button_start', [WO]))
w = etat('après button_start sans employé')
if emp_me:
    x('hr.employee', 'write', [emp_me], {'user_id': uid})
nettoyer([654])
print('2) automatisation posée (uid de test = %d) puis button_start avec employé lié' % uid)
aid = poser(uid)
print('   automatisation :', aid)
sur(lambda: x('mrp.workorder', 'button_start', [WO]))
w = etat('après button_start avec garde-fou')
ok = w['employee_assigned_ids'] == [654]
print('   RÉSULTAT : opérateur ajouté retiré ->', ok)
sur(lambda: x('mrp.workorder', 'button_finish', [WO]))
w = etat('après button_finish avec garde-fou')
print('   RÉSULTAT finish :', w['employee_assigned_ids'] == [654])
# remise en état : OT prêt, sans pointage, assigné [] comme avant le test
sur(lambda: x('ir.actions.server', 'run', [1940], context={'active_model': 'mrp.workorder', 'active_ids': [WO]}))
nettoyer([])
etat('final (base de test)')
