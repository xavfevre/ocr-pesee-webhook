# -*- coding: utf-8 -*-
"""Captures d'écran réelles pour la procédure opérateurs (Playwright + Edge, session Odoo obtenue par l'API).
Aucune écriture : on ouvre les fenêtres (choix de palette, pavé quantité), on scanne une palette existante
(lecture seule au poste de scan v3), on provoque un refus ⛔ et on annule le pavé quantité."""
import os, sys, ssl, io, xmlrpc.client, requests
from playwright.sync_api import sync_playwright
import pymupdf
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'ocr')
import web_actions as wa
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
OUT = 'ocr/docs/captures'; os.makedirs(OUT, exist_ok=True)
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
def call(model, method, *params, **kw): return m.execute_kw(D, uid, p, model, method, list(params), kw)
s = requests.Session()
r = s.post(U + '/web/session/authenticate', json={'jsonrpc': '2.0', 'method': 'call', 'params': {'db': D, 'login': us, 'password': p}}, timeout=60).json()
assert r.get('result', {}).get('uid'), r
sid = s.cookies.get('session_id')

# ── exemples réels ──
def contenu(cid):
    return call('mrp.production', 'search_count', [['x_studio_colis', '=', cid]]) + call('x_repartition_palette', 'search_count', [['x_studio_colis_id', '=', cid]])
ouv = call('stock.package', 'search_read', [['x_studio_cloturee', '!=', True], ['x_operateur_id', '!=', False]],
           fields=['name', 'x_operateur_id'], order='write_date desc', limit=30)
pal = next((q for q in ouv if contenu(q['id'])), None) or (ouv[0] if ouv else None)
owner = pal['x_operateur_id'][0] if pal else None
print('palette exemple :', pal and (pal['name'], pal['x_operateur_id'][1]))
of_qte = of_refus = None
for o in call('mrp.production', 'search_read', [['state', '=', 'done'], ['x_studio_colis', '=', False], ['company_id', '=', 1], ['date_finished', '>=', '2026-07-01']],
              fields=wa.OF_CHAMPS, order='date_finished desc', limit=150):
    if call('x_repartition_palette', 'search_count', [['x_studio_of_id', '=', o['id']]]):
        continue
    ops = wa._of_operateurs(call, o)
    if not ops:
        continue
    if owner and owner not in ops and not of_refus:
        of_refus = o
    if owner and owner in ops and int(o['x_studio_nbr'] or 1) >= 2 and not of_qte:
        of_qte = o
    if of_qte and of_refus:
        break
print('OF pavé quantité :', of_qte and (of_qte['name'], of_qte['x_studio_nbr']), '| OF refus :', of_refus and of_refus['name'])

