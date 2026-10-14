# -*- coding: utf-8 -*-
"""Page « Heures engins » du relais : objets Odoo (14/10/2026).
  - paramètre système `maquignon.engins_key` (clé d'accès de la page), créé s'il n'existe pas ;
  - action URL + menu « ⏱ Heures engins » dans l'application Parc automobile (zéro code).
   python engins_heures_setup.py dry | apply | etat | retour
Identifiants attendus dans l'environnement : ODOO_USER, ODOO_PWD."""
import os, sys, secrets, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
MODE = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
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
RELAIS = 'https://ocr-pesee-webhook.onrender.com/heures-engins/'
NOM = '⏱ Heures engins'
cle = x('ir.config_parameter', 'get_param', 'maquignon.engins_key', '') or ''
racine = x('ir.model.data', 'search_read', [['module', '=', 'fleet'], ['name', '=', 'menu_root']], fields=['res_id'])
racine = racine[0]['res_id'] if racine else None
menus = x('ir.ui.menu', 'search_read', [['name', 'ilike', 'Heures engins']], fields=['id', 'parent_id', 'action', 'name'])
print('clé :', 'présente' if cle else 'ABSENTE', '| menu racine Parc automobile :', racine, '| menu :', menus or 'absent')
if MODE == 'etat':
    print('URL :', RELAIS + '?k=' + cle); sys.exit()
if MODE == 'retour':
    for mn in menus:
        x('ir.ui.menu', 'unlink', [mn['id']])
        if mn['action'] and mn['action'].startswith('ir.actions.act_url,'):
            x('ir.actions.act_url', 'unlink', [int(mn['action'].split(',')[1])])
    print('menu et action supprimés'); sys.exit()
if MODE != 'apply':
    print('Simulation :', ('créer la clé' if not cle else 'clé conservée') + ', ' + ('créer' if not menus else 'mettre à jour') + ' le menu « %s » (action URL vers %s) sous le menu racine %s.' % (NOM, RELAIS, racine)); sys.exit()
assert racine, 'menu racine du Parc automobile introuvable'
if not cle:
    cle = secrets.token_urlsafe(18); x('ir.config_parameter', 'set_param', 'maquignon.engins_key', cle); print('clé créée')
url = RELAIS + '?k=' + cle
if menus and menus[0]['action'] and menus[0]['action'].startswith('ir.actions.act_url,'):
    aid = int(menus[0]['action'].split(',')[1]); x('ir.actions.act_url', 'write', [aid], {'name': NOM, 'url': url, 'target': 'new'}); x('ir.ui.menu', 'write', [menus[0]['id']], {'name': NOM}); print('action %d et menu %d mis à jour (%s)' % (aid, menus[0]['id'], NOM))
else:
    aid = one(x('ir.actions.act_url', 'create', [{'name': NOM, 'url': url, 'target': 'new'}])); print('action URL créée :', aid)
    if menus:
        x('ir.ui.menu', 'write', [menus[0]['id']], {'action': 'ir.actions.act_url,%d' % aid, 'parent_id': racine, 'sequence': 60}); print('menu %d relié' % menus[0]['id'])
    else:
        print('menu créé :', one(x('ir.ui.menu', 'create', [{'name': NOM, 'parent_id': racine, 'sequence': 60, 'action': 'ir.actions.act_url,%d' % aid}])))
print('URL de la page :', url)
