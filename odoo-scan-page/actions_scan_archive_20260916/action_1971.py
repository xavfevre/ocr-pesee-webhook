# 1971 | Tablette : mettre l'OF au colis | Manufacturing Order
colis_id = env.context.get('colis_id')
colis_name = (env.context.get('colis_name') or '').strip()
for record in records:
    if colis_id:
        colis = env['stock.package'].browse(colis_id)
        if not colis.exists():
            raise UserError('Colis introuvable')
    elif colis_name:
        colis = env['stock.package'].sudo().search([('name', '=ilike', colis_name)], limit=1)
        if not colis:
            raise UserError('Colis introuvable : ' + colis_name)
    else:
        raise UserError('Aucun colis indiqué')
    if colis.x_studio_cloturee:
        raise UserError(colis.name + ' est clôturé')
    if record.x_studio_colis:
        raise UserError(record.name + ' est déjà dans ' + record.x_studio_colis.name)
    if record.state != 'done':
        raise UserError(record.name + " n'est pas encore terminé (état : " + record.state + ")")
    if env['x_repartition_palette'].search_count([('x_studio_of_id', '=', record.id)]):
        raise UserError(record.name + ' est en répartition partielle : passez par le poste de scan')
    record.write({'x_studio_colis': colis.id})
    op_id = int(env.context.get('op_id') or 0)
    if op_id and op_id not in colis.x_operateur_ids.ids:
        colis.sudo().write({'x_operateur_ids': [(4, op_id)]})