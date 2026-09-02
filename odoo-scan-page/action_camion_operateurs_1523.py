# Action serveur Odoo 1523 (automatisation 18, on_create_or_write project.task)
# 1) lie le vehicule Fleet depuis le nom du transport ;
# 2) ajoute le chauffeur aux Operateurs (vue unifiee par personne) ;
# 3) date les taches terminees sans date planifiee (duplication native).

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

# vue unifiee du Service sur site : le chauffeur fait partie des operateurs
# (colonnes par personne, groupees sur x_studio_operateurs)
for record in records:
    if record.x_studio_chauffeur and record.x_studio_chauffeur.id not in record.x_studio_operateurs.ids:
        record.write({'x_studio_operateurs': [(4, record.x_studio_chauffeur.id)]})


# une tache marquee Terminee sans date planifiee (duplication native d'Odoo :
# les dates ne sont pas copiees) recoit la date du moment — sinon elle est
# invisible des plannings et de la facturation
for record in records:
    if record.state == '1_done' and not record.planned_date_begin:
        record.write({'planned_date_begin': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
