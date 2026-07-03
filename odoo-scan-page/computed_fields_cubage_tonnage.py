# Champs calculés (non stockés) sur stock.package — totaux du colisage.
# Calculés à partir des OF affectés à la palette (mise à jour en direct au scan).

# x_studio_cubage (float, m³) :
for record in self:
    vol = 0.0
    for of in record.env['mrp.production'].search([('x_studio_colis','=',record.id)]):
        vol += of.x_studio_vol_total or 0.0
    for ln in record.env['x_repartition_palette'].search([('x_studio_colis_id','=',record.id)]):
        of = ln.x_studio_of_id
        nbr = of.x_studio_nbr or 0
        if nbr:
            vol += (of.x_studio_vol_total or 0.0) * (ln.x_studio_qte / nbr)
    record['x_studio_cubage'] = vol

# x_studio_tonnage (float, kg) : volume x poids/m³ (product.weight, uom m³) :
for record in self:
    ton = 0.0
    for of in record.env['mrp.production'].search([('x_studio_colis','=',record.id)]):
        ton += (of.x_studio_vol_total or 0.0) * (of.product_id.weight or 0.0)
    for ln in record.env['x_repartition_palette'].search([('x_studio_colis_id','=',record.id)]):
        of = ln.x_studio_of_id
        nbr = of.x_studio_nbr or 0
        if nbr:
            ton += (of.x_studio_vol_total or 0.0) * (of.product_id.weight or 0.0) * (ln.x_studio_qte / nbr)
    record['x_studio_tonnage'] = ton
