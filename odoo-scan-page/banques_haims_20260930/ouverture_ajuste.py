# -*- coding: utf-8 -*-
"""Ajuste le montant de la ligne « Déclaration d'ouverture » d'un journal de banque synchronisé pour que le solde des
relevés Odoo rejoigne le solde de la banque (méthode Odoo : l'ouverture est portée par cette ligne, pas par une OD).
  python ouverture_ajuste.py <journal_id> <nouveau montant d'ouverture> [apply]
Sans « apply » : contrôle seul. Refuse si la ligne d'ouverture est déjà rapprochée."""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
JID = int(sys.argv[1]); NOUVEAU = float(sys.argv[2].replace(',', '.')); mode = (sys.argv[3] if len(sys.argv) > 3 else 'dry').lower()
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
def x(mo, me, *a, **k):
    try:
        return m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [1, 2, 3, 4, 13]}))
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in str(e):
            return None
        raise
j = x('account.journal', 'read', [JID], ['name', 'company_id', 'current_statement_balance'])[0]
ouv = x('account.bank.statement.line', 'search_read', [['journal_id', '=', JID], ['payment_ref', 'ilike', 'ouverture']], fields=['date', 'amount', 'payment_ref', 'is_reconciled', 'move_id'])
assert len(ouv) == 1, ouv
o = ouv[0]
oa = x('account.online.account', 'search_read', [['journal_ids', 'in', [JID]]], fields=['balance', 'last_sync'])
bal = oa and oa[0]['balance']
delta = round(NOUVEAU - o['amount'], 2)
print('%s (%s) : ouverture %s %.2f -> %.2f (delta %+.2f) | relevés %.2f -> %.2f | banque en ligne %s au %s' % (
    j['name'], j['company_id'][1], o['date'], o['amount'], NOUVEAU, delta, j['current_statement_balance'], j['current_statement_balance'] + delta, bal, oa and oa[0]['last_sync']))
a890 = x('account.account', 'search', [['company_ids', 'in', [j['company_id'][0]]], ['code', '=like', '890%']], limit=1)
if mode != 'apply':
    print('(ligne rapprochée : %s ; en mode apply elle est dé-rapprochée, modifiée puis remise sur le 890)' % o['is_reconciled'])
    sys.exit(0)
if o['is_reconciled']:
    x('account.bank.statement.line', 'action_undo_reconciliation', [o['id']])
x('account.bank.statement.line', 'write', [o['id']], {'amount': NOUVEAU})
cp = x('account.move.line', 'search_read', [['move_id', '=', o['move_id'][0]], ['account_id.code', 'not like', '512%']], fields=['account_id'])
if a890 and any(l['account_id'][0] != a890[0] for l in cp):
    x('account.move.line', 'write', [l['id'] for l in cp if l['account_id'][0] != a890[0]], {'account_id': a890[0]})
o2 = x('account.bank.statement.line', 'read', [o['id']], ['amount', 'is_reconciled'])[0]
ls = x('account.move.line', 'search_read', [['move_id', '=', o['move_id'][0]]], fields=['account_id', 'balance'])
print('après : ouverture %.2f rapprochée %s | écriture %s | relevés %.2f | banque %s' % (o2['amount'], o2['is_reconciled'], [(l['account_id'][1][:22], l['balance']) for l in ls], x('account.journal', 'read', [JID], ['current_statement_balance'])[0]['current_statement_balance'], bal))
