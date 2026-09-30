# -*- coding: utf-8 -*-
"""Lecture seule : par banque synchronisée, retard de la synchro (dernière ligne vs dernière synchro), lignes des 10 derniers
jours, écart relevés / solde en ligne, ligne d'ouverture."""
import os, ssl, sys, xmlrpc.client
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [1, 2, 3, 4, 13]}))
online = {}
for a in x('account.online.account', 'search_read', [['journal_ids', '!=', False]], fields=['balance', 'last_sync', 'journal_ids', 'account_online_link_id']):
    for j in a['journal_ids']:
        online[j] = (a['balance'], a['last_sync'], a['account_online_link_id'] and a['account_online_link_id'][1])
for comp, nom in ((1, 'SARL MAQUIGNON'), (3, "CHATEL'GRANULATS"), (4, "CARRIERE D'HAIMS")):
    print('=' * 100); print(nom)
    for j in x('account.journal', 'search_read', [['company_id', '=', comp], ['type', '=', 'bank']], fields=['name', 'current_statement_balance'], order='id'):
        if j['id'] not in online:
            continue
        bal, sync, lien = online[j['id']]
        last = x('account.bank.statement.line', 'search_read', [['journal_id', '=', j['id']]], fields=['date', 'amount', 'payment_ref', 'create_date'], order='date desc, id desc', limit=1)
        n10 = x('account.bank.statement.line', 'search_count', [['journal_id', '=', j['id']], ['date', '>=', (datetime.utcnow() - timedelta(days=10)).strftime('%Y-%m-%d')]])
        ouv = x('account.bank.statement.line', 'search_read', [['journal_id', '=', j['id']], ['payment_ref', 'ilike', 'ouverture']], fields=['date', 'amount'], limit=1)
        print('  %-22s relevés %11.2f | banque %11.2f au %s | écart %+10.2f | dernière ligne %s (importée %s) | lignes 10 j : %2d | ouverture %s %s | lien %s' % (
            j['name'][:22], j['current_statement_balance'], bal, sync, bal - j['current_statement_balance'], last and last[0]['date'], last and last[0]['create_date'][:10], n10,
            ouv and ouv[0]['date'], ouv and ouv[0]['amount'], (lien or '')[:22]))
