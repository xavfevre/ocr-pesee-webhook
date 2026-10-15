# -*- coding: utf-8 -*-
"""Patch du chargeur tarifs_pierres_2027.py (15/10/2026) : les prix de la grille sont au m² pour les pierres d'épaisseur
(colonne « Unité » = m²) alors que les listes de prix Odoo sont au m³ (le devis multiplie par l'épaisseur « Larg. (m) »
quand « Vente m2 » est coché). On convertit donc : prix m³ = prix m² ÷ épaisseur nominale (« (4 cm) » -> 0,04).
Les articles « à l'unité » (unité grille « Unité ») restent sur devis : exclus."""
import io, re
p = 'tarifs_pierres_2027.py'
s = io.open(p, encoding='utf-8').read()

# 1) lecture : garder l'unité de la grille et l'épaisseur nominale
old = """    K, L, M, O = (w.cell(r, c).value for c in (11, 12, 13, 15))
    if isinstance(L, str) and L.startswith('='):
        L = (M / 1.1) if ('/1.1' in L and nombre(M)) else (K * 1.03 if nombre(K) else None)
    pierres.append({'art': a, 'cat': cat.split('›')[-1].strip(), 'pro_2026': nombre(K), 'pro_v1': nombre(L), 'pro_2027': nombre(M), 'part_2027': nombre(O)})
"""
new = """    K, L, M, O = (w.cell(r, c).value for c in (11, 12, 13, 15))
    if isinstance(L, str) and L.startswith('='):
        L = (M / 1.1) if ('/1.1' in L and nombre(M)) else (K * 1.03 if nombre(K) else None)
    unite = (w.cell(r, 2).value or '').strip()
    mm_ep = re.search(r'\\((\\d+)\\s*cm\\)', a)
    pierres.append({'art': a, 'cat': cat.split('›')[-1].strip(), 'pro_2026': nombre(K), 'pro_v1': nombre(L), 'pro_2027': nombre(M), 'part_2027': nombre(O),
                    'unite': unite, 'ep': (int(mm_ep.group(1)) / 100.0) if (unite == 'm²' and mm_ep) else None})
"""
assert old in s; s = s.replace(old, new)

# 2) appariement : exclusions + conversion m² -> m³
old = """    if not q['pro_2027'] or q['pro_2027'] <= 1 or not q['part_2027'] or q['part_2027'] <= 1:
        ignores.append((q['art'], 'prix à 1 € = sur devis')); continue
    q.update(pid=pr['id'], fiche=pr['lst_price'], actif=pr['active'], pro_v1=round(q['pro_v1']), pro_v2=round(q['pro_2027']),
             part_v1=round(q['part_2027'] / 1.1), part_v2=round(q['part_2027']))
    actifs.append(q)
pids = {q['pid'] for q in actifs}
"""
new = """    if not q['pro_2027'] or q['pro_2027'] <= 1 or not q['part_2027'] or q['part_2027'] <= 1:
        ignores.append((q['art'], 'prix à 1 € = sur devis')); continue
    if q['unite'] == 'Unité':
        ignores.append((q['art'], 'article à l unité : reste sur devis')); continue
    if q['unite'] == 'm²' and not q['ep']:
        ignores.append((q['art'], 'prix au m² mais épaisseur introuvable dans le nom')); continue
    # prix de la grille arrondis à l'euro (m² ou m³ selon la grille), puis prix Odoo au m³ = prix m² ÷ épaisseur
    q.update(pid=pr['id'], fiche=pr['lst_price'], actif=pr['active'], pro_v1=round(q['pro_v1']), pro_v2=round(q['pro_2027']),
             part_v1=round(q['part_2027'] / 1.1), part_v2=round(q['part_2027']))
    q['coef'] = (1.0 / q['ep']) if q['ep'] else 1.0
    for k in ('pro_v1', 'pro_v2', 'part_v1', 'part_v2'):
        q[k + '_m3'] = round(q[k] * q['coef'], 2)
    actifs.append(q)
pids = {q['pid'] for q in actifs}
coef_de = {q['pid']: q['coef'] for q in actifs}
"""
assert old in s; s = s.replace(old, new)

# 3) onglets clients : mêmes conversions
old = """        if p26 and p27:
            lignes.append({'art': a, 'pid': pr['id'], 'prix_2026': round(p26, 2), 'prix_2027': round(p27)})
"""
new = """        if p26 and p27:
            c = coef_de[pr['id']]
            lignes.append({'art': a, 'pid': pr['id'], 'prix_2026': round(p26, 2), 'prix_2027': round(p27), 'prix_2026_m3': round(round(p26, 2) * c, 2), 'prix_2027_m3': round(round(p27) * c, 2)})
"""
assert old in s; s = s.replace(old, new)

