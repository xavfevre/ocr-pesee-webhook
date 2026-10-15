# -*- coding: utf-8 -*-
"""Le chargeur accepte en source le tableau de validation (feuille « Validation », colonnes A code, B pierre, C unité,
F pro 01/11, G pro 01/01, J particulier 01/11, K particulier 01/01, M validé) : ce que Xavier valide est ce qui est chargé.
Lignes marquées « non » en M ignorées."""
import io
p = 'tarifs_pierres_2027.py'
s = io.open(p, encoding='utf-8').read()
old = """wb = load_workbook(FICHIER, data_only=False)
w = wb['Grille 2027 (2)']
pierres, cat = [], None
for r in range(2, w.max_row + 1):
"""
new = """wb = load_workbook(FICHIER, data_only=False)
pierres, cat = [], None
if 'Validation' in wb.sheetnames:            # tableau validé par Xavier (tableau_validation.py) : source prioritaire
    wv = wb['Validation']
    for r in range(5, wv.max_row + 1):
        code, nom, unite = (wv.cell(r, c).value for c in (1, 2, 3))
        if not nom or not unite:
            continue                          # ligne de catégorie ou vide
        F, G, J, K_, valide = (wv.cell(r, c).value for c in (6, 7, 10, 11, 13))
        if isinstance(valide, str) and valide.strip().lower().startswith('n'):
            continue
        a = ('[%s] %s' % (code, nom)) if code else nom
        mm_ep = re.search(r'\((\d+)\s*cm\)', a)
        pierres.append({'art': a, 'cat': 'validation', 'pro_2026': None, 'pro_v1': nombre(F), 'pro_2027': nombre(G), 'part_v1_valide': nombre(J), 'part_2027': nombre(K_),
                        'unite': unite.strip(), 'ep': (int(mm_ep.group(1)) / 100.0) if (unite.strip() == 'm²' and mm_ep) else None})
    print('source : tableau de validation (%d lignes)' % len(pierres))
w = wb['Grille 2027 (2)'] if 'Grille 2027 (2)' in wb.sheetnames else None
for r in (range(2, w.max_row + 1) if (w is not None and not pierres) else []):
"""
assert old in s; s = s.replace(old, new)
# vague 1 particulier : valeur validée si présente (sinon O ÷ 1,1)
old = """    q.update(pid=pr['id'], fiche=pr['lst_price'], actif=pr['active'], pro_v1=round(q['pro_v1']), pro_v2=round(q['pro_2027']),
             part_v1=round(q['part_2027'] / 1.1), part_v2=round(q['part_2027']))
"""
new = """    q.update(pid=pr['id'], fiche=pr['lst_price'], actif=pr['active'], pro_v1=round(q['pro_v1']), pro_v2=round(q['pro_2027']),
             part_v1=round(q['part_v1_valide']) if q.get('part_v1_valide') else round(q['part_2027'] / 1.1), part_v2=round(q['part_2027']))
"""
assert old in s; s = s.replace(old, new)
# les prix "à 1 €" : le test existant garde son sens ; pro_v1 absent -> ignorer
old = """    if not q['pro_2027'] or q['pro_2027'] <= 1 or not q['part_2027'] or q['part_2027'] <= 1:
        ignores.append((q['art'], 'prix à 1 € = sur devis')); continue
"""
new = """    if not q['pro_2027'] or q['pro_2027'] <= 1 or not q['part_2027'] or q['part_2027'] <= 1 or not q['pro_v1']:
        ignores.append((q['art'], 'prix à 1 € ou absent = sur devis')); continue
"""
assert old in s; s = s.replace(old, new)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('chargeur : source « Validation » acceptée')
