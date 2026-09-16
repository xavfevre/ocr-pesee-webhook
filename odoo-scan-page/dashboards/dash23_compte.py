# -*- coding: utf-8 -*-
"""Tableau de bord 23 « Chiffre d'affaires par société » : ajoute un bloc « DÉTAIL PAR COMPTE COMPTABLE »
(pivot account.move.line : société › compte, crédit / débit / CA HT net / quantité), lignes produit ET lignes de taxe
sur comptes de produits (TGAP, REP sont des taxes dans Odoo, imputées sur 707/708) — comparable à la balance Sage.
Usage : python dash23_compte.py dry | apply"""
import os, ssl, sys, json, io, re, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
DID = 23
raw = x('spreadsheet.dashboard', 'read', [DID], fields=['spreadsheet_data'])[0]['spreadsheet_data']
io.open('audit/dash23.BEFORE.json', 'w', encoding='utf-8').write(raw)
js = json.loads(raw)
sh = js['sheets'][0]
assert 'A165' in sh['cells'] and sh['cells']['A165'].startswith('CA PAR ARTICLE'), sh['cells'].get('A165')
assert '4' not in js['pivots']
SHIFT = 60          # le bloc par compte prend 60 lignes (titre + pivot 55 lignes)
NEW_ROW = 165       # position du nouveau bloc (à la place de « CA PAR ARTICLE », décalé)


def shift_addr(a):
    mm = re.match(r'^([A-Z]+)(\d+)$', a)
    col, row = mm.group(1), int(mm.group(2))
    return '%s%d' % (col, row + SHIFT) if row >= NEW_ROW else a


def shift_zone(z):
    return ':'.join(shift_addr(part) for part in z.split(':'))


# cellules, styles, formats, fusions, hauteurs de lignes : décalage de tout ce qui est à partir de la ligne 165
sh['cells'] = {shift_addr(k): v for k, v in sh['cells'].items()}
for key in ('styles', 'formats', 'borders'):
    if isinstance(sh.get(key), dict):
        sh[key] = {shift_zone(k): v for k, v in sh[key].items()}
sh['merges'] = [shift_zone(z) for z in sh.get('merges', [])]
rows = {}
for k, v in (sh.get('rows') or {}).items():
    r = int(k)
    rows[str(r + SHIFT) if r + 1 >= NEW_ROW else k] = v
sh['rows'] = rows
sh['rowNumber'] = max(int(sh.get('rowNumber', 1000)), 1000) + SHIFT
# style du titre : celui de A40 (bandeau)
st_titre = None
for z, sid in sh['styles'].items():
    if z in ('A40:F40', 'A40'):
        st_titre = sid
if st_titre is None:
    st_titre = 3
sh['cells']['A165'] = 'DÉTAIL PAR COMPTE COMPTABLE — ventes + contributions TGAP/REP (comparable à la balance Sage)'
sh['cells']['A166'] = '=PIVOT(4, 55, TRUE, TRUE)'
sh['styles']['A165:H165'] = st_titre
sh['merges'].append('A165:H165')
sh['rows']['164'] = {'size': 30}
sheet_id = sh['id']
js['pivots']['4'] = {
    'type': 'ODOO', 'model': 'account.move.line', 'name': 'CA par compte comptable', 'formulaId': '4',
    'rows': [{'fieldName': 'company_id'}, {'fieldName': 'account_id'}], 'columns': [],
    'measures': [
        {'id': 'credit', 'fieldName': 'credit', 'aggregator': 'sum', 'userDefinedName': 'Crédit'},
        {'id': 'debit', 'fieldName': 'debit', 'aggregator': 'sum', 'userDefinedName': 'Débit'},
        {'id': 'ca_net', 'fieldName': 'ca_net', 'aggregator': 'sum', 'userDefinedName': 'CA HT net',
         'computedBy': {'sheetId': sheet_id, 'formula': '=credit-debit'}},
        {'id': 'quantity', 'fieldName': 'quantity', 'aggregator': 'sum', 'userDefinedName': 'Qté'},
    ],
    'domain': ['&', '&', '&', ['parent_state', '=', 'posted'], ['move_id.move_type', 'in', ['out_invoice', 'out_refund']],
               ['account_id.account_type', 'in', ['income', 'income_other']], ['display_type', 'in', ['product', 'tax']]],
    'context': {}, 'sortedColumn': None,
    'fieldMatching': {'flt_period': {'chain': 'date', 'type': 'date', 'offset': 0},
                      'flt_company': {'chain': 'company_id', 'type': 'many2one'},
                      'flt_categ': {'chain': 'product_id.categ_id', 'type': 'many2one'}},
}
js['pivotNextId'] = 5
data = json.dumps(js, ensure_ascii=False)
io.open('audit/dash23.AFTER.json', 'w', encoding='utf-8').write(data)
print('cellules :', {k: (v if len(str(v)) < 70 else str(v)[:70]) for k, v in sorted(sh['cells'].items(), key=lambda kv: int(re.sub(r'[A-Z]', '', kv[0])))})
print('fusions :', sh['merges'], '| rowNumber :', sh['rowNumber'])
if mode == 'apply':
    x('spreadsheet.dashboard', 'write', [DID], {'spreadsheet_data': data})
    print('tableau de bord 23 mis à jour (sauvegarde audit/dash23.BEFORE.json)')
