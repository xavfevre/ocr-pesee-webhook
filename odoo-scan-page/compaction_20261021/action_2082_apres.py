# Cohérence fiche client (projet Sage) : société, code MAQ/HAI/CG/DIS, étiquette « Client X ». Un contact suit sa fiche mère (société
# + étiquette, jamais de code) ; les codes Sage « nom » ne sont jamais touchés. Remplace l'ancienne règle « Num client ».
PREFIXES = {1: 'MAQ', 4: 'HAI', 3: 'CG', 2: 'DIS'}
ETIQUETTES = {1: 'Client Maquignon', 4: 'Client Haims', 3: 'Client Chatel', 2: 'Client Distri Beton'}
for r in records:
    noms = [c.name for c in r.category_id]
    if r.user_ids or 'Compte odoo' in noms or 'Société du Groupe' in noms:
        continue
    if r.parent_id:
        comp = r.parent_id.company_id.id if r.parent_id.company_id else False
        if not comp:
            continue
        if not r.company_id or r.company_id.id != comp:
            r.write({'company_id': comp})
    else:
        if not r.company_id:
            r.write({'company_id': env.company.id})
        comp = r.company_id.id
        pref, ref = PREFIXES.get(comp), (r.ref or '').strip()
        mauvais = [p2 for c2, p2 in PREFIXES.items() if c2 != comp and ref.startswith(p2) and ref[len(p2):].isdigit()]   # code d'une autre société
        if pref and (not ref or mauvais):
            mx = 0
            for e in env['res.partner'].sudo().with_context(active_test=False).search([('ref', '=like', pref + '%')]):
                suffixe = (e.ref or '')[len(pref):]
                if suffixe.isdigit() and (pref != 'DIS' or int(suffixe) < 90000):
                    mx = max(mx, int(suffixe))
            r.write({'ref': '%s%05d' % (pref, mx + 1)})
    bonne = ETIQUETTES.get(comp)
    if not bonne:
        continue
    noms = [c.name for c in r.category_id]
    ops = [(3, c.id) for c in r.category_id if c.name in ETIQUETTES.values() and c.name != bonne]
    if bonne not in noms:
        tag = env['res.partner.category'].sudo().search([('name', '=', bonne)], limit=1)
        if tag:
            ops.append((4, tag.id))
    if ops:
        r.write({'category_id': ops})
