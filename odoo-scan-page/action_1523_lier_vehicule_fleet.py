# Action serveur 1523 — automatisation 18 « Lier véhicule Fleet automatiquement »
# Déclencheur : project.task on_create_or_write (donc aussi à la duplication).
# sudo() sur la recherche fleet.vehicle : l'utilisateur qui crée/duplique la
# tâche n'a pas forcément le droit Parc automobile (ex. Céline CERBELLE).
for record in records:
    if record.x_studio_transport and not record.x_vehicle_id:
        transport_name = record.x_studio_transport.name or ''
        # sudo : la recherche de vehicules est un mecanisme technique,
        # l'utilisateur qui cree/duplique la tache n'a pas forcement le droit Parc automobile
        vehicles = env['fleet.vehicle'].sudo().search([])
        for vehicle in vehicles:
            if vehicle.license_plate and vehicle.license_plate in transport_name:
                record.write({'x_vehicle_id': vehicle.id})
                break
