# -*- coding: utf-8 -*-
"""Vue Opérateur (tablette, vue 7907) : un seul opérateur par OT.
Tous les opérateurs utilisent le compte Odoo « Atelier » (employé lié : PIRONNET Thomas). Le bouton Démarrer appelait
mrp.workorder.button_start, qui pointe l'employé du compte et l'AJOUTE aux opérateurs assignés -> 2 opérateurs sur l'OT,
et il revient à chaque Démarrer/Terminer même si le chef d'atelier l'enlève.
Correctif : deux actions serveur qui reçoivent l'opérateur choisi dans la liste de la tablette (context employee_id) :
  - Démarrer : start_employee(op) (pointage au nom de l'opérateur) + date de début si vide + opérateurs assignés = [op]
  - Terminer : button_finish() puis opérateurs assignés = [op]
La vue appelle ces actions ; sans opérateur choisi, la tablette refuse Démarrer / Terminer.   Modes : dry | apply"""
import os, ssl, sys, io, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)


def x(mo, me, *a, **k):
    k.setdefault('context', {'allowed_company_ids': [1]})
    return m.execute_kw(D, uid, p, mo, me, list(a), k)


mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
MODEL_WO = 1042
CODE_START = r"""# Tablette : démarrer l'OT au nom de l'opérateur choisi (context employee_id), un seul opérateur assigné
emp_id = int(env.context.get('employee_id') or 0)
emp = env['hr.employee'].browse(emp_id) if emp_id else env['hr.employee']
if not emp.exists():
    raise UserError("Choisis ton nom en haut de l'écran avant de démarrer.")
for rec in records:
    if rec.state in ('done', 'cancel'):
        continue
    if rec.qty_producing == 0 and rec.qty_remaining:
        rec.write({'qty_producing': rec.qty_remaining})
    rec.start_employee(emp.id)
    vals = {}
    if not rec.date_start:
        vals['date_start'] = datetime.datetime.now()
    if rec.employee_assigned_ids.ids != [emp.id]:
        vals['employee_assigned_ids'] = [Command.set([emp.id])]
    if vals:
        rec.write(vals)
    if not rec.production_id.date_start:
        rec.production_id.write({'date_start': datetime.datetime.now()})
    log('OT %s démarré par %s (tablette)' % (rec.display_name, emp.name), level='info')
"""
CODE_FINISH = r"""# Tablette : terminer l'OT, l'opérateur choisi (context employee_id) reste le seul assigné
emp_id = int(env.context.get('employee_id') or 0)
emp = env['hr.employee'].browse(emp_id) if emp_id else env['hr.employee']
for rec in records:
    if rec.state in ('done', 'cancel'):
        continue
    rec.button_finish()
    if emp.exists() and rec.employee_assigned_ids.ids != [emp.id]:
        rec.write({'employee_assigned_ids': [Command.set([emp.id])]})
    log('OT %s terminé par %s (tablette)' % (rec.display_name, emp.name or '?'), level='info')
"""
NAMES = {'start': 'Tablette - Démarrer OT (opérateur choisi)', 'finish': 'Tablette - Terminer OT (opérateur choisi)'}
ids = {}
for key, name in NAMES.items():
    ex = x('ir.actions.server', 'search', [['name', '=', name], ['model_id', '=', MODEL_WO]])
    ids[key] = ex[0] if ex else None
print('actions existantes :', ids)
raw = x('ir.ui.view', 'read', [7907], fields=['arch'])[0]['arch']
io.open('vue_7907.BEFORE_operateur.xml', 'w', encoding='utf-8').write(raw)
OLD = """              var body;
              if(m==='undo_finish' || m==='button_pending'){
                var _act = (m==='undo_finish') ? 1940 : 1953;
                body = {jsonrpc:'2.0',method:'call',params:{model:'ir.actions.server',method:'run',args:[[_act]],kwargs:{context:{active_model:'mrp.workorder',active_ids:[id]}}}};
              } else {
                body = {jsonrpc:'2.0',method:'call',params:{model:'mrp.workorder',method:m,args:[[id]],kwargs:{}}};
              }
"""
assert raw.count(OLD) == 1, 'bloc JS introuvable (%d)' % raw.count(OLD)
if mode != 'apply':
    print('dry : bloc trouvé, rien écrit'); sys.exit(0)
for key, code in (('start', CODE_START), ('finish', CODE_FINISH)):
    vals = {'name': NAMES[key], 'model_id': MODEL_WO, 'state': 'code', 'code': code}
    if ids[key]:
        x('ir.actions.server', 'write', [ids[key]], vals)
    else:
        r = x('ir.actions.server', 'create', [vals]); ids[key] = r[0] if isinstance(r, list) else r
print('actions serveur :', ids)
NEW = """              var body;
              var opInt = parseInt(op)||0;
              if((m==='button_start' || m==='button_finish') &amp;&amp; !opInt){ voToast("Choisis ton nom en haut de l'écran avant de démarrer ou terminer."); b.disabled=false; render(card); renderP(card); return; }
              var _acts = {undo_finish:1940, button_pending:1953, button_start:%d, button_finish:%d};
              var _act = _acts[m];
              body = {jsonrpc:'2.0',method:'call',params:{model:'ir.actions.server',method:'run',args:[[_act]],kwargs:{context:{active_model:'mrp.workorder',active_ids:[id],employee_id:opInt}}}};
""" % (ids['start'], ids['finish'])
new = raw.replace(OLD, NEW)
x('ir.ui.view', 'write', [7907], {'arch': new})
chk = x('ir.ui.view', 'read', [7907], fields=['arch'])[0]['arch']
io.open('vue_7907.AFTER_operateur.xml', 'w', encoding='utf-8').write(chk)
print('vue 7907 mise à jour :', 'employee_id:opInt' in chk, '| actions', ids)
