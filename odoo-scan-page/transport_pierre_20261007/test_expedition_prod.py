# -*- coding: utf-8 -*-
"""Test en production de l'action 2104 via le relais Render.
  lecture : scan d'une palette clôturée (lecture seule), départs récents ;
  cycle   : départ « enlèvement client » SANS mail sur une palette clôturée, contrôle des champs, liste de chargement
            servie, puis annulation et nettoyage (notes retirées, étape de la tâche restaurée).
  python test_expedition_prod.py lecture <PACK…> | cycle <PACK…>"""
import os, ssl, sys, json, urllib.request, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode, code = sys.argv[1], sys.argv[2]
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [1]}))
RENDER = 'https://ocr-pesee-webhook.onrender.com/heures/rpc'


def rpc(ctx):
    req = urllib.request.Request(RENDER, data=json.dumps({'action_id': 2104, 'ctx': ctx}).encode(), headers={'Content-Type': 'application/json'})
    d = json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
    if d.get('error'):
        raise Exception(d['error'].get('message'))
    return d.get('result') or {}


p1 = rpc({'mode': 'scanner', 'code': code})
print('scan :', json.dumps({k: p1[k] for k in ('name', 'commande', 'client', 'adresse', 'zone', 'n', 'ton', 'cub', 'mode_devis', 'statut', 'tache_id')}, ensure_ascii=False))
print('départs récents :', rpc({'mode': 'lots', 'jours': 3}))
if mode != 'cycle':
    sys.exit(0)
pk_id = p1['id']
tache = p1['tache_id']
stage_avant = x('project.task', 'read', [tache], ['stage_id'])[0]['stage_id'] if tache else None
n_msg_so = x('mail.message', 'search_count', [['model', '=', 'sale.order'], ['res_id', '=', p1['commande_id']]]) if p1['commande_id'] else 0
r = rpc({'mode': 'valider', 'palettes': [pk_id], 'exp_mode': 'client', 'chauffeur': 'TEST (à annuler)', 'camion': 'XX-000-XX', 'charge_par': 0, 'sans_mail': 1})
print('départ :', r['msg'], '| liste :', r['liste_url'])
pk = x('stock.package', 'read', [pk_id], ['x_exp_statut', 'x_exp_mode', 'x_exp_chauffeur', 'x_exp_camion', 'x_exp_date', 'x_exp_lot'])[0]
print('palette après départ :', pk)
import urllib.request as ur
html = ur.urlopen('https://maquignon.odoo.com' + r['liste_url'], timeout=60).read().decode('utf-8', 'ignore')
print('liste de chargement servie :', ('Liste de chargement' in html) and (p1['name'] in html), '| mentions :', [t for t in ('Enlèvement par le client', 'TEST (à annuler)', 'XX-000-XX', p1['client'][:12]) if t in html])
try:
    print('re-scan (doit refuser) :', rpc({'mode': 'scanner', 'code': code}))
except Exception as e:
    print('re-scan refusé :', e)
lv = rpc({'mode': 'livrer', 'palettes': [pk_id], 'qui': 'TEST', 'source': 'bureau'})
pkl = x('stock.package', 'read', [pk_id], ['x_exp_statut', 'x_livraison_date'])[0]
print('livraison :', lv['msg'], '|', pkl)
lots = rpc({'mode': 'lots', 'jours': 10})
print('départs récents (livrées) :', [(l['lot'], l.get('livrees'), l['n']) for l in lots['lots'] if l['lot'] == r['lot']])
a0 = rpc({'mode': 'annuler', 'palette_id': pk_id})
print('annulation livraison :', a0['msg'], '|', x('stock.package', 'read', [pk_id], ['x_exp_statut', 'x_livraison_date'])[0])
a = rpc({'mode': 'annuler', 'palette_id': pk_id})
print('annulation :', a['msg'])
pk2 = x('stock.package', 'read', [pk_id], ['x_exp_statut', 'x_exp_mode', 'x_exp_chauffeur', 'x_exp_camion', 'x_exp_date', 'x_exp_lot'])[0]
print('palette après annulation :', pk2)
# nettoyage : notes de test et étape de la tâche
msgs = []
if p1['commande_id']:
    msgs += x('mail.message', 'search', [['model', '=', 'sale.order'], ['res_id', '=', p1['commande_id']], '|', '|', ['body', 'ilike', r['lot']], ['body', 'ilike', 'Livraison le'], ['body', 'ilike', 'Livraison annulée']])
if tache:
    msgs += x('mail.message', 'search', [['model', '=', 'project.task'], ['res_id', '=', tache], '|', ['body', 'ilike', r['lot']], ['body', 'ilike', 'Livré :']])
    st = x('project.task', 'read', [tache], ['stage_id'])[0]['stage_id']
    if stage_avant and st and st[0] != stage_avant[0]:
        x('project.task', 'write', [tache], {'stage_id': stage_avant[0]}); print('étape de la tâche restaurée :', stage_avant[1])
    else:
        print('étape de la tâche inchangée :', st and st[1])
if msgs:
    x('mail.message', 'unlink', msgs)
print('notes de test retirées : %d | notes commande : %d -> %d' % (len(msgs), n_msg_so, x('mail.message', 'search_count', [['model', '=', 'sale.order'], ['res_id', '=', p1['commande_id']]]) if p1['commande_id'] else 0))
print('RÉSULTAT :', 'OK' if (pk['x_exp_statut'] == 'enlevee' and not pk2['x_exp_statut'] and not pk2['x_exp_lot']) else 'À VÉRIFIER')