with sync_playwright() as pw:
    b = pw.chromium.launch(channel='msedge', headless=True)
    ctx = b.new_context(viewport={'width': 1280, 'height': 960}, locale='fr-FR')
    ctx.add_cookies([{'name': 'session_id', 'value': sid, 'domain': 'maquignon.odoo.com', 'path': '/', 'secure': True, 'httpOnly': True}])
    pg = ctx.new_page()

    def shot(page, name):
        page.screenshot(path='%s/%s.png' % (OUT, name))
        print('capture', name)

    BUREAU_SEUL = 'bureau' in sys.argv
    # 1) tablette — Ma production (PIRONNET) + pavé quantité + choix de palette (aucune écriture)
    if not BUREAU_SEUL: pg.goto(U + '/vue-operateur?op=497', wait_until='networkidle', timeout=90000); pg.wait_for_timeout(1200)
    if not BUREAU_SEUL: shot(pg, 'tablette_ma_production')
    btn = pg.locator('.__none__') if BUREAU_SEUL else pg.locator('.vo-palpart:visible').first if pg.locator('.vo-palpart:visible').count() else pg.locator('.vo-addcolis2:visible').first
    if btn.count():
        btn.scroll_into_view_if_needed(); btn.click(); pg.wait_for_timeout(500)
        if pg.locator('#vo-qte-pop').is_visible():
            shot(pg, 'tablette_pave_quantite'); pg.click('#vo-qte-ok'); pg.wait_for_timeout(500)
        if pg.locator('#vo-colis-pop').is_visible():
            shot(pg, 'tablette_choisir_palette'); pg.click('#vo-colis-close')
    else:
        print('pas de bouton Palettiser / Mettre au colis pour 497')
    # 2) tablette — Historique (GUERIN) : opération restante
    if not BUREAU_SEUL: pg.goto(U + '/vue-operateur?op=628&hist=1', wait_until='networkidle', timeout=90000); pg.wait_for_timeout(1200)
    for _ in ([] if BUREAU_SEUL else range(8)):   # un seul jour affiché à la fois : reculer jusqu'à une carte « Reste à faire » visible
        vis = pg.locator('text=Reste à faire').filter(visible=True)
        if vis.count():
            vis.first.scroll_into_view_if_needed(); pg.wait_for_timeout(300); break
        if not pg.locator('#vd-prev').count() or pg.locator('#vd-prev').is_disabled():
            break
        pg.click('#vd-prev'); pg.wait_for_timeout(300)
    if not BUREAU_SEUL: shot(pg, 'tablette_historique')

    # 3) poste de scan — contexte public neuf (pas de palette mémorisée)
    ctx2 = b.new_context(viewport={'width': 1000, 'height': 1180}, locale='fr-FR')
    p2 = ctx2.new_page()
    if not BUREAU_SEUL: p2.goto(U + '/scan', wait_until='networkidle', timeout=90000); p2.wait_for_timeout(2500)
    if not BUREAU_SEUL: shot(p2, 'scan_accueil')
    if pal and not BUREAU_SEUL:
        p2.fill('#scan-input', pal['name']); p2.press('#scan-input', 'Enter')
        p2.wait_for_function("document.getElementById('colis-name').textContent.trim() === '%s'" % pal['name'], timeout=30000); p2.wait_for_timeout(600)
        shot(p2, 'scan_palette_active')
        if of_refus:
            p2.fill('#scan-input', of_refus['name']); p2.press('#scan-input', 'Enter')
            p2.wait_for_function("document.getElementById('scan-res').textContent.indexOf('\\u26d4') === 0", timeout=30000); p2.wait_for_timeout(300)
            shot(p2, 'scan_refus')
        if of_qte:
            p2.fill('#scan-input', of_qte['name']); p2.press('#scan-input', 'Enter')
            p2.wait_for_selector('#qte-pop', state='visible', timeout=30000); p2.wait_for_timeout(300)
            shot(p2, 'scan_quantite'); p2.click('#qte-cancel'); p2.wait_for_timeout(300)
        p2.click('#btn-colis-nav'); p2.wait_for_selector('#nav-list .nav-row', timeout=30000); p2.wait_for_timeout(400)
        shot(p2, 'scan_palettes_ouvertes'); p2.click('#nav-cancel')
    ctx2.close()

    # 4) bureau — liste des colis et fiche d'une palette
    pg.set_viewport_size({'width': 1400, 'height': 800})
    pg.goto(U + '/odoo/action-stock.action_package_view', wait_until='domcontentloaded', timeout=120000)
    pg.wait_for_selector('.o_list_renderer, .o_list_view, .o_kanban_view', timeout=90000); pg.wait_for_timeout(3000)
    print('back-office :', pg.url, '|', pg.title())
    shot(pg, 'bureau_colis_liste')
    if pal:
        pg.goto(U + '/odoo/action-stock.action_package_view/%d' % pal['id'], wait_until='domcontentloaded', timeout=120000)
        pg.wait_for_selector('.o_form_view', timeout=90000); pg.wait_for_timeout(3000)
        shot(pg, 'bureau_colis_fiche')
    b.close()

# 5) bon de colisage (dernière palette clôturée avec opérateur) : PDF -> image
last = call('stock.package', 'search_read', [['x_studio_cloturee', '=', True], ['x_operateur_id', '!=', False]], fields=['name'], order='write_date desc', limit=1)
if last:
    pdf = s.get(U + '/report/pdf/maquignon.report_bon_colisage/%d' % last[0]['id'], timeout=120).content
    doc = pymupdf.open(stream=pdf, filetype='pdf')
    pix = doc[0].get_pixmap(dpi=110)
    pix.save('%s/bureau_bon_colisage.png' % OUT)
    print('capture bureau_bon_colisage (%s, %d pages)' % (last[0]['name'], len(doc)))
print('fichiers :', sorted(os.listdir(OUT)))
