# -*- coding: utf-8 -*-
"""Automatisation 7 « Transfert champs BC vers OF » (action serveur 1477) : la quantité de l'OF n'est réécrite que si
elle change réellement une fois arrondie à l'unité (m³, 0,001). Avant : réécriture systématique (volume à 4-5 décimales
sur un OF déjà à la bonne quantité arrondie) = 0,37 s par OF, les deux tiers du temps de confirmation.
  python fix_auto7.py show | apply | restore"""
import io, os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'show').lower()
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
ACTION = 1477
DOSSIER = 'ocr/odoo-scan-page/automations_perf_20260924'
AVANT = DOSSIER + '/action_1477_qty_avant.py'
APRES = DOSSIER + '/action_1477_qty_apres.py'
ANCRE = "        if vol_total:\n            vals['product_qty'] = vol_total"
NOUVEAU = ("        # quantité de l'OF réécrite seulement si elle change une fois arrondie à l'unité (sinon 0,37 s de recalculs par OF)\n"
           "        if vol_total and float_compare(vol_total, record.product_qty, precision_rounding=record.product_uom_id.rounding or 0.001) != 0:\n"
           "            vals['product_qty'] = vol_total")
code = x('ir.actions.server', 'read', [ACTION], ['name', 'code'])[0]['code']
if mode == 'show':
    i = code.find(ANCRE)
    print('ancre trouvée %d fois' % code.count(ANCRE), '| déjà corrigé :', 'float_compare(vol_total' in code)
    if i >= 0:
        print(code[i - 200:i + 120])
elif mode == 'apply':
    if 'float_compare(vol_total' in code:
        print('déjà corrigé'); sys.exit(0)
    assert code.count(ANCRE) == 1, code.count(ANCRE)
    os.makedirs(DOSSIER, exist_ok=True)
    io.open(AVANT, 'w', encoding='utf-8', newline='\n').write(code)
    nouveau = code.replace(ANCRE, NOUVEAU)
    compile(nouveau, 'action_1477', 'exec')
    x('ir.actions.server', 'write', [ACTION], {'code': nouveau})
    io.open(APRES, 'w', encoding='utf-8', newline='\n').write(nouveau)
    relu = x('ir.actions.server', 'read', [ACTION], ['code'])[0]['code']
    print('appliqué :', relu == nouveau, '| sauvegardes :', AVANT, APRES)
    i = relu.find('float_compare(vol_total')
    print(relu[i - 150:i + 200])
elif mode == 'restore':
    avant = io.open(AVANT, encoding='utf-8').read()
    x('ir.actions.server', 'write', [ACTION], {'code': avant})
    print('restauré :', x('ir.actions.server', 'read', [ACTION], ['code'])[0]['code'] == avant)
