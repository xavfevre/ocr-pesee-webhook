import os, sys, json, requests
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://testmaq230926v2.odoo.com', 'testmaq230926v2'
K = json.load(open('cles_test.json'))
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
s = requests.Session()
s.post(U + '/web/session/authenticate', json={'jsonrpc': '2.0', 'method': 'call', 'params': {'db': D, 'login': us, 'password': p}}, timeout=60)
sid = s.cookies.get('session_id')
with sync_playwright() as pw:
    b = pw.chromium.launch(channel='msedge', headless=True)
    ctx = b.new_context(viewport={'width': 1300, 'height': 700}, locale='fr-FR')
    ctx.add_cookies([{'name': 'session_id', 'value': sid, 'domain': 'testmaq230926v2.odoo.com', 'path': '/', 'secure': True, 'httpOnly': True}])
    pg = ctx.new_page(); errs = []
    def relais(route, request):
        r = requests.post('http://127.0.0.1:5055/heures/rpc', data=request.post_data, headers={'Content-Type': 'application/json'}, timeout=120)
        route.fulfill(status=200, content_type='application/json', body=r.text, headers={'Access-Control-Allow-Origin': '*'})
    pg.route('**/heures/rpc', relais)
    pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
    emp = K['jolly'][0]
    pg.goto(U + '/heures-salarie?emp=%d&du=2026-08-25&au=2026-09-22&k=%s' % (emp, K['k']), wait_until='domcontentloaded', timeout=120000); pg.wait_for_timeout(2500)
    print('titre :', pg.locator('h4').first.inner_text()[:60], '| dates', pg.locator('#fs-du').input_value(), pg.locator('#fs-au').input_value(), '| erreurs', errs)
    pg.screenshot(path='captures_rh/test_fiche_dates.png', full_page=False)
    pg.fill('#fs-du', '2026-08-24'); pg.fill('#fs-au', '2026-09-20'); pg.click('#fs-per-go'); pg.wait_for_timeout(4000)
    print('après Afficher :', pg.url.replace(K['k'], 'CLE'), '| dates', pg.locator('#fs-du').input_value(), pg.locator('#fs-au').input_value(), '| semaines', pg.locator('tr.fs-sem').count(), '| erreurs', errs)
    pg.goto(U + '/heures-admin?k=%s&sem=2026-09-21' % K['k'], wait_until='domcontentloaded', timeout=120000); pg.wait_for_timeout(2500)
    tr = pg.locator('tr[data-emp="%d"]' % emp)
    print('ligne JOLLY dans Heures admin :', tr.locator('.ha-fx-du').input_value(), '->', tr.locator('.ha-fx-au').input_value())
    # remise de la période initiale sur la base de test
    pg.goto(U + '/heures-salarie?emp=%d&du=2026-08-25&au=2026-09-22&k=%s' % (emp, K['k']), wait_until='domcontentloaded', timeout=120000); pg.wait_for_timeout(2000)
    pg.click('#fs-per-go'); pg.wait_for_timeout(3000)
    b.close()
