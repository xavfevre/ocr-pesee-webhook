# -*- coding: utf-8 -*-
"""Haims : les 28 paiements ont 511900 comme compte d'attente mais Odoo ne régénère pas leurs écritures (ni à l'écriture
du champ, ni par brouillon/revalidation). On déplace donc directement la ligne de banque de chaque écriture de paiement
du 512 vers 511900 (écriture directe, sinon brouillon -> modification -> validation -> re-lettrage des factures).
  python haims_paiements_lignes.py dry | apply"""
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
lines = x('account.move.line', 'search_read', [['account_id', 'in', acc512], ['payment_id', '!=', False], ['parent_state', '=', 'posted']], fields=['move_id', 'payment_id', 'balance', 'account_id', 'reconciled'])
print('%d lignes de paiement sur 512 (%.2f) | soldes 512 BNP %.2f, BP %.2f, 511900 %.2f' % (len(lines), sum(l['balance'] for l in lines), solde('51210000'), solde('51210001'), solde('511900')))
for l in lines:
    print('   %-20s %-16s %10.2f  paiement %s' % (l['move_id'][1][:20], l['account_id'][1][:16], l['balance'], l['payment_id'][1][:18]))
if mode != 'apply':
    sys.exit(0)
print('--- déplacement des lignes vers 511900')
for l in lines:
    pay = x('account.payment', 'read', [l['payment_id'][0]], ['reconciled_invoice_ids', 'state'])[0]
    inv_avant = list(pay['reconciled_invoice_ids'])
    try:
        x('account.move.line', 'write', [l['id']], {'account_id': ACC_ATT})
        voie = 'directe'
    except Exception as e:
        x('account.payment', 'action_draft', [l['payment_id'][0]])
        x('account.move.line', 'write', [l['id']], {'account_id': ACC_ATT})
        x('account.payment', 'action_post', [l['payment_id'][0]])
        rec = x('account.move.line', 'search_read', [['move_id', '=', l['move_id'][0]], ['account_id.account_type', '=', 'asset_receivable'], ['reconciled', '=', False]], fields=['id'])
        for inv in inv_avant:
            il = x('account.move.line', 'search_read', [['move_id', '=', inv], ['account_id.account_type', '=', 'asset_receivable'], ['reconciled', '=', False]], fields=['id'])
            if rec and il:
                x('account.move.line', 'reconcile', [r['id'] for r in rec] + [r['id'] for r in il])
        voie = 'brouillon/revalidation (%s)' % str(e)[:60]
    apres = x('account.move.line', 'read', [l['id']], ['account_id', 'parent_state'])[0]
    etats = x('account.move', 'read', inv_avant, ['name', 'payment_state']) if inv_avant else []
    print('   %-18s -> %-16s %-7s voie %s | factures %s' % (l['payment_id'][1][:18], apres['account_id'][1][:16], apres['parent_state'], voie, [(e_['name'], e_['payment_state']) for e_ in etats]))
print('soldes après : 512 BNP %.2f (attendu 36 945,68) | 512 BP %.2f (attendu 44 680,73) | 511900 %.2f | lignes de paiement restantes sur 512 : %d' % (
    solde('51210000'), solde('51210001'), solde('511900'), x('account.move.line', 'search_count', [['account_id', 'in', acc512], ['payment_id', '!=', False], ['parent_state', '=', 'posted']])))
