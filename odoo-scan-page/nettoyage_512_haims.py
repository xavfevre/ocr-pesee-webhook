# -*- coding: utf-8 -*-
"""Carrière d'Haims : écritures de banque fictives « Reprise historique Sage — PBNP/… » créées le 02/09/2026 par l'import
de lettrage Sage (512 BNP débité / 511900 crédité, sans ligne de relevé). Pour chacune : délettrage de sa ligne 511900,
passage en brouillon et suppression ; le paiement repasse « en cours » sur 511900. Si une vraie ligne de relevé non
rapprochée existe (même journal, même montant, même client ou sans client, ± 20 jours), le paiement y est rapproché.
Les lettrages facture ↔ paiement (411) ne sont pas touchés.   Modes : dry | apply"""
import os, ssl, sys, datetime as dt, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
CTX = {'allowed_company_ids': [4]}


def x(mo, me, *a, **k):
    k.setdefault('context', CTX)
    return m.execute_kw(D, uid, p, mo, me, list(a), k)


mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
co = x('res.company', 'read', [4], fields=['name', 'fiscalyear_lock_date', 'hard_lock_date'])[0]
print('société :', co['name'], '| verrous :', co.get('fiscalyear_lock_date'), co.get('hard_lock_date'))
fakes = x('account.move', 'search_read', [['company_id', '=', 4], ['ref', 'ilike', 'Reprise historique Sage —'], ['journal_id.type', '=', 'bank'],
                                          ['statement_line_id', '=', False], ['move_type', '=', 'entry'], ['state', '=', 'posted']],
          fields=['name', 'ref', 'date', 'journal_id', 'amount_total', 'inalterable_hash'], order='id')
jinfo = {}


def infos(jid):
    if jid not in jinfo:
        j = x('account.journal', 'read', [jid], fields=['default_account_id', 'suspense_account_id'])[0]
        jinfo[jid] = (j['default_account_id'][0], j['suspense_account_id'][0] if j['suspense_account_id'] else None)
    return jinfo[jid]


plan = []
for mv in fakes:
    bank, att = infos(mv['journal_id'][0])
    lines = x('account.move.line', 'search_read', [['move_id', '=', mv['id']]], fields=['account_id', 'debit', 'credit', 'matched_debit_ids', 'matched_credit_ids'])
    l_att = [l for l in lines if l['account_id'][0] != bank]
    partiels = [pid for l in l_att for pid in l['matched_debit_ids'] + l['matched_credit_ids']]
    pays, partner, att_pay = set(), None, None
    for pr in x('account.partial.reconcile', 'read', partiels, fields=['debit_move_id', 'credit_move_id']):
        for k in ('debit_move_id', 'credit_move_id'):
            ml = x('account.move.line', 'read', [pr[k][0]], fields=['move_id', 'payment_id', 'partner_id', 'account_id'])[0]
            if ml['payment_id']:
                pays.add(ml['payment_id'][0]); partner = ml['partner_id'] and ml['partner_id'][0]; att_pay = ml['account_id'][0]
    d0 = dt.date.fromisoformat(mv['date'])
    cands = [s for s in x('account.bank.statement.line', 'search_read', [['journal_id', '=', mv['journal_id'][0]], ['is_reconciled', '=', False], ['amount', '=', mv['amount_total']]],
                          fields=['date', 'amount', 'payment_ref', 'move_id', 'partner_id'])
             if abs((dt.date.fromisoformat(s['date']) - d0).days) <= 20 and (not s['partner_id'] or not partner or s['partner_id'][0] == partner)]
    plan.append((mv, sorted(pays), partiels, cands, att_pay or att, bank))
    print('%-16s %s %9.2f | %-38s | paiement %s | hash %s | relevé candidat : %s' % (mv['name'], mv['date'], mv['amount_total'], mv['ref'][26:64], sorted(pays), 'oui' if mv.get('inalterable_hash') else 'non',
                                                                                     [(s['date'], (s['payment_ref'] or '')[:28]) for s in cands]))
print('écritures fictives :', len(plan), '| total %.2f' % sum(pl[0]['amount_total'] for pl in plan), '| avec une ligne de relevé candidate :', sum(1 for pl in plan if len(pl[3]) == 1))
if mode != 'apply':
    sys.exit(0)
ok = err = 0; rapp = 0
for mv, pays, partiels, cands, att, bank in plan:
    try:
        if partiels:
            x('account.partial.reconcile', 'unlink', partiels)
        try:
            x('account.move', 'button_draft', [mv['id']])
        except Exception as e:  # noqa: BLE001
            if 'cannot marshal None' not in str(e):
                raise
        x('account.move', 'unlink', [mv['id']])
        tag = 'paiement laissé « en cours »'
        if len(cands) == 1 and pays:
            s = cands[0]
            moves = [pp['move_id'][0] for pp in x('account.payment', 'read', pays, fields=['move_id']) if pp['move_id']]
            l_pay = x('account.move.line', 'search', [['move_id', 'in', moves], ['account_id', '=', att], ['reconciled', '=', False]])
            l_stmt = []
            for ml in x('account.move.line', 'search_read', [['move_id', '=', s['move_id'][0]], ['reconciled', '=', False]], fields=['account_id', 'credit']):
                if ml['account_id'][0] != bank and ml['credit'] > 0:
                    if ml['account_id'][0] != att:
                        x('account.move.line', 'write', [ml['id']], {'account_id': att})
                    l_stmt.append(ml['id'])
            if l_pay and l_stmt:
                try:
                    x('account.move.line', 'reconcile', l_pay + l_stmt)
                except Exception as e:  # noqa: BLE001
                    if 'cannot marshal None' not in str(e):
                        raise
                tag = 'rapproché avec la ligne de relevé du %s' % s['date']; rapp += 1
        ok += 1; print('OK', mv['name'], mv['amount_total'], '->', tag)
    except Exception as e:  # noqa: BLE001
        err += 1; print('ERREUR', mv['name'], ':', str(e).strip().split('\n')[-1][:200])
print('supprimées :', ok, '| rapprochées avec le relevé :', rapp, '| erreurs :', err)
st = x('account.payment', 'read_group', [['company_id', '=', 4], ['memo', 'ilike', 'Reprise historique Sage']], ['amount:sum'], ['state'], lazy=False)
print('paiements Reprise historique Sage Haims :', [(r['state'], r['__count'], round(r['amount'], 2)) for r in st])
inv = x('account.move', 'search_count', [['company_id', '=', 4], ['move_type', '=', 'out_invoice'], ['state', '=', 'posted'], ['payment_state', '=', 'paid'], ['invoice_payments_widget', '!=', False]]) if False else None
print('contrôle factures : FAC/2026/00204 =', x('account.move', 'search_read', [['name', '=', 'FAC/2026/00204'], ['company_id', '=', 4]], fields=['payment_state'])[0]['payment_state'])
