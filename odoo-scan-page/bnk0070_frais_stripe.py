# -*- coding: utf-8 -*-
"""BNK1/26-27/0070 (SARL MAQUIGNON, virement Stripe du 11/05/2026, brouillon) : la ligne de 2,47 € au débit du client
Patrimoine et Création passe en frais bancaires Stripe, puis l'écriture est comptabilisée. Usage : dry | apply"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
ctx = {'allowed_company_ids': [1]}
# comptes 627 de la société et pratique existante pour les frais Stripe
cpt = x('account.account', 'search_read', [['code', '=like', '627%'], ['company_ids', 'in', [1]]], fields=['code', 'name'], order='code', context=ctx)
print('comptes 627 :', [(a['code'], a['name']) for a in cpt])
prat = x('account.move.line', 'read_group', [['company_id', '=', 1], ['account_id.code', '=like', '6%'], '|', ['name', 'ilike', 'stripe'], ['move_id.ref', 'ilike', 'stripe'], ['parent_state', '=', 'posted']],
         ['balance:sum'], ['account_id'], lazy=False, context=ctx)
print('frais Stripe déjà comptabilisés (écritures validées, comptes 6) :', [(r['account_id'][1], round(r['balance'], 2), r['__count']) for r in prat])
stripe = [a for a in cpt if 'stripe' in a['name'].lower()]
if prat:
    best = max(prat, key=lambda r: r['__count'])['account_id']
    compte = x('account.account', 'read', [best[0]], fields=['code', 'name'], context=ctx)[0]
elif stripe:
    compte = stripe[0]
else:
    compte = next((a for a in cpt if 'commission' in a['name'].lower() or 'service' in a['name'].lower()), cpt[0] if cpt else None)
print('compte retenu :', compte and (compte['code'], compte['name']))
mv = x('account.move', 'search_read', [['name', '=', 'BNK1/26-27/0070'], ['company_id', '=', 1]], fields=['state', 'line_ids', 'date'], context=ctx)[0]
lines = x('account.move.line', 'read', mv['line_ids'], fields=['account_id', 'partner_id', 'debit', 'credit', 'name', 'reconciled'], context=ctx)
cible = [l for l in lines if l['account_id'][1].startswith('41100000') and abs(l['debit'] - 2.47) < 0.005 and not l['reconciled']]
print('écriture :', mv['state'], mv['date'], '| ligne 2,47 trouvée :', [(l['id'], l['name']) for l in cible])
if mode == 'apply' and compte and len(cible) == 1 and mv['state'] == 'draft':
    x('account.move.line', 'write', [cible[0]['id']], {'account_id': compte['id'], 'name': 'Frais Stripe (commission sur virement)'}, context=ctx)
    try:
        x('account.move', 'action_post', [mv['id']], context=ctx)
    except Exception as e:  # noqa: BLE001
        if 'cannot marshal None' not in str(e):
            raise
    mv2 = x('account.move', 'read', [mv['id']], fields=['state'], context=ctx)[0]
    print('après : état', mv2['state'])
    for l in x('account.move.line', 'read', mv['line_ids'], fields=['account_id', 'partner_id', 'debit', 'credit', 'name', 'reconciled'], context=ctx):
        print('   ', l['account_id'][1][:40], (l['partner_id'] and l['partner_id'][1][:24]) or '-', 'D', l['debit'], 'C', l['credit'], 'lettré' if l['reconciled'] else '', (l['name'] or '')[:40])
    inv = x('account.move', 'search_read', [['name', '=', 'FAC/26-27/0265']], fields=['payment_state', 'amount_residual'], context=ctx)[0]
    print('facture FAC/26-27/0265 :', inv['payment_state'], 'reste', inv['amount_residual'])
