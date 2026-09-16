# -*- coding: utf-8 -*-
import os, sys, requests
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
U='https://maquignon.odoo.com'; D='maquignon'; us=os.environ['ODOO_USER']; p=os.environ['ODOO_PWD']
OUT='ocr/docs/captures'
s=requests.Session(); r=s.post(U+'/web/session/authenticate',json={'jsonrpc':'2.0','method':'call','params':{'db':D,'login':us,'password':p}},timeout=60).json()
assert r.get('result',{}).get('uid'); sid=s.cookies.get('session_id')
with sync_playwright() as pw:
    b=pw.chromium.launch(channel='msedge',headless=True)
    ctx=b.new_context(viewport={'width':1400,'height':760},locale='fr-FR')
    ctx.add_cookies([{'name':'session_id','value':sid,'domain':'maquignon.odoo.com','path':'/','secure':True,'httpOnly':True}])
    pg=ctx.new_page()
    pg.goto(U+'/odoo/action-stock.action_package_view',wait_until='domcontentloaded',timeout=120000)
    pg.wait_for_selector('.o_list_renderer, .o_list_view',timeout=90000); pg.wait_for_timeout(2500)
    for txt in ('Emplacement','Dans emplacements internes'):
        f=pg.locator('.o_searchview_facet',has_text=txt)
        if f.count(): f.first.locator('.o_facet_remove').click(); pg.wait_for_timeout(1200)
    inp=pg.locator('.o_searchview_input').first; inp.click(); inp.fill('PIRONNET'); pg.wait_for_timeout(1000)
    pg.wait_for_timeout(800)
    items=pg.locator('.o_searchview_autocomplete li, .o_searchview_autocomplete .o-dropdown-item, .o_searchview .dropdown-menu li')
    print('options :', [items.nth(i).inner_text().replace(chr(10),' ')[:70] for i in range(min(items.count(),12))])
    item=None
    for i in range(items.count()):
        if 'Opérateur' in items.nth(i).inner_text(): item=items.nth(i); break
    if item is not None: item.click(); pg.wait_for_timeout(3000)
    else:
        pg.screenshot(path=OUT+'/debug_recherche.png'); inp.press('Escape'); pg.wait_for_timeout(500)
        # repli : filtre « Palettes clôturées » du menu Filtres
        pg.locator('.o_searchview_dropdown_toggler').click(); pg.wait_for_timeout(800)
        f=pg.locator('.o_filter_menu .o_menu_item', has_text='clôturées')
        print('filtre clôturées :', f.count())
        if f.count(): f.first.click(); pg.wait_for_timeout(2500)
        pg.keyboard.press('Escape')
    # regroupement par emplacement encore actif : déplier les groupes
    for _ in range(6):
        g=pg.locator('.o_group_header:not(.o_group_open)')
        if not g.count(): break
        g.first.click(); pg.wait_for_timeout(900)
    print('lignes visibles :', pg.locator('.o_data_row').count())
    pg.screenshot(path=OUT+'/bureau_colis_liste.png'); print('capture bureau_colis_liste')
    b.close()
