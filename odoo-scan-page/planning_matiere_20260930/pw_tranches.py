# -*- coding: utf-8 -*-
"""Lecture seule : contrôle de la page /planning-tranches (sections par matière, tableaux remplis par le script,
changement d'épaisseur sur une pièce, onglet présent sur les autres pages) + captures d'écran."""
import os, sys, requests
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
r = requests.post(U + '/web/session/authenticate', json={'jsonrpc': '2.0', 'method': 'call', 'params': {'db': D, 'login': us, 'password': p}}, timeout=60)
sid = r.cookies.get('session_id'); assert sid
ETAT = """(function(){
  var secs = Array.from(document.querySelectorAll('.tr-mat')).map(function(s){
    return {mat: s.getAttribute('data-mat'), of: s.querySelectorAll('tr.tr-piece').length, grp: s.querySelectorAll('tr.tr-grp').length,
            res: Array.from(s.querySelectorAll('table.tr-res tbody tr')).map(function(t){ return t.textContent.trim().replace(/\\s+/g, ' '); }),
            head: (s.querySelector('.tr-head') || {}).textContent.trim().replace(/\\s+/g, ' ')};
  });
  var err = document.querySelector('.o_error_detail, pre') ? (document.querySelector('.o_error_detail, pre').textContent || '').trim().slice(0, 200) : '';
  return {titre: document.title, secs: secs, chips: Array.from(document.querySelectorAll('.tr-outils a.btn')).map(function(a){ return a.textContent.trim(); }), err: err,
          tabs: Array.from(document.querySelectorAll('.nav-tabs a')).map(function(a){ return a.textContent.trim(); })};
})()"""
with sync_playwright() as pw:
    b = None
    for ch in ('chrome', 'msedge'):
        try:
            b = pw.chromium.launch(channel=ch); break
        except Exception:
            pass
    if b is None:
        b = pw.chromium.launch()
    ctx = b.new_context(viewport={'width': 1600, 'height': 1000}, locale='fr-FR')
    ctx.add_cookies([{'name': 'session_id', 'value': sid, 'domain': 'maquignon.odoo.com', 'path': '/'}])
    page = ctx.new_page()
    errs = []
    page.on('pageerror', lambda e: errs.append(str(e)[:160]))
    for url in ('/planning-tranches', '/planning-tranches?days=30&tp=HAIMS'):
        page.goto(U + url, wait_until='domcontentloaded', timeout=180000)
        page.wait_for_selector('.nav-tabs', timeout=120000)
        page.wait_for_timeout(1500)
        d = page.evaluate(ETAT)
        print('=== %s | titre %s | onglets %d (Tranches %s) | chips %s%s' % (url, d['titre'], len(d['tabs']), 'présent' if any('Tranches' in t for t in d['tabs']) else 'ABSENT', d['chips'], (' | ERREUR ' + d['err']) if d['err'] else ''))
        for s in d['secs']:
            print('   %-10s OF %3d | groupes d épaisseur %2d | en-tête « %s »' % (s['mat'], s['of'], s['grp'], s['head'][:90]))
            for row in s['res'][:6]:
                print('        ', row)
        if url == '/planning-tranches' and d['secs']:
            # clic sur la 2e cote de la première pièce -> le regroupement doit changer
            avant = page.evaluate("document.querySelector('.tr-mat table.tr-res tbody').textContent.replace(/\\s+/g, ' ').trim()")
            btns = page.query_selector_all('.tr-mat tr.tr-piece td.tr-ep .ep-btn')
            if len(btns) > 1:
                btns[1].click(); page.wait_for_timeout(300)
                apres = page.evaluate("document.querySelector('.tr-mat table.tr-res tbody').textContent.replace(/\\s+/g, ' ').trim()")
                print('   clic sur une autre cote : résumé modifié =', avant != apres)
                print('     avant :', avant[:120]); print('     après :', apres[:120])
                page.reload(wait_until='domcontentloaded'); page.wait_for_selector('.tr-mat', timeout=120000); page.wait_for_timeout(1200)
                apres2 = page.evaluate("document.querySelector('.tr-mat table.tr-res tbody').textContent.replace(/\\s+/g, ' ').trim()")
                print('   après rechargement, choix conservé (localStorage) =', apres2 == apres)
                page.click('#tr-reset'); page.wait_for_timeout(300)
                print('   après « Tout en H », retour à l état initial =', page.evaluate("document.querySelector('.tr-mat table.tr-res tbody').textContent.replace(/\\s+/g, ' ').trim()") == avant)
        page.screenshot(path='tranches_%d.png' % (0 if url == '/planning-tranches' else 1), full_page=False)
    page.goto(U + '/planning-machines?board=complet', wait_until='domcontentloaded', timeout=180000)
    page.wait_for_selector('.nav-tabs', timeout=120000)
    print('onglets board complet :', page.evaluate("Array.from(document.querySelectorAll('.nav-tabs a')).map(function(a){ return a.textContent.trim(); })"))
    print('erreurs JS :', errs[:3])
    b.close()
