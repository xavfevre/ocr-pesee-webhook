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
    ctx = b.new_context(viewport={'width': 1300, 'height': 700}, locale='fr-FR')
    ctx.add_cookies([{'name': 'session_id', 'value': sid, 'domain': dom, 'path': '/', 'secure': True, 'httpOnly': True}])
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
    pg.goto(U + '/heures-salarie?emp=%d&du=2026-08-25&au=2026-09-22&k=%s' % (K['jolly'][0], K['k']), wait_until='domcontentloaded', timeout=120000); pg.wait_for_timeout(2500)
    bar = pg.locator('.fs-emp')
    print('barre :', bar.inner_text().replace('\n', ' | ')[:120], '| options :', pg.locator('#fs-emp-sel option').count(), '| erreurs', errs)
    print('liens :', [(a.inner_text(), a.get_attribute('href').replace(K['k'], 'CLE')) for a in bar.locator('a').all()])
    pg.screenshot(path='captures_rh/%s_fiche_nav.png' % mode, full_page=False)
    bar.locator('a').last.click(); pg.wait_for_timeout(3000)
    print('après « suivant » :', pg.url.replace(K['k'], 'CLE'), '|', pg.locator('h4').first.inner_text()[:70])
    pg.select_option('#fs-emp-sel', str(K['theo'][0])); pg.wait_for_timeout(3000)
    print('après liste (Théo) :', pg.url.replace(K['k'], 'CLE'), '|', pg.locator('h4').first.inner_text()[:70], '| erreurs', errs)
    b.close()
