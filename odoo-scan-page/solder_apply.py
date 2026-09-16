# -*- coding: utf-8 -*-
"""Solde des commandes « à facturer » — 16/09/2026 (demande : « solde les 12 et les 4 »).
Modes : dry (défaut) | apply (les 8 transport + 3 sur-facturées vérifiées) | attente (les 4 transport mises en attente).
Principe : quantité commandée = quantité facturée ; si la ligne est « livrée » on remet d'abord la quantité livrée au
niveau facturé (Odoo refuse une commande inférieure au livré). Un Excel récapitulatif est écrit sur le Bureau."""
import os, ssl, sys, xmlrpc.client, datetime
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
ctx = {'allowed_company_ids': [1, 2, 3, 4, 13], 'active_test': False}
# (ligne, qté commandée cible, qté livrée cible ou None, prix cible ou None, motif)
PLAN = {'apply': [
    (1422, 0, None, None, 'S00755 transport facturé à la main sur FAC/2025/00061 (Transport Forfait 2 x 230)'),
    (1465, 0, None, None, 'S00766 transport facturé à la main sur FAC/2025/00057 (Transport Forfait 1 x 190)'),
    (346560, 30.56, 30.56, None, 'S07703 facturé 30,56 t sur FAC/26-27/0144 : écart de pesée 0,02 t'),
    (346259, 0, 0, None, 'S07827 transport facturé sur FAC/26-27/0167 (Transport de granulats 30,6 t x 3,50, ligne non liée)'),
    (346988, 0, 0, None, 'S07978 transport facturé sur FAC/26-27/0378 via une autre ligne de commande'),
    (352368, 0, 0, None, 'S09349 FAC/26-27/0362 annulée par avoir, transport refacturé sur FAC/26-27/0627 via la commande S11748'),
    (357383, 0, None, None, 'S10710 transport facturé sur FAC/26-27/0511 via une autre ligne de commande'),
    (362288, 0, 0, None, 'S11120 transport facturé sur FAC/26-27/0691 en 2 x 650 (Location camion 8x4)'),
    (356220, 1, None, 900.0, 'S10294 facturé 1 x 900 sur FAC/26-27/0373 : ligne alignée (1 h x 900)'),
    (361483, 14.32, None, None, 'S11793 facturé 14,32 t sur FAC/2026/00257 : commande alignée sur la pesée'),
], 'attente': [
    (347967, 0, 0, None, 'S07049 transport 165 absent de FAC/26-27/0582'),
    (343085, 0, 0, None, 'S07412 FAC/26-27/0092 annulée intégralement (avoir RVE/26-27/0004), rien refacturé'),
    (343132, 0, 0, None, 'S07420 FAC/26-27/0094 annulée intégralement (avoir RVE/26-27/0023), rien refacturé'),
    (352101, 0, 0, None, 'S09209 FAC/26-27/0354 annulée intégralement (avoir RVE/26-27/0011), rien refacturé'),
]}
S07523 = [344738, 344739, 344740, 344741, 344742, 344743, 344744, 344745]
PICK_OBSOLETE = 6923   # WH/PICK/02490, transfert vers la zone de colisage créé le 25/06 après la livraison du 23/06
plan = PLAN['attente'] if mode == 'attente' else PLAN['apply']
F = ['order_id', 'product_id', 'name', 'product_uom_qty', 'qty_delivered', 'qty_invoiced', 'price_unit', 'discount',
     'price_subtotal', 'invoice_status', 'untaxed_amount_to_invoice']


def lire(ids):
    return {l['id']: l for l in x('sale.order.line', 'read', ids, fields=F, context=ctx)}


def cde(l):
    return l['order_id'][1]


def art(l):
    return (l['product_id'] and l['product_id'][1]) or l['name']


avant = lire([t[0] for t in plan] + (S07523 if mode != 'attente' else []))
err = []
for lid, q, liv, prix, motif in plan:
    l = avant[lid]
    print('%-9s %-42s cdé %8.3f -> %8.3f | livré %8.3f -> %s | fact %8.3f | %s' % (
        cde(l), art(l)[:42], l['product_uom_qty'], q, l['qty_delivered'], liv if liv is not None else '=', l['qty_invoiced'], motif[:60]))
    if mode == 'dry':
        continue
    try:
        if liv is not None and abs(l['qty_delivered'] - liv) > 1e-6:
            x('sale.order.line', 'write', [lid], {'qty_delivered': liv}, context=ctx)
        vals = {'product_uom_qty': q, 'price_unit': prix if prix is not None else l['price_unit'], 'discount': l['discount']}
        x('sale.order.line', 'write', [lid], vals, context=ctx)
    except Exception as e:  # noqa: BLE001
        err.append((cde(l), str(e).strip().splitlines()[-1][:160]))
