# -*- coding: utf-8 -*-
"""Lecture seule : journal BNP *8837* de SARL MAQUIGNON — écart au 31/08/2026 (relevé 145 406,76 vs Odoo), paires
date+montant identiques (doublons possibles), lots de ré-importation, lignes manuelles, montant 5 530,63 ou combinaisons simples."""
import os, ssl, sys, xmlrpc.client, itertools
from collections import defaultdict
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [1, 2, 3, 4, 13]}))
JID = 6; RELEVE_3108 = 145406.76
lines = x('account.bank.statement.line', 'search_read', [['journal_id', '=', JID]], fields=['date', 'amount', 'payment_ref', 'online_transaction_identifier', 'create_date', 'is_reconciled'], order='date, id')
s = 0.0; par_date = {}
for l in lines:
    s += l['amount']; par_date[l['date']] = s
odoo_3108 = par_date[max(d for d in par_date if d <= '2026-08-31')]
ecart = round(RELEVE_3108 - odoo_3108, 2)
print('Odoo au 31/08/2026 %.2f | relevé %.2f | écart (relevé - Odoo) %+.2f' % (odoo_3108, RELEVE_3108, ecart))
print('lignes manuelles :', [(l['date'], l['amount'], (l['payment_ref'] or '')[:40]) for l in lines if not l['online_transaction_identifier']])
grp = defaultdict(list)
for l in lines:
    grp[(l['date'], round(l['amount'], 2))].append(l)
print('paires même date + même montant (|montant| >= 10) :')
for k, v in sorted(grp.items()):
    if len(v) > 1 and abs(k[1]) >= 10:
        print('   %s %11.2f ×%d  %s' % (k[0], k[1], len(v), ' | '.join('%s:%s:%s' % (l['id'], (l['payment_ref'] or '')[:24], l['create_date'][:10]) for l in v)))
tard = [l for l in lines if l['online_transaction_identifier'] and (datetime.strptime(l['create_date'][:10], '%Y-%m-%d') - datetime.strptime(l['date'], '%Y-%m-%d')).days > 6]
lots = defaultdict(list)
for l in tard:
    lots[l['create_date'][:16]].append(l)
print('lots importés tardivement :', [(k, len(v), min(l['date'] for l in v), max(l['date'] for l in v), round(sum(l['amount'] for l in v), 2)) for k, v in sorted(lots.items())])
cand = [l for l in lines if l['date'] <= '2026-08-31' and abs(abs(l['amount']) - abs(ecart)) < 0.005]
print('lignes de %.2f :' % abs(ecart), [(l['date'], l['amount'], (l['payment_ref'] or '')[:40]) for l in cand])
petits = [l for l in lines if l['date'] <= '2026-08-31']
trouve = []
for a, b in itertools.combinations(petits, 2):
    if abs(a['amount'] + b['amount'] - (-ecart)) < 0.005 or abs(a['amount'] + b['amount'] - ecart) < 0.005:
        trouve.append((a['date'], a['amount'], b['date'], b['amount']))
print('paires de lignes dont la somme = ±écart :', trouve[:8])
print('trous > 6 jours :', [(lines[i - 1]['date'], lines[i]['date']) for i in range(1, len(lines)) if (datetime.strptime(lines[i]['date'], '%Y-%m-%d') - datetime.strptime(lines[i - 1]['date'], '%Y-%m-%d')).days > 6])
