import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [1, 2, 3, 4, 13]}))
for jid in (36, 76, 6, 77, 78, 48, 75):
    for o in x('account.bank.statement.line', 'search_read', [['journal_id', '=', jid], ['payment_ref', 'ilike', 'ouverture']], fields=['date', 'amount', 'is_reconciled', 'move_id', 'journal_id']):
        ls = x('account.move.line', 'search_read', [['move_id', '=', o['move_id'][0]]], fields=['account_id', 'balance', 'reconciled', 'matched_debit_ids', 'matched_credit_ids', 'full_reconcile_id'])
        det = []
        for l in ls:
            prs = x('account.partial.reconcile', 'read', l['matched_debit_ids'] + l['matched_credit_ids'], ['debit_move_id', 'credit_move_id', 'amount']) if (l['matched_debit_ids'] or l['matched_credit_ids']) else []
            avec = []
            for pr in prs:
                for side in ('debit_move_id', 'credit_move_id'):
                    if pr[side][0] != l['id']:
                        a2 = x('account.move.line', 'read', [pr[side][0]], ['move_id', 'name', 'date'])[0]
                        avec.append('%s %s %.2f' % (a2['move_id'][1][:22], a2['date'], pr['amount']))
            det.append('%s %.2f%s%s' % (l['account_id'][1][:24], l['balance'], ' lettrée' if l['reconciled'] else '', (' avec ' + '; '.join(avec)) if avec else ''))
        print('%-20s ouverture %s %12.2f rapprochée %-5s | %s' % (o['journal_id'][1][:20], o['date'], o['amount'], o['is_reconciled'], ' || '.join(det)))
