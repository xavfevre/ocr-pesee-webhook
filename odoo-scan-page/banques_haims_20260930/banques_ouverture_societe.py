# -*- coding: utf-8 -*-
"""Soldes initiaux des banques synchronisées, méthode Odoo, pour une société (1 Maquignon, 3 Chatel) :
 1. suppression de l'OD « Solde initial banque » du 01/01/2024 (OD/23-24/01/0001) : l'ouverture est portée par la ligne
    « Déclaration d'ouverture » de chaque journal (solde de la banque au démarrage de la synchronisation) ;
 2. lignes de relevé comptabilisées sur un autre compte 512 que celui du journal (Maquignon BNP : 512001 « Bank ») ramenées
    sur le compte du journal ;
 3. contrepartie des lignes « Déclaration d'ouverture » = 890 Bilan d'ouverture (ouverture_890.py).
  python banques_ouverture_societe.py <société> dry | apply"""
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


def solde(aid):
    r = x('account.move.line', 'read_group', [['account_id', '=', aid], ['parent_state', '=', 'posted']], ['balance:sum'], [])
    return (r[0]['balance'] or 0.0) if r else 0.0


js = x('account.journal', 'search_read', [['company_id', '=', COMP], ['type', '=', 'bank']], fields=['name', 'default_account_id'], order='id')
# 1. OD d ouverture
od = x('account.move', 'search_read', [['company_id', '=', COMP], ['name', '=', 'OD/23-24/01/0001'], ['state', '!=', 'cancel']], fields=['name', 'date', 'ref', 'state', 'line_ids'])
if od:
    od = od[0]
    lo = x('account.move.line', 'read', od['line_ids'], ['account_id', 'balance', 'reconciled'])
    print('1. %s du %s (%s) : %s' % (od['name'], od['date'], od['state'], [(l['account_id'][1][:24], l['balance'], 'lettrée' if l['reconciled'] else '') for l in lo]))
    assert not any(l['reconciled'] for l in lo)
else:
    print('1. pas d OD d ouverture')
# 2. lignes de relevé hors compte du journal
deplacements = []
for j in js:
    mal = x('account.move.line', 'search_read', [['statement_line_id.journal_id', '=', j['id']], ['account_id.code', '=like', '512%'], ['account_id', '!=', j['default_account_id'][0]], ['parent_state', '=', 'posted']], fields=['move_id', 'account_id', 'balance'])
    if mal:
        deplacements.append((j, mal))
        print('2. %s : %d lignes de relevé sur %s (total %.2f) -> %s' % (j['name'], len(mal), mal[0]['account_id'][1][:24], sum(l['balance'] for l in mal), j['default_account_id'][1][:24]))
if not deplacements:
    print('2. toutes les lignes de relevé sont sur le compte de leur journal')
for j in js:
    print('   %-22s solde compte %s : %.2f' % (j['name'][:22], j['default_account_id'][1][:24], solde(j['default_account_id'][0])))
if mode != 'apply':
    sys.exit(0)
print('--- application')
if od:
    x('account.move', 'button_draft', [od['id']])
    try:
        x('account.move', 'unlink', [od['id']], context={'force_delete': True}); print('   OD supprimée')
    except Exception as e:
        x('account.move', 'button_cancel', [od['id']]); print('   OD annulée (suppression refusée : %s)' % str(e)[:80])
for j, mal in deplacements:
    mids = sorted({l['move_id'][0] for l in mal})
    for mid in mids:
        lids = [l['id'] for l in mal if l['move_id'][0] == mid]
        try:
            x('account.move.line', 'write', lids, {'account_id': j['default_account_id'][0]})
        except Exception:
            x('account.move', 'button_draft', [mid])
            x('account.move.line', 'write', lids, {'account_id': j['default_account_id'][0]})
            x('account.move', 'action_post', [mid])
    print('   %s : %d écritures de relevé ramenées sur %s' % (j['name'], len(mids), j['default_account_id'][1][:24]))
for j in js:
    print('   %-22s solde compte %s : %.2f' % (j['name'][:22], j['default_account_id'][1][:24], solde(j['default_account_id'][0])))
print('   (3. lancer ensuite : python ouverture_890.py %d apply)' % COMP)
