# -*- coding: utf-8 -*-
"""Base de test : pourquoi la ligne d'acompte de la commande a un prix 0 depuis septembre ?
 A. assistant acompte (montant fixe 50) sur une commande confirmée sans facture -> prix de la ligne d'acompte SO
    avant validation, puis après validation de la facture d'acompte ; puis facture finale -> montant déduit
 B. même chose avec les automatisations sale.order.line (on_create_or_write) désactivées
 C. remise des automatisations"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://testmaq230926.odoo.com', 'testmaq230926'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
common = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c)
print('version :', common.version())
uid = common.authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)


def x(mo, me, *a, **k):
    k['context'] = dict({'allowed_company_ids': [1]}, **k.get('context', {}))
    return m.execute_kw(D, uid, p, mo, me, list(a), k)


def sur(fn):
    try:
        return fn()
    except xmlrpc.client.Fault as e:
        s = str(e)
        if 'cannot marshal None' in s:
            return None
        print('   ERREUR :', s.strip().split('\n')[-1][:250]); return 'ERR'


def lignes_acompte(oid, lab):
    ls = x('sale.order.line', 'search_read', [['order_id', '=', oid], ['is_downpayment', '=', True], ['display_type', '=', False]], fields=['name', 'price_unit', 'qty_invoiced', 'product_id', 'product_uom_id', 'tax_ids', 'write_date', 'write_uid'])
    print('   [%s] lignes acompte SO : %s' % (lab, [(l['id'], round(l['price_unit'], 2), l['qty_invoiced'], l['product_id'] and l['product_id'][1], l['product_uom_id'] and l['product_uom_id'][1], l['tax_ids'], l['write_uid'][1][:8]) for l in ls]))
    return ls


def scenario(lab, exclude):
    o = x('sale.order', 'search_read', [['company_id', '=', 1], ['state', '=', 'sale'], ['invoice_ids', '=', False], ['amount_untaxed', '>', 100], ['id', 'not in', exclude]], fields=['name', 'amount_untaxed', 'amount_total', 'order_line'], order='id desc', limit=1)[0]
    print('== %s : commande %s HT %.2f' % (lab, o['name'], o['amount_untaxed']))
    wctx = {'active_model': 'sale.order', 'active_ids': [o['id']], 'active_id': o['id']}
    wiz = x('sale.advance.payment.inv', 'create', [{'advance_payment_method': 'fixed', 'fixed_amount': 50.0, 'sale_order_ids': [[6, 0, [o['id']]]]}], context=wctx)
    wiz = wiz[0] if isinstance(wiz, list) else wiz
    sur(lambda: x('sale.advance.payment.inv', 'create_invoices', [wiz], context=wctx))
    ls = lignes_acompte(o['id'], 'après assistant (facture brouillon)')
    inv = x('account.move', 'search_read', [['invoice_origin', '=', o['name']], ['state', '=', 'draft']], fields=['name', 'amount_untaxed', 'invoice_line_ids'])
    for v in inv:
        print('   facture brouillon HT %.2f lignes : %s' % (v['amount_untaxed'], [(l['name'][:20], l['quantity'], l['price_unit'], l['sale_line_ids']) for l in x('account.move.line', 'read', v['invoice_line_ids'], fields=['name', 'quantity', 'price_unit', 'sale_line_ids', 'display_type']) if l['display_type'] == 'product']))
        sur(lambda: x('account.move', 'action_post', [v['id']]))
    lignes_acompte(o['id'], 'après validation de la facture d\'acompte')
    # facture finale
    wiz2 = x('sale.advance.payment.inv', 'create', [{'advance_payment_method': 'delivered', 'deduct_down_payments': True, 'sale_order_ids': [[6, 0, [o['id']]]]}], context=wctx)
    wiz2 = wiz2[0] if isinstance(wiz2, list) else wiz2
    sur(lambda: x('sale.advance.payment.inv', 'create_invoices', [wiz2], context=wctx))
    fin = x('account.move', 'search_read', [['invoice_origin', '=', o['name']], ['state', '=', 'draft']], fields=['name', 'amount_untaxed', 'invoice_line_ids'])
    for v in fin:
        ded = [(l['name'][:25], l['quantity'], l['price_unit'], l['price_subtotal']) for l in x('account.move.line', 'read', v['invoice_line_ids'], fields=['name', 'quantity', 'price_unit', 'price_subtotal', 'display_type']) if l['display_type'] == 'product' and 'compte' in (l['name'] or '').lower()]
        print('   facture finale brouillon HT %.2f | lignes acompte déduites : %s' % (v['amount_untaxed'], ded))
    return o['id']


AUTOS = [a['id'] for a in x('base.automation', 'search_read', [['active', '=', True], ['model_id.model', '=', 'sale.order.line'], ['trigger', 'in', ['on_create_or_write', 'on_write', 'on_create']]], fields=['name'])]
print('automatisations sale.order.line serveur :', AUTOS)
o1 = scenario('A. automatisations actives', [])
x('base.automation', 'write', AUTOS, {'active': False})
try:
    o2 = scenario('B. automatisations sale.order.line désactivées', [o1])
finally:
    x('base.automation', 'write', AUTOS, {'active': True})
    print('automatisations réactivées :', [a['active'] for a in x('base.automation', 'read', AUTOS, fields=['active'])])
