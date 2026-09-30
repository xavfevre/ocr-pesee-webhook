# -*- coding: utf-8 -*-
"""Haims : les 28 paiements ont bien 511900 comme compte d'attente (script précédent) mais leurs écritures sont restées
sur les 512. Remise en brouillon puis revalidation de chaque paiement : Odoo régénère l'écriture avec la ligne d'attente
sur 511900 ; les factures sont re-lettrées à l'identique. Contrôle des soldes 512 attendus : BNP 36 945,68, BP 44 680,73.
  python haims_paiements_repost.py dry | apply"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
CTX = {'allowed_company_ids': [4, 1, 2, 3, 13]}


def x(mo, me, *a, **k):
    ctx = dict(CTX); ctx.update(k.pop('context', {})); k['context'] = ctx
    try:
        return m.execute_kw(D, uid, p, mo, me, list(a), k)
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in str(e):
            return None
        raise


def solde(code):
    a = x('account.account', 'search', [['company_ids', 'in', [4]], ['code', '=', code]])[0]
    r = x('account.move.line', 'read_group', [['account_id', '=', a], ['parent_state', '=', 'posted']], ['balance:sum'], [])
    return (r[0]['balance'] or 0.0) if r else 0.0


ACC_ATT = x('account.account', 'search', [['company_ids', 'in', [4]], ['code', '=', '511900']])[0]
acc512 = x('account.account', 'search', [['company_ids', 'in', [4]], ['code', 'in', ['51210000', '51210001']]])
amls = x('account.move.line', 'search_read', [['account_id', 'in', acc512], ['payment_id', '!=', False], ['parent_state', '=', 'posted']], fields=['payment_id', 'balance'])
pids = sorted({l['payment_id'][0] for l in amls})
pays = x('account.payment', 'read', pids, ['name', 'amount', 'state', 'move_id', 'outstanding_account_id', 'reconciled_invoice_ids', 'is_matched'])
print('%d paiements avec écriture sur 512 (%.2f) | soldes : BNP %.2f, BP %.2f, 511900 %.2f' % (len(pays), sum(l['balance'] for l in amls), solde('51210000'), solde('51210001'), solde('511900')))
for q in pays:
    print('   %-18s %9.2f état %-10s attente %-16s rapproché %-5s factures %s' % (q['name'], q['amount'], q['state'], (q['outstanding_account_id'] or ['', '?'])[1][:16], q['is_matched'], q['reconciled_invoice_ids']))
if mode != 'apply':
    sys.exit(0)
print('--- remise en brouillon / revalidation')
for q in pays:
    inv_avant = list(q['reconciled_invoice_ids'])
    x('account.payment', 'action_draft', [q['id']])
    if not q['outstanding_account_id'] or q['outstanding_account_id'][0] != ACC_ATT:
        x('account.payment', 'write', [q['id']], {'outstanding_account_id': ACC_ATT})
    x('account.payment', 'action_post', [q['id']])
    rec = x('account.move.line', 'search_read', [['move_id', '=', q['move_id'][0]], ['account_id.account_type', '=', 'asset_receivable'], ['reconciled', '=', False]], fields=['id'])
    for inv in inv_avant:
        il = x('account.move.line', 'search_read', [['move_id', '=', inv], ['account_id.account_type', '=', 'asset_receivable'], ['reconciled', '=', False]], fields=['id'])
        if rec and il:
            x('account.move.line', 'reconcile', [r['id'] for r in rec] + [r['id'] for r in il])
    liq = x('account.move.line', 'search_read', [['move_id', '=', q['move_id'][0]], ['account_id', 'in', acc512 + [ACC_ATT]]], fields=['account_id'])
    q2 = x('account.payment', 'read', [q['id']], ['state', 'is_matched', 'reconciled_invoice_ids'])[0]
    etats = x('account.move', 'read', inv_avant, ['name', 'payment_state']) if inv_avant else []
    print('   %-18s ligne sur %-16s état %-10s rapproché %-5s factures %s' % (q['name'], liq and liq[0]['account_id'][1][:16], q2['state'], q2['is_matched'], [(e['name'], e['payment_state']) for e in etats]))
print('soldes après : BNP %.2f | BP %.2f | 511900 %.2f (attendus 36 945,68 / 44 680,73)' % (solde('51210000'), solde('51210001'), solde('511900')))
