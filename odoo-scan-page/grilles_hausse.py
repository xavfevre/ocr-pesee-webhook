# -*- coding: utf-8 -*-
"""Grille simple + hausse 2027 : reprend Grille_simple_Maquignon_<date>.xlsx (prix observés, Particulier / Pro proposés,
colonnes clients) et ajoute PARTICULIER 2027 / PRO 2027 = prix proposé × (1 + taux de la famille), arrondis, avec un onglet
« Hausse » (taux par famille, impact sur le CA 2026 annualisé). Usage : python grilles_hausse.py [pierres%] [granulats%] [transport%] [prestations%]"""
import sys, io, re, datetime, collections
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
sys.stdout.reconfigure(encoding='utf-8')
today = datetime.date.today().strftime('%Y-%m-%d')
TAUX = {'Pierres': 4.0, 'Granulats / terre': 4.0, 'Transport / location': 5.0, 'Prestations / divers': 4.0}
for i, k in enumerate(['Pierres', 'Granulats / terre', 'Transport / location', 'Prestations / divers']):
    if len(sys.argv) > i + 1:
        TAUX[k] = float(sys.argv[i + 1].replace(',', '.'))
CA_2026 = {'Pierres': 648438, 'Transport / location': 576051, 'Prestations / divers': 199400, 'Granulats / terre': 191064}   # factures - avoirs, 01/01 -> 17/09/2026
MOIS = 8.55


def famille(n):
    n = n.lower()
    if any(t in n for t in ('pré-sciée', 'pre-sciee', 'tranche', 'bloc', 'tuffeau', 'haims', 'migné', 'richemont', 'tervoux', 'sireuil')):
        return 'Pierres'
    if any(t in n for t in ('transport', 'location', 'transfert')):
        return 'Transport / location'
    if any(t in n for t in ('gobetage', 'gravier', 'concass', 'sable', 'terre', 'décharge', 'béton', 'remblai')):
        return 'Granulats / terre'
    return 'Prestations / divers'


def arrondi(v, fam, unite):
    if v is None or v == '':
        return None
    if fam == 'Pierres':
        return round(v) if v >= 300 else round(v * 10) / 10          # m³ à l'euro, m² au dixième
    if fam == 'Granulats / terre':
        return round(v * 20) / 20 if v < 50 else round(v)             # tonne : 0,05 €
    if fam == 'Transport / location':
        return round(v * 20) / 20 if v < 50 else round(v)             # tonne : 0,05 € ; forfaits à l'euro
    return round(v * 2) / 2 if v < 20 else round(v)                   # prestations


src = 'C:/Users/xavfe/Desktop/Maquignon/Grille_simple_Maquignon_2026-09-17.xlsx'
wb0 = openpyxl.load_workbook(src)
ws0 = wb0['Grille']
rows = list(ws0.iter_rows(values_only=True))
hdr = list(rows[0]); data = rows[1:]
wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Grille'
H = Font(bold=True, color='FFFFFF'); HF = PatternFill('solid', fgColor='01666B'); JAUNE = PatternFill('solid', fgColor='FFF2CC'); VERT = PatternFill('solid', fgColor='E2EFDA'); ORANGE = PatternFill('solid', fgColor='F8CBAD'); GRIS = PatternFill('solid', fgColor='EDEDED')
new_hdr = hdr[:7] + ['Famille', 'Hausse %', 'PARTICULIER 2027', 'PRO 2027'] + hdr[7:]
ws.append(new_hdr)
for i, cell in enumerate(ws[1], 1):
    cell.font = H; cell.fill = HF; cell.alignment = Alignment(wrap_text=True, vertical='center')
    ws.column_dimensions[get_column_letter(i)].width = 50 if i == 1 else (7 if i == 2 else (18 if i == 8 else (11 if i <= 11 else 13)))
ws.row_dimensions[1].height = 48; ws.freeze_panes = 'C2'
impact = collections.Counter()
for r in data:
    fam = famille(r[0] or ''); taux = TAUX[fam]
    part, pro = r[5], r[6]
    p27 = arrondi(part * (1 + taux / 100), fam, r[1]) if isinstance(part, (int, float)) and part else None
    o27 = arrondi(pro * (1 + taux / 100), fam, r[1]) if isinstance(pro, (int, float)) and pro else None
    ws.append(list(r[:7]) + [fam, taux, p27, o27] + list(r[7:]))
    n = ws.max_row
    ws.cell(n, 6).fill = JAUNE; ws.cell(n, 7).fill = JAUNE; ws.cell(n, 10).fill = VERT; ws.cell(n, 11).fill = VERT
    for j in range(12, len(new_hdr) + 1):
        v = ws.cell(n, j).value
        if v is None:
            ws.cell(n, j).fill = GRIS
        elif isinstance(pro, (int, float)) and pro and abs(v - pro) / pro > 0.02:
            ws.cell(n, j).fill = ORANGE
ws.auto_filter.ref = ws.dimensions
w2 = wb.create_sheet('Hausse')
w2.append(['Famille', 'Hausse proposée %', 'CA facturé 2026 (01/01 → 17/09)', 'CA 2026 annualisé', 'Gain annuel estimé'])
for cell in w2[1]:
    cell.font = H; cell.fill = HF; cell.alignment = Alignment(wrap_text=True)
tot = [0, 0]
for fam, ca in CA_2026.items():
    an = ca * 12 / MOIS; g = an * TAUX[fam] / 100; tot[0] += an; tot[1] += g
    w2.append([fam, TAUX[fam], round(ca), round(an), round(g)])
w2.append(['TOTAL', round(tot[1] / tot[0] * 100, 1), round(sum(CA_2026.values())), round(tot[0]), round(tot[1])])
w2.append([]); w2.append(['Arrondis : pierres au m³ à l\'euro, au m² au dixième ; granulats et transport à la tonne à 0,05 €, forfaits à l\'euro ; prestations à l\'euro.'])
w2.append(['Les prix spécifiques clients (colonnes de droite) suivent la même hausse que la grille pro, sauf indication contraire de ta part.'])
w2.append(['Référence : sources professionnelles 2026, matériaux de construction +4 à +7 % vs 2025 ; alerte UNICEM de mars 2026 sur le carburant (production et transport des granulats).'])
for col, w in zip('ABCDE', (26, 16, 24, 18, 18)):
    w2.column_dimensions[col].width = w
if 'Lisez-moi' in wb0.sheetnames:
    w3 = wb.create_sheet('Lisez-moi'); w3.column_dimensions['A'].width = 120
    for r in wb0['Lisez-moi'].iter_rows(values_only=True):
        w3.append(list(r))
out = 'C:/Users/xavfe/Desktop/Maquignon/Grille_simple_Maquignon_hausse_2027_%s.xlsx' % today
wb.save(out)
print('fichier :', out, '| lignes :', ws.max_row - 1)
print('taux :', TAUX, '| CA annualisé %.0f € -> gain estimé %.0f €/an (%.1f %%)' % (tot[0], tot[1], tot[1] / tot[0] * 100))
for r in list(ws.iter_rows(min_row=2, max_row=9, values_only=True)):
    print('   %-46s %-4s part %8s -> %8s | pro %8s -> %8s (%s +%s %%)' % ((r[0] or '')[:46], r[1], r[5], r[9], r[6], r[10], r[7], r[8]))
