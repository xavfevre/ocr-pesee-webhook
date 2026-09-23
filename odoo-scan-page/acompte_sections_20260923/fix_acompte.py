# -*- coding: utf-8 -*-
"""Acompte remis à 0 sur la commande après validation de la facture d'acompte (S12398, S11946, S11805, S12002).
Cause : l'automatisation 84 « Facture depuis commande : reprendre les sections imbriquées » insère dans la facture
d'ACOMPTE une section « Acomptes » reliée à la ligne de section de la commande. À la validation, Odoo recalcule le prix
de la ligne d'acompte de la commande = somme des lignes d'acompte des factures validées HORS « vraies » factures
(= factures reliées à d'autres lignes de la commande) ; la facture d'acompte, reliée à la section, est prise pour une
vraie facture -> prix 0 -> la facture finale déduit 0.
Correctif : l'automatisation ignore les lignes d'acompte (pas de section « Acomptes » insérée).
Réparation : prix des lignes d'acompte des 4 commandes = montant de la facture d'acompte ; section « Acomptes » des
4 factures d'acompte déliée de la commande.
  test : patch sur la base de test + scénario complet (acompte, validation, facture finale)
  prod : patch + réparation + contrôle"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'test').lower()
U, D = ('https://testmaq230926.odoo.com', 'testmaq230926') if mode == 'test' else ('https://maquignon.odoo.com', 'maquignon')
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)


def x(mo, me, *a, **k):
    k['context'] = dict({'allowed_company_ids': [1, 2, 3, 4, 13]}, **k.get('context', {}))
    return m.execute_kw(D, uid, p, mo, me, list(a), k)


def sur(fn):
    try:
        return fn()
    except xmlrpc.client.Fault as e:
        s = str(e)
        if 'cannot marshal None' in s:
            return None
        print('   ERREUR :', s.strip().split('\n')[-1][:250]); return 'ERR'


# ---- 1. patch de l'automatisation 84
auto = x('base.automation', 'search_read', [['name', '=', 'Facture depuis commande : reprendre les sections imbriquées']], fields=['action_server_ids'])
assert len(auto) == 1, auto
act = auto[0]['action_server_ids']
code = x('ir.actions.server', 'read', act, fields=['code'])[0]['code']
OLD = "        sol = il.sale_line_ids[0]\n        if sol.id not in index_by_id:\n            continue\n"
NEW = "        sol = il.sale_line_ids[0]\n        if sol.is_downpayment:\n            continue\n        if sol.id not in index_by_id:\n            continue\n"
if NEW in code:
    print('automatisation 84 : déjà patchée')
else:
    assert code.count(OLD) == 1, 'bloc introuvable'
    x('ir.actions.server', 'write', act, {'code': code.replace(OLD, NEW)})
    print('automatisation 84 patchée (lignes d\'acompte ignorées)')


def lignes_acompte(oid):
    return x('sale.order.line', 'search_read', [['order_id', '=', oid], ['is_downpayment', '=', True], ['display_type', '=', False]], fields=['name', 'price_unit', 'qty_invoiced', 'invoice_lines'])


if mode == 'test':
    o = x('sale.order', 'search_read', [['company_id', '=', 1], ['state', '=', 'sale'], ['invoice_ids', '=', False], ['amount_untaxed', '>', 100], ['invoice_status', '=', 'to invoice']], fields=['name', 'amount_untaxed'], order='id desc', limit=1)[0]
    print('== scénario sur', o['name'], 'HT %.2f' % o['amount_untaxed'])
    wctx = {'active_model': 'sale.order', 'active_ids': [o['id']], 'active_id': o['id']}
    wiz = x('sale.advance.payment.inv', 'create', [{'advance_payment_method': 'fixed', 'fixed_amount': 50.0, 'sale_order_ids': [[6, 0, [o['id']]]]}], context=wctx)
    wiz = wiz[0] if isinstance(wiz, list) else wiz
    sur(lambda: x('sale.advance.payment.inv', 'create_invoices', [wiz], context=wctx))
    dep = x('account.move', 'search_read', [['invoice_origin', '=', o['name']], ['state', '=', 'draft']], fields=['name', 'amount_untaxed', 'invoice_line_ids'])[0]
    print('   facture d\'acompte brouillon : lignes', [(l['display_type'], (l['name'] or '')[:15], l['sale_line_ids']) for l in x('account.move.line', 'read', dep['invoice_line_ids'], fields=['display_type', 'name', 'sale_line_ids'])])
    sur(lambda: x('account.move', 'action_post', [dep['id']]))
    print('   après validation : lignes acompte SO', [(l['id'], round(l['price_unit'], 2), l['qty_invoiced']) for l in lignes_acompte(o['id'])])
    wiz2 = x('sale.advance.payment.inv', 'create', [{'advance_payment_method': 'delivered', 'deduct_down_payments': True, 'sale_order_ids': [[6, 0, [o['id']]]]}], context=wctx)
    wiz2 = wiz2[0] if isinstance(wiz2, list) else wiz2
    sur(lambda: x('sale.advance.payment.inv', 'create_invoices', [wiz2], context=wctx))
    fin = x('account.move', 'search_read', [['invoice_origin', '=', o['name']], ['state', '=', 'draft']], fields=['name', 'amount_untaxed', 'invoice_line_ids'])[0]
    print('   facture finale brouillon HT %.2f | lignes : %s' % (fin['amount_untaxed'], [(l['display_type'], (l['name'] or '')[:22], l['quantity'], round(l['price_unit'], 2)) for l in x('account.move.line', 'read', fin['invoice_line_ids'], fields=['display_type', 'name', 'quantity', 'price_unit'])]))
    sys.exit(0)

# ---- 2. réparation en production
for name in ('S12398', 'S11946', 'S11805', 'S12002'):
    o = x('sale.order', 'search_read', [['name', '=', name]], fields=['name', 'invoice_ids', 'company_id'])[0]
    for l in lignes_acompte(o['id']):
        il = x('account.move.line', 'read', l['invoice_lines'], fields=['price_unit', 'parent_state', 'move_id', 'quantity'])
        total = round(sum(i['price_unit'] * (1 if i['quantity'] >= 0 else -1) for i in il if i['parent_state'] == 'posted'), 2)
        if abs(l['price_unit'] - total) > 0.005:
            x('sale.order.line', 'write', [l['id']], {'price_unit': total})
        print('   %s ligne %s : prix %.2f -> %.2f' % (name, l['id'], l['price_unit'], total))
    # sections « Acomptes » des factures d'acompte reliées à la commande : on délie
    for v in x('account.move', 'read', o['invoice_ids'], fields=['name', 'invoice_line_ids', 'state']):
        secs = [s for s in x('account.move.line', 'read', v['invoice_line_ids'], fields=['display_type', 'name', 'sale_line_ids']) if s['display_type'] == 'line_section' and s['sale_line_ids'] and 'compte' in (s['name'] or '').lower()]
        if secs:
            x('account.move.line', 'write', [s['id'] for s in secs], {'sale_line_ids': [[5]]})
            print('   %s : section « %s » déliée de la commande' % (v['name'], secs[0]['name']))
    print('   contrôle', name, [(l['id'], l['price_unit'], l['qty_invoiced']) for l in lignes_acompte(o['id'])])
