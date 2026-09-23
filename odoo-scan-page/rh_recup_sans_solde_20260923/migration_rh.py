# -*- coding: utf-8 -*-
"""Migration des jours existants vers la nouvelle logique (x_hs = heures comptées en récup) :
 1. jours entiers de récup : x_hs = − x_theo, x_h_recup = x_theo
 2. jours de travail avec note « Récupération — … » (récup partielle, ancien mode : théo réduit) :
    x_theo = horaire complet du calendrier, x_h_recup = horaire − travaillé, x_hs = − x_h_recup, note « Récup X h (bureau/demande) »
 3. JOLLY Floran 11/09/2026 : « absence » -> journée sans solde (feuille manuelle de Charlotte : sans solde −5,00)
 4. automatisation 87 (miroir hr.leave) : type sans_solde -> Congés sans solde (type natif 9)
 5. contrôle : x_hs des jours de travail = heures − théo (S = 0), aucun jour de type inconnu
   python migration_rh.py test|prod [apply]"""
import os, ssl, sys, xmlrpc.client, datetime, importlib.util
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'test').lower()
apply = 'apply' in sys.argv[2:]
U, D = ('https://testmaq230926v2.odoo.com', 'testmaq230926v2') if mode == 'test' else ('https://maquignon.odoo.com', 'maquignon')
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
def call(mo, me, *a, **k): return m.execute_kw(D, uid, p, mo, me, list(a), k)
spec = importlib.util.spec_from_file_location('ha', 'ocr/heures_actions.py'); ha = importlib.util.module_from_spec(spec); spec.loader.exec_module(ha)
F = ['x_employee_id', 'x_date', 'x_type', 'x_heures', 'x_theo', 'x_hs', 'x_h_recup', 'x_h_sans_solde', 'x_note']
print('==', mode, '| apply' if apply else '| simulation')
# 1. jours entiers de récup
rec = call('x_heures_jour', 'search_read', [['x_type', '=', 'recup']], F)
for r in rec:
    print('1. récup journée', r['x_employee_id'][1][:18], r['x_date'], 'theo', r['x_theo'], '-> hs', -r['x_theo'])
    if apply:
        call('x_heures_jour', 'write', [r['id']], {'x_hs': -r['x_theo'], 'x_h_recup': r['x_theo'], 'x_h_sans_solde': 0.0})
# 2. récup partielle ancien mode
part = call('x_heures_jour', 'search_read', [['x_type', '=', 'travail'], ['x_note', 'like', 'Récupération —']], F)
for r in part:
    emp = call('hr.employee', 'read', [r['x_employee_id'][0]], ['resource_calendar_id'])[0]
    d = datetime.datetime.strptime(r['x_date'], '%Y-%m-%d').date()
    cal, atts = ha._cal_info(call, emp['resource_calendar_id'][0])
    theo = sum(x[1] - x[0] for x in ha._rngs_jour(cal, atts, d))
    hr = max(theo - r['x_heures'], 0.0)
    origine = 'demande' if '(demande' in r['x_note'] else 'bureau'
    note = 'Récup %s h (%s)' % (('%.2f' % hr).replace('.', ','), origine)
    print('2. récup partielle', r['x_employee_id'][1][:18], r['x_date'], 'H', r['x_heures'], 'théo', r['x_theo'], '->', theo, '| récup', hr, '| note', repr(note))
    if apply:
        call('x_heures_jour', 'write', [r['id']], {'x_theo': theo, 'x_h_recup': hr, 'x_h_sans_solde': 0.0, 'x_hs': round(r['x_heures'] - theo, 4), 'x_note': note})
# 3. JOLLY 11/09
j = call('x_heures_jour', 'search_read', [['x_employee_id.name', '=', 'JOLLY Floran'], ['x_date', '=', '2026-09-11']], F)
for r in j:
    print('3. JOLLY 11/09 :', r['x_type'], 'theo', r['x_theo'], '-> sans_solde, S =', r['x_theo'])
    if apply and r['x_type'] == 'absence':
        call('x_heures_jour', 'write', [r['id']], {'x_type': 'sans_solde', 'x_h_sans_solde': r['x_theo'], 'x_h_recup': 0.0, 'x_hs': 0.0, 'x_note': 'Sans solde (feuille papier)'})
# 4. automatisation 87
a = call('base.automation', 'read', [87], ['action_server_ids', 'name'])[0]
code = call('ir.actions.server', 'read', a['action_server_ids'], ['code'])[0]['code']
OLD = "    elif rec.x_type == 'recup':\n        lt = 8\n"
NEW = "    elif rec.x_type == 'recup':\n        lt = 8\n    elif rec.x_type == 'sans_solde':\n        lt = 9\n"
if NEW in code:
    print('4. automatisation 87 : déjà patchée')
else:
    assert code.count(OLD) == 1, 'bloc introuvable dans 87'
    print('4. automatisation 87 :', a['name'], '-> sans_solde miroité en type natif 9')
    if apply:
        call('ir.actions.server', 'write', a['action_server_ids'], {'code': code.replace(OLD, NEW)})
# 5. contrôle
if apply:
    bad = [r for r in call('x_heures_jour', 'search_read', [['x_type', '=', 'travail']], F) if abs((r['x_heures'] + (r['x_h_sans_solde'] or 0) - r['x_theo']) - r['x_hs']) > 0.01]
    print('5. contrôle : jours de travail dont x_hs != H + S − T :', len(bad), [(b['x_employee_id'][1][:15], b['x_date'], b['x_heures'], b['x_theo'], b['x_hs']) for b in bad[:8]])
    print('   types :', {t: call('x_heures_jour', 'search_count', [['x_type', '=', t]]) for t in ('travail', 'cp', 'maladie', 'ferie', 'absence', 'recup', 'repos', 'sans_solde')})
