for record in self:
    parts = []
    ofs = record.env['mrp.production'].search([('sale_line_id','=',record.id)])
    for of in ofs:
        if of.x_studio_colis:
            p = of.x_studio_colis
            z = (' - ' + p.x_studio_zone) if p.x_studio_zone else ''
            parts.append(p.name + ' (' + str(int(of.x_studio_nbr or 0)) + ' pcs' + z + ')')
        else:
            for ln in record.env['x_repartition_palette'].search([('x_studio_of_id','=',of.id)]):
                p = ln.x_studio_colis_id
                z = (' - ' + p.x_studio_zone) if p.x_studio_zone else ''
                parts.append(p.name + ' (' + str(ln.x_studio_qte) + ' pcs' + z + ')')
    record['x_studio_palettes'] = ' · '.join(parts)
