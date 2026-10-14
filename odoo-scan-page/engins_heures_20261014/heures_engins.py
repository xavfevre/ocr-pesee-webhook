# -*- coding: utf-8 -*-
"""Heures de fonctionnement des engins non routiers par trimestre / semestre / année (Xavier, 14/10/2026,
« équivalent TICPE pour les engins non routiers »).

Source : relevés de compteur du Parc automobile Odoo (fleet.vehicle.odometer). Pour les engins, le compteur est
l'horamètre (unité « miles » dans Odoo, faute d'unité « heures »). Les engins = catégories Pelle, Chargeuse,
Tombereau, Chariot élévateur, ou compteur en « miles ».

Méthode : le compteur à chaque borne de période (1er janvier, 1er avril, 1er juillet, 1er octobre, 31 décembre) est
interpolé linéairement entre les deux relevés qui l'encadrent (prorata temporis) ; heures de la période = différence.
Aucune extrapolation : avant le premier relevé ou après le dernier, la période est partielle (noté) ou vide.
Un relevé inférieur au précédent (remise à zéro, faute de frappe) ouvre un nouveau segment et est signalé.

   python heures_engins.py            -> années 2024, 2025, 2026 (jusqu'au dernier relevé)
   python heures_engins.py 2025 2026  -> années choisies
Sortie : Desktop/Maquignon/Heures_engins_non_routiers_<date>.xlsx (une feuille par année + Relevés + Méthode).
Identifiants attendus dans l'environnement : ODOO_USER, ODOO_PWD."""
import os, sys, xmlrpc.client, collections
from datetime import date, datetime, timedelta
sys.stdout.reconfigure(encoding='utf-8')
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ANNEES = [int(a) for a in sys.argv[1:]] or [2024, 2025, 2026]
CATEGORIES = ('Pelle', 'Chargeuse', 'Tombereau', 'Chariot élévateur')
SORTIE = r"C:\Users\xavfe\Desktop\Maquignon\Heures_engins_non_routiers_%s.xlsx" % date.today().strftime('%Y-%m-%d')
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common').authenticate(D, us, p, {})
assert uid, 'authentification refusée'
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object')
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'active_test': False, 'allowed_company_ids': [1, 3, 4]}))

veh = x('fleet.vehicle', 'search_read', [], fields=['name', 'license_plate', 'category_id', 'odometer', 'odometer_unit', 'company_id', 'active', 'model_id'], limit=500)
engins = [v for v in veh if v['odometer_unit'] == 'miles' or (v['category_id'] and v['category_id'][1] in CATEGORIES)]
engins.sort(key=lambda v: ((v['category_id'] and v['category_id'][1]) or 'zzz', v['name']))
logs = x('fleet.vehicle.odometer', 'search_read', [['vehicle_id', 'in', [v['id'] for v in engins]]], fields=['vehicle_id', 'date', 'value'], limit=10000, order='date')
releves = collections.defaultdict(list)
for l in logs:
    releves[l['vehicle_id'][0]].append((datetime.strptime(l['date'], '%Y-%m-%d').date(), float(l['value'])))


MAX_H_JOUR = 24.0   # un horamètre ne peut pas avancer de plus de 24 h par jour


def nettoie(pts):
    """Trie les relevés, écarte les relevés aberrants et découpe en segments.
    - relevé plus petit que le précédent : si un relevé ultérieur revient au-dessus du précédent, c'est une faute de
      frappe -> écarté ; sinon c'est une remise à zéro (nouveau compteur) -> nouveau segment ;
    - relevé qui ferait avancer le compteur de plus de 24 h/jour : faute de frappe -> écarté si la suite est cohérente
      avec le relevé précédent.
    Retourne (segments, anomalies) ; anomalies = liste de (date, valeur, explication)."""
    pts = sorted(pts); segs, cur, anomalies = [], [], []
    for i, (d, v) in enumerate(pts):
        if cur:
            dp, vp = cur[-1]; jours = max((d - dp).days, 1); suite = pts[i + 1:]
            if v < vp:
                if any(s[1] >= vp for s in suite):
                    anomalies.append((d, v, 'relevé inférieur au précédent (%s le %s) alors que les suivants repassent au-dessus : faute de frappe probable, relevé ignoré' % (int(vp), dp.strftime('%d/%m/%Y')))); continue
                anomalies.append((d, v, 'compteur en baisse (%s le %s) et jamais rattrapé : remise à zéro ou changement de compteur, nouvelle série' % (int(vp), dp.strftime('%d/%m/%Y'))))
                segs.append(cur); cur = [(d, v)]; continue
            if v - vp > MAX_H_JOUR * jours + 24:
                coherent = [s for s in suite if 0 <= s[1] - vp <= MAX_H_JOUR * max((s[0] - dp).days, 1) + 24]
                if coherent or not suite:
                    anomalies.append((d, v, '+%s h en %d jour(s) depuis %s : impossible (> 24 h/jour), faute de frappe probable, relevé ignoré' % (int(v - vp), jours, int(vp)))); continue
                anomalies.append((d, v, '+%s h en %d jour(s) : > 24 h/jour mais la suite confirme ce niveau, relevé gardé (vérifier le relevé précédent %s)' % (int(v - vp), jours, int(vp))))
        cur.append((d, v))
    if cur:
        segs.append(cur)
    return segs, anomalies


