# 1587 | Retirer dernier OF du colis | Poste de scan
for record in records:
    if not record.x_studio_colis_actifs:
        record.write({
            'x_studio_rsultat': "⚠️ Aucun colis sélectionné"
        })
        continue
    
    # Trouver le dernier OF ajouté à ce colis
    last_of = env['mrp.production'].search([
        ('x_studio_colis', '=', record.x_studio_colis_actifs.id)
    ], order='write_date desc', limit=1)
    
    if not last_of:
        record.write({
            'x_studio_rsultat': "ℹ️ Aucun OF dans ce colis"
        })
        continue
    
    # Retirer les move lines du colis
    finished_moves = last_of.move_finished_ids.filtered(lambda m: m.state == 'done')
    for move in finished_moves:
        for ml in move.move_line_ids:
            if ml.result_package_id and ml.result_package_id.id == record.x_studio_colis_actifs.id:
                ml.sudo().write({'result_package_id': False})
    
    # Nettoyer les quants
    quants = env['stock.quant'].sudo().search([
        ('product_id', '=', last_of.product_id.id),
        ('package_id', '=', record.x_studio_colis_actifs.id),
    ])
    
    # Vérifier qu'aucun autre OF n'utilise ce quant dans ce colis
    for q in quants:
        other_ofs = env['mrp.production'].search_count([
            ('x_studio_colis', '=', record.x_studio_colis_actifs.id),
            ('product_id', '=', last_of.product_id.id),
            ('id', '!=', last_of.id),
        ])
        if not other_ofs:
            q.sudo().write({'package_id': False, 'x_studio_infos_pierre': ''})
    
    # Retirer l'OF du colis
    last_of.write({'x_studio_colis': False})
    
    count = env['mrp.production'].search_count([
        ('x_studio_colis', '=', record.x_studio_colis_actifs.id)
    ])
    
    record.write({
        'x_studio_rsultat': "↩️ " + last_of.name + " retiré (" + str(count) + " OF restants)"
    })