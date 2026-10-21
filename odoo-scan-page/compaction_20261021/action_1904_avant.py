TASKS = records.mapped('x_studio_tache')
STAGES = [113, 119, 114, 115, 116, 117, 118]
for task in TASKS:
    if not task:
        continue
    so_recs = task.x_studio_devis_commandes_1
    of_recs = task.x_studio_of
    idx = 0
    if so_recs:
        idx = 1
    has_sale = False
    has_deliv = False
    has_inv = False
    for s in so_recs:
        if s.state == 'sale':
            has_sale = True
        if s.delivery_status == 'full':
            has_deliv = True
        if s.invoice_status == 'invoiced':
            has_inv = True
    of_total = 0
    of_done = 0
    of_open = 0
    of_inprog = False
    for o in of_recs:
        of_total += 1
        if o.state in ('confirmed', 'progress', 'to_close'):
            of_inprog = True
        if o.state == 'done':
            of_done += 1
        if o.state not in ('done', 'cancel'):
            of_open += 1
    if has_sale and idx < 2:
        idx = 2
    if of_inprog and idx < 3:
        idx = 3
    if of_total > 0 and of_open == 0 and of_done > 0 and idx < 4:
        idx = 4
    if has_deliv and idx < 5:
        idx = 5
    if has_inv and idx < 6:
        idx = 6
    cur = 0
    if task.stage_id and task.stage_id.id in STAGES:
        cur = STAGES.index(task.stage_id.id)
    if idx > cur:
        task.write({'stage_id': STAGES[idx]})
