# -*- coding: utf-8 -*-
"""Lecture seule : banques de CARRIERE D'HAIMS (société 4). Soldes Odoo (lignes de relevé) aux dates des relevés papier
(BNP 30/04/2025 = 28 057,09 ; BP 23/04/2025 = 81 405,58, 30/04/2025 = 88 827,31), solde en ligne de la synchro,
lignes manuelles (sans identifiant de synchro), doublons, montants candidats pour l'écart, sommes mensuelles."""
import os, ssl, sys, re, xmlrpc.client
from collections import defaultdict, Counter
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [4, 1, 2, 3, 13]}))
REF = {'BNP': {'2025-04-30': 28057.09}, 'BP': {'2025-04-23': 81405.58, '2025-04-30': 88827.31}}
jns = x('account.journal', 'search_read', [['company_id', '=', 4], ['type', '=', 'bank']], fields=['name', 'code', 'bank_account_id', 'current_statement_balance', 'kanban_dashboard'])
for j in jns:
    print('=' * 100)
    print('Journal %s (%s) id %s | solde relevés (current_statement_balance) %s' % (j['name'], j['code'], j['id'], j['current_statement_balance']))
    kd = j['kanban_dashboard'] or ''
    for k in ('account_balance', 'nb_lines_bank_account_balance', 'outstanding_pay_account_balance', 'has_at_least_one_statement', 'bank_statements_source', 'last_balance'):
        mt = re.search(r'"%s": ?("[^"]*"|[^,}]*)' % k, kd)
        if mt:
            print('   tableau de bord %s = %s' % (k, mt.group(1)))
    cle = 'BNP' if 'BNP' in j['name'].upper() or 'BNP' in (j['code'] or '').upper() else 'BP'
    lines = x('account.bank.statement.line', 'search_read', [['journal_id', '=', j['id']]],
              fields=['date', 'amount', 'payment_ref', 'online_transaction_identifier', 'statement_id', 'is_reconciled', 'partner_id', 'create_date', 'create_uid', 'move_id'], order='date, id')
    print('   %d lignes de relevé, du %s au %s' % (len(lines), lines and lines[0]['date'], lines and lines[-1]['date']))
    manuelles = [l for l in lines if not l['online_transaction_identifier']]
    print('   lignes SANS identifiant de synchro (manuelles) : %d' % len(manuelles))
    for l in manuelles[:25]:
        print('      %s %12.2f  %-50s créée le %s par %s' % (l['date'], l['amount'], (l['payment_ref'] or '')[:50], l['create_date'][:10], (l['create_uid'] or ['', ''])[1][:18]))
    solde = 0.0; par_date = {}; par_mois = defaultdict(lambda: [0.0, 0])
    for l in lines:
        solde += l['amount']; par_date[l['date']] = solde
        par_mois[l['date'][:7]][0] += l['amount']; par_mois[l['date'][:7]][1] += 1
    def solde_au(d):
        ds = [k for k in par_date if k <= d]
        return par_date[max(ds)] if ds else 0.0
    for d, ref in sorted(REF[cle].items()):
        s = solde_au(d)
        print('   solde Odoo au %s = %12.2f | relevé papier %12.2f | écart %+.2f' % (d, s, ref, s - ref))
    print('   solde Odoo final (toutes lignes) = %.2f' % solde)
    # doublons : même date, même montant, libellé proche
    grp = defaultdict(list)
    for l in lines:
        grp[(l['date'], round(l['amount'], 2), re.sub(r'\W+', '', (l['payment_ref'] or '').lower())[:25])].append(l)
    dbl = [v for v in grp.values() if len(v) > 1]
    print('   doublons potentiels (même date, montant, libellé) : %d groupes' % len(dbl))
    for v in dbl[:15]:
        print('      %s %12.2f ×%d  %-45s ids %s  synchro %s' % (v[0]['date'], v[0]['amount'], len(v), (v[0]['payment_ref'] or '')[:45], [l['id'] for l in v], [bool(l['online_transaction_identifier']) for l in v]))
    print('   sommes mensuelles (mois : total, nb lignes, solde fin de mois) :')
    cumul = 0.0
    for mo in sorted(par_mois):
        cumul += par_mois[mo][0]
        print('      %s  %12.2f  %4d  -> %12.2f' % (mo, par_mois[mo][0], par_mois[mo][1], cumul))
oa = x('account.online.account', 'search_read', [], fields=['name', 'balance', 'last_sync', 'journal_ids', 'account_online_link_id', 'company_id'])
print('=' * 100)
print('Comptes bancaires en ligne (synchro) :')
for a in oa:
    print('   %-40s solde %12s | dernière synchro %s | journaux %s | société %s' % (a['name'][:40], a['balance'], a['last_sync'], a['journal_ids'], a['company_id'] and a['company_id'][1]))
