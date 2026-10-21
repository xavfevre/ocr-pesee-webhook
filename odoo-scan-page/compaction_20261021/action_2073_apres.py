# Miroir congés natifs : chaque jour d'absence posé sur le planning maintient un hr.leave validé (lien x_hj_id). Démarrage : 01/08/2026.
DEBUT = datetime.date(2026, 8, 1)
LBL_TYPES = {'Sans solde': 9, 'Congé maternité': 80, 'Congé paternité': 81, 'Événement familial': 82, 'Enfant malade': 83}
TYPES = {'cp': 'CP', 'maladie': 2, 'recup': 8, 'sans_solde': 9}
HL = env['hr.leave'].sudo().with_context(tracking_disable=True, mail_notrack=True, mail_create_nosubscribe=True, mail_activity_automation_skip=True, mail_notify_force_send=False)
for rec in records:
    if not rec.x_date or rec.x_date < DEBUT or not rec.x_employee_id:
        continue
    note, half, lt = rec.x_note or '', False, TYPES.get(rec.x_type)
    if rec.x_type == 'absence':
        lt = LBL_TYPES.get(note.split(' approuvé')[0].split(' — ')[0].strip(), 84)
    elif rec.x_type == 'travail' and ' — ' in note and ('matin en congé' in note or 'après-midi en congé' in note):
        lbl = note.split(' — ')[0].strip()
        half = 'am' if 'matin en congé' in note else 'pm'
        lt = {'Congés payés': 'CP', 'Récupération': 8, 'Maladie': 2}.get(lbl) or LBL_TYPES.get(lbl, 84)
    keep = False
    for l in HL.search([('x_hj_id', '=', rec.id)]):
        tid_ok = (lt == 'CP' and l.holiday_status_id.id in (1, 7)) or (lt == l.holiday_status_id.id)
        if lt and tid_ok and (l.request_date_from_period if l.request_unit_half else False) == (half or False) and l.state == 'validate' and not keep:
            keep = True
        else:
            for fn in (l.action_refuse, l.unlink):
                try:
                    fn()
                except Exception:
                    pass
    if lt and not keep:
        tid = lt
        if lt == 'CP':   # consommer d'abord le reliquat N-1 (convention paie française)
            dom = [('employee_id', '=', rec.x_employee_id.id), ('holiday_status_id', '=', 7), ('state', '=', 'validate')]
            reste = sum(env['hr.leave.allocation'].sudo().search(dom).mapped('number_of_days')) - sum(env['hr.leave'].sudo().search(dom).mapped('number_of_days'))
            tid = 7 if reste >= (0.5 if half else 1.0) else 1
        jour = rec.x_date.strftime('%Y-%m-%d')
        vals = {'employee_id': rec.x_employee_id.id, 'holiday_status_id': tid, 'request_date_from': jour, 'request_date_to': jour, 'x_hj_id': rec.id, 'name': (note or 'Pose planning')[:120]}
        if half:
            vals['request_date_from_period'] = half
        try:
            l = HL.create(vals)
            if half:   # request_unit_half / number_of_days sont readonly ORM en v19 : fixation SQL (0,5 j + fenêtre UTC)
                win = ('06:00:00', '10:00:00') if half == 'am' else ('11:00:00', '15:00:00')
                env.cr.execute('UPDATE hr_leave SET request_unit_half = TRUE, number_of_days = 0.5, date_from = %s, date_to = %s WHERE id = %s', [jour + ' ' + win[0], jour + ' ' + win[1], l.id])
                env.invalidate_all()
            if l.state in ('draft', 'confirm'):
                l.action_approve()
            try:
                if l.state != 'validate':
                    l.action_validate()
            except Exception:
                pass
        except Exception as e:
            env['ir.logging'].sudo().create({'name': 'conges_natifs', 'type': 'server', 'level': 'WARNING', 'dbname': env.cr.dbname, 'path': 'base_automation', 'func': 'sync_conges', 'line': '0',
                                             'message': 'Miroir hr.leave impossible (jour %s, %s) : %s' % (rec.id, rec.x_date, str(e)[:300])})
