# -*- coding: utf-8 -*-
"""Lecture seule : écritures sur les comptes bancaires 512 de CARRIERE D'HAIMS qui ne viennent ni des lignes de relevé
ni des paiements (OD, reprises, extournes) : détail, lettrage, contreparties, et solde 512 recalculé sans elles."""
import os, ssl, sys, xmlrpc.client
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [4, 1, 2, 3, 13]}))
jns = {j['id']: j for j in x('account.journal', 'search_read', [['company_id', '=', 4]], fields=['name', 'code', 'type', 'default_account_id'])}
comptes = x('account.account', 'search_read', [['company_ids', 'in', [4]], ['code', '=like', '512%']], fields=['code', 'name'])
print('Comptes 512 de Haims :', [(a['code'], a['name'][:30]) for a in comptes])
for a in comptes:
    amls = x('account.move.line', 'search_read', [['account_id', '=', a['id']], ['company_id', '=', 4], ['parent_state', '!=', 'cancel']],
             fields=['move_id', 'date', 'debit', 'credit', 'balance', 'journal_id', 'statement_line_id', 'payment_id', 'reconciled', 'name', 'ref', 'parent_state', 'full_reconcile_id', 'matched_debit_ids', 'matched_credit_ids'], order='date, id')
    if not amls:
        continue
    print('=' * 110)
    print('Compte %s %s : %d lignes, solde %.2f' % (a['code'], a['name'][:40], len(amls), sum(l['balance'] for l in amls)))
    par = defaultdict(lambda: [0.0, 0])
    for l in amls:
        typ = 'relevé' if l['statement_line_id'] else ('paiement' if l['payment_id'] else 'autre (%s)' % jns.get(l['journal_id'][0], {}).get('code', l['journal_id'][1]))
        par[typ][0] += l['balance']; par[typ][1] += 1
    for k, v in sorted(par.items()):
        print('   %-28s %12.2f  (%d lignes)' % (k, v[0], v[1]))
    autres = [l for l in amls if not l['statement_line_id'] and not l['payment_id']]
    if autres:
        print('   --- écritures « autres » (OD…) :')
        mids = sorted({l['move_id'][0] for l in autres})
        mv = {q['id']: q for q in x('account.move', 'read', mids, ['name', 'date', 'ref', 'state', 'journal_id', 'reversed_entry_id', 'reversal_move_ids', 'line_ids', 'amount_total'])}
        tot = 0.0
        for l in autres:
            q = mv[l['move_id'][0]]
            cps = x('account.move.line', 'search_read', [['move_id', '=', q['id']], ['id', '!=', l['id']]], fields=['account_id', 'balance'])
            cp = ', '.join('%s %.2f' % (c_['account_id'][1][:28], c_['balance']) for c_ in cps[:3])
            tot += l['balance']
            print('   %s %-20s %-6s %10.2f  %-28s état %-7s lettrée %-5s extourne de %s | contreparties : %s' % (
                l['date'], q['name'], jns.get(q['journal_id'][0], {}).get('code', '?'), l['balance'], (l['name'] or q['ref'] or '')[:28], q['state'], l['reconciled'],
                q['reversed_entry_id'] and q['reversed_entry_id'][1] or '-', cp))
        print('   total « autres » sur ce compte : %.2f -> solde 512 sans elles : %.2f' % (tot, sum(l['balance'] for l in amls) - tot))
    pays = [l for l in amls if l['payment_id']]
    if pays:
        print('   --- paiements directement sur le 512 : %d lignes, %.2f' % (len(pays), sum(l['balance'] for l in pays)))
        for l in pays[:25]:
            print('      %s %-20s %10.2f %-40s lettrée %s' % (l['date'], l['move_id'][1][:20], l['balance'], (l['name'] or '')[:40], l['reconciled']))
