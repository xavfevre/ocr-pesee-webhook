# -*- coding: utf-8 -*-
"""Test de bout en bout sur une BASE DE TEST Odoo (copie de la production), sans nettoyage :
  1. devis : mode « Transporteur extérieur », transporteur à consulter, action « Demander un tarif transport »,
     prix saisi, confirmation -> report sur le devis (automatisation) ;
  2. expédition via le relais (Origin = base de test) : scan, départ, BL validé avec reliquat, notes, mail (base de test) ;
  3. livraison : palette livrée, note, statut ; départs récents.
  ODOO_USER / ODOO_PWD identiques à la production.   python test_e2e_base_test.py <hote> <PACK…>   ex. testmaq071026.odoo.com PACK0000102"""
import os, ssl, sys, json, urllib.request, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
HOTE, CODE = sys.argv[1], sys.argv[2]
U, D = 'https://' + HOTE, HOTE.split('.')[0]
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
assert uid, 'authentification refusée sur ' + HOTE
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)


def x(mo, me, *a, **k):
    ctx = {'allowed_company_ids': [1]}; ctx.update(k.pop('context', {})); k['context'] = ctx
    try:
        return m.execute_kw(D, uid, p, mo, me, list(a), k)
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in str(e):
            return None
        raise


RENDER = 'https://ocr-pesee-webhook.onrender.com/heures/rpc'


def rpc(ctx):
    req = urllib.request.Request(RENDER, data=json.dumps({'action_id': 2104, 'ctx': ctx}).encode(),
                                 headers={'Content-Type': 'application/json', 'Origin': U})
    d = json.loads(urllib.request.urlopen(req, timeout=180).read().decode())
    if d.get('error'):
        raise Exception(d['error'].get('message'))
    return d.get('result') or {}


def notes(so_id, n=6):
    import re
    return [re.sub(r'<[^>]+>', '', q['body'])[:170] for q in x('mail.message', 'search_read', [['model', '=', 'sale.order'], ['res_id', '=', so_id], ['message_type', '=', 'comment']], fields=['body'], order='id desc', limit=n)]


print('=== base %s (db %s), uid %s ===' % (HOTE, D, uid))
pk = x('stock.package', 'search_read', [['name', '=', CODE]], fields=['id', 'x_commande_id', 'x_studio_cloturee', 'x_exp_statut'])[0]
so_id = pk['x_commande_id'][0]; so = x('sale.order', 'read', [so_id], ['name', 'partner_id', 'x_mode_transport', 'x_transporteur_id', 'x_transporteurs_ids', 'invoice_status'])[0]
print('palette %s clôturée %s | commande %s (%s) | mode devis %s' % (CODE, pk['x_studio_cloturee'], so['name'], so['partner_id'][1][:30], so['x_mode_transport']))

# ── 1. devis : transporteur extérieur + demande de tarif
cat = x('res.partner.category', 'search', [['name', '=', 'Transporteur']])[0]
gendron = x('res.partner', 'search', [['name', '=', 'GENDRON TRANSPORTS']])[0]
x('sale.order', 'write', [so_id], {'x_mode_transport': 'exterieur', 'x_transporteurs_ids': [[6, 0, [gendron]]]})
act = x('ir.actions.server', 'search', [['name', '=', 'Devis : demander un tarif transport']])[0]
r = x('ir.actions.server', 'run', [act], context={'active_model': 'sale.order', 'active_ids': [so_id], 'active_id': so_id})
pos = x('purchase.order', 'search_read', [['origin', '=', so['name']]], fields=['name', 'partner_id', 'state', 'order_line'])
print('1. demandes de prix :', [(q['name'], q['partner_id'][1], q['state']) for q in pos])
po = [q for q in pos if q['partner_id'][0] == gendron][0]
x('purchase.order.line', 'write', po['order_line'], {'price_unit': 410.0})
x('purchase.order', 'button_confirm', [po['id']])
so2 = x('sale.order', 'read', [so_id], ['x_transporteur_id', 'x_transport_achat', 'x_ordre_transport_id'])[0]
print('   après confirmation du tarif :', so2)
print('   dernières notes devis :', notes(so_id, 2))

# ── 2. expédition via le relais (base de test)
sc = rpc({'mode': 'scanner', 'code': CODE})
print('2. scan ->', {k: sc[k] for k in ('name', 'commande', 'client', 'mode_devis', 'mode_devis_src', 'transporteur_devis', 'ton', 'n')})
plan = rpc({'mode': 'bl_plan', 'palettes': [sc['id']]})
print('   plan BL :', plan['plan'])
lids = [int(k) for k in plan['plan'][0]['lignes']]
avant = {l['id']: (l['qty_delivered'], l['qty_invoiced']) for l in x('sale.order.line', 'read', lids, ['qty_delivered', 'qty_invoiced'])} if lids else {}
bl_avant = [(q['name'], q['state']) for q in x('stock.picking', 'search_read', [['sale_id', '=', so_id]], fields=['name', 'state'], order='id')]
print('   lignes avant (livré, facturé) :', avant, '| transferts avant :', bl_avant)
dep = rpc({'mode': 'valider', 'palettes': [sc['id']], 'exp_mode': 'exterieur', 'transporteur_id': sc['transporteur_devis_id'], 'camion': 'AB-123-CD', 'chauffeur': '', 'charge_par': 478, 'lettre': 'LV-TEST-1'})
print('   départ ->', dep['msg'], '| liste', dep['liste_url'])
pk2 = x('stock.package', 'read', [sc['id']], ['x_exp_statut', 'x_exp_mode', 'x_exp_transporteur_id', 'x_exp_camion', 'x_exp_lot', 'x_exp_par_id', 'x_exp_lettre'])[0]
print('   palette :', pk2)
apres = {l['id']: (l['qty_delivered'], l['qty_invoiced']) for l in x('sale.order.line', 'read', lids, ['qty_delivered', 'qty_invoiced'])} if lids else {}
bl_apres = [(q['name'], q['state'], q['carrier_tracking_ref']) for q in x('stock.picking', 'search_read', [['sale_id', '=', so_id]], fields=['name', 'state', 'carrier_tracking_ref'], order='id')]
print('   lignes après (livré, facturé) :', apres, '\n   transferts après :', bl_apres)
print('   notes devis :', notes(so_id, 3))
mails = x('mail.mail', 'search_read', [['subject', 'ilike', 'Départ palettes']], fields=['subject', 'state', 'email_to'], order='id desc', limit=1)
print('   mail bureau (base de test) :', mails)
tache = sc.get('tache_id')
if tache:
    print('   tâche Commande Pierres :', x('project.task', 'read', [tache], ['name', 'stage_id'])[0])
html = urllib.request.urlopen(U + dep['liste_url'], timeout=60).read().decode('utf-8', 'ignore')
print('   liste de chargement servie :', 'Liste de chargement' in html and CODE in html)

# ── 3. livraison
liv = rpc({'mode': 'livrer', 'palettes': [sc['id']], 'qui': 'TEST', 'source': 'bureau'})
print('3. livraison ->', liv['msg'], '|', x('stock.package', 'read', [sc['id']], ['x_exp_statut', 'x_livraison_date'])[0])
print('   départs récents :', [(l['lot'], l['n'], l.get('livrees')) for l in rpc({'mode': 'lots', 'jours': 10})['lots']])
print('   notes devis :', notes(so_id, 2))
print('\nTEST BASE DE TEST TERMINÉ (rien n a été nettoyé : c est une base de test)')
