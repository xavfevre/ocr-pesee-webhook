# -*- coding: utf-8 -*-
"""Tableau de bord 23 v7 (Xavier, 22/10/2026 : « exclus les écarts de caisse du tableau de bord ») : le CA ne compte plus que les
comptes 70xxxxx (ventes), comme la balance Sage classe 70. Les écarts de caisse (758000), produits divers et autres classes 74-79
sortent du CA. Part du contenu actuel du tableau dans Odoo (pas d'un fichier). Usage : python dash23_v7.py dry|apply"""
import os, ssl, sys, json, io, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context(); uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
ICI = os.path.dirname(os.path.abspath(__file__))
raw = x('spreadsheet.dashboard', 'read', [23], ['spreadsheet_data'])[0]['spreadsheet_data']
js = json.loads(raw); sh = js['sheets'][0]
io.open(os.path.join(ICI, 'audit', 'dash23.BEFORE_v7.json'), 'w', encoding='utf-8').write(raw)
DOM = ['&', '&', ['parent_state', '=', 'posted'], ['account_id.code', '=like', '70%'], ['display_type', 'in', ['product', 'tax']]]
touches = []
for pid, pv in js['pivots'].items():
    if pv.get('model') == 'account.move.line':
        pv['domain'] = DOM; touches.append('pivot ' + pid)
for fg in sh.get('figures', []):
    sp = fg.get('data', {}).get('searchParams')
    if sp is not None and fg['data'].get('metaData', {}).get('resModel') == 'account.move.line':
        sp['domain'] = DOM; touches.append('graphique ' + str(fg['data'].get('title', {}).get('text', fg.get('id'))))
sh['cells']['A2'] = "Toutes les écritures validées sur les comptes de ventes 70xxxxx (factures, avoirs, caisse) — ventes + contributions TGAP/REP, hors écarts de caisse et produits divers · filtres Période / Société / Catégorie en haut"
data = json.dumps(js, ensure_ascii=False)
io.open(os.path.join(ICI, 'audit', 'dash23.AFTER_v7.json'), 'w', encoding='utf-8').write(data)
print('domaines mis à jour :', touches)
if mode == 'apply':
    x('spreadsheet.dashboard', 'write', [23], {'spreadsheet_data': data}); print('tableau de bord 23 mis à jour (v7 : comptes 70 seulement)')
else:
    print('(essai : rien écrit dans Odoo, relancer avec apply)')
