# -*- coding: utf-8 -*-
"""Page « Tarifs pierres » du relais : menu Odoo (15/10/2026).
  - action URL + menu « 💶 Tarifs pierres » dans l'application Ventes (zéro code), jeton = `maquignon.tarifs_key`
    (déjà présent : page Tarifs client).
   python tarifs_pierres_setup.py dry | apply | etat | retour
Identifiants attendus dans l'environnement : ODOO_USER, ODOO_PWD (et ODOO_URL/ODOO_DB facultatifs pour une base de test)."""
import os, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
MODE = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = os.environ.get('ODOO_URL', 'https://maquignon.odoo.com'); D = os.environ.get('ODOO_DB', 'maquignon'); us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common').authenticate(D, us, p, {})
assert uid, 'authentification refusée'
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object')


def x(mo, me, *a, **k):
    k = dict(k); ctx = {'active_test': False}; ctx.update(k.pop('context', {})); k['context'] = ctx
    try:
        return m.execute_kw(D, uid, p, mo, me, list(a), k)
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in str(e):
            return None
        raise


one = lambda v: v[0] if isinstance(v, list) else v
RELAIS = 'https://ocr-pesee-webhook.onrender.com/tarifs-pierres/'
NOM = '💶 Tarifs pierres'
cle = x('ir.config_parameter', 'get_param', 'maquignon.tarifs_key', '') or ''
racine = x('ir.model.data', 'search_read', [['module', '=', 'sale'], ['name', '=', 'sale_menu_root']], fields=['res_id'])
racine = racine[0]['res_id'] if racine else None
menus = x('ir.ui.menu', 'search_read', [['name', '=', NOM]], fields=['id', 'parent_id', 'action'])
print('clé maquignon.tarifs_key :', 'présente' if cle else 'ABSENTE', '| menu racine Ventes :', racine, '| menu :', menus or 'absent')
if MODE == 'etat':
    print('URL :', RELAIS + '?k=' + cle); print('config listes :', x('ir.config_parameter', 'get_param', 'maquignon.tarifs_pierres_cfg', '')); sys.exit()
if MODE == 'retour':
    for mn in menus:
        x('ir.ui.menu', 'unlink', [mn['id']])
        if mn['action'] and mn['action'].startswith('ir.actions.act_url,'):
            x('ir.actions.act_url', 'unlink', [int(mn['action'].split(',')[1])])
    print('menu et action supprimés'); sys.exit()
if MODE != 'apply':
    print('Simulation :', ('créer' if not menus else 'mettre à jour') + ' le menu « %s » (action URL vers %s) sous Ventes.' % (NOM, RELAIS)); sys.exit()
assert cle, 'clé maquignon.tarifs_key absente (page Tarifs client non installée ?)'
url = RELAIS + '?k=' + cle
if menus and menus[0]['action'] and menus[0]['action'].startswith('ir.actions.act_url,'):
    aid = int(menus[0]['action'].split(',')[1]); x('ir.actions.act_url', 'write', [aid], {'name': NOM, 'url': url, 'target': 'new'}); print('action %d et menu %d mis à jour' % (aid, menus[0]['id']))
else:
    aid = one(x('ir.actions.act_url', 'create', [{'name': NOM, 'url': url, 'target': 'new'}]))
    print('menu créé :', one(x('ir.ui.menu', 'create', [{'name': NOM, 'parent_id': racine, 'sequence': 96, 'action': 'ir.actions.act_url,%d' % aid}])), '(action URL %d)' % aid)
print('URL de la page :', url)
