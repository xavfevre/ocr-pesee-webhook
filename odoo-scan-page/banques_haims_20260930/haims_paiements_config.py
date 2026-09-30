# -*- coding: utf-8 -*-
"""Lecture seule : configuration des journaux bancaires Haims (comptes d'attente des paiements), comptes 511x disponibles,
détail des doublons Stripe / outil du 02/09/2026, du paiement « Reprise historique Sage », et des factures lettrées
à la fois par un paiement et par une ligne de relevé."""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [4, 1, 2, 3, 13]}))
print('--- journaux et méthodes de paiement')
for j in x('account.journal', 'search_read', [['company_id', '=', 4], ['type', 'in', ['bank', 'cash']]], fields=['name', 'code', 'default_account_id', 'suspense_account_id', 'inbound_payment_method_line_ids', 'outbound_payment_method_line_ids']):
    print('%s (%s) compte %s | suspens %s' % (j['name'], j['code'], j['default_account_id'][1], j['suspense_account_id'][1]))
    for l in x('account.payment.method.line', 'read', j['inbound_payment_method_line_ids'] + j['outbound_payment_method_line_ids'], ['name', 'payment_method_id', 'payment_account_id', 'payment_provider_id']):
        print('    %-22s %-18s compte d attente : %s%s' % (l['name'], l['payment_method_id'][1], l['payment_account_id'] and l['payment_account_id'][1] or 'AUCUN (paiement direct sur 512)', ('  fournisseur ' + l['payment_provider_id'][1]) if l['payment_provider_id'] else ''))
print('--- comptes 511 / 58 de Haims :', [(a['code'], a['name'][:34], 'récon' if a['reconcile'] else '') for a in x('account.account', 'search_read', [['company_ids', 'in', [4]], '|', ['code', '=like', '511%'], ['code', '=like', '58%']], fields=['code', 'name', 'reconcile'])])
print('--- comptes d attente des autres sociétés (exemple SARL MAQUIGNON, journal 6) :')
for l in x('account.payment.method.line', 'search_read', [['journal_id', '=', 6]], fields=['name', 'payment_account_id']):
    print('    %-22s %s' % (l['name'], l['payment_account_id'] and l['payment_account_id'][1]))


def partiels(inv_id):
    out = []
    for l in x('account.move.line', 'search_read', [['move_id', '=', inv_id], ['account_id.account_type', '=', 'asset_receivable']], fields=['matched_credit_ids', 'matched_debit_ids', 'amount_residual']):
        for pid in l['matched_credit_ids'] + l['matched_debit_ids']:
            pr = x('account.partial.reconcile', 'read', [pid], ['credit_move_id', 'debit_move_id', 'amount'])[0]
            for side in ('credit_move_id', 'debit_move_id'):
                aml = x('account.move.line', 'read', [pr[side][0]], ['move_id', 'statement_line_id', 'payment_id', 'account_id'])[0]
                if aml['move_id'][0] != inv_id:
                    out.append('%s %.2f (%s)' % (aml['move_id'][1][:20], pr['amount'], 'relevé' if aml['statement_line_id'] else ('paiement' if aml['payment_id'] else aml['account_id'][1][:15])))
        out.append('reste dû %.2f' % l['amount_residual'])
    return out


print('--- doublons du 02/09/2026 (outil) face aux paiements Stripe :')
for nom_outil, nom_stripe in (('PBNP/25-26/0016', 'PAY00071'), ('PBNP/25-26/0017', 'PAY00088'), ('PBNP/26-27/0005', 'PAY00096'), ('PBNP/26-27/0006', 'PAY00141'), ('PBNP/26-27/0007', 'PAY00280')):
    po = x('account.payment', 'search_read', [['name', '=', nom_outil], ['company_id', '=', 4]], fields=['amount', 'is_matched', 'is_reconciled', 'reconciled_invoice_ids', 'move_id', 'outstanding_account_id', 'journal_id'])[0]
    ps = x('account.payment', 'search_read', [['name', '=', nom_stripe], ['company_id', '=', 4]], fields=['amount', 'is_matched', 'is_reconciled', 'reconciled_invoice_ids', 'outstanding_account_id', 'journal_id'])[0]
    inv = po['reconciled_invoice_ids'] or ps['reconciled_invoice_ids']
    print('  %s (outil : journal %s, compte %s, matched %s, reconciled %s) / %s (Stripe : journal %s, compte %s, matched %s, reconciled %s) -> facture %s' % (
        nom_outil, po['journal_id'][1][:10], po['outstanding_account_id'] and po['outstanding_account_id'][1][:20], po['is_matched'], po['is_reconciled'],
        nom_stripe, ps['journal_id'][1][:10], ps['outstanding_account_id'] and ps['outstanding_account_id'][1][:20], ps['is_matched'], ps['is_reconciled'], partiels(inv[0]) if inv else '-'))
print('--- reprise Sage 801,54 : lignes de relevé 801,54 :', x('account.bank.statement.line', 'search_read', [['amount', '=', 801.54], ['journal_id', 'in', [48, 75]]], fields=['date', 'payment_ref', 'is_reconciled']))
print('--- factures lettrées paiement + relevé :')
for nom in ('PAY00023', 'PAY00025', 'PBNP/25-26/0014', 'PBNP/26-27/0001', 'PAY00128', 'PAY00157'):
    pm = x('account.payment', 'search_read', [['name', '=', nom], ['company_id', '=', 4]], fields=['amount', 'is_matched', 'reconciled_invoice_ids', 'outstanding_account_id'])[0]
    print('  %-16s %9.2f matched %-5s compte %-22s -> %s' % (nom, pm['amount'], pm['is_matched'], pm['outstanding_account_id'] and pm['outstanding_account_id'][1][:22], partiels(pm['reconciled_invoice_ids'][0]) if pm['reconciled_invoice_ids'] else '-'))
