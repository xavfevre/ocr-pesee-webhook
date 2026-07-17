# Action serveur Odoo 1524 — « Mettre à jour odomètre Fleet » (automatisation 19, worksheet on_create_or_write)
# v3 :
#  - garde-fou : compteur qui recule ou saut > 15 000 km => relevé non créé ;
#  - date du relevé = date de la feuille (x_studio_date, rempli à 100 %), pas la date de saisie —
#    une feuille remplie/modifiée en retard ne fausse plus la chronologie ;
#  - déduplication toutes dates confondues (vehicle_id + value) : la re-sauvegarde d'une feuille
#    ne recrée jamais un relevé (cause historique de 98 doublons).
for record in records:
    km = record.x_studio_km
    veh = record.x_vehicle_id
    if km and veh:
        cur = veh.odometer or 0.0
        if cur and (km < cur - 1000 or km > cur + 15000):
            continue
        existing = env['fleet.vehicle.odometer'].search([
            ('vehicle_id', '=', veh.id),
            ('value', '=', km),
        ], limit=1)
        if not existing:
            odo_date = record.x_studio_date or datetime.date.today()
            vals = {
                'vehicle_id': veh.id,
                'value': km,
                'date': odo_date,
            }
            if record.x_studio_conducteur:
                vals['x_studio_employ'] = record.x_studio_conducteur.id
            env['fleet.vehicle.odometer'].create(vals)
