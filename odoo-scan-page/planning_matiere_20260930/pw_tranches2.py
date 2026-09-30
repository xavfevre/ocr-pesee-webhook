# -*- coding: utf-8 -*-
"""Contrôle du choix d'épaisseur partagé : clic sur une cote -> champ x_epaisseur_tranche écrit sur l'OF (lu par XML-RPC),
visible après rechargement (autre écran), puis « Tout en H » remet 0. Le champ testé est remis à sa valeur initiale."""
import os, ssl, sys, requests, xmlrpc.client
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
r = requests.post(U + '/web/session/authenticate', json={'jsonrpc': '2.0', 'method': 'call', 'params': {'db': D, 'login': us, 'password': p}}, timeout=60)
sid = r.cookies.get('session_id'); assert sid
with sync_playwright() as pw:
    b = None
    for ch in ('chrome', 'msedge'):
        try:
            b = pw.chromium.launch(channel=ch); break
        except Exception:
            pass
    if b is None:
        b = pw.chromium.launch()
    ctx = b.new_context(viewport={'width': 1600, 'height': 1000}, locale='fr-FR')
    ctx.add_cookies([{'name': 'session_id', 'value': sid, 'domain': 'maquignon.odoo.com', 'path': '/'}])
    page = ctx.new_page()
    errs = []
    page.on('pageerror', lambda e: errs.append(str(e)[:160]))
    page.on('dialog', lambda d: d.accept())
    page.goto(U + '/planning-tranches', wait_until='domcontentloaded', timeout=180000)
    page.wait_for_selector('.tr-mat', timeout=120000); page.wait_for_timeout(1200)
    tr = page.query_selector('tr.tr-piece')
    of_id = int(tr.get_attribute('data-of')); nom = tr.get_attribute('data-name')
    ep0 = x('mrp.production', 'read', [of_id], ['x_epaisseur_tranche'])[0]['x_epaisseur_tranche']
    btns = tr.query_selector_all('td.tr-ep .ep-btn')
    print('OF test %s (%d) : cotes %s, valeur initiale du champ %s' % (nom, of_id, [q.text_content() for q in btns], ep0))
    cible = [q for q in btns if 'on' not in (q.get_attribute('class') or '')][0]
    v = float(cible.text_content())
    cible.click(); page.wait_for_timeout(1500)
    ep1 = x('mrp.production', 'read', [of_id], ['x_epaisseur_tranche'])[0]['x_epaisseur_tranche']
    print('clic sur %.3f -> champ OF = %s : %s' % (v, ep1, 'OK' if abs((ep1 or 0) - v) < 1e-6 else 'ÉCART'))
    page.reload(wait_until='domcontentloaded'); page.wait_for_selector('.tr-mat', timeout=120000); page.wait_for_timeout(1200)
    tr2 = page.query_selector('tr.tr-piece[data-of="%d"]' % of_id)
    on = [q.text_content() for q in tr2.query_selector_all('td.tr-ep .ep-btn.on')]
    print('après rechargement (autre écran) : cote retenue affichée %s, marque ✎ %s' % (on, bool(tr2.query_selector('td.tr-ep span'))))
    page.click('#tr-reset'); page.wait_for_timeout(1500)
    ep2 = x('mrp.production', 'read', [of_id], ['x_epaisseur_tranche'])[0]['x_epaisseur_tranche']
    print('« Tout en H » (confirmation acceptée) -> champ OF = %s : %s' % (ep2, 'OK' if not ep2 else 'ÉCART'))
    if ep0:
        x('mrp.production', 'write', [of_id], {'x_epaisseur_tranche': ep0}); print('valeur initiale remise :', ep0)
    print('erreurs JS :', errs)
    page.screenshot(path='tranches_2.png')
    b.close()
