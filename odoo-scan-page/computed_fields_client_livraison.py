# Champs calculés (non stockés) sur stock.package pour le Bon de colisage.
# x_studio_client (char) : nom du client (1er OF non vide, champ x_studio_nom_du_client)
for record in self:
    client = ''
    ofs = record.env['mrp.production'].search([('x_studio_colis','=',record.id)])
    for ln in record.env['x_repartition_palette'].search([('x_studio_colis_id','=',record.id)]):
        ofs |= ln.x_studio_of_id
    for of in ofs:
        if not client and of.x_studio_nom_du_client:
            client = of.x_studio_nom_du_client
    record['x_studio_client'] = client

# x_studio_partner_livraison (many2one res.partner) : adresse de livraison via la commande liée
for record in self:
    partner = record.env['res.partner']
    ofs = record.env['mrp.production'].search([('x_studio_colis','=',record.id)])
    for ln in record.env['x_repartition_palette'].search([('x_studio_colis_id','=',record.id)]):
        ofs |= ln.x_studio_of_id
    for of in ofs:
        if not partner and of.sale_line_id:
            partner = of.sale_line_id.order_id.partner_shipping_id
    record['x_studio_partner_livraison'] = partner.id if partner else False