if mode == 'apply':
    print('S07523 : annulation du transfert obsolète WH/PICK/02490 puis quantités livrées = facturées')
    pk = x('stock.picking', 'read', [PICK_OBSOLETE], fields=['name', 'state', 'origin'], context=ctx)[0]
    assert pk['name'] == 'WH/PICK/02490' and pk['origin'] == 'S07523', pk
    if pk['state'] not in ('done', 'cancel'):
        try:
            x('stock.picking', 'action_cancel', [PICK_OBSOLETE], context=ctx)
        except Exception as e:  # noqa: BLE001
            if 'cannot marshal None' not in str(e):
                err.append(('S07523 BL', str(e)[:160]))
    for lid, l in lire(S07523).items():
        if abs(l['qty_delivered'] - l['product_uom_qty']) > 1e-6:
            try:
                x('sale.order.line', 'write', [lid], {'qty_delivered': l['product_uom_qty']}, context=ctx)
            except Exception as e:  # noqa: BLE001
                err.append(('S07523', str(e)[:160]))
if mode != 'dry':
    apres = lire(list(avant))
    oids = sorted({l['order_id'][0] for l in avant.values()})
    st = {o['name']: o['invoice_status'] for o in x('sale.order', 'read', oids, fields=['name', 'invoice_status'], context=ctx)}
    pks = x('stock.picking', 'search_read', [['sale_id', 'in', oids], ['state', 'not in', ['done', 'cancel']],
                                             ['create_date', '>=', datetime.date.today().isoformat()]], fields=['name', 'origin', 'state'], context=ctx)
    if pks:
        print('BL créés aujourd hui par les ajustements :', [(k['name'], k['origin']) for k in pks], '-> annulation')
        try:
            x('stock.picking', 'action_cancel', [k['id'] for k in pks], context=ctx)
        except Exception as e:  # noqa: BLE001
            if 'cannot marshal None' not in str(e):
                err.append(('BL créés', str(e)[:160]))
    from openpyxl import Workbook
    from openpyxl.styles import Font
    wb = Workbook(); ws = wb.active; ws.title = 'Lignes soldées'
    ws.append(['Commande', 'Article', 'Qté cdée avant', 'Qté cdée après', 'Livré avant', 'Livré après', 'Qté facturée', 'Prix avant',
               'Prix après', 'Montant HT avant', 'Montant HT après', 'Statut ligne après', 'Statut commande après', 'Motif'])
    motifs = {t[0]: t[4] for t in plan}
    motifs.update({i: 'S07523 facturé sans quantité livrée (transfert WH/PICK/02005 fait le 23/06) : livré remis = facturé, WH/PICK/02490 annulé' for i in S07523})
    for lid in avant:
        a, b = avant[lid], apres[lid]
        ws.append([cde(a), art(a), a['product_uom_qty'], b['product_uom_qty'], a['qty_delivered'], b['qty_delivered'], b['qty_invoiced'],
                   a['price_unit'], b['price_unit'], round(a['price_subtotal'], 2), round(b['price_subtotal'], 2), b['invoice_status'],
                   st.get(cde(a)), motifs.get(lid, '')])
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = 'A2'
    for col, w in zip('ABCDEFGHIJKLMN', (11, 45, 12, 12, 11, 11, 12, 10, 10, 14, 14, 14, 16, 90)):
        ws.column_dimensions[col].width = w
    ws2 = wb.create_sheet('Erreurs'); ws2.append(['Commande', 'Erreur'])
    for e in err:
        ws2.append(list(e))
    out = 'C:/Users/xavfe/Desktop/Maquignon/Solde_commandes_%s_%s.xlsx' % (mode, datetime.date.today().strftime('%Y-%m-%d'))
    wb.save(out)
    print('\nrésultat :')
    for lid in avant:
        a, b = avant[lid], apres[lid]
        print('  %-9s %-40s cdé %8.3f livré %8.3f fact %8.3f reste %8.2f  ligne=%-10s commande=%s' % (
            cde(a), art(a)[:40], b['product_uom_qty'], b['qty_delivered'], b['qty_invoiced'], b['untaxed_amount_to_invoice'], b['invoice_status'], st.get(cde(a))))
    print('erreurs :', err)
    print('fichier :', out)
