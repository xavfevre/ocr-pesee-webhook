# -*- coding: utf-8 -*-
"""Lecture seule : pour chaque action serveur « code » non standard, où est-elle branchée ?
(menu contextuel binding_model_id, menus, boutons de vues type="action", automatisations, crons, actions parentes,
références dans le code du relais). Sortie : actions_inventaire.json + tableau."""
import os, sys, re, json, subprocess, xmlrpc.client
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
URL = 'https://maquignon.odoo.com'; DB = 'maquignon'
U = os.environ['ODOO_USER']; P = os.environ['ODOO_PWD']
uid = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/common').authenticate(DB, U, P, {})
m = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/object', allow_none=True)
def call(model, meth, *a, **k):
    return m.execute_kw(DB, uid, P, model, meth, list(a), k)
CTX = {'context': {'allowed_company_ids': [1, 2, 3, 4, 13], 'active_test': False}}
ICI = os.path.dirname(os.path.abspath(__file__)); OCR = os.path.join(ICI, '..', 'ocr')

def cloc(code):
    n = 0
    for l in (code or '').splitlines():
        s = l.strip()
        if s and not s.startswith('#'):
            n += 1
    return n

std_mods = set()
xmlid = defaultdict(list)
for x in call('ir.model.data', 'search_read', [['model', '=', 'ir.actions.server']], fields=['res_id', 'module'], limit=100000, **CTX):
    xmlid[x['res_id']].append(x['module'])
acts = call('ir.actions.server', 'search_read', [['state', '=', 'code']], fields=['name', 'model_id', 'code', 'binding_model_id', 'binding_type', 'usage', 'create_date', 'write_date', 'child_ids', 'groups_id' if 'groups_id' in call('ir.actions.server', 'fields_get', attributes=['type'], **CTX) else 'name'], order='id', **CTX)
custom = [a for a in acts if not any(mod not in ('studio_customization', '__export__', '__import__', 'maquignon', '__custom__', 'False') for mod in xmlid.get(a['id'], []))]
ids = {a['id'] for a in custom}
# menus
menus = defaultdict(list)
for mn in call('ir.ui.menu', 'search_read', [['action', 'like', 'ir.actions.server,']], fields=['complete_name', 'action'], **CTX):
    menus[int(mn['action'].split(',')[1])].append(mn['complete_name'])
# crons
crons = defaultdict(list)
for c in call('ir.cron', 'search_read', [], fields=['name', 'active', 'ir_actions_server_id'], **CTX):
    if c['ir_actions_server_id']:
        crons[c['ir_actions_server_id'][0]].append((c['name'], 'actif' if c['active'] else 'INACTIF'))
# automatisations
autos = defaultdict(list)
for au in call('base.automation', 'search_read', [], fields=['name', 'active', 'action_server_ids', 'trigger'], **CTX):
    for sid in au['action_server_ids']:
        autos[sid].append((au['name'], 'active' if au['active'] else 'INACTIVE', au['trigger']))
# parents (actions multiples)
parents = defaultdict(list)
for pa in call('ir.actions.server', 'search_read', [['child_ids', '!=', False]], fields=['name', 'child_ids'], **CTX):
    for cid in pa['child_ids']:
        parents[cid].append(pa['name'])
# boutons de vues : <button name="<id>" type="action"> (ou %(xmlid)d non utilisé ici)
boutons = defaultdict(list)
for v in call('ir.ui.view', 'search_read', [['arch_db', 'ilike', 'type="action"']], fields=['name', 'model', 'arch_db'], **CTX):
    for mt in re.finditer(r'<button[^>]*name="(\d+)"[^>]*type="action"|<button[^>]*type="action"[^>]*name="(\d+)"', v['arch_db']):
        bid = int(mt.group(1) or mt.group(2))
        if bid in ids:
            boutons[bid].append('%s (%s)' % (v['name'], v['model']))
# relais : références par numéro dans le code (web_actions.py, app.py, transport_webhooks.py ...)
relais = defaultdict(list)
try:
    out = subprocess.run(['git', 'grep', '-n', '-E', r'\b(1[4-9][0-9]{2}|2[0-1][0-9]{2})\b', '--', '*.py'], cwd=OCR, capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
    for line in out.splitlines():
        if line.startswith('odoo-scan-page/') or line.startswith('odoo-backups/'):
            continue
        for num in set(re.findall(r'\b(1[4-9][0-9]{2}|2[0-1][0-9]{2})\b', line)):
            n = int(num)
            if n in ids and len(relais[n]) < 3:
                relais[n].append(line.split(':')[0] + ':' + line.split(':')[1])
except Exception as e:  # noqa: BLE001
    print('grep relais impossible :', e)

rows = []
for a in custom:
    lignes = cloc(a['code'])
    refs = {'binding': a['binding_model_id'] and a['binding_model_id'][1], 'menus': menus.get(a['id'], []), 'crons': crons.get(a['id'], []),
            'autos': autos.get(a['id'], []), 'parents': parents.get(a['id'], []), 'boutons': boutons.get(a['id'], []), 'relais': relais.get(a['id'], [])}
    branche = any(refs[k] for k in refs)
    rows.append({'id': a['id'], 'nom': a['name'], 'modele': a['model_id'] and a['model_id'][1], 'lignes': lignes, 'usage': a['usage'], 'cree': a['create_date'][:10], 'modifie': a['write_date'][:10], 'refs': refs, 'branche': branche})
json.dump(rows, open(os.path.join(ICI, 'actions_inventaire.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('actions custom avec code :', len(rows), '| branchées quelque part :', sum(1 for r in rows if r['branche']), '| non branchées :', sum(1 for r in rows if not r['branche']))
print('\n== NON BRANCHÉES (ni menu, ni bouton, ni automatisation, ni cron, ni parent, ni relais) ==')
for r in sorted([r for r in rows if not r['branche']], key=lambda x: -x['lignes']):
    print('  %4d l. | id %4d | %-58s | %-26s | créé %s modif %s' % (r['lignes'], r['id'], r['nom'][:58], (r['modele'] or '')[:26], r['cree'], r['modifie']))
print('\n== BRANCHÉES : où ==')
for r in sorted([r for r in rows if r['branche']], key=lambda x: -x['lignes']):
    f = r['refs']
    ou = []
    if f['binding']: ou.append('menu Action sur ' + f['binding'])
    if f['menus']: ou.append('menu ' + '; '.join(f['menus']))
    if f['boutons']: ou.append('bouton ' + '; '.join(f['boutons'][:2]))
    if f['autos']: ou.append('auto ' + '; '.join('%s [%s, %s]' % t for t in f['autos']))
    if f['crons']: ou.append('cron ' + '; '.join('%s [%s]' % t for t in f['crons']))
    if f['parents']: ou.append('dans ' + '; '.join(f['parents']))
    if f['relais']: ou.append('relais ' + '; '.join(f['relais'][:2]))
    print('  %4d l. | id %4d | %-50s | %s' % (r['lignes'], r['id'], r['nom'][:50], ' | '.join(ou)[:150]))
