# Action serveur Odoo 2046 — « Transport : Nouvelle demande -> In Progress à la planification »
# Automatisation 83 (on_write, planned_date_begin renseigné, étape Nouvelle demande).
# Depuis le 02/09/2026 : les tâches étiquetées TP (tag 1) partent dans l'étape TP (84)
# pour apparaître dans la colonne du kanban Planning TP ; les autres en In Progress (11).

# Demande de transport : Nouvelle demande -> In Progress des qu'une date est planifiee
# (les taches etiquetees TP partent dans l'etape TP, pour la colonne Planning TP)
for rec in records:
    if rec.project_id.name == 'Demande de transport' and rec.stage_id and rec.stage_id.name == 'Nouvelle demande' and rec.planned_date_begin:
        rec.write({'stage_id': 84 if 1 in rec.tag_ids.ids else 11})
