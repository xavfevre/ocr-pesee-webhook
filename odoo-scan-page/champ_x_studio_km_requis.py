# Champ calculé Odoo x_studio_km_requis (id 53731) — modèle x_project_task_worksheet_template_1
# bool, non stocké, depends: x_vehicle_id,x_studio_km
# Vrai si aucun relevé odomètre aujourd'hui pour le camion → la vue rend le kilométrage
# obligatoire (1re tâche du jour) et affiche un bandeau d'avertissement.
# NB : x_vehicle_id (champ 24630) a été détaché de la tâche (related supprimé, readonly=False) ;
# il est pré-rempli par l'automatisation 69 et synchronisé par la 70.
for record in self:
    req = False
    if record.x_vehicle_id and not record.x_studio_km:
        n = record.env['fleet.vehicle.odometer'].search_count([
            ('vehicle_id', '=', record.x_vehicle_id.id),
            ('date', '=', datetime.date.today()),
        ])
        req = not n
    record['x_studio_km_requis'] = req
