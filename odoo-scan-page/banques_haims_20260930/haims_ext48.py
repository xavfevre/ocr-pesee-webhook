import os, ssl, sys, xmlrpc.client
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [4, 1, 2, 3, 13]}))
mv = x('account.move', 'search_read', [['company_id', '=', 4], ['date', '=', '2026-08-26'], ['journal_id', '=', 48]], fields=['name', 'ref', 'state', 'line_ids', 'reversed_entry_id', 'statement_line_id', 'create_date', 'create_uid'], order='name')
print('%d écritures du 26/08/2026 dans le journal BNP' % len(mv))
combos = Counter()
for e in mv:
    ls = x('account.move.line', 'read', e['line_ids'], ['account_id', 'balance', 'reconciled', 'partner_id'])
    combo = tuple(sorted(l['account_id'][1][:14] for l in ls))
    combos[(combo, e['state'], (e['ref'] or '')[:16])] += 1
    print('%-18s %-7s %-40s relevé %-5s créée %s par %-12s | %s' % (e['name'], e['state'], (e['ref'] or '')[:40], bool(e['statement_line_id']), e['create_date'][:16], (e['create_uid'] or ['', ''])[1][:12], ', '.join('%s %.2f%s' % (l['account_id'][1][:14], l['balance'], ' L' if l['reconciled'] else '') for l in ls)))
print('résumé :', combos)
rep = x('account.move', 'search_read', [['company_id', '=', 4], '|', ['ref', 'ilike', 'reprise'], ['name', 'ilike', 'reprise'], ['ref', 'not ilike', 'Extourne']], fields=['name', 'ref', 'date', 'state', 'journal_id'], limit=20, order='date')
print('écritures « reprise » (non extourne) :', len(rep), [(r['name'], r['date'], r['state'], (r['ref'] or '')[:30]) for r in rep[:20]])
