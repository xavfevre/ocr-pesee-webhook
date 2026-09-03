# Action serveur Odoo 2055 — « Parc auto : enregistrer une intervention (planning web) »
# ARCHIVE avant suppression (03/09/2026) — portée vers Render (web_actions.py, action 2055)
# Compteur de lignes de l'abonnement Odoo (« Maintenance par 100 lignes »).

# Planning des controles : enregistre une intervention dans l'historique Fleet natif,
# planifie automatiquement le prochain controle, gere la contre-visite,
# et peut appliquer la meme validation a l'attelage habituel (tracteur <-> remorque).
ctx = env.context
rid = ctx.get('pc_id')
date_val = (ctx.get('pc_date') or '').strip()
cv_limite = (ctx.get('pc_cv_limite') or '').strip()
cv_done = ctx.get('pc_cv_done')
row = env['x_controle_vehicule'].sudo().browse(int(rid))
fst = row.x_type_id.x_fleet_service_type_id

if cv_limite:
    row.write({'x_cv_limite': cv_limite})
    if fst:
        env['fleet.vehicle.log.services'].sudo().create({
            'vehicle_id': row.x_vehicule_id.id,
            'service_type_id': fst.id,
            'date': cv_limite,
            'state': 'new',
            'notes': 'CONTRE-VISITE a passer avant cette date (planning des controles obligatoires)',
        })
    action = {'ok': 1}
elif cv_done:
    dd = date_val or str(datetime.date.today())
    if fst:
        anciens = env['fleet.vehicle.log.services'].sudo().search([
            ('vehicle_id', '=', row.x_vehicule_id.id),
            ('service_type_id', '=', fst.id),
            ('state', '=', 'new'),
            ('notes', 'like', 'CONTRE-VISITE'),
        ])
        anciens.write({'state': 'cancelled'})
        env['fleet.vehicle.log.services'].sudo().create({
            'vehicle_id': row.x_vehicule_id.id,
            'service_type_id': fst.id,
            'date': dd,
            'state': 'done',
            'notes': 'Contre-visite effectuee (planning des controles obligatoires)',
        })
    row.write({'x_cv_limite': False})
    action = {'ok': 1}
else:
    cibles = [row]
    if date_val and ctx.get('pc_combo_too'):
        partenaire = row.x_vehicule_id.x_attelage_id
        if partenaire:
            prow = env['x_controle_vehicule'].sudo().search([
                ('x_vehicule_id', '=', partenaire.id),
                ('x_type_id', '=', row.x_type_id.id),
            ], limit=1)
            if prow:
                cibles.append(prow)
    for cible in cibles:
        cfst = cible.x_type_id.x_fleet_service_type_id
        if cfst:
            ancien_planifie = env['fleet.vehicle.log.services'].sudo().search([
                ('vehicle_id', '=', cible.x_vehicule_id.id),
                ('service_type_id', '=', cfst.id),
                ('state', '=', 'new'),
            ])
            ancien_planifie.write({'state': 'cancelled'})
        if date_val:
            if cfst:
                # une correction fait foi : les « Terminé » dates APRES la nouvelle
                # date (saisie erronee) sont annules, sinon l'affichage (dernier
                # Terminé) continuerait de montrer l'ancienne date
                errones = env['fleet.vehicle.log.services'].sudo().search([
                    ('vehicle_id', '=', cible.x_vehicule_id.id),
                    ('service_type_id', '=', cfst.id),
                    ('state', '=', 'done'),
                    ('date', '>', date_val),
                ])
                errones.write({'state': 'cancelled'})
                env['fleet.vehicle.log.services'].sudo().create({
                    'vehicle_id': cible.x_vehicule_id.id,
                    'service_type_id': cfst.id,
                    'date': date_val,
                    'state': 'done',
                    'notes': 'Saisi depuis le planning des controles obligatoires (/parc-controles)',
                })
                prochaine = datetime.datetime.strptime(date_val, '%Y-%m-%d').date() + datetime.timedelta(days=30 * cible.x_type_id.x_periodicite_mois)
                env['fleet.vehicle.log.services'].sudo().create({
                    'vehicle_id': cible.x_vehicule_id.id,
                    'service_type_id': cfst.id,
                    'date': prochaine,
                    'state': 'new',
                    'notes': 'Prochain controle planifie automatiquement (planning des controles obligatoires)',
                })
            cible.write({'x_derniere_date': date_val, 'x_cv_limite': False})
        else:
            cible.write({'x_derniere_date': False, 'x_cv_limite': False})
    action = {'ok': 1, 'nb': len(cibles)}
