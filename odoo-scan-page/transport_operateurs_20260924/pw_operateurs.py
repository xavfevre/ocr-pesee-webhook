import os, sys, ssl, requests, xmlrpc.client
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
mode = sys.argv[1] if len(sys.argv) > 1 else 'test'
U, D, dom = ('https://testmaq230926v2.odoo.com', 'testmaq230926v2', 'testmaq230926v2.odoo.com') if mode == 'test' else ('https://maquignon.odoo.com', 'maquignon', 'maquignon.odoo.com')
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [1, 2, 3, 4, 13]}))
tr = x('project.task', 'search', [['project_id', '=', 2], ['tag_ids', 'not in', [1]], ['x_studio_chauffeur', '!=', False], ['state', '=', '01_in_progress']], limit=1)[0]
tp = x('project.task', 'search', [['project_id', '=', 2], ['tag_ids', 'in', [1]]], order='id desc', limit=1)[0]
s = requests.Session()
s.post(U + '/web/session/authenticate', json={'jsonrpc': '2.0', 'method': 'call', 'params': {'db': D, 'login': us, 'password': p}}, timeout=60)
sid = s.cookies.get('session_id')
with sync_playwright() as pw:
    b = pw.chromium.launch(channel='msedge', headless=True)
    ctx = b.new_context(viewport={'width': 1400, 'height': 1000}, locale='fr-FR')
    ctx.add_cookies([{'name': 'session_id', 'value': sid, 'domain': dom, 'path': '/', 'secure': True, 'httpOnly': True}, {'name': 'cids', 'value': '1', 'domain': dom, 'path': '/', 'secure': True}])
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
    for lab, tid in (('transport', tr), ('TP', tp)):
        pg.goto(U + '/odoo/action-project.action_view_all_task/%d' % tid, wait_until='domcontentloaded', timeout=120000); pg.wait_for_timeout(6000)
        op = pg.locator('.o_field_widget[name="x_studio_operateurs"]'); ch = pg.locator('.o_field_widget[name="x_studio_chauffeur"]')
        print('%-9s tâche %d : Opérateurs visible = %s | Chauffeur visible = %s | titre %r | erreurs %s' % (lab, tid, op.count() > 0 and op.first.is_visible(), ch.count() > 0 and ch.first.is_visible(), pg.title()[:40], errs[:2]))
        pg.screenshot(path='captures_rh/%s_tache_%s.png' % (mode, lab), full_page=False)
    b.close()
