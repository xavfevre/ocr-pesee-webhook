
NON_ANCHOR_TYPES = ('line_section', 'line_note')
for move in records:
    if move.move_type not in ('out_invoice', 'out_refund'):
        continue
    if not move.invoice_origin:
        continue
    origins = []
    for o in move.invoice_origin.split(','):
        o = o.strip()
        if o:
            origins.append(o)
    if not origins:
        continue
    orders = env['sale.order'].sudo().search([('name', 'in', origins)])
    if not orders:
        continue
    ordered = list(orders.order_line.sorted('sequence'))
    index_by_id = {}
    idx_counter = 0
    for ol in ordered:
        index_by_id[ol.id] = idx_counter
        idx_counter += 1

    inv_list = list(move.invoice_line_ids.sorted('sequence'))
    existing_section_order_ids = set()
    existing_section_names = []
    for il in inv_list:
        if il.display_type == 'line_section':
            if il.sale_line_ids:
                existing_section_order_ids.add(il.sale_line_ids[0].id)
            existing_section_names.append((il.name or '').lower())
    existing_names_blob = ' || '.join(existing_section_names)

    inserted_this_run = set()
    insertion_map = {}
    for il in inv_list:
        if il.display_type in NON_ANCHOR_TYPES or not il.sale_line_ids:
            continue
        sol = il.sale_line_ids[0]
        if sol.id not in index_by_id:
            continue
        j = index_by_id[sol.id] - 1
        ancestors = []
        while j >= 0:
            prev = ordered[j]
            if prev.display_type == 'line_section':
                ancestors.append(prev)
                j -= 1
            else:
                break
        ancestors.reverse()
        if not ancestors:
            continue
        ancestor_ids = set()
        for a in ancestors:
            ancestor_ids.add(a.id)
        marker_id = il.id
        best_found = False
        for x in inv_list:
            if best_found:
                break
            if x.display_type == 'line_section' and x.sale_line_ids and x.sale_line_ids[0].id in ancestor_ids:
                marker_id = x.id
                best_found = True
        missing = []
        for anc in ancestors:
            prefix = (anc.name or '').split(' - ')[0].strip().lower()
            deja_par_nom = bool(prefix) and prefix in existing_names_blob
            if anc.id not in existing_section_order_ids and anc.id not in inserted_this_run and not deja_par_nom:
                missing.append(anc)
                inserted_this_run.add(anc.id)
        if missing:
            insertion_map[marker_id] = missing

    if not insertion_map:
        continue

    full_plan = []
    for il in inv_list:
        if il.id in insertion_map:
            for anc in insertion_map[il.id]:
                full_plan.append(('new', anc))
        full_plan.append(('existing', il))

    seq = 0
    for kind, obj in full_plan:
        seq += 10
        if kind == 'existing':
            if obj.sequence != seq:
                obj.sudo().write({'sequence': seq})
        else:
            env['account.move.line'].sudo().create({
                'move_id': move.id,
                'display_type': 'line_section',
                'name': obj.name,
                'sequence': seq,
                'sale_line_ids': [(6, 0, [obj.id])],
            })
