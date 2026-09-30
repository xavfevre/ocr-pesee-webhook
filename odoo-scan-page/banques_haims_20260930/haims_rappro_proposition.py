# -*- coding: utf-8 -*-
"""Lecture seule : proposition de rapprochement des paiements passés directement sur 512 (Haims) avec les lignes de relevé
non lettrées : correspondance exacte, à quelques euros près (virements Colas…), ou par combinaison (remises de chèques :
sous-ensemble de paiements dont la somme = la ligne). État des paiements Stripe non rapprochés."""
import os, ssl, sys, itertools, xmlrpc.client
from datetime import datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [4, 1, 2, 3, 13]}))
acc512 = x('account.account', 'search', [['company_ids', 'in', [4]], ['code', 'in', ['51210000', '51210001']]])
amls = x('account.move.line', 'search_read', [['account_id', 'in', acc512], ['payment_id', '!=', False], ['parent_state', '=', 'posted']], fields=['payment_id'])
pays = x('account.payment', 'read', sorted({l['payment_id'][0] for l in amls}), ['name', 'date', 'amount', 'partner_id', 'journal_id', 'reconciled_invoice_ids', 'memo'])
pays.sort(key=lambda q: q['date'])
d = lambda s: datetime.strptime(s, '%Y-%m-%d')
lignes = x('account.bank.statement.line', 'search_read', [['journal_id', 'in', [48, 75]], ['is_reconciled', '=', False], ['amount', '>', 0]], fields=['date', 'amount', 'payment_ref', 'journal_id', 'partner_id'], order='date')
print('%d paiements directement sur 512 | %d lignes de relevé entrantes non lettrées (BNP+BP)' % (len(pays), len(lignes)))
restants = list(pays); props = []
# 1. correspondance exacte ou approchée (±25 €, ±0,3 %) sur le même journal, date de la ligne entre J-30 et J+45
for pm in list(restants):
    cands = [l for l in lignes if l['journal_id'][0] == pm['journal_id'][0] and -30 <= (d(l['date']) - d(pm['date'])).days <= 45]
    exact = [l for l in cands if abs(l['amount'] - pm['amount']) < 0.005]
    proche = [l for l in cands if abs(l['amount'] - pm['amount']) <= max(25.0, 0.003 * pm['amount']) and l not in exact]
    if exact:
        props.append(('exact', pm, exact[0])); restants.remove(pm); lignes.remove(exact[0])
    elif len(proche) == 1:
        props.append(('approché (écart %.2f)' % (proche[0]['amount'] - pm['amount']), pm, proche[0])); restants.remove(pm); lignes.remove(proche[0])
# 2. combinaisons (remises) : sous-ensembles de 2 à 5 paiements du même journal dont la somme = une ligne, paiements datés avant la ligne (J-45..J+3)
for l in list(lignes):
    pool = [pm for pm in restants if pm['journal_id'][0] == l['journal_id'][0] and -45 <= (d(l['date']) - d(pm['date'])).days <= 45]
    trouve = None
    for k in range(2, 6):
        for combo in itertools.combinations(pool, k):
            if abs(sum(q['amount'] for q in combo) - l['amount']) < 0.005:
                trouve = combo; break
        if trouve:
            break
    if trouve:
        props.append(('combinaison', trouve, l))
        for q in trouve:
            restants.remove(q)
        lignes.remove(l)
print('\n=== propositions (%d) :' % len(props))
for typ, pm, l in props:
    if typ == 'combinaison':
        print('  ligne %5s %-3s %s %9.2f %-38s <= %s' % (l['id'], 'BNP' if l['journal_id'][0] == 48 else 'BP', l['date'], l['amount'], (l['payment_ref'] or '')[:38], ' + '.join('%s %.2f %s' % (q['name'], q['amount'], (q['partner_id'] or ['', ''])[1][:14]) for q in pm)))
    else:
        print('  ligne %5s %-3s %s %9.2f %-38s <= %s %.2f %-18s [%s]' % (l['id'], 'BNP' if l['journal_id'][0] == 48 else 'BP', l['date'], l['amount'], (l['payment_ref'] or '')[:38], pm['name'], pm['amount'], (pm['partner_id'] or ['', ''])[1][:18], typ))
print('\n=== paiements sans ligne trouvée (%d) :' % len(restants))
for pm in restants:
    print('  %-18s %s %9.2f %-26s %s' % (pm['name'], pm['date'], pm['amount'], (pm['partner_id'] or ['', ''])[1][:26], (pm['memo'] or '')[:30]))
print('\n=== lignes entrantes non lettrées restantes : %d, total %.2f (les 12 plus grosses) :' % (len(lignes), sum(l['amount'] for l in lignes)))
for l in sorted(lignes, key=lambda q: -q['amount'])[:12]:
    print('  %5s %-3s %s %9.2f %s' % (l['id'], 'BNP' if l['journal_id'][0] == 48 else 'BP', l['date'], l['amount'], (l['payment_ref'] or '')[:60]))
print('\n=== paiements Stripe / portail non rapprochés :')
for pm in x('account.payment', 'search_read', [['company_id', '=', 4], ['journal_id', 'in', [48, 75]], ['is_matched', '=', False], ['name', 'like', 'PAY%']], fields=['name', 'date', 'amount', 'state', 'move_id', 'is_reconciled', 'reconciled_invoice_ids', 'partner_id']):
    mv = x('account.move', 'read', [pm['move_id'][0]], ['state', 'line_ids'])[0] if pm['move_id'] else None
    print('  %-10s %s %9.2f %-22s état %-10s écriture %s reconciled %s factures %s' % (pm['name'], pm['date'], pm['amount'], (pm['partner_id'] or ['', ''])[1][:22], pm['state'], mv and mv['state'], pm['is_reconciled'], pm['reconciled_invoice_ids']))
