# -*- coding: utf-8 -*-
"""Rendu + interactions des pages RH sur la base de test (relais local 5055). Captures dans captures_rh/.
  python pw_rh.py rendu | saisie"""
import os, sys, json, requests
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://testmaq230926v2.odoo.com', 'testmaq230926v2'
K = json.load(open('cles_test.json'))
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
os.makedirs('captures_rh', exist_ok=True)
s = requests.Session()
s.post(U + '/web/session/authenticate', json={'jsonrpc': '2.0', 'method': 'call', 'params': {'db': D, 'login': us, 'password': p}}, timeout=60)
sid = s.cookies.get('session_id')
quoi = sys.argv[1:] or ['rendu']
with sync_playwright() as pw:
    b = pw.chromium.launch(channel='msedge', headless=True)
    ctx = b.new_context(viewport={'width': 1300, 'height': 1100}, locale='fr-FR')
    ctx.add_cookies([{'name': 'session_id', 'value': sid, 'domain': 'testmaq230926v2.odoo.com', 'path': '/', 'secure': True, 'httpOnly': True}])
    pg = ctx.new_page(); errs = []; dialogs = []
    # les pages (https) appellent le relais local en http : on intercepte et on relaie depuis Python
    def relais(route, request):
        try:
            r = requests.post('http://127.0.0.1:5055/heures/rpc', data=request.post_data, headers={'Content-Type': 'application/json'}, timeout=120)
            route.fulfill(status=200, content_type='application/json', body=r.text, headers={'Access-Control-Allow-Origin': '*'})
        except Exception as e:
            route.fulfill(status=200, content_type='application/json', body='{"error":{"message":"relais local : %s"}}' % str(e)[:100].replace('"', "'"), headers={'Access-Control-Allow-Origin': '*'})
    pg.route('**/heures/rpc', relais)
    pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
    pg.on('dialog', lambda d: (dialogs.append(d.message[:160]), d.accept()))
    pg.on('console', lambda m: errs.append('console ' + m.type + ': ' + m.text[:160]) if m.type == 'error' else None)

    def go(url, nom, full=True):
        errs.clear()
        pg.goto(U + url, wait_until='domcontentloaded', timeout=120000)
        pg.wait_for_timeout(2500)
        html = pg.content()
        pg.screenshot(path='captures_rh/%s.png' % nom, full_page=full)
        print('%-28s titre=%r len=%d erreurs=%s' % (nom, pg.title()[:40], len(html), [e for e in errs if 'favicon' not in e][:3]))
        return html

    emp, tok = K['jolly']
    if 'rendu' in quoi:
        go('/mes-heures?emp=%d&t=%s&sem=2026-09-14' % (emp, tok), 'salarie_semaine')
        go('/mes-heures?emp=%d&t=%s&vue=mois&mois=2026-09' % (emp, tok), 'salarie_mois')
        go('/heures-admin?k=%s&sem=2026-09-14' % K['k'], 'admin_semaine')
        go('/heures-salarie?emp=%d&mois=2026-09&k=%s' % (emp, K['k']), 'fiche_jolly')
        go('/planning-rh?k=%s&mois=2026-09' % K['k'], 'planning')
    if 'saisie' in quoi:
        e2, t2 = K['theo']
        go('/mes-heures?emp=%d&t=%s&sem=2026-06-01' % (e2, t2), 'theo_avant')
        cards = pg.locator('.mh-day')
        print('cartes :', cards.count())
        c0 = cards.nth(0)
        c0.locator('button[data-act=normal]').click(); pg.wait_for_timeout(2500)
        print('lundi normal ->', c0.get_attribute('data-type'), c0.get_attribute('data-heures'), c0.get_attribute('data-hs'), '|', c0.locator('[data-role=state]').inner_text())
        c1 = cards.nth(1)
        c1.locator('input[data-f=m_deb]').fill('08:00'); c1.locator('input[data-f=m_fin]').fill('12:00')
        c1.locator('input[data-f=m_deb]').dispatch_event('input'); pg.wait_for_timeout(300)
        print('mardi 4 h, contrôle :', c1.locator('[data-role=ctrl]').inner_text()[:160], '| bloc manque visible :', c1.locator('[data-role=manque]').is_visible())
        c1.locator('button[data-act=q-recup]').click(); pg.wait_for_timeout(300)
        print('   après « tout en récup » : récup =', c1.locator('input[data-f=h_recup]').input_value(), '| contrôle :', c1.locator('[data-role=ctrl]').inner_text()[:120])
        c1.locator('button[data-act=save]').click(); pg.wait_for_timeout(2500)
        print('   enregistré ->', c1.get_attribute('data-type'), c1.get_attribute('data-heures'), c1.get_attribute('data-hs'), '|', c1.locator('[data-role=state]').inner_text())
        c2 = cards.nth(2)
        c2.locator('button[data-act=recup]').click(); pg.wait_for_timeout(3500)
        print('mercredi journée récup -> dialog :', dialogs[-1:], '| type', c2.get_attribute('data-type'))
        pg.wait_for_timeout(1500)
        cards = pg.locator('.mh-day'); c2 = cards.nth(2)
        print('   après rechargement : classe', c2.get_attribute('class'), '|', c2.locator('[data-role=state]').inner_text())
        c3 = cards.nth(3)
        c3.locator('input[data-f=m_deb]').fill('08:00'); c3.locator('input[data-f=m_fin]').fill('12:00'); c3.locator('input[data-f=am_deb]').fill('13:30'); c3.locator('input[data-f=am_fin]').fill('19:00')
        c3.locator('input[data-f=am_fin]').dispatch_event('input'); pg.wait_for_timeout(300)
        print('jeudi 9,5 h contrôle :', c3.locator('[data-role=ctrl]').inner_text()[:140])
        c3.locator('button[data-act=save]').click(); pg.wait_for_timeout(2500)
        print('   enregistré ->', c3.get_attribute('data-hs'), '|', c3.locator('[data-role=state]').inner_text())
        c4 = cards.nth(4)
        c4.locator('button[data-act=ss]').click(); pg.wait_for_timeout(3500)
        print('vendredi sans solde -> dialog :', dialogs[-1:], '| tot :', pg.locator('#mh-tot').inner_text())
        pg.screenshot(path='captures_rh/theo_apres.png', full_page=True)
        go('/heures-salarie?emp=%d&mois=2026-06&k=%s' % (e2, K['k']), 'fiche_theo_juin')
        tr = pg.locator('tr[data-date="2026-06-08"]')
        tr.locator('input[data-f=m_deb]').fill('08:00'); tr.locator('input[data-f=m_fin]').fill('12:00'); tr.locator('input[data-f=am_deb]').fill('13:30'); tr.locator('input[data-f=am_fin]').fill('17:00')
        tr.locator('input[data-f=am_fin]').dispatch_event('change'); pg.wait_for_timeout(2500)
        print('fiche 08/06 saisi ->', tr.get_attribute('data-type'), tr.get_attribute('data-h'), tr.get_attribute('data-hs'), '| état', tr.locator('[data-role=etat]').inner_text())
        tr.locator('input[data-f=am_fin]').fill('15:00'); tr.locator('input[data-f=h_ss]').fill('2'); tr.locator('input[data-f=h_ss]').dispatch_event('change'); pg.wait_for_timeout(2500)
        print('fiche 08/06 sans solde 2 h ->', tr.get_attribute('data-h'), tr.get_attribute('data-hs'), tr.get_attribute('data-s'), '| état', tr.locator('[data-role=etat]').inner_text(), '| dialogs', dialogs[-1:])
        tr9 = pg.locator('tr[data-date="2026-06-09"]')
        tr9.locator('select[data-f=type]').select_option('recup'); pg.wait_for_timeout(2500)
        print('fiche 09/06 type récup ->', tr9.get_attribute('data-type'), tr9.get_attribute('data-hs'), '| dialog', dialogs[-1:])
        tr10 = pg.locator('tr[data-date="2026-06-10"]')
        tr10.locator('.fs-q').click(); pg.wait_for_timeout(2500)
        print('fiche 10/06 ⚡ ->', tr10.get_attribute('data-type'), tr10.get_attribute('data-h'), '| reste :', pg.locator('#fs-m-reste').inner_text(), '| total mois :', pg.locator('#fs-m-h').inner_text())
        pg.screenshot(path='captures_rh/fiche_theo_apres.png', full_page=True)
        go('/heures-admin?k=%s&sem=2026-06-01' % K['k'], 'admin_theo_juin')
    b.close()
