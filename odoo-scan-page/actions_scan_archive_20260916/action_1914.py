# 1914 | Placer OF dans palette (quantité) | Poste de scan
of_id = env.context.get('of_place_id')
qte_in = env.context.get('qte_place')
for record in records:
    colis = record.x_studio_colis_actifs
    if not colis:
        record.write({'x_studio_rsultat': "⚠️ Scanner un colis d'abord"})
        continue
    if colis.x_studio_cloturee:
        record.write({'x_studio_rsultat': "🔒 " + colis.name + " est clôturée"})
        continue
    if not of_id:
        record.write({'x_studio_rsultat': "⚠️ Aucun OF indiqué"})
        continue
    of = env['mrp.production'].browse(of_id)
    if not of.exists():
        record.write({'x_studio_rsultat': "❌ OF introuvable"})
        continue
    if of.x_studio_colis:
        record.write({'x_studio_rsultat': "⚠️ " + of.name + " est entier dans " + of.x_studio_colis.name})
        continue
    if of.state != 'done':
        record.write({'x_studio_rsultat': "⚠️ " + of.name + " pas encore terminé"})
        continue
    total = int(of.x_studio_nbr or 1)
    lines = env['x_repartition_palette'].search([('x_studio_of_id', '=', of.id)])
    placed = 0
    for l in lines:
        placed += l.x_studio_qte
    remaining = total - placed
    if remaining <= 0:
        record.write({'x_studio_rsultat': "ℹ️ " + of.name + " déjà entièrement réparti (" + str(total) + ")"})
        continue
    q = int(qte_in) if qte_in else remaining
    if q < 1:
        q = 1
    if q > remaining:
        q = remaining
    existing = lines.filtered(lambda x: x.x_studio_colis_id.id == colis.id)
    if existing:
        existing[0].write({'x_studio_qte': existing[0].x_studio_qte + q})
    else:
        env['x_repartition_palette'].create({
            'x_name': of.name + ' / ' + colis.name,
            'x_studio_of_id': of.id,
            'x_studio_colis_id': colis.id,
            'x_studio_qte': q,
        })
    reste = total - (placed + q)
    if reste > 0:
        record.write({'x_studio_rsultat': "✂️ " + str(q) + " pcs de " + of.name + " sur " + colis.name + " (reste " + str(reste) + "/" + str(total) + ")"})
    else:
        record.write({'x_studio_rsultat': "✅ " + of.name + " entièrement réparti (" + str(total) + " pcs)"})
