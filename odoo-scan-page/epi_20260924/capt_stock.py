import os, sys, ssl, requests, xmlrpc.client
from playwright.sync_api import sync_playwright
from PIL import Image
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
    ctx = b.new_context(viewport={'width': 1200, 'height': 900}, locale='fr-FR', device_scale_factor=2)
    ctx.add_cookies([{'name': 'session_id', 'value': sid, 'domain': 'maquignon.odoo.com', 'path': '/', 'secure': True, 'httpOnly': True}])
    pg = ctx.new_page()
    pg.goto(U + '/epi?k=' + K, wait_until='domcontentloaded', timeout=120000); pg.wait_for_timeout(3000)
    pg.locator('.ep-card').nth(2).screenshot(path='captures_epi/stock.png')
    b.close()
im = Image.open('captures_epi/stock.png'); w, h = im.size
im.crop((0, int(h * 0.76), w, h)).save('captures_epi/stock_bas.png')
im.crop((0, 0, w, int(h * 0.42))).save('captures_epi/stock.png'); print('stock haut / bas recadrés', (w, h))
