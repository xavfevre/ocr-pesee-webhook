# Action serveur Odoo 1964 (automatisation 70, project.task on_create_or_write, champ déclencheur x_vehicle_id)
# Le planning change le camion de la tâche → répercute sur la feuille tant que le km n'est pas saisi
# (ne touche jamais une correction manuelle faite après saisie du kilométrage).
for record in records:
    if record.x_vehicle_id:
        for ws in env['x_project_task_worksheet_template_1'].search([('x_project_task_id', '=', record.id)]):
            if not ws.x_studio_km and ws.x_vehicle_id.id != record.x_vehicle_id.id:
                ws.write({'x_vehicle_id': record.x_vehicle_id.id})
