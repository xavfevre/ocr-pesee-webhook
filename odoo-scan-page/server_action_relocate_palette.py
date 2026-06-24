# Action serveur Odoo "Relocaliser palette (emplacement)" (modèle x_poste_de_scan, état=code)
# Déclenchée par la page /scan lors du scan/clic d'un emplacement.
# Lit x_poste_de_scan.x_studio_colis_actifs, mappe x_studio_zone -> stock.location (par nom, usage interne)
# et fait un transfert interne réel de la palette vers cet emplacement.
for record in records:
    colis = record.x_studio_colis_actifs
    if not colis:
        record.write({'x_studio_rsultat': "Aucune palette active"})
        continue
    tid = env.context.get('target_loc')
    if tid:
        loc = env['stock.location'].browse(tid)
    else:
        loc = env['stock.location'].search([('name','=',colis.x_studio_zone or ''),('usage','=','internal')], limit=1)
    if not loc:
        record.write({'x_studio_rsultat': "Emplacement inconnu"})
        continue
    quants = env['stock.quant']
    for q in colis.quant_ids:
        if q.quantity > 0 and q.location_id.id != loc.id:
            quants |= q
    if not quants:
        record.write({'x_studio_rsultat': "Deja en " + loc.display_name})
        continue
    src_ids = []
    for q in quants:
        if q.location_id.id not in src_ids:
            src_ids.append(q.location_id.id)
    ptype = env['stock.picking.type'].search([('code','=','internal'),('company_id','=',colis.company_id.id or 1)], limit=1)
    for src_id in src_ids:
        picking = env['stock.picking'].create({'picking_type_id': ptype.id, 'location_id': src_id, 'location_dest_id': loc.id, 'origin': colis.name})
        todo = []
        for q in quants:
            if q.location_id.id == src_id:
                move = env['stock.move'].create({'product_id': q.product_id.id, 'product_uom_qty': q.quantity, 'product_uom': q.product_id.uom_id.id, 'picking_id': picking.id, 'location_id': src_id, 'location_dest_id': loc.id})
                todo.append((move.id, q.product_id.id, q.quantity, q.product_id.uom_id.id))
        picking.action_confirm()
        for t in todo:
            env['stock.move.line'].create({'move_id': t[0], 'picking_id': picking.id, 'product_id': t[1], 'quantity': t[2], 'product_uom_id': t[3], 'location_id': src_id, 'location_dest_id': loc.id, 'package_id': colis.id, 'result_package_id': colis.id, 'picked': True})
        picking.with_context(skip_backorder=True).button_validate()
    record.write({'x_studio_rsultat': "Palette deplacee en " + loc.display_name})
