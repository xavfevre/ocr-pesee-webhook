# -*- coding: utf-8 -*-
"""2113 / 2114 contre la prod : fournisseur de test + prix sur les Defender, mini/maxi sur les pointures 42 et 43,
demandes de prix générées puis tout supprimé (demandes de prix brouillon, ligne fournisseur, règles, fournisseur archivé)."""
import os, ssl, sys, importlib.util, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)


def call(mo, me, *a, **k):
    try:
        return m.execute_kw(D, uid, p, mo, me, list(a), k)
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in str(e):
            return None   # méthode Odoo qui renvoie None (button_cancel…)
        raise


sys.path.insert(0, 'ocr')
spec = importlib.util.spec_from_file_location('wa', 'ocr/web_actions.py'); wa = importlib.util.module_from_spec(spec); spec.loader.exec_module(wa)
K = call('ir.config_parameter', 'get_param', 'maquignon.epi_key')
v42 = call('product.product', 'search', [['product_tmpl_id', '=', 2989], ['product_template_attribute_value_ids.name', '=', '42']])[0]
v43 = call('product.product', 'search', [['product_tmpl_id', '=', 2989], ['product_template_attribute_value_ids.name', '=', '43']])[0]
ex = call('res.partner', 'search', [['name', '=', 'FOURNISSEUR EPI TEST (à archiver)']], context={'active_test': False})
if ex:
    fid = ex[0]
else:
    fid = call('res.partner', 'create', [{'name': 'FOURNISSEUR EPI TEST (à archiver)', 'is_company': True, 'supplier_rank': 1}])
    fid = fid[0] if isinstance(fid, list) else fid
call('res.partner', 'write', [fid], {'active': True})
si = call('product.supplierinfo', 'create', [{'partner_id': fid, 'product_tmpl_id': 2989, 'price': 59.9, 'min_qty': 1, 'delay': 7, 'product_code': 'DEF-LOCK'}])
si = si[0] if isinstance(si, list) else si
print('fournisseur test', fid, '| ligne fournisseur', si)


def essai(lab, fn):
    try:
        r = fn(); print('OK ', lab, '->', r); return r
    except wa.WebErreur as e:
        print('REF', lab, '->', str(e)[:140])


try:
    essai('mini 2 / maxi 4 sur la 42', lambda: wa.executer(call, 2113, {'epi_k': K, 'product': v42, 'mini': '2', 'maxi': '4'}))
    essai('mini 1 sans maxi sur la 43', lambda: wa.executer(call, 2113, {'epi_k': K, 'product': v43, 'mini': '1', 'maxi': ''}))
    essai('mini -1 refusé', lambda: wa.executer(call, 2113, {'epi_k': K, 'product': v42, 'mini': '-1', 'maxi': ''}))
    essai('aperçu demandes de prix', lambda: wa.executer(call, 2114, {'epi_k': K, 'apercu': 1}))
    r = essai('création demandes de prix', lambda: wa.executer(call, 2114, {'epi_k': K}))
    essai('2e passage (mise à jour, pas de doublon)', lambda: wa.executer(call, 2114, {'epi_k': K}))
    for cde in (r or {}).get('commandes', []):
        po = call('purchase.order', 'read', [cde['id']], fields=['name', 'partner_id', 'state', 'origin', 'picking_type_id', 'amount_total', 'order_line'])[0]
        print('   ', po['name'], po['partner_id'][1], po['state'], po['origin'], po['picking_type_id'][1], po['amount_total'],
              [(l['product_id'][1][-6:], l['product_qty'], l['price_unit'], l['name'][:30]) for l in call('purchase.order.line', 'read', po['order_line'], fields=['product_id', 'product_qty', 'price_unit', 'name'])])
    print('règles :', [(o['product_id'][1][-6:], o['product_min_qty'], o['product_max_qty'], o['trigger'], o['location_id'][1]) for o in call('stock.warehouse.orderpoint', 'search_read', [['product_id', 'in', [v42, v43]]], fields=['product_id', 'product_min_qty', 'product_max_qty', 'trigger', 'location_id'])])
    essai('mini 0 -> règle supprimée (42)', lambda: wa.executer(call, 2113, {'epi_k': K, 'product': v42, 'mini': '0', 'maxi': '0'}))
finally:
    pos = call('purchase.order', 'search', [['origin', '=', 'EPI stock mini'], ['partner_id', '=', fid], ['state', 'in', ['draft', 'sent', 'cancel']]])
    if pos:
        call('purchase.order', 'button_cancel', pos); call('purchase.order', 'unlink', pos)
    ops = call('stock.warehouse.orderpoint', 'search', [['product_id', 'in', [v42, v43]]])
    if ops:
        call('stock.warehouse.orderpoint', 'unlink', ops)
    sis = call('product.supplierinfo', 'search', [['partner_id', '=', fid]])
    if sis:
        call('product.supplierinfo', 'unlink', sis)
    call('res.partner', 'write', [fid], {'active': False})
    print('nettoyage : demandes', pos, '| règles', ops, '| ligne fournisseur supprimée | fournisseur test archivé')
