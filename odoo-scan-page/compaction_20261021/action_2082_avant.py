# Coherence fiche client : societe + code + etiquette (projet Sage).
# - societe manquante -> societe active du createur (fiche autonome) ;
# - contact : herite la societe ET l'etiquette de sa fiche mere, jamais de code ;
# - code selon la societe de la FICHE : MAQxxxxx / HAIxxxxx / CGxxxxx / DISxxxxx
#   (attribue si absent, recode si prefixe sequence d'une autre societe ;
#   les codes Sage « nom » ne sont jamais touches) ;
# - etiquette « Client X » de la societe ajoutee, les autres retirees.
# Remplace l'ancienne regle « Num client » (choix par societe active de l'utilisateur).
PREFIXES = {1: 'MAQ', 4: 'HAI', 3: 'CG', 2: 'DIS'}
ETIQUETTES = {1: 'Client Maquignon', 4: 'Client Haims', 3: 'Client Chatel', 2: 'Client Distri Beton'}
for r in records:
    if r.user_ids:
        continue
    exclu = False
    for c in r.category_id:
        if c.name in ('Compte odoo', 'Société du Groupe'):
            exclu = True
    if exclu:
        continue
    if r.parent_id:
        # contact : suit sa fiche mere (societe + etiquette), pas de code
        pcomp = r.parent_id.company_id.id if r.parent_id.company_id else False
        if not pcomp:
            continue
        if not r.company_id or r.company_id.id != pcomp:
            r.write({'company_id': pcomp})
        comp = pcomp
    else:
        if not r.company_id:
            r.write({'company_id': env.company.id})
        comp = r.company_id.id
        pref = PREFIXES.get(comp)
        if pref:
            ref = (r.ref or '').strip()
            mauvais = False
            for c2, p2 in PREFIXES.items():
                if c2 != comp and ref.startswith(p2) and ref[len(p2):].isdigit():
                    mauvais = True
            if (not ref) or mauvais:
                existants = env['res.partner'].sudo().with_context(active_test=False).search([('ref', '=like', pref + '%')])
                mx = 0
                for e in existants:
                    suffixe = (e.ref or '')[len(pref):]
                    if suffixe.isdigit() and (pref != 'DIS' or int(suffixe) < 90000):
                        n = int(suffixe)
                        if n > mx:
                            mx = n
                r.write({'ref': '%s%05d' % (pref, mx + 1)})
    bonne = ETIQUETTES.get(comp)
    if not bonne:
        continue
    autres = [v for k, v in ETIQUETTES.items() if v != bonne]
    ops = []
    noms_presents = [c.name for c in r.category_id]
    for c in r.category_id:
        if c.name in autres:
            ops.append((3, c.id))
    if bonne not in noms_presents:
        tag = env['res.partner.category'].sudo().search([('name', '=', bonne)], limit=1)
        if tag:
            ops.append((4, tag.id))
    if ops:
        r.write({'category_id': ops})
