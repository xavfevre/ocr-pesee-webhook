# actions 2086 (sale.order) / 2087 (account.move, variante move_type out_*)
# Code client des le premier devis / premiere facture (projet Sage) :
# la fiche mere du client recoit son code societe si elle n'en a pas encore.
# Les fiches-artefacts (emails entrants) ne sont jamais codees : elles n'ont
# ni devis ni facture.
PREFIXES = {1: 'MAQ', 4: 'HAI', 3: 'CG', 2: 'DIS'}
for r in records:
    pass
    p = r.partner_id.commercial_partner_id if r.partner_id else False
    if not p or p.ref or p.user_ids:
        continue
    exclu = False
    for c in p.category_id:
        if c.name in ('Compte odoo', 'Société du Groupe'):
            exclu = True
    if exclu:
        continue
    comp = p.company_id.id if p.company_id else (r.company_id.id if r.company_id else False)
    pref = PREFIXES.get(comp)
    if not pref:
        continue
    if not p.company_id:
        p.write({'company_id': comp})
    existants = env['res.partner'].sudo().with_context(active_test=False).search([('ref', '=like', pref + '%')])
    mx = 0
    for e in existants:
        suffixe = (e.ref or '')[len(pref):]
        if suffixe.isdigit() and (pref != 'DIS' or int(suffixe) < 90000):
            n = int(suffixe)
            if n > mx:
                mx = n
    p.write({'ref': '%s%05d' % (pref, mx + 1)})
