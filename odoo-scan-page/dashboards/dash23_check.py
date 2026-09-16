# -*- coding: utf-8 -*-
"""Ouvre le tableau de bord 23 (session obtenue par l'API), vérifie que le bloc par compte s'affiche, capture."""
import os, sys, requests
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
s = requests.Session()
r = s.post(U + '/web/session/authenticate', json={'jsonrpc': '2.0', 'method': 'call', 'params': {'db': D, 'login': us, 'password': p}}, timeout=60).json()
sid = s.cookies.get('session_id')
with sync_playwright() as pw:
    b = pw.chromium.launch(channel='msedge', headless=True)
    ctx = b.new_context(viewport={'width': 1700, 'height': 1000}, locale='fr-FR')
    ctx.add_cookies([{'name': 'session_id', 'value': sid, 'domain': 'maquignon.odoo.com', 'path': '/', 'secure': True, 'httpOnly': True}])
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
    pg.goto(U + '/odoo/dashboards?dashboard_id=23', wait_until='domcontentloaded', timeout=120000)
    pg.wait_for_timeout(9000)
    txt = pg.locator('body').inner_text()
    print('titre présent :', 'DÉTAIL PAR COMPTE COMPTABLE' in txt, '| compte 70750000 :', '70750000' in txt, '| Contribution TGAP :', 'Contribution TGAP' in txt, '| #ERROR :', '#ERROR' in txt or '#ERREUR' in txt)
    # la grille est un canvas : défiler à la molette jusqu'au bloc par compte (ligne 165)
    pg.mouse.move(700, 600)
    for i, dy in enumerate((1000, 400)):
        pg.mouse.wheel(0, dy); pg.wait_for_timeout(2500)
        pg.screenshot(path='audit/dash23_compte_%d.png' % i)
    i = txt.find('DÉTAIL PAR COMPTE COMPTABLE')
    print(txt[i:i + 900].replace('\n', ' | ') if i >= 0 else txt[:600])
    print('erreurs JS :', errs[:3])
    b.close()
