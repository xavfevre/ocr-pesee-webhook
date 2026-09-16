# 1588 | Traiter le scan | Poste de scan
for record in records:
    barcode = (record.x_studio_scanner or '').strip()
    if not barcode:
        record.write({
            'x_studio_rsultat': "⚠️ Rien à scanner"
        })
        continue
    
    # 1. Chercher si c'est un colis
    package = env['stock.package'].search([('name', '=', barcode)], limit=1)
    if not package:
        package = env['stock.package'].search([('name', '=', barcode.upper())], limit=1)
    
    if package:
        count = env['mrp.production'].search_count([
            ('x_studio_colis', '=', package.id)
        ])
        record.write({
            'x_studio_colis_actifs': package.id,
            'x_studio_scanner': False,
            'x_studio_rsultat': "📦 " + package.name + " (" + str(count) + " OF)"
        })
        continue
    
    # 2. Chercher si c'est un OF
    of = env['mrp.production'].search([('name', '=', barcode)], limit=1)
    if not of:
        of = env['mrp.production'].search([('name', '=', barcode.upper())], limit=1)
    
    if of:
        rep_n = env['x_repartition_palette'].search_count([('x_studio_of_id', '=', of.id)])
        if rep_n:
            record.write({'x_studio_scanner': False, 'x_studio_rsultat': "✂️ " + of.name + " est en répartition partielle (panneau Répartir)"})
            continue
        if not record.x_studio_colis_actifs:
            record.write({
                'x_studio_scanner': False,
                'x_studio_rsultat': "⚠️ SCANNER UN COLIS D'ABORD"
            })
            continue
        
        if of.x_studio_colis:
            if of.x_studio_colis.id == record.x_studio_colis_actifs.id:
                record.write({
                    'x_studio_scanner': False,
                    'x_studio_rsultat': "ℹ️ " + of.name + " déjà dans ce colis"
                })
            else:
                record.write({
                    'x_studio_scanner': False,
                    'x_studio_rsultat': "⚠️ " + of.name + " est dans " + of.x_studio_colis.name
                })
            continue
        
        if of.state != 'done':
            record.write({
                'x_studio_scanner': False,
                'x_studio_rsultat': "⚠️ " + of.name + " pas encore terminé (état: " + str(of.state) + ")"
            })
            continue
        
        # Assigner l'OF au colis
        of.write({'x_studio_colis': record.x_studio_colis_actifs.id})
        
        # Construire la ligne d'infos pierre
        infos = []
        if of.x_studio_ref_pierre:
            infos.append(str(of.x_studio_ref_pierre))
        if of.x_studio_nbr:
            infos.append(str(int(of.x_studio_nbr)) + " pcs")
        dims = []
        if of.x_studio_long_m_1:
            dims.append(("{:.3f}".format(of.x_studio_long_m_1)).rstrip('0').rstrip('.'))
        if of.x_studio_larg_m_1:
            dims.append(("{:.3f}".format(of.x_studio_larg_m_1)).rstrip('0').rstrip('.'))
        if of.x_studio_haut_m_1:
            dims.append(("{:.3f}".format(of.x_studio_haut_m_1)).rstrip('0').rstrip('.'))
        if dims:
            infos.append(" x ".join(dims) + " m")
        if of.x_studio_surf_total:
            infos.append(("{:.3f}".format(of.x_studio_surf_total)).rstrip('0').rstrip('.') + " m²")
        if of.x_studio_vol_total:
            infos.append(("{:.3f}".format(of.x_studio_vol_total)).rstrip('0').rstrip('.') + " m³")
        
        infos_str = " — ".join(infos) if infos else ""
        
        # Remplir le CONTENT du colis via les move lines
        finished_moves = of.move_finished_ids.filtered(lambda m: m.state == 'done')
        
        for move in finished_moves:
            for ml in move.move_line_ids:
                if not ml.result_package_id:
                    ml.sudo().write({'result_package_id': record.x_studio_colis_actifs.id})
        
        # Mettre à jour les infos pierre sur les quants du colis
        quants = env['stock.quant'].sudo().search([
            ('product_id', '=', of.product_id.id),
            ('package_id', '=', record.x_studio_colis_actifs.id),
        ])
        
        if quants:
            quants.sudo().write({'x_studio_infos_pierre': infos_str})
        
        count = env['mrp.production'].search_count([
            ('x_studio_colis', '=', record.x_studio_colis_actifs.id)
        ])
        
        record.write({
            'x_studio_scanner': False,
            'x_studio_rsultat': "✅ " + of.name + " ajouté (" + str(count) + " OF)"
        })
        continue
    
    # 3. Code non reconnu
    record.write({
        'x_studio_scanner': False,
        'x_studio_rsultat': "❌ Inconnu : " + barcode
    })