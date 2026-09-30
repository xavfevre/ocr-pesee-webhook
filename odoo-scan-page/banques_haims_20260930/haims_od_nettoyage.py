# -*- coding: utf-8 -*-
"""CARRIERE D'HAIMS, comptes bancaires 512 :
 1. suppression de l'écriture d'ouverture OD/24-25/06/0001 (BP -21 132,72 / BNP -11 152,10 / 890 +32 284,82) ;
 2. suppression des 26 « Extourne reprise » du 26/08/2026 (journal BNP, contrepartie 511900), sans écriture d'origine ;
 3. les 10 lignes de relevé BNP comptabilisées sur 51210001 « BANQUE POPULAIRE » (dont l'ouverture 28 057,09) repassent sur 51210000 BNP.
  python haims_od_nettoyage.py dry | apply"""
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
    return a, (r[0]['balance'] or 0.0) if r else 0.0


ACC_BNP, s_bnp = solde('51210000'); ACC_BPO, s_bpo = solde('51210001'); ACC_BP, s_bp = solde('51200002')
print('soldes avant : 51210000 BNP %.2f | 51210001 BANQUE POPULAIRE %.2f | 51200002 BP %.2f' % (s_bnp, s_bpo, s_bp))
# 1. écriture d'ouverture
od = x('account.move', 'search_read', [['company_id', '=', 4], ['name', '=', 'OD/24-25/06/0001']], fields=['name', 'date', 'state', 'ref', 'line_ids'])
assert len(od) == 1, od
od = od[0]
lo = x('account.move.line', 'read', od['line_ids'], ['account_id', 'balance', 'reconciled', 'name'])
print('1. %s du %s (%s) : %s' % (od['name'], od['date'], od['state'], [(l['account_id'][1][:22], l['balance'], 'lettrée' if l['reconciled'] else '') for l in lo]))
assert abs(sum(l['balance'] for l in lo)) < 0.005 and len(lo) == 3
# 2. extournes
ext = x('account.move', 'search_read', [['company_id', '=', 4], ['ref', 'ilike', 'Extourne reprise'], ['date', '=', '2026-08-26'], ['state', '=', 'posted']], fields=['name', 'ref', 'line_ids', 'journal_id', 'reversed_entry_id'], order='name')
print('2. %d extournes du 26/08/2026 (journal %s) : 26 sur 512 BNP / 511900 et 22 sur 411 / 511900, écritures d origine supprimées' % (len(ext), ext and ext[0]['journal_id'][1]))
assert len(ext) == 48, len(ext)
ACC_511900 = x('account.account', 'search', [['company_ids', 'in', [4]], ['code', '=', '511900']])[0]
ACC_411 = x('account.account', 'search', [['company_ids', 'in', [4]], ['code', '=', '41100000']])[0]
tot_ext = 0.0; tot_411 = 0.0; n_bn = n_pb = 0
for e in ext:
    ls = x('account.move.line', 'read', e['line_ids'], ['account_id', 'balance', 'reconciled'])
    accs = {l['account_id'][0] for l in ls}
    assert len(ls) == 2 and accs in ({ACC_BNP, ACC_511900}, {ACC_411, ACC_511900}), (e['name'], ls)
    assert not any(l['reconciled'] for l in ls), ('ligne lettrée', e['name'])
    assert not e['reversed_entry_id'], e['name']
    if ACC_BNP in accs:
        n_bn += 1; tot_ext += [l['balance'] for l in ls if l['account_id'][0] == ACC_BNP][0]
    else:
        n_pb += 1; tot_411 += [l['balance'] for l in ls if l['account_id'][0] == ACC_411][0]
print('   %d extournes 512 BNP / 511900 : total sur 512 BNP %.2f | %d extournes 411 / 511900 : total sur 411 clients %.2f (débits sans contrepartie)' % (n_bn, tot_ext, n_pb, tot_411))
# 3. lignes de relevé sur 51210001
mal = x('account.move.line', 'search_read', [['account_id', '=', ACC_BPO], ['company_id', '=', 4]], fields=['move_id', 'date', 'balance', 'statement_line_id', 'name', 'parent_state'], order='date')
print('3. %d lignes sur 51210001, total %.2f (toutes de relevé : %s)' % (len(mal), sum(l['balance'] for l in mal), all(l['statement_line_id'] for l in mal)))
for l in mal:
    print('   %s %-20s %10.2f  %s' % (l['date'], l['move_id'][1][:20], l['balance'], (l['name'] or '')[:45]))
print('=> soldes attendus après : 51210000 BNP %.2f (= relevés 36 945,68 + paiements manuels 33 395,31) | 51210001 0,00 | 51200002 BP %.2f (= relevés 44 680,73 + paiements manuels 25 842,97)' % (s_bnp - tot_ext + 11152.10 + sum(l['balance'] for l in mal), s_bp + 21132.72))
if mode != 'apply':
    sys.exit(0)
print('--- application')
ids = [od['id']] + [e['id'] for e in ext]
for mid in ids:
    nom = x('account.move', 'read', [mid], ['name'])[0]['name']
    x('account.move', 'button_draft', [mid])
    try:
        x('account.move', 'unlink', [mid], context={'force_delete': True})
        print('   supprimée :', nom)
    except Exception as e:
        x('account.move', 'button_cancel', [mid])
        print('   suppression refusée (%s) -> annulée :' % str(e)[:80], nom)
mids = sorted({l['move_id'][0] for l in mal})
for mid in mids:
    lids = [l['id'] for l in mal if l['move_id'][0] == mid]
    try:
        x('account.move.line', 'write', lids, {'account_id': ACC_BNP})
    except Exception as e:
        x('account.move', 'button_draft', [mid])
        x('account.move.line', 'write', lids, {'account_id': ACC_BNP})
        x('account.move', 'action_post', [mid])
print('   %d écritures de relevé repassées sur 51210000' % len(mids))
ACC_BNP, s_bnp = solde('51210000'); ACC_BPO, s_bpo = solde('51210001'); ACC_BP, s_bp = solde('51200002')
print('soldes après : 51210000 BNP %.2f | 51210001 %.2f | 51200002 BP %.2f' % (s_bnp, s_bpo, s_bp))
