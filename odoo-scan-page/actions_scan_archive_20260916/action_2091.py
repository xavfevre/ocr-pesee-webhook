# 2091 | Poste de scan : opérateur | Poste de scan
op_id = int(env.context.get('op_id') or 0)
mode = env.context.get('mode') or 'select'
emp = env['hr.employee'].sudo().browse(op_id) if op_id else None
for record in records:
    rec = record.sudo()
    if not emp or not emp.exists():
        rec.write({'x_studio_colis_actifs': False, 'x_studio_rsultat': "👤 Choisissez votre nom d'abord"})
        continue
    if mode == 'select':
        pal = emp.x_palette_scan_id
        if pal and pal.x_studio_cloturee:
            pal = None
        if pal:
            rec.write({'x_studio_colis_actifs': pal.id, 'x_studio_rsultat': "👤 " + emp.name + " — palette " + pal.name + " reprise"})
        else:
            rec.write({'x_studio_colis_actifs': False, 'x_studio_rsultat': "👤 " + emp.name + " — aucune palette active : scannez une palette"})
    else:
        pal = rec.x_studio_colis_actifs
        emp.write({'x_palette_scan_id': pal.id if pal else False})
        if pal and emp.id not in pal.x_operateur_ids.ids:
            pal.sudo().write({'x_operateur_ids': [(4, emp.id)]})
