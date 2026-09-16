# -*- coding: utf-8 -*-
"""Ménage des BL en attente créés par les articles de transport / location / transfert (consommables, facturés sur
quantités commandées : le BL ne sert à rien). Familles : Transport de granulats, Transport Appro, Transport de pierres,
Transport de blocs, Location de matériel Transport, Transfert de matériel, autres « Transport ».
Usage : python menage_bl_transport2.py <mode> [famille]
  mode    dry : état des lieux (rien n'est modifié, défaut)
          bl  : annule les BL en attente ne contenant que ces articles ; dans les BL mixtes, met la demande du mouvement
                transport à 0 (le mouvement est annulé par Odoo à la validation du BL, les lignes pierre restent)
  famille all (défaut) | granulats | appro | pierres | blocs | location | transfert | autre
Périmètre : BL de SARL MAQUIGNON uniquement. Un Excel récapitulatif est écrit sur le Bureau."""
import os, ssl, sys, xmlrpc.client, collections, datetime, re
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
fam_arg = (sys.argv[2] if len(sys.argv) > 2 else 'all').lower()
FAM_KEY = {'granulats': 'Transport de granulats', 'appro': 'Transport appro', 'pierres': 'Transport de pierres', 'blocs': 'Transport de blocs',
           'location': 'Location de mat', 'transfert': 'Transfert de mat', 'autre': 'Autre transport / livraison'}
assert fam_arg == 'all' or fam_arg in FAM_KEY, 'famille inconnue : ' + fam_arg
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
CTX = {'allowed_company_ids': [1, 2, 3, 4, 13], 'active_test': False}
MOTS = ['transport', 'location de mat', 'transfert de mat', 'livraison']
dom = ['&', '&', ['type', '=', 'consu'], ['is_storable', '=', False], '|'] * 1
dom = [['type', '=', 'consu'], ['is_storable', '=', False], '|', '|', '|'] + [['name', 'ilike', w] for w in MOTS]
prods = x('product.product', 'search_read', dom, fields=['name', 'display_name', 'company_id', 'product_tmpl_id'], context=CTX)
pid_soc = {pr['id']: (pr['company_id'] and pr['company_id'][1]) or 'toutes' for pr in prods}


def famille(nom):
    n = nom.lower()
    for k in ('transport de granulats', 'transport appro', 'transport de pierres', 'transport de blocs', 'location de mat', 'transfert de mat'):
        if k in n:
            return k.capitalize()
    return 'Autre transport / livraison'


pid_fam = {pr['id']: famille(pr['display_name']) for pr in prods}
if fam_arg != 'all':
    pid_fam = {k: v for k, v in pid_fam.items() if v == FAM_KEY[fam_arg]}
print('articles consommables transport/location/transfert/livraison retenus :', len(pid_fam), dict(collections.Counter(pid_fam.values())))
pids = list(pid_fam)
mv = x('stock.move', 'search_read', [['product_id', 'in', pids], ['state', 'not in', ['done', 'cancel']], ['picking_id', '!=', False], ['company_id', '=', 1]],
       fields=['picking_id', 'product_id', 'product_uom_qty', 'quantity', 'state', 'company_id'], limit=20000, context=CTX)
pick_ids = sorted({mm['picking_id'][0] for mm in mv})
allm = x('stock.move', 'search_read', [['picking_id', 'in', pick_ids], ['state', 'not in', ['done', 'cancel']]], fields=['picking_id', 'product_id', 'product_uom_qty'], limit=60000, context=CTX) if pick_ids else []
bypk = collections.defaultdict(list)
for mm in allm:
    bypk[mm['picking_id'][0]].append(mm)
# BL « purs » : tous les mouvements restants sont du transport (ou à demande 0)
purs = [pk for pk in pick_ids if all(mm['product_id'][0] in pid_fam or mm['product_uom_qty'] == 0 for mm in bypk[pk])]
mixtes = [pk for pk in pick_ids if pk not in purs]
mv_mixte = [mm for mm in mv if mm['picking_id'][0] in mixtes and mm['product_uom_qty'] != 0]
picks = {pk['id']: pk for pk in x('stock.picking', 'read', pick_ids, fields=['name', 'origin', 'state', 'company_id', 'picking_type_id', 'scheduled_date'], context=CTX)} if pick_ids else {}
print('BL en attente : %d (purs transport : %d, mixtes : %d -> %d mouvements transport à neutraliser)' % (len(pick_ids), len(purs), len(mixtes), len(mv_mixte)))
fam_pk = collections.Counter()
for mm in mv:
    fam_pk[(pid_fam[mm['product_id'][0]], mm['company_id'][1], 'pur' if mm['picking_id'][0] in purs else 'mixte')] += 1
print('mouvements par famille / société / type de BL :')
for k, v in sorted(fam_pk.items(), key=lambda kv: -kv[1]):
    print('   %-32s %-22s %-6s %5d' % (k[0], k[1][:22], k[2], v))
pk_fam = collections.defaultdict(set)
for mm in mv:
    pk_fam[mm['picking_id'][0]].add(pid_fam[mm['product_id'][0]])
cnt = collections.Counter()
for pk, fams in pk_fam.items():
    for f in fams:
        cnt[(f, 'pur' if pk in purs else 'mixte')] += 1
print('BL par famille :', {('%s %s' % k): v for k, v in sorted(cnt.items())})
from openpyxl import Workbook
wb = Workbook(); ws = wb.active; ws.title = 'BL'
ws.append(['BL', 'Société', 'Type', 'Origine', 'État', 'Date prévue', 'BL', 'Articles transport'])
for pk in pick_ids:
    k = picks[pk]
    ws.append([k['name'], k['company_id'][1], k['picking_type_id'][1], k['origin'] or '', k['state'], (k['scheduled_date'] or '')[:10], 'pur (annulé)' if pk in purs else 'mixte (mouvement transport à 0)',
               ' | '.join('%s x%s' % (mm['product_id'][1][:40], mm['product_uom_qty']) for mm in mv if mm['picking_id'][0] == pk)])
out = 'C:/Users/xavfe/Desktop/Maquignon/Menage_BL_transport_familles_%s.xlsx' % datetime.date.today().strftime('%Y-%m-%d')
wb.save(out); print('récapitulatif :', out)
if mode != 'bl':
    sys.exit(0)
faits = collections.Counter()
for i in range(0, len(purs), 40):
    lot = purs[i:i + 40]
    try:
        x('stock.picking', 'action_cancel', lot, context=CTX)
    except Exception as e:  # noqa: BLE001
        if 'cannot marshal None' not in str(e):
            print('  erreur lot BL', lot[:3], str(e)[:150]); continue
    faits['BL annulés'] += len(lot)
for mm in mv_mixte:
    try:
        x('stock.move', 'write', [mm['id']], {'product_uom_qty': 0, 'quantity': 0}, context=CTX); faits['mouvements transport mis à 0 (BL mixtes)'] += 1
    except Exception as e:  # noqa: BLE001
        print('  mouvement', mm['id'], mm['picking_id'][1], str(e).strip().splitlines()[-1][:150])
print('contrôle BL purs restants :', x('stock.picking', 'search_count', [['id', 'in', purs], ['state', 'not in', ['done', 'cancel']]], context=CTX))
print('fait :', dict(faits))
