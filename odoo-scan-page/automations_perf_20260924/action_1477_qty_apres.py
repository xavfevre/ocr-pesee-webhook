if record.sale_line_id:
    _dups = env['mrp.production'].search([
        ('sale_line_id', '=', record.sale_line_id.id),
        ('id', '!=', record.id),
        ('state', '!=', 'cancel'),
    ])
    if _dups:
        _already = env['mail.message'].search_count([
            ('model', '=', 'mrp.production'),
            ('res_id', '=', record.id),
            ('subject', '=', 'Doublon OF potentiel'),
        ])
        if not _already:
            record.message_post(
                subject='Doublon OF potentiel',
                body="\u26a0\ufe0f Doublon potentiel : OF actif(s) deja existant(s) pour cette ligne : %s"
                     % ', '.join(_dups.mapped('name')),
            )
if record.origin and not record.x_studio_nom_du_client:
    sale_order = env['sale.order'].search([('name', '=', record.origin)], limit=1)
    if sale_order and sale_order.partner_id:
        vals = {'x_studio_nom_du_client': sale_order.partner_id.name}
        try:
            vals['x_studio_ref_commande_client'] = sale_order.client_order_ref or ''
        except Exception:
            vals['x_studio_ref_commande_client'] = ''
        matching_line = False
        if record.sale_line_id and record.sale_line_id.order_id.id == sale_order.id:
            matching_line = record.sale_line_id
        if not matching_line and sale_order.order_line and record.product_id:
            product_lines = sale_order.order_line.filtered(
                lambda l: l.product_id.id == record.product_id.id
            ).sorted(key=lambda l: (l.sequence, l.id))
            if len(product_lines) == 1:
                matching_line = product_lines[0]
            elif len(product_lines) > 1:
                existing_mos_count = env['mrp.production'].search_count([
                    ('origin', '=', record.origin),
                    ('product_id', '=', record.product_id.id),
                    ('id', '<', record.id),
                    ('state', '!=', 'cancel'),
                ])
                index = existing_mos_count % len(product_lines)
                matching_line = product_lines[index]
        if not matching_line and sale_order.order_line:
            matching_line = sale_order.order_line[0]
        if matching_line:
            try:
                if not record.sale_line_id:
                    vals['sale_line_id'] = matching_line.id
            except Exception:
                pass
            try:
                vals['x_studio_ref_pierre'] = matching_line.x_studio_ref_pierre or ''
            except Exception:
                vals['x_studio_ref_pierre'] = ''
            try:
                vals['x_studio_nbr'] = matching_line.x_studio_nbr or 0
            except Exception:
                vals['x_studio_nbr'] = 0
            try:
                vals['x_studio_long_m_1'] = matching_line.x_studio_long or 0.0
            except Exception:
                vals['x_studio_long_m_1'] = 0.0
            try:
                vals['x_studio_larg_m_1'] = matching_line.x_studio_larg or 0.0
            except Exception:
                vals['x_studio_larg_m_1'] = 0.0
            try:
                vals['x_studio_haut_m_1'] = matching_line.x_studio_epais or 0.0
            except Exception:
                vals['x_studio_haut_m_1'] = 0.0
            try:
                vals['x_studio_surf_total'] = matching_line.x_studio_surf or 0.0
            except Exception:
                vals['x_studio_surf_total'] = 0.0
            try:
                vals['x_studio_vol_total'] = matching_line.x_studio_vol or 0.0
            except Exception:
                vals['x_studio_vol_total'] = 0.0
        vol_total = vals.get('x_studio_vol_total', 0) or 0
        # quantité de l'OF réécrite seulement si elle change une fois arrondie à l'unité (sinon 0,37 s de recalculs par OF)
        if vol_total and float_compare(vol_total, record.product_qty, precision_rounding=record.product_uom_id.rounding or 0.001) != 0:
            vals['product_qty'] = vol_total
        if matching_line:
            try:
                line_name = matching_line.name or ''
                desc_parts = line_name.split('\n')
                vals['x_studio_description_article'] = (
                    '\n'.join(desc_parts[1:]).strip() if len(desc_parts) > 1 else ''
                )
            except Exception:
                vals['x_studio_description_article'] = ''
        vals['log_note'] = "%s | %s\nNbr: %s  L: %.3f  l: %.3f  H: %.3f m" % (
            vals.get('x_studio_nom_du_client', '') or '',
            vals.get('x_studio_ref_pierre', '') or '',
            int(vals.get('x_studio_nbr', 0) or 0),
            float(vals.get('x_studio_long_m_1', 0) or 0),
            float(vals.get('x_studio_larg_m_1', 0) or 0),
            float(vals.get('x_studio_haut_m_1', 0) or 0),
        )
        record.write(vals)
if record.origin:
    sale_order = env['sale.order'].search([('name', '=', record.origin)], limit=1)
    if sale_order and sale_order.order_line and record.product_id:
        if record.sale_line_id and record.sale_line_id.order_id.id == sale_order.id:
            matching_line = record.sale_line_id
        else:
            product_lines = sale_order.order_line.filtered(
                lambda l: l.product_id.id == record.product_id.id
            ).sorted(key=lambda l: (l.sequence, l.id))
            if product_lines:
                existing_mos_count = env['mrp.production'].search_count([
                    ('origin', '=', record.origin),
                    ('product_id', '=', record.product_id.id),
                    ('id', '<', record.id),
                    ('state', '!=', 'cancel'),
                ])
                index = existing_mos_count % len(product_lines) if len(product_lines) > 0 else 0
                matching_line = product_lines[index]
            else:
                matching_line = False
        if matching_line and matching_line.x_studio_taille_de_p:
            already_exists = record.workorder_ids.filtered(
                lambda w: 'taille de pierre' in w.name.lower()
            )
            if not already_exists:
                workcenter = env['mrp.workcenter'].search(
                    [('name', 'ilike', 'TC1350 Atelier')], limit=1
                ) or env['mrp.workcenter'].search([('name', 'ilike', 'TC1350')], limit=1)
                if workcenter:
                    texte = matching_line.x_studio_taille_de_p.strip()
                    workorder_name = 'Taille de pierre - ' + texte if texte else 'Taille de pierre'
                    env['mrp.workorder'].create({
                        'name': workorder_name,
                        'production_id': record.id,
                        'workcenter_id': workcenter.id,
                        'product_uom_id': record.product_uom_id.id,
                        'qty_production': record.product_qty,
                    })
if record.origin:
    sale_order = env['sale.order'].search([('name', '=', record.origin)], limit=1)
    if sale_order and sale_order.x_studio_tache:
        tache_id = sale_order.x_studio_tache.id
        record.write({'x_studio_tche_commande_pierre': tache_id})
        for workorder in record.workorder_ids:
            workorder.write({'x_studio_tche_commande_pierre': tache_id})