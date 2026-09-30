# -*- coding: utf-8 -*-
"""Lecture seule : tous les paiements de CARRIERE D'HAIMS dont l'écriture touche directement un compte 512 (sans ligne de
banque) + les paiements non rapprochés : factures réglées, lignes de relevé candidates (même montant, ±60 j) et leur lettrage."""
import os, ssl, sys, xmlrpc.client
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [4, 1, 2, 3, 13]}))
acc512 = x('account.account', 'search', [['company_ids', 'in', [4]], ['code', 'in', ['51210000', '51200002']]])
amls = x('account.move.line', 'search_read', [['account_id', 'in', acc512], ['payment_id', '!=', False], ['parent_state', '=', 'posted']], fields=['payment_id', 'balance', 'date'])
pids = sorted({l['payment_id'][0] for l in amls})
autres = x('account.payment', 'search', [['company_id', '=', 4], ['journal_id', 'in', [48, 75]], ['is_matched', '=', False], ['state', 'in', ['posted', 'paid', 'in_process']]])
pids = sorted(set(pids) | set(autres))
pays = x('account.payment', 'read', pids, ['name', 'date', 'amount', 'payment_type', 'partner_id', 'journal_id', 'reconciled_invoice_ids', 'is_matched', 'is_reconciled', 'memo', 'state', 'payment_method_line_id'])
pays.sort(key=lambda q: (q['journal_id'][0], q['date']))
print('%d paiements (%d directement sur 512, %d non rapprochés)' % (len(pays), len({l['payment_id'][0] for l in amls}), len(autres)))
tot = {}
for pm in pays:
    jn = 'BNP' if pm['journal_id'][0] == 48 else 'BP'
    tot.setdefault(jn, [0, 0.0]); tot[jn][0] += 1; tot[jn][1] += pm['amount']
    inv = x('account.move', 'read', pm['reconciled_invoice_ids'], ['name', 'amount_total', 'payment_state', 'invoice_date']) if pm['reconciled_invoice_ids'] else []
    signe = 1 if pm['payment_type'] == 'inbound' else -1
    d0 = datetime.strptime(pm['date'], '%Y-%m-%d')
    cands = x('account.bank.statement.line', 'search_read', [['journal_id', 'in', [48, 75]], ['amount', '=', signe * pm['amount']]], fields=['date', 'amount', 'payment_ref', 'is_reconciled', 'partner_id', 'journal_id'], order='date')
    cands = [q for q in cands if abs((datetime.strptime(q['date'], '%Y-%m-%d') - d0).days) <= 60]
    print('-' * 112)
    print('%-3s %-18s %s %9.2f %-8s %-26s sur512=%-5s factures %s' % (jn, pm['name'], pm['date'], pm['amount'], pm['payment_type'], (pm['partner_id'] or ['', '-'])[1][:26], pm['id'] in {l['payment_id'][0] for l in amls},
          [(i['name'], i['payment_state'], i['amount_total']) for i in inv] or pm['memo']))
    if not cands:
        print('      aucune ligne de relevé de ce montant à ±60 jours (BNP ou BP)')
    for q in cands:
        print('      ligne %5s %-3s %s %9.2f %-46s %s %s' % (q['id'], 'BNP' if q['journal_id'][0] == 48 else 'BP', q['date'], q['amount'] * signe, (q['payment_ref'] or '')[:46], 'LETTRÉE' if q['is_reconciled'] else 'non lettrée', (q['partner_id'] or ['', ''])[1][:18]))
print('=' * 112)
print('totaux :', tot)
