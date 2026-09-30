# -*- coding: utf-8 -*-
"""Journal Banque Populaire de CARRIERE D'HAIMS (journal 75) : suppression des 9 lignes de relevé importées en double
par la synchronisation après le changement de connecteur du 10/09/2025. Aucune n'est lettrée. Effet attendu sur le solde
des relevés : +4 710,25 € (39 970,48 -> 44 680,73 = solde en ligne de la banque).
  python haims_bp_nettoyage.py dry    -> contrôle sans rien modifier
  python haims_bp_nettoyage.py apply  -> suppression"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [4, 1, 2, 3, 13]}))
JOURNAL = 75
# id à supprimer : (date, montant, début de libellé, id de la ligne conservée)
DOUBLONS = {
    1467: ('2025-09-01', -0.41, 'FRAIS REM.ENCT', 1412),
    1468: ('2025-09-01', 1612.53, 'VIREMENT DISTRIMAT', 1413),
    1469: ('2025-09-01', -235.09, 'LCR S.A.R.L. SARL HYTRA', 1414),
    1470: ('2025-09-01', -265.20, 'LCR S.A.S.   TFC VIENNE', 1415),
    1524: ('2025-09-17', -3428.00, 'PRLV SEPA DGFIP IS-092025', 1526),
    1548: ('2025-09-23', -16.00, 'PRLV SEPA DGFIP PASDSN15092025', 1551),
    1697: ('2025-10-22', -16.00, 'PRLV SEPA DGFIP PASDSN15102025', 1701),
    1710: ('2025-10-23', -2169.00, 'PRLV SEPA DGFIP TVA-102025', 1712),
    1654: ('2025-10-07', -193.08, 'AGIOS DE CPT 3 EME TRIMESTRE 2025', 1626),
}
cie = x('res.company', 'read', [4], ['name', 'fiscalyear_lock_date', 'tax_lock_date'])[0]
print('société :', cie)
lignes = {l['id']: l for l in x('account.bank.statement.line', 'read', list(DOUBLONS) + [v[3] for v in DOUBLONS.values()], ['journal_id', 'date', 'amount', 'payment_ref', 'is_reconciled', 'move_id'])}
total = 0.0
for i, (d, mt, lib, garde) in DOUBLONS.items():
    l, g = lignes[i], lignes[garde]
    assert l['journal_id'][0] == JOURNAL and g['journal_id'][0] == JOURNAL, i
    assert l['date'] == d and abs(l['amount'] - mt) < 0.005 and (l['payment_ref'] or '').startswith(lib), (i, l)
    assert g['date'] == d and abs(g['amount'] - mt) < 0.005, (garde, g)
    assert not l['is_reconciled'], ('ligne lettrée, arrêt', i)
    total += l['amount']
    print('   supprimer %5s %s %11.2f %-45s | conservée %5s %s' % (i, l['date'], l['amount'], (l['payment_ref'] or '')[:45], garde, 'lettrée' if g['is_reconciled'] else 'non lettrée'))
avant = x('account.journal', 'read', [JOURNAL], ['current_statement_balance'])[0]['current_statement_balance']
print('somme des lignes à supprimer : %.2f -> solde des relevés %.2f attendu après suppression : %.2f' % (total, avant, avant - total))
if mode == 'apply':
    x('account.bank.statement.line', 'unlink', list(DOUBLONS))
    apres = x('account.journal', 'read', [JOURNAL], ['current_statement_balance'])[0]['current_statement_balance']
    restes = x('account.bank.statement.line', 'search_count', [['id', 'in', list(DOUBLONS)]])
    print('supprimées ; lignes restantes parmi les 9 : %d ; solde des relevés : %.2f' % (restes, apres))
