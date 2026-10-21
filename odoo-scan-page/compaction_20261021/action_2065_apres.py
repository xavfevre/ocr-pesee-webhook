for move in records:
    origins = [o.strip() for o in (move.invoice_origin or '').split(',') if o.strip()]
    if move.move_type not in ('out_invoice', 'out_refund') or not origins:
        continue
    orders = env['sale.order'].sudo().search([('name', 'in', origins)])
    if not orders:
        continue
    ordered = list(orders.order_line.sorted('sequence'))
    index_by_id = {ol.id: i for i, ol in enumerate(ordered)}
    inv_list = list(move.invoice_line_ids.sorted('sequence'))
    sections = [il for il in inv_list if il.display_type == 'line_section']
    existing_ids = {il.sale_line_ids[0].id for il in sections if il.sale_line_ids}
    names_blob = ' || '.join((il.name or '').lower() for il in sections)
    inserted, insertion_map = set(), {}
    for il in inv_list:
        if il.display_type in ('line_section', 'line_note') or not il.sale_line_ids or il.sale_line_ids[0].is_downpayment or il.sale_line_ids[0].id not in index_by_id:
            continue
        j, ancestors = index_by_id[il.sale_line_ids[0].id] - 1, []
        while j >= 0 and ordered[j].display_type == 'line_section':   # sections immédiatement au-dessus de la ligne dans le bon
            ancestors.append(ordered[j])
            j -= 1
        ancestors.reverse()
        if not ancestors:
            continue
        ancestor_ids = {a.id for a in ancestors}
        marker_id = il.id
        for x in inv_list:
            if x.display_type == 'line_section' and x.sale_line_ids and x.sale_line_ids[0].id in ancestor_ids:
                marker_id = x.id
                break
        missing = []
        for anc in ancestors:
            prefix = (anc.name or '').split(' - ')[0].strip().lower()
            if anc.id not in existing_ids and anc.id not in inserted and not (prefix and prefix in names_blob):
                missing.append(anc)
                inserted.add(anc.id)
        if missing:
            insertion_map[marker_id] = missing
    if not insertion_map:
        continue
    seq = 0
    for il in inv_list:
        for anc in insertion_map.get(il.id, []):
            seq += 10
            env['account.move.line'].sudo().create({'move_id': move.id, 'display_type': 'line_section', 'name': anc.name, 'sequence': seq, 'sale_line_ids': [(6, 0, [anc.id])]})
        seq += 10
        if il.sequence != seq:
            il.sudo().write({'sequence': seq})
