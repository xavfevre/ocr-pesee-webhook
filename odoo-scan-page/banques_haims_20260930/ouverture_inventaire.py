# -*- coding: utf-8 -*-
"""Lecture seule : soldes d'ouverture des banques synchronisées (Maquignon 1, Chatel 3, Haims 4) : première ligne de relevé,
ligne « Déclaration d'ouverture » éventuelle et son compte de contrepartie, somme des relevés, OD « Solde initial banque »
sur le compte du journal, solde comptable, solde en ligne de la banque."""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [1, 2, 3, 4, 13], 'active_test': False}))
online = {}
for a in x('account.online.account', 'search_read', [['journal_ids', '!=', False]], fields=['balance', 'last_sync', 'journal_ids']):
    for j in a['journal_ids']:
        online[j] = (a['balance'], a['last_sync'])
for comp, nom in ((1, 'SARL MAQUIGNON'), (3, "CHATEL'GRANULATS"), (4, "CARRIERE D'HAIMS")):
    print('=' * 112); print(nom)
    for j in x('account.journal', 'search_read', [['company_id', '=', comp], ['type', '=', 'bank']], fields=['name', 'code', 'default_account_id'], order='id'):
        st = x('account.bank.statement.line', 'search_read', [['journal_id', '=', j['id']]], fields=['date', 'amount', 'payment_ref', 'move_id', 'is_reconciled'], order='date, id')
        if not st:
            continue
        ouv = [l for l in st if 'ouverture' in (l['payment_ref'] or '').lower()]
        tot = sum(l['amount'] for l in st)
        # comptes des lignes de banque des relevés du journal
        accs = {}
        for g in x('account.move.line', 'read_group', [['statement_line_id.journal_id', '=', j['id']], ['account_id.code', '=like', '512%'], ['parent_state', '=', 'posted']], ['balance:sum'], ['account_id']):
            accs[g['account_id'][1][:28]] = round(g['balance'], 2)
        od = x('account.move.line', 'search_read', [['account_id', '=', j['default_account_id'][0]], ['statement_line_id', '=', False], ['payment_id', '=', False], ['parent_state', '=', 'posted']], fields=['move_id', 'date', 'balance', 'name'])
        gl = x('account.move.line', 'read_group', [['account_id', '=', j['default_account_id'][0]], ['parent_state', '=', 'posted']], ['balance:sum'], [])
        ob = online.get(j['id'])
        print('  %-22s %-5s compte %-30s | 1re ligne %s | lignes %4d | relevés %12.2f | GL compte %12.2f | banque en ligne %s' % (
            j['name'][:22], j['code'], j['default_account_id'][1][:30], st[0]['date'], len(st), tot, (gl[0]['balance'] or 0) if gl else 0, ob and ('%.2f au %s' % (ob[0], ob[1])) or '-'))
        if len(accs) > 1:
            print('      relevés répartis sur plusieurs comptes :', accs)
        for l in ouv:
            cp = x('account.move.line', 'search_read', [['move_id', '=', l['move_id'][0]], ['account_id.code', 'not like', '512%']], fields=['account_id', 'reconciled'])
            print('      ouverture : %s %12.2f  « %s »  contrepartie %s  lettrée %s' % (l['date'], l['amount'], (l['payment_ref'] or '')[:40], [q['account_id'][1][:30] for q in cp], l['is_reconciled']))
        for o in od:
            print('      OD sur le compte : %s %-20s %12.2f  %s' % (o['date'], o['move_id'][1][:20], o['balance'], (o['name'] or '')[:30]))