# 4) affichage
old = """print('%-62s %8s | pro 2026 %8s -> 01/11 %6s -> 2027 %6s | part 01/11 %6s -> 2027 %6s' % ('article', 'fiche', '', '', '', '', ''))
for q in actifs:
    print('%-62s %8.2f | pro 2026 %8s -> 01/11 %6d -> 2027 %6d | part 01/11 %6d -> 2027 %6d%s' % (q['art'][:62], q['fiche'] or 0, q['pro_2026'], q['pro_v1'], q['pro_v2'], q['part_v1'], q['part_v2'], '' if q['actif'] else '  (archivé)'))
"""
new = """print('%-58s %-3s %9s | pro 2026 %7s -> 01/11 %6s -> 2027 %6s | part 01/11 %6s -> 2027 %6s | Odoo (m³) pro %8s %8s part %8s %8s' % ('article', 'u.', 'fiche m³', '', '', '', '', '', '', '', '', ''))
for q in actifs:
    print('%-58s %-3s %9.2f | pro 2026 %7s -> 01/11 %6d -> 2027 %6d | part 01/11 %6d -> 2027 %6d | Odoo (m³) pro %8.2f %8.2f part %8.2f %8.2f%s' % (q['art'][:58], q['unite'][:3], q['fiche'] or 0, q['pro_2026'], q['pro_v1'], q['pro_v2'], q['part_v1'], q['part_v2'], q['pro_v1_m3'], q['pro_v2_m3'], q['part_v1_m3'], q['part_v2_m3'], '' if q['actif'] else '  (archivé)'))
"""
assert old in s; s = s.replace(old, new)
old = """        print('      %-58s 2026 %8.2f -> 2027 %6d' % (l['art'][:58], l['prix_2026'], l['prix_2027']))
"""
new = """        print('      %-58s 2026 %8.2f -> 2027 %6d   (Odoo m³ : %8.2f -> %8.2f)' % (l['art'][:58], l['prix_2026'], l['prix_2027'], l['prix_2026_m3'], l['prix_2027_m3']))
"""
assert old in s; s = s.replace(old, new)

# 5) création des règles : valeurs au m³
old = """    for lid, v1, v2 in ((e['liste_pro'], q['pro_v1'], q['pro_v2']), (e['liste_part'], q['part_v1'], q['part_v2'])):
"""
new = """    for lid, v1, v2 in ((e['liste_pro'], q['pro_v1_m3'], q['pro_v2_m3']), (e['liste_part'], q['part_v1_m3'], q['part_v2_m3'])):
"""
assert old in s; s = s.replace(old, new)
old = """            e['regles_clients'].append(one(x('product.pricelist.item', 'create', [{'pricelist_id': lid, 'applied_on': '0_product_variant', 'product_id': l['pid'], 'compute_price': 'fixed', 'fixed_price': l['prix_2026']}])))
        e['regles_clients'].append(one(x('product.pricelist.item', 'create', [{'pricelist_id': lid, 'applied_on': '0_product_variant', 'product_id': l['pid'], 'compute_price': 'fixed', 'fixed_price': l['prix_2027'], 'date_start': V2_DEBUT}])))
"""
new = """            e['regles_clients'].append(one(x('product.pricelist.item', 'create', [{'pricelist_id': lid, 'applied_on': '0_product_variant', 'product_id': l['pid'], 'compute_price': 'fixed', 'fixed_price': l['prix_2026_m3']}])))
        e['regles_clients'].append(one(x('product.pricelist.item', 'create', [{'pricelist_id': lid, 'applied_on': '0_product_variant', 'product_id': l['pid'], 'compute_price': 'fixed', 'fixed_price': l['prix_2027_m3'], 'date_start': V2_DEBUT}])))
"""
assert old in s; s = s.replace(old, new)

# 6) en-tête du script
old = "Les articles à 1 € dans la grille (à l'unité, sur devis) sont ignorés."
new = ("Les articles à 1 € dans la grille et les articles « à l'unité » restent sur devis (ignorés). Les prix de la grille au m²\n"
       "(pierres d'épaisseur) sont convertis en €/m³ (÷ épaisseur nominale du nom, ex. « (4 cm) » -> ÷ 0,04) : les listes de prix\n"
       "Odoo sont au m³ et le devis multiplie par l'épaisseur pour les ventes au m² (champ « Vente m2 »). Patch du 15/10/2026.")
assert old in s; s = s.replace(old, new)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('chargeur patché')
