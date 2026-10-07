# -*- coding: utf-8 -*-
"""Test en production, SANS écriture : le relais déployé doit répondre « confirmer » (tablette 2101) et
« demande_autre » (poste de scan 2102) quand la palette est à un autre opérateur, sans rien modifier.
Vérifie avant/après que la palette et l'OF n'ont pas bougé.   python test_live_lecture_seule.py <op_id> <of_id> <colis_id> <code_of>"""
import os, ssl, sys, json, urllib.request, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
op, of_id, colis_id, code = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [1, 2, 3, 4, 13]}))
RENDER = 'https://ocr-pesee-webhook.onrender.com/heures/rpc'


def rpc(action_id, ctx):
    req = urllib.request.Request(RENDER, data=json.dumps({'action_id': action_id, 'ctx': ctx}).encode(), headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=120).read().decode())


def etat():
    pk = x('stock.package', 'read', [colis_id], ['name', 'x_operateur_id', 'x_operateur_ids', 'write_date', 'x_studio_cloturee'])[0]
    of = x('mrp.production', 'read', [of_id], ['name', 'x_studio_colis', 'write_date'])[0]
    rep = x('x_repartition_palette', 'search_count', [['x_studio_of_id', '=', of_id]])
    emp = x('hr.employee', 'read', [op], ['name', 'x_palette_scan_id'])[0]
    nmsg = x('mail.message', 'search_count', [['model', '=', 'stock.package'], ['res_id', '=', colis_id]])
    return pk, of, rep, emp, nmsg


avant = etat()
pk, of, rep, emp, nmsg = avant
print('avant : palette %s de %s (co-op %s) | OF %s colis %s, répartitions %d | opérateur %s palette active %s | messages palette %d' % (
    pk['name'], pk['x_operateur_id'] and pk['x_operateur_id'][1], pk['x_operateur_ids'], of['name'], of['x_studio_colis'], rep, emp['name'], emp['x_palette_scan_id'], nmsg))
r1 = rpc(2101, {'op': op, 'of_id': of_id, 'colis_id': colis_id, 'qte': 0})
print('2101 tablette sans confirmation ->', json.dumps(r1, ensure_ascii=False)[:400])
r2 = rpc(2102, {'mode': 'scan', 'colis_id': colis_id, 'code': code})
res2 = r2.get('result') or {}
print('2102 poste de scan, scan de l OF -> ok=%s | msg=%s | demande_autre=%s' % (res2.get('ok'), res2.get('msg'), json.dumps(res2.get('demande_autre'), ensure_ascii=False)))
r3 = rpc(2102, {'mode': 'placer', 'colis_id': colis_id, 'of_id': of_id, 'qte': 1})
res3 = r3.get('result') or {}
print('2102 « placer » sans autre_ok (garde-fou) -> ok=%s | %s' % (res3.get('ok'), (res3.get('msg') or '')[:120]))
apres = etat()
print('après identique à avant :', apres == avant)
ok = (r1.get('result', {}).get('confirmer') == 1 and res2.get('ok') == 0 and bool(res2.get('demande_autre')) and res3.get('ok') == 0 and apres == avant)
print('RÉSULTAT :', 'OK' if ok else 'À VÉRIFIER')
