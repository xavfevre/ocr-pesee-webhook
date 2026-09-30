# -*- coding: utf-8 -*-
"""Lecture seule : les paiements manuels de CARRIERE D'HAIMS comptabilisés directement sur les comptes 512 (sans ligne
de banque) — factures réglées, et ligne(s) de relevé candidates (même montant, date proche) avec leur état de lettrage."""
import os, ssl, sys, xmlrpc.client
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [4, 1, 2, 3, 13]}))
pays = x('account.payment', 'search_read', [['company_id', '=', 4], ['journal_id', 'in', [48, 75]], ['state', 'in', ['posted', 'paid', 'in_process']]],
         fields=['name', 'date', 'amount', 'payment_type', 'partner_id', 'journal_id', 'reconciled_invoice_ids', 'is_reconciled', 'is_matched', 'move_id', 'memo', 'state'], order='journal_id, date')
print('%d paiements sur les journaux BNP / BP' % len(pays))
resume = {'bnp': [0, 0.0], 'bp': [0, 0.0]}
for pm in pays:
    if pm['is_matched']:
        continue   # déjà rapproché avec une ligne de banque
    jn = 'bnp' if pm['journal_id'][0] == 48 else 'bp'
    resume[jn][0] += 1; resume[jn][1] += pm['amount']
    inv = x('account.move', 'read', pm['reconciled_invoice_ids'], ['name', 'amount_total', 'payment_state', 'invoice_date', 'amount_residual']) if pm['reconciled_invoice_ids'] else []
    signe = 1 if pm['payment_type'] == 'inbound' else -1
    d0 = datetime.strptime(pm['date'], '%Y-%m-%d')
    cands = x('account.bank.statement.line', 'search_read', [['journal_id', '=', pm['journal_id'][0]], ['amount', '=', signe * pm['amount']]], fields=['date', 'payment_ref', 'is_reconciled', 'partner_id'], order='date')
    cands = [q for q in cands if abs((datetime.strptime(q['date'], '%Y-%m-%d') - d0).days) <= 45]
    print('-' * 110)
    print('%s %-18s %s %9.2f %-8s %-28s factures %s' % (jn.upper(), pm['name'], pm['date'], pm['amount'], pm['payment_type'], (pm['partner_id'] or ['', '-'])[1][:28],
          [(i['name'], i['payment_state'], i['amount_total']) for i in inv]))
    if not cands:
        print('      aucune ligne de relevé de ce montant à ±45 jours')
    for q in cands:
        print('      ligne %5s %s %9.2f %-48s %s %s' % (q['id'], q['date'], q['amount'] * signe, (q['payment_ref'] or '')[:48], 'LETTRÉE' if q['is_reconciled'] else 'non lettrée', (q['partner_id'] or ['', ''])[1][:20]))
print('=' * 110)
print('non rapprochés : BNP %d paiements %.2f | BP %d paiements %.2f' % (resume['bnp'][0], resume['bnp'][1], resume['bp'][0], resume['bp'][1]))
