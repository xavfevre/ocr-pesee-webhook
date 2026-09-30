import os, ssl, sys, re, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [4, 1, 2, 3, 13], 'active_test': False}))
for jid in (75, 48):
    j = x('account.journal', 'read', [jid], ['name', 'default_account_id', 'current_statement_balance', 'kanban_dashboard'])[0]
    ab = re.search(r'"account_balance": ?"([^"]*)"', j['kanban_dashboard'] or '')
    print('journal %-16s compte %-36s solde relevés %10.2f | solde comptable %s' % (j['name'], j['default_account_id'][1], j['current_statement_balance'], ab and ab.group(1).replace('\u00a0', ' ').replace('\u20ac', '€')))
for code in ('51200001', '51200002', '51210000', '51210001'):
    a = x('account.account', 'search_read', [['company_ids', 'in', [4]], ['code', '=', code]], fields=['name', 'active', 'account_type'])
    if not a:
        print(code, ': absent'); continue
    a = a[0]
    r = x('account.move.line', 'read_group', [['account_id', '=', a['id']], ['parent_state', '=', 'posted']], ['balance:sum'], [])
    n = x('account.move.line', 'search_count', [['account_id', '=', a['id']]])
    st = x('account.move.line', 'search_count', [['account_id', '=', a['id']], ['statement_line_id', '!=', False]])
    print('%s %-30s %-8s %-10s lignes %4d (relevé %4d) solde %10.2f' % (code, a['name'][:30], 'actif' if a['active'] else 'ARCHIVÉ', a['account_type'], n, st, (r[0]['balance'] or 0.0) if r else 0.0))
# cohérence : toute ligne de relevé du journal BP doit être sur le compte du journal
mal = x('account.move.line', 'search_count', [['statement_line_id.journal_id', '=', 75], ['account_id.code', '!=', '51210001'], ['account_id.code', '=like', '512%']])
print('lignes de relevé BP sur un autre 512 que 51210001 :', mal)
