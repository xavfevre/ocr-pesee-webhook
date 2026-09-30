# -*- coding: utf-8 -*-
"""Haims : vérification après revalidation des 28 paiements (soldes 512, lignes d'attente, factures), puis mode
'nettoyage' : annulation / suppression des paiements Stripe résiduels sans écriture (PAY000xx annulés ou « Payé » sans move)."""
import os, ssl, sys, xmlrpc.client
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'verif').lower()
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


print('soldes : 512 BNP %.2f (relevés %.2f) | 512 BP %.2f (relevés %.2f) | 511900 %.2f' % (
    solde('51210000'), x('account.journal', 'read', [48], ['current_statement_balance'])[0]['current_statement_balance'],
    solde('51210001'), x('account.journal', 'read', [75], ['current_statement_balance'])[0]['current_statement_balance'], solde('511900')))
acc512 = x('account.account', 'search', [['company_ids', 'in', [4]], ['code', 'in', ['51210000', '51210001']]])
print('lignes de paiement encore sur un 512 :', x('account.move.line', 'search_count', [['account_id', 'in', acc512], ['payment_id', '!=', False], ['parent_state', '=', 'posted']]))
pays = x('account.payment', 'search_read', [['company_id', '=', 4], ['journal_id', 'in', [48, 75]], ['state', 'not in', ['cancel', 'draft']], ['payment_type', '=', 'inbound'], ['move_id', '!=', False]], fields=['name', 'state', 'is_matched', 'outstanding_account_id', 'reconciled_invoice_ids', 'amount'])
print('paiements avec écriture : %d | états %s | compte d attente %s' % (len(pays), dict(Counter(q['state'] for q in pays)), dict(Counter((q['outstanding_account_id'] or ['', '?'])[1][:12] for q in pays))))
inv_ids = sorted({i for q in pays for i in q['reconciled_invoice_ids']})
print('factures liées : %d, états %s | paiements sans facture lettrée : %s' % (len(inv_ids), dict(Counter(i['payment_state'] for i in x('account.move', 'read', inv_ids, ['payment_state']))), [q['name'] for q in pays if not q['reconciled_invoice_ids']]))
resid = x('account.payment', 'search_read', [['company_id', '=', 4], ['journal_id', 'in', [48, 75]], ['move_id', '=', False]], fields=['name', 'state', 'amount', 'partner_id', 'payment_transaction_id', 'reconciled_invoice_ids'])
print('paiements SANS écriture (résidus Stripe) : %d' % len(resid))
for q in resid:
    print('   %-10s %-9s %9.2f %-24s transaction %s factures %s' % (q['name'], q['state'], q['amount'], (q['partner_id'] or ['', ''])[1][:24], q['payment_transaction_id'] and q['payment_transaction_id'][1], q['reconciled_invoice_ids']))
if mode == 'nettoyage':
    for q in resid:
        try:
            if q['state'] != 'cancel':
                x('account.payment', 'action_cancel', [q['id']])
            x('account.payment', 'unlink', [q['id']])
            print('   supprimé :', q['name'])
        except Exception as e:
            st = x('account.payment', 'read', [q['id']], ['state'])[0]['state']
            print('   %s : suppression refusée (%s) -> état %s' % (q['name'], str(e)[:90], st))
    print('résidus restants :', x('account.payment', 'search_count', [['company_id', '=', 4], ['journal_id', 'in', [48, 75]], ['move_id', '=', False]]))