def segments(pts):
    return nettoie(pts)[0]


def valeur_a(seg, d):
    """Compteur interpolé à la date d dans le segment (None hors du segment)."""
    if d < seg[0][0] or d > seg[-1][0]:
        return None
    for (d1, v1), (d2, v2) in zip(seg, seg[1:]):
        if d1 <= d <= d2:
            return v1 if d2 == d1 else v1 + (v2 - v1) * (d - d1).days / (d2 - d1).days
    return seg[-1][1]


def heures(seg_list, debut, fin):
    """Heures entre debut et fin (fin incluse = compteur au soir de fin -> borne fin+1 jour), sur tous les segments.
    Retourne (heures, couverture) : couverture = 'complet', 'partiel' (une partie de la période seulement) ou None."""
    fin1 = fin + timedelta(days=1)
    total, couv = 0.0, None
    for seg in seg_list:
        a, b = max(debut, seg[0][0]), min(fin1, seg[-1][0])
        if a >= b:
            continue
        va, vb = valeur_a(seg, a), valeur_a(seg, b)
        if va is None or vb is None:
            continue
        total += vb - va
        couv = 'complet' if (a == debut and b == fin1 and couv in (None, 'complet')) else 'partiel'
    return (round(total), couv) if couv else (None, None)


wb = Workbook(); wb.remove(wb.active)
gras = Font(bold=True); titre = Font(bold=True, size=13); fond = PatternFill('solid', fgColor='EEF2FF'); gris = Font(color='64748B', italic=True)
bord = Border(bottom=Side(style='thin', color='CBD5E1'))
for an in ANNEES:
    ws = wb.create_sheet(str(an))
    ws['A1'] = "Heures de fonctionnement des engins non routiers %d (horamètres du Parc automobile Odoo, interpolation entre relevés)" % an; ws['A1'].font = titre
    ent = ['Catégorie', 'Engin', 'Société', 'Actif', 'T1', 'T2', 'T3', 'T4', 'S1', 'S2', 'Année', 'Relevés utilisés', 'Dernier relevé', 'Compteur', 'Remarques']
    ws.append([]); ws.append(ent)
    for c in ws[3]:
        c.font = gras; c.fill = fond; c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    per = {'T1': (date(an, 1, 1), date(an, 3, 31)), 'T2': (date(an, 4, 1), date(an, 6, 30)), 'T3': (date(an, 7, 1), date(an, 9, 30)), 'T4': (date(an, 10, 1), date(an, 12, 31)),
           'S1': (date(an, 1, 1), date(an, 6, 30)), 'S2': (date(an, 7, 1), date(an, 12, 31)), 'Année': (date(an, 1, 1), date(an, 12, 31))}
    tot = collections.Counter()
    for v in engins:
        pts = releves.get(v['id'], [])
        segs, anomalies = nettoie(pts)
        rem = ['%s : %s' % (d.strftime('%d/%m/%Y'), txt) for d, val, txt in anomalies]
        if v['odometer_unit'] != 'miles':
            rem.append("unité du compteur « %s » dans Odoo (pas « miles » = heures) : à vérifier" % v['odometer_unit'])
        if pts and v['odometer'] and abs(v['odometer'] - max(p[1] for p in pts)) > 0.5:
            rem.append('fiche véhicule : compteur %s différent du plus grand relevé %s' % (int(v['odometer']), int(max(p[1] for p in pts))))
        ligne = [(v['category_id'] and v['category_id'][1]) or '', v['name'], (v['company_id'] and v['company_id'][1]) or '', 'oui' if v['active'] else 'archivé']
        partiel = []
        for k in ('T1', 'T2', 'T3', 'T4', 'S1', 'S2', 'Année'):
            h, couv = heures(segs, *per[k])
            ligne.append(h if h is not None else '')
            if couv == 'partiel':
                partiel.append(k)
            if h is not None and k in ('T1', 'T2', 'T3', 'T4'):
                tot[k] += h
        n_an = [p for p in pts if p[0].year == an]
        dans = [p for p in pts if date(an - 1, 1, 1) <= p[0] <= date(an + 1, 12, 31)]
        if partiel:
            rem.insert(0, 'période(s) couverte(s) en partie seulement (relevés manquants) : ' + ', '.join(partiel))
        if not pts:
            rem.append('aucun relevé de compteur dans Odoo')
        ligne += [len(dans), pts[-1][0].strftime('%d/%m/%Y') + ' (%s h)' % int(pts[-1][1]) if pts else '', int(v['odometer']) if v['odometer'] else '', ' ; '.join(rem)]
        ws.append(ligne)
    ws.append([]); ws.append(['', 'TOTAL engins (périodes renseignées)', '', '', tot['T1'], tot['T2'], tot['T3'], tot['T4'], tot['T1'] + tot['T2'], tot['T3'] + tot['T4'], sum(tot.values())])
    for c in ws[ws.max_row]:
        c.font = gras
    for i, w in enumerate([16, 46, 20, 8, 8, 8, 8, 8, 9, 9, 9, 9, 20, 10, 70], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=4, max_row=ws.max_row):
        for c in row[4:11]:
            c.number_format = '# ##0'; c.alignment = Alignment(horizontal='right')
        row[14].alignment = Alignment(wrap_text=True, vertical='top'); row[1].alignment = Alignment(vertical='top')
    ws.freeze_panes = 'C4'
