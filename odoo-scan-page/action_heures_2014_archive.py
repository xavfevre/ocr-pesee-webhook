# Planning RH : approuver / refuser une demande de congés
ctx = env.context
dc_id = ctx.get('dc_id')
adm = (ctx.get('hj_k') or '')
adm_ref = env['ir.config_parameter'].sudo().get_param('maquignon.rh_admin_key') or ''
if dc_id and adm and adm == adm_ref:
    dc = env['x_demande_conge'].sudo().browse(int(dc_id))
    decision = ctx.get('dc_decision')
    if decision not in ('approuve', 'refuse'):
        raise UserError('Décision invalide.')
    dc.write({'x_statut': decision, 'x_reponse': (ctx.get('dc_reponse') or '').strip() or False})
    n = 0
    if decision == 'approuve':
        emp = dc.x_employee_id
        cal = emp.resource_calendar_id
        typmap = {'cp': 'cp', 'recup': 'recup', 'sans_solde': 'absence', 'maternite': 'absence', 'paternite': 'absence', 'evt_familial': 'absence', 'enfant_malade': 'absence'}
        typlbl = {'cp': 'Congés payés', 'recup': 'Récupération', 'sans_solde': 'Sans solde', 'maternite': 'Congé maternité', 'paternite': 'Congé paternité', 'evt_familial': 'Événement familial', 'enfant_malade': 'Enfant malade'}
        jtyp = typmap.get(dc.x_type, 'cp')
        periode = dc.x_periode or 'journee'
        HJ = env['x_heures_jour'].sudo()
        d = dc.x_du
        while d <= dc.x_au:
            rngs = []
            if cal:
                days = (d - datetime.date(1970, 1, 5)).days
                wt = str((days // 7) % 2)
                for att in cal.attendance_ids:
                    if att.dayofweek != str(d.weekday()):
                        continue
                    if cal.two_weeks_calendar and att.week_type and att.week_type != wt:
                        continue
                    if att.display_type:
                        continue
                    rngs.append([att.hour_from, att.hour_to])
            theo = 0.0
            for r in rngs:
                theo += (r[1] - r[0])
            if theo > 0:
                dstr = d.strftime('%Y-%m-%d')
                keep = []
                if periode == 'matin':
                    keep = [r for r in rngs if r[0] >= 12.5]
                elif periode == 'apresmidi':
                    keep = [r for r in rngs if r[0] < 12.5]
                elif periode == 'horaires':
                    for r in rngs:
                        a0 = r[0]
                        a1 = r[1]
                        if dc.x_h_a <= a0 or dc.x_h_de >= a1:
                            keep.append([a0, a1])
                        elif dc.x_h_de <= a0 and dc.x_h_a >= a1:
                            continue
                        elif dc.x_h_de <= a0:
                            keep.append([dc.x_h_a, a1])
                        elif dc.x_h_a >= a1:
                            keep.append([a0, dc.x_h_de])
                        else:
                            if (dc.x_h_de - a0) >= (a1 - dc.x_h_a):
                                keep.append([a0, dc.x_h_de])
                            else:
                                keep.append([dc.x_h_a, a1])
                if periode == 'journee' or not keep:
                    vals = {'x_employee_id': emp.id, 'x_date': dstr, 'x_type': jtyp,
                            'x_m_deb': 0.0, 'x_m_fin': 0.0, 'x_am_deb': 0.0, 'x_am_fin': 0.0,
                            'x_heures': 0.0, 'x_theo': theo, 'x_hs': 0.0,
                            'x_note': '%s approuvé (demande %s)' % (typlbl.get(dc.x_type, 'Congé'), dc.id)}
                    purge = True
                else:
                    # 2 créneaux affichables max : on garde les 2 plus longs (cohérence affichage/total)
                    keep2 = sorted(sorted(keep, key=lambda r: r[1] - r[0], reverse=True)[:2], key=lambda r: r[0])
                    m = [0.0, 0.0]
                    am = [0.0, 0.0]
                    if len(keep2) == 2:
                        m = keep2[0]
                        am = keep2[1]
                    elif keep2:
                        if keep2[0][0] < 12.5:
                            m = keep2[0]
                        else:
                            am = keep2[0]
                    tot = 0.0
                    for r in keep2:
                        tot += (r[1] - r[0])
                    if periode == 'matin':
                        perlbl = 'matin en congé'
                    elif periode == 'apresmidi':
                        perlbl = 'après-midi en congé'
                    else:
                        perlbl = 'congé de %.2gh à %.2gh' % (dc.x_h_de, dc.x_h_a)
                    vals = {'x_employee_id': emp.id, 'x_date': dstr, 'x_type': 'travail',
                            'x_m_deb': m[0], 'x_m_fin': m[1], 'x_am_deb': am[0], 'x_am_fin': am[1],
                            'x_heures': tot, 'x_theo': tot, 'x_hs': 0.0,
                            'x_note': '%s — %s (demande %s)' % (typlbl.get(dc.x_type, 'Congé'), perlbl, dc.id)}
                    purge = False
                ex = HJ.search([('x_employee_id', '=', emp.id), ('x_date', '=', dstr)], limit=1)
                if ex:
                    ex.write(vals)
                else:
                    HJ.create(vals)
                if purge:
                    tzp = timezone('Europe/Paris')
                    utcz = timezone('UTC')
                    day0 = tzp.localize(datetime.datetime(d.year, d.month, d.day)).astimezone(utcz).replace(tzinfo=None)
                    day1 = tzp.localize(datetime.datetime(d.year, d.month, d.day) + datetime.timedelta(days=1)).astimezone(utcz).replace(tzinfo=None)
                    env['hr.attendance'].sudo().search([('employee_id', '=', emp.id), ('check_in', '>=', day0.strftime('%Y-%m-%d %H:%M:%S')), ('check_in', '<', day1.strftime('%Y-%m-%d %H:%M:%S'))]).unlink()
                n += 1
            d = d + datetime.timedelta(days=1)
    action = {'dc_ok': 1, 'jours': n}
