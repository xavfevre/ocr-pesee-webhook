# Page horaires : semaine type d'un salarié (simple ou cycle 2 semaines)
ctx = env.context
adm = (ctx.get('hj_k') or '')
adm_ref = env['ir.config_parameter'].sudo().get_param('maquignon.rh_admin_key') or ''
emp_id = ctx.get('emp_id')
hor = ctx.get('horaires')
hor_b = ctx.get('horaires_b') or []
deux = bool(ctx.get('deux_semaines')) and len(hor_b) == 7
if emp_id and adm and adm == adm_ref and hor and len(hor) == 7:
    emp = env['hr.employee'].sudo().browse(int(emp_id))
    JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    weeks = [(hor, '0', 1, 'Semaine A')]
    if deux:
        weeks.append((hor_b, '1', 26, 'Semaine B'))
    att_vals = []
    tot = 0.0
    ndays = 0
    for wk in weeks:
        hh = wk[0]
        wt = wk[1]
        seq = wk[2]
        if deux:
            att_vals.append((0, 0, {'name': wk[3], 'dayofweek': '0',
                                    'hour_from': 0.0, 'hour_to': 0.0,
                                    'day_period': 'morning', 'week_type': wt,
                                    'display_type': 'line_section', 'sequence': seq - 1}))
        for i in range(7):
            md = float(hh[i][0] or 0)
            mf = float(hh[i][1] or 0)
            ad = float(hh[i][2] or 0)
            af = float(hh[i][3] or 0)
            day = False
            if mf > md:
                v = {'name': JOURS[i] + ' matin', 'dayofweek': str(i),
                     'hour_from': md, 'hour_to': mf, 'day_period': 'morning',
                     'sequence': seq + i * 3}
                if deux:
                    v['week_type'] = wt
                att_vals.append((0, 0, v))
                tot += mf - md
                day = True
            if af > ad:
                v = {'name': JOURS[i] + ' après-midi', 'dayofweek': str(i),
                     'hour_from': ad, 'hour_to': af, 'day_period': 'afternoon',
                     'sequence': seq + i * 3 + 1}
                if deux:
                    v['week_type'] = wt
                att_vals.append((0, 0, v))
                tot += af - ad
                day = True
            if day:
                ndays += 1
    if not att_vals:
        raise UserError('Aucune plage horaire saisie.')
    name = 'Horaire — %s' % emp.name
    cal = emp.resource_calendar_id
    err = ''
    if cal and (cal.name or '').startswith('Horaire — '):
        cal.sudo().write({'attendance_ids': [(5, 0, 0)]})
        cal.sudo().write({'name': name, 'two_weeks_calendar': deux,
                          'attendance_ids': att_vals})
        newcal = cal
    else:
        newcal = env['resource.calendar'].sudo().create({
            'name': name, 'company_id': emp.company_id.id,
            'two_weeks_calendar': deux, 'attendance_ids': att_vals})
        try:
            emp.write({'resource_calendar_id': newcal.id})
        except Exception as e:
            det = str(e)
            if 'attribution' in det or 'allocation' in det:
                raise UserError("Impossible de changer l'horaire de %s : un de ses congés déjà validés n'est couvert par aucune attribution de congés (période close ou attribution manquante). Créez l'attribution correspondante dans Congés, puis réessayez." % emp.name)
            raise UserError("Impossible de changer l'horaire de %s : %s" % (emp.name, det[:200]))
    if ndays:
        newcal.sudo().write({'hours_per_day': tot / ndays})
    action = {'ok': 1, 'total': tot, 'deux': deux, 'cal': newcal.id,
              'semaine': tot / 2.0 if deux else tot}


