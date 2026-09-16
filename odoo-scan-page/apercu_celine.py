# -*- coding: utf-8 -*-
"""Aperçu (dry) ou envoi (send) du mail « Commandes entièrement produites, non facturées » à Céline."""
import os, ssl, sys, io, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8'); sys.path.insert(0, 'ocr')
import web_actions as wa
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
def call(model, method, *params, **kw): return m.execute_kw(D, uid, p, model, method, list(params), kw)
rows, html = wa._commandes_produites(call)
print('commandes entièrement produites non facturées :', len(rows))
for cmd, lst in rows[:40]:
    print('  ', cmd, '|', (lst[0]['x_studio_nom_du_client'] or '-')[:34], '|', len(lst), 'OF |',
          sum(int(o['x_studio_nbr'] or 1) for o in lst), 'pierres | dernier', max(o['date_finished'] for o in lst)[:10])
io.open('C:/Users/xavfe/Desktop/Maquignon/Apercu_mail_commandes_produites_celine.html', 'w', encoding='utf-8').write(
    '<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Commandes entièrement produites (aperçu)</title>'
    '<style>body{font-family:Arial,sans-serif;max-width:900px;margin:24px auto;color:#0f172a}</style></head><body>' + html + '</body></html>')
if mode == 'send':
    r = wa._alerte_palettes(call, {'envoyer_celine': 1})
    print('envoyé :', r.get('envoye_celine_a'), '|', r.get('n_commandes_produites'), 'commande(s)')
