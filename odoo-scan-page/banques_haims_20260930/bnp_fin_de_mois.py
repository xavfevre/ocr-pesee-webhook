# -*- coding: utf-8 -*-
"""Lecture seule : solde des relevés Odoo en fin de mois pour les journaux BNP (à comparer au « solde créditeur » des relevés
papier BNP pour mesurer l'écart structurel, indépendamment du solde en ligne du connecteur)."""
import os, ssl, sys, xmlrpc.client
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [1, 2, 3, 4, 13]}))
for jid, nom in ((6, 'Maquignon BNP *8837*'), (77, 'Maquignon BNP Bis *5566*'), (76, 'Chatel BNP'), (48, 'Haims BNP')):
    lines = x('account.bank.statement.line', 'search_read', [['journal_id', '=', jid]], fields=['date', 'amount'], order='date, id')
    mois = defaultdict(float)
    for l in lines:
        mois[l['date'][:7]] += l['amount']
    cumul = 0.0; out = []
    for mo in sorted(mois):
        cumul += mois[mo]; out.append('%s %11.2f' % (mo, cumul))
    print('%-26s (%d lignes, du %s)' % (nom, len(lines), lines and lines[0]['date']))
    for i in range(0, len(out), 4):
        print('    ' + ' | '.join(out[i:i + 4]))
