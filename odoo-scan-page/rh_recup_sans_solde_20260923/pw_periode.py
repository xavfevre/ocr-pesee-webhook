import os, sys, json, requests
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
mode = sys.argv[1] if len(sys.argv) > 1 else 'test'
U, D, dom = ('https://testmaq230926v2.odoo.com', 'testmaq230926v2', 'testmaq230926v2.odoo.com') if mode == 'test' else ('https://maquignon.odoo.com', 'maquignon', 'maquignon.odoo.com')
K = json.load(open('cles_%s.json' % mode))
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
s = requests.Session()
s.post(U + '/web/session/authenticate', json={'jsonrpc': '2.0', 'method': 'call', 'params': {'db': D, 'login': us, 'password': p}}, timeout=60)
sid = s.cookies.get('session_id')
with sync_playwright() as pw:
    b = pw.chromium.launch(channel='msedge', headless=True)
    ctx = b.new_context(viewport={'width': 1300, 'height': 900}, locale='fr-FR')
    ctx.add_cookies([{'name': 'session_id', 'value': sid, 'domain': dom, 'path': '/', 'secure': True, 'httpOnly': True}])
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
    emp = K['jolly'][0]
    pg.goto(U + '/heures-admin?k=%s&sem=2026-09-21' % K['k'], wait_until='domcontentloaded', timeout=120000); pg.wait_for_timeout(2500)
    tr = pg.locator('tr[data-emp="%d"]' % emp)
    print('ligne JOLLY : dates', tr.locator('.ha-fx-du').input_value(), '->', tr.locator('.ha-fx-au').input_value(), '| en-tête', pg.locator('#ha-ex-du').input_value(), '->', pg.locator('#ha-ex-au').input_value())
    tr.locator('a.ha-fiche').click(); pg.wait_for_timeout(3500)
    print('après clic 📋 :', pg.url.replace(K['k'], 'CLE'), '| titre h4 :', pg.locator('h4').first.inner_text()[:80], '| erreurs', errs)
    print('semaines :', pg.locator('tr.fs-sem').count(), '| 1re :', pg.locator('tr.fs-sem').first.inner_text()[:50], '| dernière :', pg.locator('tr.fs-sem').last.inner_text()[:50])
    print('recap :', ' | '.join(pg.locator('.fs-recap div').nth(i).inner_text().replace('\n', ' ') for i in range(6)))
    print('lien Excel :', pg.locator('a:has-text("Feuille Excel")').get_attribute('href').replace(K['k'], 'CLE') if pg.locator('a:has-text("Feuille Excel")').count() else '?', '| nav :', [pg.locator('.fs-nav a').nth(i).inner_text() for i in range(4)])
    pg.screenshot(path='captures_rh/%s_fiche_periode.png' % mode, full_page=False)
    b.close()
