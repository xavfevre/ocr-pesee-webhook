STAGES = [113, 119, 114, 115, 116, 117, 118]   # Nouveau, Devis, Commandé, En fabrication, Fabriqué, Livré, Facturé

def etape(task):
    """Étape de la tâche Commande Pierres d'après ses devis/commandes et ses OF : ne recule jamais."""
    sos, ofs = task.x_studio_devis_commandes_1, task.x_studio_of
    etats = [o.state for o in ofs]
    idx = 1 if sos else 0
    if any(s.state == 'sale' for s in sos):
        idx = max(idx, 2)
    if any(e in ('confirmed', 'progress', 'to_close') for e in etats):
        idx = max(idx, 3)
    if etats and 'done' in etats and all(e in ('done', 'cancel') for e in etats):
        idx = max(idx, 4)
    if any(s.delivery_status == 'full' for s in sos):
        idx = max(idx, 5)
    if any(s.invoice_status == 'invoiced' for s in sos):
        idx = max(idx, 6)
    cur = STAGES.index(task.stage_id.id) if task.stage_id and task.stage_id.id in STAGES else 0
    if idx > cur:
        task.write({'stage_id': STAGES[idx]})

etape(record)
