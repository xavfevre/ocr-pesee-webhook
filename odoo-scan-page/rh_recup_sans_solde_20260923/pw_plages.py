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
    ctx = b.new_context(viewport={'width': 1300, 'height': 1100}, locale='fr-FR')
    ctx.add_cookies([{'name': 'session_id', 'value': sid, 'domain': 'testmaq230926v2.odoo.com', 'path': '/', 'secure': True, 'httpOnly': True}])
    pg = ctx.new_page(); errs = []; dialogs = []
    def relais(route, request):
        r = requests.post('http://127.0.0.1:5055/heures/rpc', data=request.post_data, headers={'Content-Type': 'application/json'}, timeout=120)
        route.fulfill(status=200, content_type='application/json', body=r.text, headers={'Access-Control-Allow-Origin': '*'})
    pg.route('**/heures/rpc', relais)
    pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
    pg.on('dialog', lambda d: (dialogs.append(d.message[:120]), d.accept()))
    e2, t2 = K['theo']
    pg.goto(U + '/mes-heures?emp=%d&t=%s&sem=2026-06-15' % (e2, t2), wait_until='domcontentloaded', timeout=120000); pg.wait_for_timeout(2500)
    c = pg.locator('.mh-day').nth(0)   # lundi 15/06, horaire 08:00-12:00 / 13:30-17:00
    c.locator('button[data-act=normal]').click(); pg.wait_for_timeout(2500)
    print('journée normale ->', c.locator('[data-role=state]').inner_text(), '| erreurs', errs)
    c.locator('[data-role=manque-t]').click(); pg.wait_for_timeout(300)
    print('bloc ouvert :', c.locator('[data-role=manque]').get_attribute('open') is not None, '|', c.locator('[data-role=manque-t]').inner_text())
    c.locator('input[data-f=recup_de]').fill('16:00'); c.locator('input[data-f=recup_a]').fill('17:00')
    c.locator('input[data-f=recup_a]').dispatch_event('change'); pg.wait_for_timeout(400)
    print('créneau récup 16:00-17:00 -> ap.-midi', c.locator('input[data-f=am_deb]').input_value(), '-', c.locator('input[data-f=am_fin]').input_value(), '| h_recup', c.locator('input[data-f=h_recup]').input_value(), '| contrôle :', c.locator('[data-role=ctrl]').inner_text()[:110])
    c.locator('button[data-act=save]').click(); pg.wait_for_timeout(2500)
    print('enregistré ->', c.locator('[data-role=state]').inner_text(), '| data', c.get_attribute('data-heures'), c.get_attribute('data-hs'))
    c.locator('input[data-f=ss_de]').fill('08:00'); c.locator('input[data-f=ss_a]').fill('09:00')
    c.locator('input[data-f=ss_a]').dispatch_event('change'); pg.wait_for_timeout(400)
    print('créneau sans solde 08:00-09:00 -> matin', c.locator('input[data-f=m_deb]').input_value(), '-', c.locator('input[data-f=m_fin]').input_value(), '| h_ss', c.locator('input[data-f=h_ss]').input_value(), '| contrôle :', c.locator('[data-role=ctrl]').inner_text()[:110])
    c.locator('button[data-act=save]').click(); pg.wait_for_timeout(2500)
    print('enregistré ->', c.locator('[data-role=state]').inner_text(), '| dialogs', dialogs)
    pg.reload(wait_until='domcontentloaded'); pg.wait_for_timeout(2500)
    c = pg.locator('.mh-day').nth(0)
    print('après rechargement -> état', c.locator('[data-role=state]').inner_text(), '| préremplis', c.locator('input[data-f=recup_de]').input_value(), c.locator('input[data-f=recup_a]').input_value(), c.locator('input[data-f=ss_de]').input_value(), c.locator('input[data-f=ss_a]').input_value(), '| erreurs', errs)
    # chevauchement volontaire : créneau récup sur des heures travaillées, saisi au serveur (sans retrait) -> refus attendu
    c.locator('input[data-f=am_fin]').fill('17:00'); c.locator('input[data-f=am_fin]').dispatch_event('input')
    c.locator('button[data-act=save]').click(); pg.wait_for_timeout(2500)
    print('chevauchement -> dialogs', dialogs[-1:])
    c.screenshot(path='captures_rh/plages_theo.png')
    b.close()
