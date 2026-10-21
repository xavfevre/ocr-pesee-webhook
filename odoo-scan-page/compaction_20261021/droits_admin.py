# -*- coding: utf-8 -*-
"""Demande Xavier 21/10/2026 : « seul l'identifiant Isabelle peut créer un utilisateur Odoo ».
La création d'utilisateurs est réservée au groupe « Droits d'accès » (base.group_erp_manager), que « Paramètres »
(base.group_system) inclut. Ce script retire ces deux groupes à tous les utilisateurs internes sauf Isabelle (uid 2) et OdooBot.
Usage : python droits_admin.py [apply]   (simulation sans apply)"""
import os, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
APPLY = len(sys.argv) > 1 and sys.argv[1] == 'apply'
URL = 'https://maquignon.odoo.com'; DB = 'maquignon'
U = os.environ['ODOO_USER']; P = os.environ['ODOO_PWD']
uid = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/common').authenticate(DB, U, P, {})
m = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/object', allow_none=True)
def call(model, meth, *a, **k):
    return m.execute_kw(DB, uid, P, model, meth, list(a), k)
CTX = {'context': {'allowed_company_ids': [1, 2, 3, 4, 13], 'active_test': False}}
def groupe(xmlid):
    mod, name = xmlid.split('.')
    return call('ir.model.data', 'search_read', [['module', '=', mod], ['name', '=', name]], fields=['res_id'], **CTX)[0]['res_id']
G_ACCES, G_PARAM = groupe('base.group_erp_manager'), groupe('base.group_system')
GARDES = {2, 1}   # Isabelle, OdooBot
users = call('res.users', 'search_read', [['share', '=', False], ['active', '=', True], ['group_ids', 'in', [G_ACCES, G_PARAM]]], fields=['name', 'login', 'group_ids'], order='name', **CTX)
plan = [u for u in users if u['id'] not in GARDES]
print('utilisateurs pouvant créer des utilisateurs aujourd hui :', [u['name'] for u in users])
for u in plan:
    print('  retirer %s à %s (%s)' % (' + '.join(n for g, n in ((G_PARAM, 'Paramètres'), (G_ACCES, 'Droits d accès')) if g in u['group_ids']), u['name'], u['login']))
if not APPLY:
    print('simulation : rien écrit'); sys.exit()
for u in plan:
    call('res.users', 'write', [u['id']], {'group_ids': [(3, G_PARAM), (3, G_ACCES)]}, **CTX)
restent = call('res.users', 'search_read', [['share', '=', False], ['active', '=', True], ['group_ids', 'in', [G_ACCES, G_PARAM]]], fields=['name'], **CTX)
print('après : peuvent créer des utilisateurs ->', [u['name'] for u in restent])
