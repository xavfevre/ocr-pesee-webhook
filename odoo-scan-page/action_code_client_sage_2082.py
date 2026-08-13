# Code client automatique par societe (projet Sage) :
# MAQxxxxx (SARL Maquignon), HAIxxxxx (Haims), CGxxxxx (Chatel), DISxxxxx (Distri).
# S'applique aux fiches clients autonomes sans code ; exclut contacts,
# comptes odoo (utilisateurs) et societes du groupe (etiquettes).
for r in records:
    if r.ref or r.parent_id:
        continue
    pref = {1: 'MAQ', 4: 'HAI', 3: 'CG', 2: 'DIS'}.get(r.company_id.id)
    if not pref:
        continue
    if r.user_ids:
        continue
    exclu = False
    for c in r.category_id:
        if c.name in ('Compte odoo', 'Société du Groupe'):
            exclu = True
    if exclu:
        continue
    existants = env['res.partner'].sudo().with_context(active_test=False).search([('ref', '=like', pref + '%')])
    mx = 0
    for e in existants:
        suffixe = (e.ref or '')[len(pref):]
        if suffixe.isdigit() and (pref != 'DIS' or int(suffixe) < 90000):
            n = int(suffixe)
            if n > mx:
                mx = n
    r.write({'ref': '%s%05d' % (pref, mx + 1)})
