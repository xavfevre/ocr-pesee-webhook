# Action serveur Odoo 1963 (automatisation 69, worksheet on_create_or_write)
# Pré-remplit le « Camion réel » (x_vehicle_id, désormais éditable) depuis la tâche.
# Contexte : x_vehicle_id du worksheet n'est plus un champ related readonly ; le chauffeur peut le corriger.
for record in records:
    if not record.x_vehicle_id and record.x_project_task_id and record.x_project_task_id.x_vehicle_id:
        record.write({'x_vehicle_id': record.x_project_task_id.x_vehicle_id.id})
