# -*- coding: utf-8 -*-
"""Champ x_epaisseur_tranche (float, m) sur mrp.production : épaisseur de tranche retenue pour la pièce, partagée entre
les écrans de la page /planning-tranches (0 = par défaut la hauteur H). Création puis attente de la disponibilité."""
import os, ssl, sys, time, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
ex = x('ir.model.fields', 'search_read', [['model', '=', 'mrp.production'], ['name', '=', 'x_epaisseur_tranche']], fields=['id', 'ttype'])
if ex:
    print('champ déjà présent :', ex)
else:
    mid = x('ir.model', 'search', [['model', '=', 'mrp.production']])[0]
    t = time.time()
    try:
        fid = x('ir.model.fields', 'create', [{'name': 'x_epaisseur_tranche', 'model_id': mid, 'field_description': 'Épaisseur de tranche retenue (m)', 'ttype': 'float', 'state': 'manual', 'store': True, 'copied': False, 'help': 'Cote de la pièce retenue comme épaisseur de tranche (page Tranches). 0 = hauteur H par défaut.'}])
        print('champ créé', fid, 'en %.0f s' % (time.time() - t))
    except Exception as e:
        print('création : réponse', str(e)[:200], '(peut être un délai dépassé pendant le rechargement du registre)')
for i in range(30):
    try:
        fg = x('mrp.production', 'fields_get', ['x_epaisseur_tranche'], ['type', 'string'])
        if 'x_epaisseur_tranche' in fg:
            print('disponible :', fg['x_epaisseur_tranche']); break
    except Exception as e:
        print('attente…', str(e)[:80])
    time.sleep(10)
