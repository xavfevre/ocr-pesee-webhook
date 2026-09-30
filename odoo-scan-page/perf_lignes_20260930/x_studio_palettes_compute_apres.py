ofs = self.env['mrp.production'].search([('sale_line_id', 'in', self.ids)]) if self.ids else self.env['mrp.production']
reps = self.env['x_repartition_palette'].search([('x_studio_of_id', 'in', ofs.ids)]) if ofs else self.env['x_repartition_palette']
by_line = {}
for of in ofs:
    by_line.setdefault(of.sale_line_id.id, []).append(of)
rep_by_of = {}
for ln in reps:
    rep_by_of.setdefault(ln.x_studio_of_id.id, []).append(ln)
for record in self:
    parts = []
    for of in by_line.get(record.id, []):
        if of.x_studio_colis:
            p = of.x_studio_colis
            z = (' - ' + p.x_studio_zone) if p.x_studio_zone else ''
            parts.append(p.name + ' (' + str(int(of.x_studio_nbr or 0)) + ' pcs' + z + ')')
        else:
            for ln in rep_by_of.get(of.id, []):
                p = ln.x_studio_colis_id
                z = (' - ' + p.x_studio_zone) if p.x_studio_zone else ''
                parts.append(p.name + ' (' + str(ln.x_studio_qte) + ' pcs' + z + ')')
    record['x_studio_palettes'] = ' · '.join(parts)
