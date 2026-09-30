# -*- coding: utf-8 -*-
"""CARRIERE D'HAIMS : les 28 paiements clients comptabilisés directement sur les comptes 512 (sans ligne de banque)
passent sur le compte d'attente 511900 « Encaissements à rapprocher », comme les paiements créés depuis. Les factures
restent réglées ; le 512 redevient égal aux relevés ; le rapprochement paiement <-> ligne de banque se fait ensuite
dans le widget (ou par le mode rappro pour les correspondances sûres).
  python haims_paiements_attente.py dry     contrôle
  python haims_paiements_attente.py apply   bascule des 28 paiements sur 511900 (factures re-lettrées à l'identique)
  python haims_paiements_attente.py rappro  lettre les correspondances sûres : 594,97 ; 10 000 ; remise 378,67 = 3 chèques"""
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
pays = x('account.payment', 'read', pids, ['name', 'date', 'amount', 'partner_id', 'journal_id', 'reconciled_invoice_ids', 'state', 'move_id', 'outstanding_account_id', 'is_matched'])
print('%d paiements sur 512 (total %.2f) | soldes 512 : BNP %.2f, BP %.2f | 511900 : %.2f' % (len(pays), sum(l['balance'] for l in amls), solde('51210000'), solde('51210001'), solde('511900')))
for q in pays:
    print('   %-18s %s %9.2f %-24s état %-6s compte %-14s factures %s' % (q['name'], q['date'], q['amount'], (q['partner_id'] or ['', ''])[1][:24], q['state'], (q['outstanding_account_id'] or ['', '?'])[1][:14], q['reconciled_invoice_ids']))
if mode == 'apply':
    print('--- bascule sur 511900')
    for q in pays:
        inv_avant = list(q['reconciled_invoice_ids'])
        ok = False
        try:
            x('account.payment', 'write', [q['id']], {'outstanding_account_id': ACC_ATT})
            liq = x('account.move.line', 'search_read', [['move_id', '=', q['move_id'][0]], ['account_id', 'in', acc512]], fields=['id'])
            ok = not liq
        except Exception as e:
            print('   %s : écriture directe refusée (%s)' % (q['name'], str(e)[:90]))
        if not ok:
            x('account.payment', 'action_draft', [q['id']])
            x('account.payment', 'write', [q['id']], {'outstanding_account_id': ACC_ATT})
            x('account.payment', 'action_post', [q['id']])
            # re-lettrage des factures
            rec = x('account.move.line', 'search_read', [['move_id', '=', q['move_id'][0]], ['account_id.account_type', '=', 'asset_receivable'], ['reconciled', '=', False]], fields=['id'])
            for inv in inv_avant:
                il = x('account.move.line', 'search_read', [['move_id', '=', inv], ['account_id.account_type', '=', 'asset_receivable'], ['reconciled', '=', False]], fields=['id'])
                if rec and il:
                    x('account.move.line', 'reconcile', [r['id'] for r in rec] + [r['id'] for r in il])
        q2 = x('account.payment', 'read', [q['id']], ['reconciled_invoice_ids', 'outstanding_account_id', 'is_matched', 'state'])[0]
        etats = x('account.move', 'read', inv_avant, ['name', 'payment_state']) if inv_avant else []
        print('   %-18s compte %-14s matched %-5s factures %s' % (q['name'], (q2['outstanding_account_id'] or ['', '?'])[1][:14], q2['is_matched'], [(e['name'], e['payment_state']) for e in etats]))
    print('soldes après : 512 BNP %.2f | 512 BP %.2f | 511900 %.2f | relevés BNP %.2f, BP %.2f' % (solde('51210000'), solde('51210001'), solde('511900'),
          x('account.journal', 'read', [48], ['current_statement_balance'])[0]['current_statement_balance'], x('account.journal', 'read', [75], ['current_statement_balance'])[0]['current_statement_balance']))
if mode == 'rappro':
    CORRESP = [(1801, ['PBNP/25-26/0003']), (1890, ['PBNP/25-26/0014']), (857, ['PBNP/25-26/0001', 'PBNP/25-26/0002', 'PBNP/25-26/0004'])]
    for lid, noms in CORRESP:
        st = x('account.bank.statement.line', 'read', [lid], ['amount', 'payment_ref', 'is_reconciled', 'move_id'])[0]
        pm = x('account.payment', 'search_read', [['name', 'in', noms], ['company_id', '=', 4]], fields=['name', 'amount', 'move_id', 'outstanding_account_id'])
        assert len(pm) == len(noms) and abs(sum(q['amount'] for q in pm) - st['amount']) < 0.005, (lid, [q['amount'] for q in pm], st['amount'])
        assert all(q['outstanding_account_id'] and q['outstanding_account_id'][0] == ACC_ATT for q in pm), 'paiement pas encore sur 511900 : lancer apply avant'
        assert not st['is_reconciled'], ('ligne déjà lettrée', lid)
        l_st = x('account.move.line', 'search_read', [['move_id', '=', st['move_id'][0]], ['account_id', '=', ACC_ATT], ['reconciled', '=', False]], fields=['id', 'balance'])
        l_pm = x('account.move.line', 'search_read', [['move_id', 'in', [q['move_id'][0] for q in pm]], ['account_id', '=', ACC_ATT], ['reconciled', '=', False]], fields=['id', 'balance'])
        assert len(l_st) == 1 and len(l_pm) == len(noms) and abs(sum(l['balance'] for l in l_st + l_pm)) < 0.005, (lid, l_st, l_pm)
        x('account.move.line', 'reconcile', [l['id'] for l in l_st + l_pm])
        print('   ligne %s (%.2f, %s) lettrée avec %s -> ligne lettrée : %s' % (lid, st['amount'], st['payment_ref'][:30], noms, x('account.bank.statement.line', 'read', [lid], ['is_reconciled'])[0]['is_reconciled']))
    print('511900 après :', solde('511900'))
