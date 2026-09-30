# -*- coding: utf-8 -*-
"""Lecture seule : contrôle du filtre Matière sur les 4 pages (barre présente, cartes filtrées, liens des onglets avec tp)."""
import os, sys, requests
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
r = requests.post(U + '/web/session/authenticate', json={'jsonrpc': '2.0', 'method': 'call', 'params': {'db': D, 'login': us, 'password': p}}, timeout=60)
sid = r.cookies.get('session_id'); assert sid
URLS = [
    ('/planning-machines?board=complet', None),
    ('/planning-machines?board=atelier&tp=HAIMS', 'HAIMS'),
    ('/planning-machines?board=complet&tp=TUFFEAU', 'TUFFEAU'),
    ('/planning-operateurs?tp=TUFFEAU', 'TUFFEAU'),
    ('/planning-fabrication?tp=HAIMS', 'HAIMS'),
    ('/planning-mois?tp=TUFFEAU', 'TUFFEAU'),
]
JS = """(function(){
  var cards = Array.from(document.querySelectorAll('.pf-card'));
  var mats = cards.map(function(c){ var s = c.querySelector('span[style*="float:right"]'); var t = s ? s.textContent.trim() : ''; var i = t.lastIndexOf('·'); return i >= 0 ? t.slice(i + 1).trim() : t; });
  var uniq = {}; mats.forEach(function(m_){ uniq[m_] = (uniq[m_] || 0) + 1; });
  var bar = Array.from(document.querySelectorAll('div')).filter(function(d){ return d.textContent.trim().indexOf('Matière :') === 0; })[0];
  var chips = bar ? Array.from(bar.querySelectorAll('a')).map(function(a){ return a.textContent.trim() + (a.className.indexOf('btn-dark') >= 0 && a.className.indexOf('outline') < 0 ? '*' : ''); }) : null;
  var tabs = Array.from(document.querySelectorAll('.nav-tabs a')).map(function(a){ return a.getAttribute('href') || ''; });
  var mois = document.querySelectorAll('a[href*="model=mrp.production"]').length;
  var err = document.querySelector('.o_error_detail, .alert-danger') ? (document.querySelector('.o_error_detail, .alert-danger').textContent || '').trim().slice(0, 120) : '';
  return {cards: cards.length, mats: uniq, chips: chips, tabsSansTp: tabs.filter(function(h){ return h !== '#' && h.indexOf('tp=') < 0; }), liensMois: mois, err: err, titre: document.title};
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
    for url, tp in URLS:
        page.goto(U + url, wait_until='domcontentloaded', timeout=180000)
        try:
            page.wait_for_selector('.nav-tabs', timeout=120000)
        except Exception:
            pass
        page.wait_for_timeout(1500)
        d = page.evaluate(JS)
        ok = (not tp) or all(k == tp for k in d['mats'])
        print('%-48s cartes %4d | matières %s | filtre %s | onglets sans tp %d | chips %s%s' % (
            url, d['cards'], d['mats'], 'OK' if ok else 'ÉCART', len(d['tabsSansTp']), d['chips'], (' | ERREUR ' + d['err']) if d['err'] else ''))
        if url.startswith('/planning-mois'):
            print('    liens OF (vue mois) :', d['liensMois'])
        page.screenshot(path='matiere_%d.png' % URLS.index((url, tp)))
    b.close()
