# -*- coding: utf-8 -*-
"""CARRIERE D'HAIMS : alignement du journal Banque Populaire (75) sur la numérotation Sage.
Compte par défaut 51200002 (nommé par l'IBAN) -> 51210001 « BANQUE POPULAIRE » ; toutes les lignes d'écriture du 51200002
(lignes de relevé, paiements) basculent sur 51210001 ; 51200002 est ensuite retiré (déprécié) s'il est vide.
  python haims_aligne_bp.py dry | apply"""
import os, ssl, sys, time, xmlrpc.client
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


JOURNAL = 75
j = x('account.journal', 'read', [JOURNAL], ['name', 'default_account_id', 'suspense_account_id', 'bank_account_id'])[0]
src = x('account.account', 'search_read', [['company_ids', 'in', [4]], ['code', '=', '51200002']], fields=['name', 'account_type', 'reconcile', 'active'])[0]
dst = x('account.account', 'search_read', [['company_ids', 'in', [4]], ['code', '=', '51210001']], fields=['name', 'account_type', 'reconcile', 'active'])[0]
print('journal %s : compte actuel %s | suspens %s | compte bancaire %s' % (j['name'], j['default_account_id'][1], j['suspense_account_id'][1], j['bank_account_id'] and j['bank_account_id'][1]))
assert j['default_account_id'][0] == src['id'], j['default_account_id']
print('source 51200002 %s : type %s | cible 51210001 %s : type %s, archivé %s' % (src['name'], src['account_type'], dst['name'], dst['account_type'], (not dst['active'])))
lines = x('account.move.line', 'search_read', [['account_id', '=', src['id']]], fields=['move_id', 'parent_state', 'balance', 'statement_line_id', 'payment_id'], context={'active_test': False})
nb_dst = x('account.move.line', 'search_count', [['account_id', '=', dst['id']]])
print('lignes sur 51200002 : %d (relevé %d, paiement %d, autres %d ; états %s) solde %.2f | lignes déjà sur 51210001 : %d' % (
    len(lines), len([l for l in lines if l['statement_line_id']]), len([l for l in lines if l['payment_id']]), len([l for l in lines if not l['statement_line_id'] and not l['payment_id']]),
    sorted({l['parent_state'] for l in lines}), sum(l['balance'] for l in lines if l['parent_state'] == 'posted'), nb_dst))
autres_j = x('account.journal', 'search_read', [['default_account_id', '=', dst['id']]], fields=['name'])
print('autres journaux déjà sur 51210001 :', autres_j or 'aucun')
if mode != 'apply':
    sys.exit(0)
print('--- application')
if dst['account_type'] != 'asset_cash':
    x('account.account', 'write', [dst['id']], {'account_type': 'asset_cash'}); print('   type de 51210001 mis à Banque et espèces')
if (not dst['active']):
    x('account.account', 'write', [dst['id']], {'active': True})
x('account.journal', 'write', [JOURNAL], {'default_account_id': dst['id']})
print('   journal basculé sur 51210001')
ids = [l['id'] for l in lines]
t = time.time()
try:
    for i in range(0, len(ids), 200):
        x('account.move.line', 'write', ids[i:i + 200], {'account_id': dst['id']})
    print('   %d lignes basculées par écriture directe en %.0f s' % (len(ids), time.time() - t))
except Exception as e:
    print('   écriture directe refusée (%s) -> passage par brouillon écriture par écriture' % str(e)[:100])
    mids = sorted({l['move_id'][0] for l in lines})
    for n, mid in enumerate(mids, 1):
        lids = [l['id'] for l in lines if l['move_id'][0] == mid]
        st = x('account.move', 'read', [mid], ['state'])[0]['state']
        if st == 'posted':
            x('account.move', 'button_draft', [mid])
        x('account.move.line', 'write', lids, {'account_id': dst['id']})
        if st == 'posted':
            x('account.move', 'action_post', [mid])
        if n % 100 == 0:
            print('      %d / %d écritures' % (n, len(mids)))
    print('   %d écritures traitées en %.0f s' % (len(mids), time.time() - t))
reste = x('account.move.line', 'search_count', [['account_id', '=', src['id']]], context={'active_test': False})
r = x('account.move.line', 'read_group', [['account_id', '=', dst['id']], ['parent_state', '=', 'posted']], ['balance:sum'], [])
print('   reste sur 51200002 : %d lignes | solde 51210001 : %.2f' % (reste, (r[0]['balance'] or 0.0) if r else 0.0))
if reste == 0:
    x('account.account', 'write', [src['id']], {'active': False})
    print('   51200002 archivé')
print('   journal :', x('account.journal', 'read', [JOURNAL], ['default_account_id'])[0]['default_account_id'][1], '| solde des relevés :', x('account.journal', 'read', [JOURNAL], ['current_statement_balance'])[0]['current_statement_balance'])
