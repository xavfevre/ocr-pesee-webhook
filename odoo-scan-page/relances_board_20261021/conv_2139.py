# -*- coding: utf-8 -*-
"""Action 2139 « RELANCES - Mise a jour du board » : 236 lignes de Python facturées -> action « Créer un enregistrement »
x_relais_tache nommé relances_board (0 ligne), exécutée par le relais (relances_board.py). Même id, même nom : tout ce qui
lançait l'action continue de marcher. Sauvegarde du code dans action_2139_code_<date>.py avant modification.
Usage : python conv_2139.py [apply]"""
import os, sys, io, xmlrpc.client, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
APPLY = len(sys.argv) > 1 and sys.argv[1] == 'apply'
URL = 'https://maquignon.odoo.com'; DB = 'maquignon'
U = os.environ['ODOO_USER']; P = os.environ['ODOO_PWD']
uid = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/common').authenticate(DB, U, P, {})
m = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/object', allow_none=True)
def call(model, meth, *a, **k):
    return m.execute_kw(DB, uid, P, model, meth, list(a), k)
CTX = {'context': {'allowed_company_ids': [1, 3, 4]}}
ICI = os.path.dirname(os.path.abspath(__file__))
a = call('ir.actions.server', 'read', [2139], fields=['name', 'state', 'code', 'model_id', 'crud_model_id', 'value', 'usage'], **CTX)[0]
print('action 2139 :', a['name'], '| type', a['state'], '| modèle', a['model_id'], '| code :', (a['code'] or '').count('\n') + 1 if a['code'] else 0, 'lignes')
if a['state'] != 'code':
    print('déjà convertie : rien à faire'); sys.exit()
sauv = os.path.join(ICI, 'action_2139_code_%s.py' % dt.datetime.now().strftime('%Y%m%d_%H%M'))
io.open(sauv, 'w', encoding='utf-8', newline='\n').write(a['code'])
print('code sauvegardé :', sauv)
modele = call('ir.model', 'search_read', [['model', '=', 'x_relais_tache']], fields=['id'], **CTX)[0]['id']
vals = {'state': 'object_create', 'model_id': modele, 'crud_model_id': modele, 'evaluation_type': 'value', 'value': 'relances_board', 'code': False,
        'name': 'RELANCES - Mise à jour du board (exécutée par le relais)'}
print('nouvelles valeurs :', vals)
if not APPLY:
    print('simulation : rien écrit'); sys.exit()
call('ir.actions.server', 'write', [2139], vals, **CTX)
b = call('ir.actions.server', 'read', [2139], fields=['name', 'state', 'code', 'model_id', 'crud_model_id', 'value'], **CTX)[0]
print('après :', b)
