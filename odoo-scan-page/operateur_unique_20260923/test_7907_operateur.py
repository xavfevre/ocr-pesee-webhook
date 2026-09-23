# -*- coding: utf-8 -*-
"""Test bout en bout de la vue tablette après correctif, sur l'OT 19021 (WH/OF/12507, Taille de pierre, assigné LANGLOIS 654,
prêt, sans pointage) avec la session Isabelle et op=654 :
  Démarrer -> pointage LANGLOIS, assigné [654], état en cours ; Pause -> prêt ; Terminer (2 clics) -> fait, assigné [654] ;
  Annuler Terminé -> prêt. Nettoyage : pointages supprimés, opérateurs travaillant vidés."""
import os, sys, requests, ssl, xmlrpc.client
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding='utf-8')
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
WO = 19021; OP = 654
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [1]}))


def etat(lab):
    w = x('mrp.workorder', 'read', [WO], fields=['state', 'employee_assigned_ids', 'employee_ids', 'time_ids', 'date_start', 'qty_produced'])[0]
    tl = x('mrp.workcenter.productivity', 'read', w['time_ids'], fields=['employee_id', 'user_id', 'date_end']) if w['time_ids'] else []
    print('   [%s] état %s | assignés %s | travaillant %s | qté produite %s | pointages %s' % (lab, w['state'], w['employee_assigned_ids'], w['employee_ids'], w['qty_produced'], [(t['employee_id'] and t['employee_id'][1], t['user_id'] and t['user_id'][1], 'fermé' if t['date_end'] else 'ouvert') for t in tl]))
    return w


etat('avant')
s = requests.Session()
s.post(U + '/web/session/authenticate', json={'jsonrpc': '2.0', 'method': 'call', 'params': {'db': D, 'login': us, 'password': p}}, timeout=60)
sid = s.cookies.get('session_id')
with sync_playwright() as pw:
    b = pw.chromium.launch(channel='msedge', headless=True)
    ctx = b.new_context(viewport={'width': 1300, 'height': 1000}, locale='fr-FR')
    ctx.add_cookies([{'name': 'session_id', 'value': sid, 'domain': 'maquignon.odoo.com', 'path': '/', 'secure': True, 'httpOnly': True},
                     {'name': 'cids', 'value': '1', 'domain': 'maquignon.odoo.com', 'path': '/', 'secure': True}])
    pg = ctx.new_page(); errs = []; calls = []
    pg.on('dialog', lambda d: d.accept())
    pg.on('pageerror', lambda e: errs.append(str(e)[:200]))
    pg.on('request', lambda r: calls.append(r.post_data[:300]) if 'call_kw' in r.url and r.post_data and 'ir.actions.server' in r.post_data else None)
    pg.goto(U + '/vue-operateur?op=%d' % OP, wait_until='domcontentloaded', timeout=120000)
    pg.wait_for_timeout(5000)
    print('titre :', pg.title()[:60], '| cartes :', pg.locator('.vo-card').count(), '| erreurs JS :', errs[:2])
    card = pg.locator('.vo-card[data-id="%d"]' % WO)
    print('carte OT %d visible :' % WO, card.count())
    assert card.count() == 1

    def clic(label, attendu):
        btn = card.locator('.vo-act', has_text=label).first
        assert btn.count() == 1, 'bouton %s absent' % label
        btn.click(); pg.wait_for_timeout(2500)
        print('   clic « %s » -> état carte %s | requêtes actions : %s' % (label, card.get_attribute('data-state'), [cc[:120] for cc in calls[-1:]]))
        w = etat('après ' + label)
        assert w['state'] == attendu, (w['state'], attendu)
        return w

    clic('Démarrer', 'progress')
    clic('Pause', 'ready')
    clic('Démarrer', 'progress')
    clic('Terminer', 'progress')          # 1er clic = demande de confirmation
    clic('Confirmer', 'done')
    clic('Annuler', 'ready')              # bouton « Annuler Terminé » (confirm() accepté)
    b.close()
w = etat('avant nettoyage')
if w['time_ids']:
    try:
        x('mrp.workcenter.productivity', 'unlink', w['time_ids'])
    except xmlrpc.client.Fault as e:
        print('   pointages non supprimés :', str(e).strip().split('\n')[-1][:150])
x('mrp.workorder', 'write', [WO], {'employee_ids': [[6, 0, []]], 'employee_assigned_ids': [[6, 0, [OP]]]})
etat('final')
