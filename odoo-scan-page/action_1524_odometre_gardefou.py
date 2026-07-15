# Action serveur Odoo 1524 — « Mettre à jour odomètre Fleet » (automatisation 19, worksheet on_create_or_write)
# Garde-fou ajouté : un compteur ne recule pas, et un saut > 15 000 km signale un camion/valeur erroné(e).
for record in records:
    km = record.x_studio_km
    veh = record.x_vehicle_id
    if km and veh:
        cur = veh.odometer or 0.0
        # Garde-fou : un compteur ne recule pas, et un saut > 15 000 km = camion/valeur erroné(e)
        if cur and (km < cur - 1000 or km > cur + 15000):
            continue
        existing = env['fleet.vehicle.odometer'].search([
            ('vehicle_id', '=', veh.id),
            ('value', '=', km),
            ('date', '=', datetime.date.today()),
        ], limit=1)
        if not existing:
            vals = {
                'vehicle_id': veh.id,
                'value': km,
                'date': datetime.date.today(),
            }
            if record.x_studio_conducteur:
                vals['x_studio_employ'] = record.x_studio_conducteur.id
            env['fleet.vehicle.odometer'].create(vals)
