# -*- coding: utf-8 -*-
"""Carrière d'Haims : suppression des paiements manuels « Reprise historique Sage » restés « en cours » (créés par l'import
de lettrage du 02/09/2026). Pour chacun : délettrage de sa ligne 411 (la facture redevient impayée), passage en brouillon,
suppression du paiement et de son écriture. Le paiement déjà rapproché avec une vraie ligne de relevé est conservé.
Modes : dry | apply"""
import os, ssl, sys, xmlrpc.client, collections
sys.stdout.reconfigure(encoding='utf-8')
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
CTX = {'allowed_company_ids': [4]}


def x(mo, me, *a, **k):
    k.setdefault('context', CTX)
    return m.execute_kw(D, uid, p, mo, me, list(a), k)


def sur(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        if 'cannot marshal None' not in str(e):
            raise


mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
pays = x('account.payment', 'search_read', [['company_id', '=', 4], ['memo', 'ilike', 'Reprise historique Sage'], ['state', '=', 'in_process']],
         fields=['name', 'amount', 'partner_id', 'move_id', 'date', 'is_reconciled'], order='name')
print('paiements « Reprise historique Sage » en cours chez Haims :', len(pays), '| total %.2f' % sum(pp['amount'] for pp in pays))
plan = []
for pp in pays:
    mv = pp['move_id'][0]
    l411 = x('account.move.line', 'search_read', [['move_id', '=', mv], ['account_id.account_type', '=', 'asset_receivable']], fields=['matched_debit_ids', 'matched_credit_ids'])
    partiels = [pid for l in l411 for pid in l['matched_debit_ids'] + l['matched_credit_ids']]
    factures = set()
    for pr in x('account.partial.reconcile', 'read', partiels, fields=['debit_move_id', 'credit_move_id']):
        for k in ('debit_move_id', 'credit_move_id'):
            ml = x('account.move.line', 'read', [pr[k][0]], fields=['move_id'])[0]
            if ml['move_id'][0] != mv:
                factures.add(ml['move_id'][1])
    plan.append((pp, partiels, sorted(factures)))
    print('  %-16s %s %-24s %9.2f | lettré avec %s' % (pp['name'], pp['date'], (pp['partner_id'] and pp['partner_id'][1][:24]) or '-', pp['amount'], sorted(factures)))
if mode != 'apply':
    sys.exit(0)
ok = err = 0; touchees = set()
for pp, partiels, factures in plan:
    try:
        if partiels:
            x('account.partial.reconcile', 'unlink', partiels)
        sur(lambda: x('account.payment', 'action_draft', [pp['id']]))
        st = x('account.payment', 'read', [pp['id']], fields=['state', 'move_id'])[0]
        if st['state'] not in ('draft', 'canceled', 'cancel'):
            sur(lambda: x('account.move', 'button_draft', [pp['move_id'][0]]))
        x('account.payment', 'unlink', [pp['id']])
        if x('account.move', 'search_count', [['id', '=', pp['move_id'][0]]]):
            sur(lambda: x('account.move', 'button_draft', [pp['move_id'][0]]))
            x('account.move', 'unlink', [pp['move_id'][0]])
        ok += 1; touchees |= set(factures); print('OK', pp['name'], pp['amount'])
    except Exception as e:  # noqa: BLE001
        err += 1; print('ERREUR', pp['name'], ':', str(e).strip().split('\n')[-1][:220])
print('supprimés :', ok, '| erreurs :', err)
reste = x('account.payment', 'read_group', [['company_id', '=', 4], ['memo', 'ilike', 'Reprise historique Sage']], ['amount:sum'], ['state'], lazy=False)
print('paiements Reprise historique Sage restants :', [(r['state'], r['__count'], round(r['amount'], 2)) for r in reste])
if touchees:
    inv = x('account.move', 'search_read', [['name', 'in', sorted(touchees)], ['company_id', '=', 4]], fields=['name', 'partner_id', 'amount_total', 'amount_residual', 'payment_state', 'invoice_date'], order='invoice_date')
    print('factures détachées : %d, total %.2f, reste dû %.2f | états %s' % (len(inv), sum(i['amount_total'] for i in inv), sum(i['amount_residual'] for i in inv), dict(collections.Counter(i['payment_state'] for i in inv))))
    for i in inv:
        print('   %-16s %s %-26s %9.2f reste %9.2f %s' % (i['name'], i['invoice_date'], i['partner_id'][1][:26], i['amount_total'], i['amount_residual'], i['payment_state']))