# --- Saisie des congés acquis N / N-1 depuis la page Horaires par défaut ---
if ctx.get('cp_mode') and emp_id and adm and adm == adm_ref:
    emp = env['hr.employee'].sudo().browse(int(emp_id))
    ALLOC = env['hr.leave.allocation'].sudo()
    resultat = {}
    for cle, type_id, libelle in [('cp_n', 1, 'Congés payés'), ('cp_n1', 7, 'Congés Payés N-1')]:
        brut = ctx.get(cle)
        if brut in (None, ''):
            continue
        try:
            val = float(brut)
        except Exception:
            raise UserError('Valeur invalide pour %s.' % libelle)
        if val < 0 or val > 100:
            raise UserError('Valeur hors limites pour %s (0 à 100 jours).' % libelle)
        allocs = ALLOC.search([('employee_id', '=', emp.id), ('holiday_status_id', '=', type_id), ('state', '=', 'validate')], order='id')
        if allocs:
            # consolidation : une seule allocation validee porte la valeur saisie
            # (celle du plan d'acquisition si elle existe, sinon la plus recente) ;
            # les autres sont refusees (une allocation ne peut pas valoir 0 en v19)
            accr = allocs.filtered(lambda a: a.allocation_type == 'accrual')
            keeper = accr[-1] if accr else allocs[-1]
            aujourd = datetime.date.today()
            periode_debut = datetime.date(aujourd.year if aujourd.month >= 6 else aujourd.year - 1, 6, 1).strftime('%Y-%m-%d')
            if val > 0:
                vals_k = {'number_of_days': val}
                if not keeper.date_from or keeper.date_from.strftime('%Y-%m-%d') > periode_debut:
                    # la validité doit couvrir la période de congés (sinon Odoo
                    # refuse les congés antérieurs à la date de l'allocation)
                    vals_k['date_from'] = periode_debut
                keeper.write(vals_k)
                for al in (allocs - keeper):
                    al.action_refuse()
            else:
                for al in allocs:
                    al.action_refuse()
        else:
            aujourd = datetime.date.today()
            periode_debut = datetime.date(aujourd.year if aujourd.month >= 6 else aujourd.year - 1, 6, 1).strftime('%Y-%m-%d')
            nouv = ALLOC.create({
                'name': '%s (%g jour(s))' % (libelle, val),
                'employee_id': emp.id,
                'holiday_status_id': type_id,
                'number_of_days': val,
                'allocation_type': 'regular',
                'date_from': periode_debut,
            })
            nouv.action_approve()
        resultat[cle] = val
    brut_r = ctx.get('recup_h')
    if brut_r not in (None, ''):
        try:
            val_r = float(brut_r)
        except Exception:
            raise UserError('Valeur invalide pour les heures à récupérer.')
        if val_r < -500 or val_r > 500:
            raise UserError('Heures à récupérer hors limites (-500 à 500).')
        emp.write({'x_recup_solde': val_r})
        resultat['recup_h'] = val_r
    brut_cm = ctx.get('contrat_mensuel')
    if brut_cm is not None:
        if str(brut_cm).strip() == '':
            emp.write({'x_contrat_mensuel': 0})
        else:
            try:
                v_cm = float(str(brut_cm).replace(',', '.'))
            except Exception:
                raise UserError('Contrat mensuel invalide.')
            if v_cm < 0 or v_cm > 300:
                raise UserError('Contrat mensuel hors limites (0 à 300 h).')
            emp.write({'x_contrat_mensuel': v_cm})
    brut_m = ctx.get('matricule')
    if brut_m is not None:
        emp.write({'x_matricule_paie': (str(brut_m).strip() or False)})
    if resultat:
        # une saisie de CP peut débloquer le miroir natif : relancer les jours d'août sans hr.leave
        HJ2 = env['x_heures_jour'].sudo()
        HL2 = env['hr.leave'].sudo()
        for rec2 in HJ2.search([('x_employee_id', '=', emp.id), ('x_date', '>=', '2026-08-01')]):
            est_conge = rec2.x_type in ('cp', 'maladie', 'recup', 'absence') or (rec2.x_type == 'travail' and rec2.x_note and 'en congé' in rec2.x_note)
            if est_conge and not HL2.search_count([('x_hj_id', '=', rec2.id), ('state', '=', 'validate')]):
                rec2.write({'x_note': rec2.x_note})
    brut_d = ctx.get('cp_date')
    if resultat:
        ref = None
        if brut_d:
            try:
                ref = datetime.datetime.strptime(str(brut_d)[:10], '%Y-%m-%d').date()
            except Exception:
                raise UserError('Date de saisie invalide (format attendu AAAA-MM-JJ).')
        else:
            ref = datetime.date.today()
        emp.write({'x_cp_ref_date': ref.strftime('%Y-%m-%d')})
        resultat['cp_date'] = ref.strftime('%Y-%m-%d')
    action = {'ok': 1, 'maj': resultat}