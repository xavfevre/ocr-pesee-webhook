# Action 1949 / automatisation 68 — UdF selon le libellé de variante du produit

# UdF selon le libelle de variante du produit : (Tonne), (Forfait), (Heure),
# (au Tour), (par jours) — posee uniquement si l'unite de mesure de la ligne
# ne porte pas deja cette unite, et sans ecraser une UdF saisie manuellement.
MAP = [('(tonne', 'Tonne'), ('(forfait', 'Forfait'), ('(heure', 'Heure'),
       ('au tour)', 'Tour'), ('par jours)', 'Jours'), ('par jour)', 'Jours')]
UOM_EQ = {'tonne': 'Tonne', 'forfait': 'Forfait', 'hours': 'Heure',
          'heure': 'Heure', 'heures': 'Heure', 'jours': 'Jours', 'jour': 'Jours',
          'unité': 'Unité(s)', 'unités': 'Unité(s)', 'm²': 'm²', 'm³': 'm³'}
for rec in records:
    if rec.x_studio_udf:
        continue
    name = (rec.product_id.display_name or rec.name or '').lower()
    uom = (rec.product_uom_id.name or '').strip().lower()
    cible = None
    for motif, udf in MAP:
        if motif in name:
            cible = udf
            break
    if cible and UOM_EQ.get(uom) != cible:
        rec.write({'x_studio_udf': cible})