ws = wb.create_sheet('Anomalies à corriger')
ws.append(['Engin', 'Date du relevé', 'Valeur saisie (h)', 'Problème', 'À faire dans Odoo (Parc automobile > engin > Compteur)'])
for c in ws[1]:
    c.font = gras; c.fill = fond
n_anom = 0
for v in engins:
    for d, val, txt in nettoie(releves.get(v['id'], []))[1]:
        ws.append([v['name'], d, int(val), txt, 'corriger ou supprimer ce relevé, puis relancer le calcul']); n_anom += 1
    if v['odometer_unit'] != 'miles':
        ws.append([v['name'], '', '', "unité du compteur « %s » : pour un engin, mettre « miles » (= heures)" % v['odometer_unit'], 'fiche engin, champ Unité du compteur']); n_anom += 1
    if not releves.get(v['id']) and v['active']:
        ws.append([v['name'], '', '', 'aucun relevé de compteur', 'saisir un relevé (date + heures) à chaque fin de trimestre']); n_anom += 1
for i, w in enumerate([46, 14, 16, 110, 52], 1):
    ws.column_dimensions[get_column_letter(i)].width = w
for row in ws.iter_rows(min_row=2):
    row[1].number_format = 'DD/MM/YYYY'; row[3].alignment = Alignment(wrap_text=True, vertical='top')
ws.freeze_panes = 'A2'
ws = wb.create_sheet('Relevés')
ws.append(['Engin', 'Date', 'Compteur (h)', 'Écart avec le relevé précédent (h)', 'Jours écoulés', 'h / jour', 'Retenu'])
for c in ws[1]:
    c.font = gras; c.fill = fond
for v in engins:
    prev = None; ecartes = {(d, val) for d, val, _ in nettoie(releves.get(v['id'], []))[1] if 'ignoré' in _}
    for d, val in sorted(releves.get(v['id'], [])):
        ws.append([v['name'], d, int(val), int(val - prev[1]) if prev else '', (d - prev[0]).days if prev else '', round((val - prev[1]) / (d - prev[0]).days, 2) if prev and (d - prev[0]).days else '', 'non (aberrant)' if (d, val) in ecartes else 'oui'])
        prev = (d, val)
for i, w in enumerate([46, 12, 14, 30, 14, 10, 14], 1):
    ws.column_dimensions[get_column_letter(i)].width = w
for row in ws.iter_rows(min_row=2):
    row[1].number_format = 'DD/MM/YYYY'
ws.freeze_panes = 'A2'
ws = wb.create_sheet('Méthode')
for l in ["Heures de fonctionnement des engins non routiers : méthode",
          "", "Source : relevés d'horamètre saisis dans Odoo, Parc automobile, onglet Compteur de chaque engin (fleet.vehicle.odometer). L'unité « miles » y tient lieu d'heures.",
          "Engins retenus : catégories Pelle, Chargeuse, Tombereau, Chariot élévateur, ou compteur en « miles ». Les véhicules routiers (compteur en km) sont exclus.",
          "Calcul : le compteur au début et à la fin de chaque période est interpolé entre les deux relevés qui l'encadrent, au prorata des jours ; heures de la période = différence.",
          "Pas d'extrapolation : avant le premier relevé ou après le dernier, la période n'est couverte qu'en partie (indiqué dans Remarques) ; sans relevé encadrant, la case reste vide.",
          "Un relevé plus petit que le précédent (remise à zéro, erreur de frappe) est signalé et les deux séries sont traitées séparément.",
          "", "Pour des chiffres exacts par trimestre : saisir un relevé d'horamètre par engin à chaque fin de trimestre (31/03, 30/06, 30/09, 31/12) dans Odoo, ou les récupérer automatiquement d'un logiciel carburant (compteur saisi à chaque plein).",
          "Généré le %s par heures_engins.py (dépôt ocr-pesee-webhook, odoo-scan-page/engins_heures_20261014)." % date.today().strftime('%d/%m/%Y')]:
    ws.append([l])
ws['A1'].font = titre; ws.column_dimensions['A'].width = 160
wb.save(SORTIE)
print('engins :', len(engins), '| relevés :', len(logs), '| anomalies :', n_anom, '| fichier :', SORTIE)
for an in ANNEES:
    s = wb[str(an)]; r = s.max_row
    print('  %d : T1 %s  T2 %s  T3 %s  T4 %s  année %s' % (an, s.cell(r, 5).value, s.cell(r, 6).value, s.cell(r, 7).value, s.cell(r, 8).value, s.cell(r, 11).value))
