if record.sale_line_id:
    dups = env['mrp.production'].search([('sale_line_id', '=', record.sale_line_id.id), ('id', '!=', record.id), ('state', '!=', 'cancel')])
    if dups and not env['mail.message'].search_count([('model', '=', 'mrp.production'), ('res_id', '=', record.id), ('subject', '=', 'Doublon OF potentiel')]):
        record.message_post(subject='Doublon OF potentiel', body="⚠️ Doublon potentiel : OF actif(s) deja existant(s) pour cette ligne : %s" % ', '.join(dups.mapped('name')))
so = env['sale.order'].search([('name', '=', record.origin)], limit=1) if record.origin else env['sale.order']

def trouver(repli):
    """Ligne de vente de l'OF : sa propre ligne, sinon la n-ième ligne du même article (n = OF déjà créés), sinon la 1re ligne si repli."""
    if record.sale_line_id and record.sale_line_id.order_id.id == so.id:
        return record.sale_line_id
    pl = so.order_line.filtered(lambda l: l.product_id.id == record.product_id.id).sorted(key=lambda l: (l.sequence, l.id)) if record.product_id else so.order_line.browse()
    if len(pl) > 1:
        return pl[env['mrp.production'].search_count([('origin', '=', record.origin), ('product_id', '=', record.product_id.id), ('id', '<', record.id), ('state', '!=', 'cancel')]) % len(pl)]
    return pl[0] if pl else (so.order_line[0] if repli and so.order_line else False)

if so and so.partner_id and not record.x_studio_nom_du_client:
    vals = {'x_studio_nom_du_client': so.partner_id.name, 'x_studio_ref_commande_client': so.client_order_ref or ''}
    ml = trouver(True)
    if ml:
        if not record.sale_line_id:
            vals['sale_line_id'] = ml.id
        vals.update({'x_studio_ref_pierre': ml.x_studio_ref_pierre or '', 'x_studio_nbr': ml.x_studio_nbr or 0, 'x_studio_long_m_1': ml.x_studio_long or 0.0, 'x_studio_larg_m_1': ml.x_studio_larg or 0.0,
                     'x_studio_haut_m_1': ml.x_studio_epais or 0.0, 'x_studio_surf_total': ml.x_studio_surf or 0.0, 'x_studio_vol_total': ml.x_studio_vol or 0.0})
        parts = (ml.name or '').split('\n')
        vals['x_studio_description_article'] = (ml.x_studio_libell_client or '').strip() or ('\n'.join(parts[1:]).strip() if len(parts) > 1 else '')   # libellé client, sinon complément du nom
    vol = vals.get('x_studio_vol_total') or 0
    if vol and float_compare(vol, record.product_qty, precision_rounding=record.product_uom_id.rounding or 0.001) != 0:   # quantité réécrite seulement si elle change (recalculs coûteux)
        vals['product_qty'] = vol
    vals['log_note'] = "%s | %s\nNbr: %s  L: %.3f  l: %.3f  H: %.3f m" % (vals['x_studio_nom_du_client'] or '', vals.get('x_studio_ref_pierre') or '', int(vals.get('x_studio_nbr') or 0),
                                                                        float(vals.get('x_studio_long_m_1') or 0), float(vals.get('x_studio_larg_m_1') or 0), float(vals.get('x_studio_haut_m_1') or 0))
    record.write(vals)
if so and so.order_line and record.product_id:
    ml = trouver(False)
    if ml and ml.x_studio_taille_de_p and not record.workorder_ids.filtered(lambda w: 'taille de pierre' in w.name.lower()):
        wc = env['mrp.workcenter'].search([('name', 'ilike', 'TC1350 Atelier')], limit=1) or env['mrp.workcenter'].search([('name', 'ilike', 'TC1350')], limit=1)
        if wc:
            texte = ml.x_studio_taille_de_p.strip()
            env['mrp.workorder'].create({'name': 'Taille de pierre - ' + texte if texte else 'Taille de pierre', 'production_id': record.id, 'workcenter_id': wc.id, 'product_uom_id': record.product_uom_id.id, 'qty_production': record.product_qty})
if so and so.x_studio_tache:
    record.write({'x_studio_tche_commande_pierre': so.x_studio_tache.id})
    record.workorder_ids.write({'x_studio_tche_commande_pierre': so.x_studio_tache.id})
