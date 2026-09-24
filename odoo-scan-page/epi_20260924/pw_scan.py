# -*- coding: utf-8 -*-
"""Scan douchette sur la page EPI (prod) : code-barres de test posé sur la pointure 42 des Defender puis retiré ;
captures des blocs Remise et Entrée en stock pour la fiche procédure."""
import os, sys, ssl, requests, xmlrpc.client
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
K = m.execute_kw(D, uid, p, 'ir.config_parameter', 'get_param', ['maquignon.epi_key'])
v42 = m.execute_kw(D, uid, p, 'product.product', 'search', [[['product_tmpl_id', '=', 2989], ['product_template_attribute_value_ids.name', '=', '42']]])[0]
m.execute_kw(D, uid, p, 'product.product', 'write', [[v42], {'barcode': '3760000000042'}])
s = requests.Session()
s.post(U + '/web/session/authenticate', json={'jsonrpc': '2.0', 'method': 'call', 'params': {'db': D, 'login': us, 'password': p}}, timeout=60)
sid = s.cookies.get('session_id')
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel='msedge', headless=True)
        ctx = b.new_context(viewport={'width': 1200, 'height': 900}, locale='fr-FR', device_scale_factor=2)
        ctx.add_cookies([{'name': 'session_id', 'value': sid, 'domain': 'maquignon.odoo.com', 'path': '/', 'secure': True, 'httpOnly': True}])
        pg = ctx.new_page(); errs = []; dialogs = []
        pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
        pg.on('dialog', lambda d: (dialogs.append(d.message[:80]), d.dismiss()))
        pg.goto(U + '/epi?k=' + K, wait_until='domcontentloaded', timeout=120000); pg.wait_for_timeout(3000)
        pg.fill('#ep-scan', '3760000000042'); pg.press('#ep-scan', 'Enter'); pg.wait_for_timeout(400)
        print('scan connu -> EPI sélectionné :', pg.locator('#ep-prod option:checked').inner_text()[:60], '| champ scan :', pg.locator('#ep-scan').get_attribute('class'), '| erreurs', errs)
        pg.select_option('#ep-emp', index=5)
        pg.locator('.ep-card').nth(0).screenshot(path='captures_epi/remise.png')
        pg.fill('#ep-rec-scan', '0000'); pg.press('#ep-rec-scan', 'Enter'); pg.wait_for_timeout(400)
        print('scan inconnu -> dialog :', dialogs[-1:])
        pg.fill('#ep-rec-scan', '3760000000042'); pg.press('#ep-rec-scan', 'Enter'); pg.wait_for_timeout(400)
        print('entrée : EPI sélectionné :', pg.locator('#ep-rec-prod option:checked').inner_text()[:60])
        pg.locator('.ep-card').nth(1).screenshot(path='captures_epi/entree.png')
        b.close()
finally:
    m.execute_kw(D, uid, p, 'product.product', 'write', [[v42], {'barcode': False}])
    print('code-barres de test retiré')
