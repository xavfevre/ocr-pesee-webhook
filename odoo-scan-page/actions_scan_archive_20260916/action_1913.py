# 1913 | Retirer un OF précis du colis | Poste de scan
of_id = env.context.get('of_remove_id')
for record in records:
    if not record.x_studio_colis_actifs:
        record.write({'x_studio_rsultat': "⚠️ Aucun colis sélectionné"})
        continue
    if not of_id:
        record.write({'x_studio_rsultat': "⚠️ Aucun OF indiqué"})
        continue
    of = env['mrp.production'].browse(of_id)
    if not of.exists() or not of.x_studio_colis or of.x_studio_colis.id != record.x_studio_colis_actifs.id:
        record.write({'x_studio_rsultat': "⚠️ OF absent de ce colis"})
        continue
    finished_moves = of.move_finished_ids.filtered(lambda m: m.state == 'done')
    for move in finished_moves:
        for ml in move.move_line_ids:
            if ml.result_package_id and ml.result_package_id.id == record.x_studio_colis_actifs.id:
                ml.sudo().write({'result_package_id': False})
    quants = env['stock.quant'].sudo().search([
        ('product_id', '=', of.product_id.id),
        ('package_id', '=', record.x_studio_colis_actifs.id),
    ])
    for q in quants:
        other_ofs = env['mrp.production'].search_count([
            ('x_studio_colis', '=', record.x_studio_colis_actifs.id),
            ('product_id', '=', of.product_id.id),
            ('id', '!=', of.id),
        ])
        if not other_ofs:
            q.sudo().write({'package_id': False, 'x_studio_infos_pierre': ''})
    of.write({'x_studio_colis': False})
    count = env['mrp.production'].search_count([
        ('x_studio_colis', '=', record.x_studio_colis_actifs.id)
    ])
    record.write({'x_studio_rsultat': "🗑️ " + of.name + " retiré (" + str(count) + " OF restants)"})
