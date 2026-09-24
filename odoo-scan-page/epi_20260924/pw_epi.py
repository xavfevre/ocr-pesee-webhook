import os, sys, ssl, requests, xmlrpc.client
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
K = m.execute_kw(D, uid, p, 'ir.config_parameter', 'get_param', ['maquignon.epi_key'])
s = requests.Session()
s.post(U + '/web/session/authenticate', json={'jsonrpc': '2.0', 'method': 'call', 'params': {'db': D, 'login': us, 'password': p}}, timeout=60)
sid = s.cookies.get('session_id')
with sync_playwright() as pw:
    b = pw.chromium.launch(channel='msedge', headless=True)
    ctx = b.new_context(viewport={'width': 1300, 'height': 1000}, locale='fr-FR')
    ctx.add_cookies([{'name': 'session_id', 'value': sid, 'domain': 'maquignon.odoo.com', 'path': '/', 'secure': True, 'httpOnly': True}])
    pg = ctx.new_page(); errs = []; dialogs = []
    pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
    pg.on('dialog', lambda d: (dialogs.append(d.message[:100]), d.dismiss()))
    pg.goto(U + '/epi?k=' + K, wait_until='domcontentloaded', timeout=120000); pg.wait_for_timeout(3000)
    print('titre', pg.title()[:30], '| salariés', pg.locator('#ep-emp option').count() - 1, '| EPI', pg.locator('#ep-prod option').count() - 1, '| lignes stock', pg.locator('.ep-card table.ep').first.locator('tr').count() - 1, '| erreurs JS', errs)
    pg.select_option('#ep-prod', index=3); pg.wait_for_timeout(300)
    print('info stock :', pg.locator('#ep-stock-info').inner_text(), '| classe', pg.locator('#ep-stock-info').get_attribute('class'))
    pg.click('#ep-go'); pg.wait_for_timeout(500)
    print('clic sans salarié -> dialog :', dialogs[-1:])
    print('remises listées :', pg.locator('.ep-annule').count(), '| conso lignes :', pg.locator('tr[data-emp-nom]').count())
    pg.screenshot(path='captures_rh/epi_page.png', full_page=True)
    pg.goto(U + '/epi', wait_until='domcontentloaded', timeout=120000); pg.wait_for_timeout(1500)
    print('sans clé :', '🔒' in pg.content())
    b.close()
