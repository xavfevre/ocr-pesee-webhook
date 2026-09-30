# -*- coding: utf-8 -*-
"""Lecture seule : origine des paiements manuels de Haims (dates et auteur de création, libellé, lot), et pour chaque facture
réglée : existe-t-il aussi une ligne de relevé lettrée avec elle (double règlement) ?"""
import os, ssl, sys, xmlrpc.client
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [4, 1, 2, 3, 13]}))
pays = x('account.payment', 'search_read', [['company_id', '=', 4], ['journal_id', 'in', [48, 75]], ['state', '!=', 'cancel']],
         fields=['name', 'date', 'amount', 'partner_id', 'journal_id', 'reconciled_invoice_ids', 'memo', 'create_date', 'create_uid', 'write_date', 'is_matched', 'payment_method_line_id', 'state'], order='create_date')
print('%d paiements sur BNP/BP ; lots de création (jour heure, auteur) :' % len(pays))
for k, v in sorted(Counter((q['create_date'][:13], (q['create_uid'] or ['', '?'])[1][:20]) for q in pays).items()):
    print('   %s  %-20s %d paiements' % (k[0], k[1], v))
print()
for q in pays:
    inv = x('account.move', 'read', q['reconciled_invoice_ids'], ['name', 'payment_state', 'amount_total', 'amount_residual']) if q['reconciled_invoice_ids'] else []
    # lignes de relevé déjà lettrées avec la même facture ?
    doubles = []
    for i in inv:
        recv = x('account.move.line', 'search_read', [['move_id', '=', i['id']], ['account_id.account_type', '=', 'asset_receivable']], fields=['matched_credit_ids', 'matched_debit_ids'])
        pr_ids = [pid for l in recv for pid in (l['matched_credit_ids'] + l['matched_debit_ids'])]
        if pr_ids:
            prs = x('account.partial.reconcile', 'read', pr_ids, ['credit_move_id', 'debit_move_id', 'amount'])
            for pr in prs:
                for side in ('credit_move_id', 'debit_move_id'):
                    aml = x('account.move.line', 'read', [pr[side][0]], ['move_id', 'statement_line_id', 'payment_id'])[0]
                    if aml['statement_line_id']:
                        doubles.append((aml['move_id'][1][:18], pr['amount']))
    print('%-18s %s %9.2f %-24s créé %s par %-18s %-32s factures %s%s' % (q['name'], q['date'], q['amount'], (q['partner_id'] or ['', '-'])[1][:24], q['create_date'][:16], (q['create_uid'] or ['', '?'])[1][:18], (q['memo'] or '')[:32],
          [(i['name'], i['payment_state']) for i in inv], ('  | AUSSI lettrée avec relevé %s' % doubles) if doubles else ''))
