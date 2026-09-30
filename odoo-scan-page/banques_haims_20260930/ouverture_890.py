# -*- coding: utf-8 -*-
"""Méthode Odoo pour le solde initial d'une banque synchronisée : la ligne de relevé « Déclaration d'ouverture »
(créée à la première synchronisation) reçoit pour contrepartie le compte 890 « Bilan d'ouverture » au lieu de rester
en attente sur 511900. Aucune OD. La ligne devient rapprochée.
  python ouverture_890.py <société> dry | apply"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
COMP = int(sys.argv[1]); mode = (sys.argv[2] if len(sys.argv) > 2 else 'dry').lower()
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
CTX = {'allowed_company_ids': [COMP, 1, 2, 3, 4, 13]}


def x(mo, me, *a, **k):
    ctx = dict(CTX); ctx.update(k.pop('context', {})); k['context'] = ctx
    try:
        return m.execute_kw(D, uid, p, mo, me, list(a), k)
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in str(e):
            return None
        raise


a890 = x('account.account', 'search_read', [['company_ids', 'in', [COMP]], ['code', '=like', '890%']], fields=['code', 'name'])
assert a890, 'compte 890 introuvable'
a890 = a890[0]
print('compte d ouverture :', a890['code'], a890['name'])
for j in x('account.journal', 'search_read', [['company_id', '=', COMP], ['type', '=', 'bank']], fields=['name', 'default_account_id'], order='id'):
    for l in x('account.bank.statement.line', 'search_read', [['journal_id', '=', j['id']], ['payment_ref', 'ilike', 'ouverture']], fields=['date', 'amount', 'payment_ref', 'move_id', 'is_reconciled']):
        cp = x('account.move.line', 'search_read', [['move_id', '=', l['move_id'][0]], ['account_id', '!=', j['default_account_id'][0]]], fields=['account_id', 'balance', 'reconciled'])
        print('%-22s %s %12.2f « %s » contrepartie %s lettrée %s' % (j['name'][:22], l['date'], l['amount'], (l['payment_ref'] or '')[:36], [(q['account_id'][1][:26], q['balance']) for q in cp], l['is_reconciled']))
        if mode != 'apply':
            continue
        cibles = [q for q in cp if q['account_id'][0] != a890['id']]
        if not cibles:
            print('   déjà sur 890'); continue
        assert not any(q['reconciled'] for q in cibles), 'contrepartie déjà lettrée'
        try:
            x('account.move.line', 'write', [q['id'] for q in cibles], {'account_id': a890['id']})
            voie = 'directe'
        except Exception as e:
            x('account.move', 'button_draft', [l['move_id'][0]])
            x('account.move.line', 'write', [q['id'] for q in cibles], {'account_id': a890['id']})
            x('account.move', 'action_post', [l['move_id'][0]])
            voie = 'brouillon/revalidation (%s)' % str(e)[:60]
        l2 = x('account.bank.statement.line', 'read', [l['id']], ['is_reconciled'])[0]
        cp2 = x('account.move.line', 'search_read', [['move_id', '=', l['move_id'][0]], ['account_id', '!=', j['default_account_id'][0]]], fields=['account_id'])
        print('   -> contrepartie %s, ligne rapprochée %s (voie %s)' % ([q['account_id'][1][:26] for q in cp2], l2['is_reconciled'], voie))
if mode == 'apply':
    r = x('account.move.line', 'read_group', [['account_id', '=', a890['id']], ['parent_state', '=', 'posted']], ['balance:sum'], [])
    print('solde 890 après : %.2f' % ((r[0]['balance'] or 0) if r else 0))
