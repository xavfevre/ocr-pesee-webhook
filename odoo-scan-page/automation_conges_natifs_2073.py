# Automatisations base.automation sur x_heures_jour (miroir congés natifs hr.leave)
# - automation 87 / action 2073 : on_create_or_write (ci-dessous, partie 1)
# - automation 88 / action 2074 : on_unlink (partie 2)
# Champ de liaison : hr.leave.x_hj_id (integer) ; démarrage de gestion : 01/08/2026.
# Types natifs : CP 1, CP N-1 7, Maladie 2, Récup 8, Sans solde 9,
#   Maternité 80, Paternité 81, Évén. familial 82, Enfant malade 83, Absence injustifiée 84.

# ============ PARTIE 1 — action 2073 (on_create_or_write) ============
# Miroir congés natifs : chaque jour d'absence posé sur le planning maintient
# un hr.leave validé (lien x_hj_id). Démarrage de la gestion : 01/08/2026.
DEBUT = datetime.date(2026, 8, 1)
LBL_TYPES = {'Sans solde': 9, 'Congé maternité': 80, 'Congé paternité': 81,
             'Événement familial': 82, 'Enfant malade': 83}
HL = env['hr.leave'].sudo().with_context(
    tracking_disable=True, mail_notrack=True, mail_create_nosubscribe=True,
    mail_activity_automation_skip=True, mail_notify_force_send=False)
for rec in records:
    if not rec.x_date or rec.x_date < DEBUT or not rec.x_employee_id:
        continue
    note = rec.x_note or ''
    half = False
    lt = None
    if rec.x_type == 'cp':
        lt = 'CP'
    elif rec.x_type == 'maladie':
        lt = 2
    elif rec.x_type == 'recup':
        lt = 8
    elif rec.x_type == 'absence':
        lbl = note.split(' approuvé')[0].split(' — ')[0].strip()
        lt = LBL_TYPES.get(lbl, 84)
    elif rec.x_type == 'travail' and ' — ' in note and ('matin en congé' in note or 'après-midi en congé' in note):
        lbl = note.split(' — ')[0].strip()
        half = 'am' if 'matin en congé' in note else 'pm'
        lt = {'Congés payés': 'CP', 'Récupération': 8, 'Maladie': 2}.get(lbl) or LBL_TYPES.get(lbl, 84)
    old = HL.search([('x_hj_id', '=', rec.id)])
    keep = False
    for l in old:
        l_half = (l.request_date_from_period if l.request_unit_half else False)
        tid_ok = (lt == 'CP' and l.holiday_status_id.id in (1, 7)) or (lt == l.holiday_status_id.id)
        if lt and tid_ok and l_half == (half or False) and l.state == 'validate' and not keep:
            keep = True
        else:
            try:
                l.action_refuse()
            except Exception:
                pass
            try:
                l.unlink()
            except Exception:
                pass
    if lt and not keep:
        tid = lt
        if lt == 'CP':
            # consommer d'abord le reliquat N-1 (convention paie française)
            a7 = sum(env['hr.leave.allocation'].sudo().search([('employee_id', '=', rec.x_employee_id.id), ('holiday_status_id', '=', 7), ('state', '=', 'validate')]).mapped('number_of_days'))
            p7 = sum(env['hr.leave'].sudo().search([('employee_id', '=', rec.x_employee_id.id), ('holiday_status_id', '=', 7), ('state', '=', 'validate')]).mapped('number_of_days'))
            tid = 7 if (a7 - p7) >= (0.5 if half else 1.0) else 1
        vals = {'employee_id': rec.x_employee_id.id, 'holiday_status_id': tid,
                'request_date_from': rec.x_date.strftime('%Y-%m-%d'),
                'request_date_to': rec.x_date.strftime('%Y-%m-%d'),
                'x_hj_id': rec.id, 'name': (note or 'Pose planning')[:120]}
        if half:
            vals['request_date_from_period'] = half
        try:
            l = HL.create(vals)
            if half:
                # request_unit_half / number_of_days sont readonly ORM en v19 et la durée
                # ne se recalcule pas depuis la période : fixation SQL (0,5 j + fenêtre UTC)
                win = ('06:00:00', '10:00:00') if half == 'am' else ('11:00:00', '15:00:00')
                env.cr.execute(
                    'UPDATE hr_leave SET request_unit_half = TRUE, number_of_days = 0.5, '
                    'date_from = %s, date_to = %s WHERE id = %s',
                    ['%s %s' % (rec.x_date.strftime('%Y-%m-%d'), win[0]),
                     '%s %s' % (rec.x_date.strftime('%Y-%m-%d'), win[1]), l.id])
                env.invalidate_all()
            if l.state in ('draft', 'confirm'):
                l.action_approve()
            try:
                if l.state != 'validate':
                    l.action_validate()
            except Exception:
                pass
        except Exception as e:
            env['ir.logging'].sudo().create({'name': 'conges_natifs', 'type': 'server', 'level': 'WARNING',
                'dbname': env.cr.dbname, 'message': 'Miroir hr.leave impossible (jour %s, %s) : %s' % (rec.id, rec.x_date, str(e)[:300]),
                'path': 'base_automation', 'func': 'sync_conges', 'line': '0'})


# ============ PARTIE 2 — action 2074 (on_unlink) ============
# Suppression d'un jour de planning : retirer le congé natif lié
for rec in records:
    for l in env['hr.leave'].sudo().search([('x_hj_id', '=', rec.id)]):
        try:
            l.action_refuse()
        except Exception:
            pass
        try:
            l.unlink()
        except Exception:
            pass

