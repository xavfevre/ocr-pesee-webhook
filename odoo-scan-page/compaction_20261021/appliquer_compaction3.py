# -*- coding: utf-8 -*-
"""Applique en PRODUCTION le code compacté des automatisations 1905, 1904, 1911 (Commande Pierres : étape selon OF, selon commande, selon tâche créée)
et 1477 (Transfert champs BC vers OF), validé par le harnais local (118 cas) et les essais sur tesmaq211026 (21/10/2026).
Garde-fou : le code actuel de production doit être exactement celui des fichiers *_avant.py (sinon on s'arrête).
Usage : python appliquer_compaction.py [apply|retour]   (retour = remet les versions avant)"""
import os, sys, io, xmlrpc.client, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
MODE = sys.argv[1] if len(sys.argv) > 1 else 'simulation'
ICI = os.path.dirname(os.path.abspath(__file__))
URL = 'https://maquignon.odoo.com'; DB = 'maquignon'
U = os.environ['ODOO_USER']; P = os.environ['ODOO_PWD']
uid = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/common').authenticate(DB, U, P, {})
m = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/object', allow_none=True)
def call(model, meth, *a, **k):
    return m.execute_kw(DB, uid, P, model, meth, list(a), k)
assert call('ir.config_parameter', 'get_param', 'web.base.url') == URL
def lire(num, version):
    return io.open(os.path.join(ICI, 'action_%d_%s.py' % (num, version)), encoding='utf-8').read()
def cloc(code):
    return sum(1 for l in code.splitlines() if l.strip() and not l.strip().startswith('#'))
ACTIONS = (1905, 1904, 1911)
actuels = {a['id']: a for a in call('ir.actions.server', 'read', list(ACTIONS), fields=['name', 'code', 'write_date'])}
total_avant = total_apres = 0
for num in ACTIONS:
    a = actuels[num]; avant, apres = lire(num, 'avant'), lire(num, 'apres')
    etat = 'AVANT (à compacter)' if a['code'] == avant else ('APRÈS (déjà compactée)' if a['code'] == apres else 'INCONNU : code différent des deux versions, on n y touche pas')
    print('  %d %-40s %3d -> %3d lignes | production = %s | modifiée %s' % (num, a['name'][:40], cloc(avant), cloc(apres), etat, a['write_date']))
    total_avant += cloc(avant); total_apres += cloc(apres)
print('total : %d -> %d lignes (-%d)' % (total_avant, total_apres, total_avant - total_apres))
if MODE == 'simulation':
    print('simulation : rien écrit'); sys.exit()
horodatage = dt.datetime.now().strftime('%Y%m%d_%H%M')
for num in ACTIONS:
    a = actuels[num]
    io.open(os.path.join(ICI, 'action_%d_prod_%s.py' % (num, horodatage)), 'w', encoding='utf-8', newline='\n').write(a['code'])
    cible = lire(num, 'apres' if MODE == 'apply' else 'avant')
    if a['code'] == cible:
        print('  %d : déjà dans l état voulu' % num); continue
    if MODE == 'apply' and a['code'] != lire(num, 'avant'):
        print('  %d : code de production inattendu, NON modifié' % num); continue
    call('ir.actions.server', 'write', [num], {'code': cible})
    print('  %d : %s' % (num, 'compactée' if MODE == 'apply' else 'remise en version avant'))
