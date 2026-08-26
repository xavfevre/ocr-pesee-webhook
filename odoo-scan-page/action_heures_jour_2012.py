# Tablette : enregistrer les heures d'un salarie pour un jour (lien signe)
ctx = env.context
emp_id = ctx.get('hj_emp')
dstr = ctx.get('hj_date')
if emp_id and dstr:
    emp = env['hr.employee'].sudo().browse(int(emp_id))
    tok = (ctx.get('hj_token') or '')
    adm = (ctx.get('hj_k') or '')
    adm_ref = env['ir.config_parameter'].sudo().get_param('maquignon.rh_admin_key') or ''
    is_adm = bool(adm and adm == adm_ref)
    if not (is_adm or (tok and tok == (emp.x_heures_token or ''))):
        raise UserError('Lien invalide — demandez votre lien personnel à votre responsable.')
    d = datetime.datetime.strptime(dstr, '%Y-%m-%d').date()
    typ = ctx.get('hj_type') or 'travail'
    HJ = env['x_heures_jour'].sudo()
    ex = HJ.search([('x_employee_id', '=', emp.id), ('x_date', '=', dstr)], limit=1)
    RESERVE = ('cp', 'maladie', 'ferie', 'absence', 'recup', 'repos')
    if not is_adm:
        verrou = env['ir.config_parameter'].sudo().get_param('maquignon.heures_verrou') or ''
        if verrou and dstr <= verrou:
            raise UserError("Les feuilles d'heures jusqu'au %s sont verrouillées (paie établie). Contactez le bureau pour toute correction." % datetime.datetime.strptime(verrou, '%Y-%m-%d').strftime('%d/%m/%Y'))
        if typ != 'travail':
            raise UserError("Seul le bureau peut enregistrer un congé, une maladie, un jour férié ou une absence. Utilisez « Demander des congés » en bas de page.")
        if ex and ex.x_type in RESERVE:
            raise UserError("Cette journée a été enregistrée par le bureau : elle n'est pas modifiable ici. Prévenez le bureau en cas d'erreur.")
    md = float(ctx.get('hj_m_deb') or 0.0); mf = float(ctx.get('hj_m_fin') or 0.0)
    ad = float(ctx.get('hj_am_deb') or 0.0); af = float(ctx.get('hj_am_fin') or 0.0)
    theo = 0.0
    rngs = []
    cal = emp.resource_calendar_id
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
            theo += (att.hour_to - att.hour_from)
            rngs.append([att.hour_from, att.hour_to])
    heures = 0.0
    if typ == 'travail':
        heures = max(mf - md, 0.0) + max(af - ad, 0.0)
    periode = (ctx.get('hj_periode') or 'journee')
    partiel = bool(is_adm and typ in RESERVE and typ != 'repos' and periode in ('matin', 'apresmidi', 'horaires'))
    c_de = 0.0
    c_a = 0.0
    if partiel:
        keep = []
        if periode == 'matin':
            keep = [r for r in rngs if r[0] >= 12.5]
        elif periode == 'apresmidi':
            keep = [r for r in rngs if r[0] < 12.5]
        else:
            c_de = float(ctx.get('hj_c_de') or 0.0)
            c_a = float(ctx.get('hj_c_a') or 0.0)
            if not (0.0 <= c_de < c_a <= 24.0):
                raise UserError('Renseignez les horaires du congé (début avant fin).')
            for r in rngs:
                a0 = r[0]
                a1 = r[1]
                if c_a <= a0 or c_de >= a1:
                    keep.append([a0, a1])
                elif c_de <= a0 and c_a >= a1:
                    continue
                elif c_de <= a0:
                    keep.append([c_a, a1])
                elif c_a >= a1:
                    keep.append([a0, c_de])
                else:
                    if (c_de - a0) >= (a1 - c_a):
                        keep.append([a0, c_de])
                    else:
                        keep.append([c_a, a1])
        if not keep:
            partiel = False
        else:
            keep2 = sorted(sorted(keep, key=lambda r: r[1] - r[0], reverse=True)[:2], key=lambda r: r[0])
            m = [0.0, 0.0]
            am = [0.0, 0.0]
            if len(keep2) == 2:
                m = keep2[0]
                am = keep2[1]
            elif keep2[0][0] < 12.5:
                m = keep2[0]
            else:
                am = keep2[0]
            md = m[0]
            mf = m[1]
            ad = am[0]
            af = am[1]
            heures = 0.0
            for r in keep2:
                heures += (r[1] - r[0])
            theo = heures
            hs = 0.0
            LBL = {'cp': 'Congés payés', 'recup': 'Récupération', 'maladie': 'Maladie', 'ferie': 'Férié', 'absence': 'Absence'}
            if periode == 'matin':
                perlbl = 'matin en congé'
            elif periode == 'apresmidi':
                perlbl = 'après-midi en congé'
            else:
                perlbl = 'congé de %.2gh à %.2gh' % (c_de, c_a)
            vals = {'x_employee_id': emp.id, 'x_date': dstr, 'x_type': 'travail',
                    'x_m_deb': md, 'x_m_fin': mf, 'x_am_deb': ad, 'x_am_fin': af,
                    'x_heures': heures, 'x_theo': theo, 'x_hs': 0.0,
                    'x_note': '%s — %s (bureau)' % (LBL.get(typ, 'Congé'), perlbl)}
    if not partiel:
        hs = (heures - theo) if typ == 'travail' else 0.0
        vals = {'x_employee_id': emp.id, 'x_date': dstr, 'x_type': typ,
                'x_m_deb': md, 'x_m_fin': mf, 'x_am_deb': ad, 'x_am_fin': af,
                'x_heures': heures, 'x_theo': theo, 'x_hs': hs,
                'x_note': (ctx.get('hj_note') or '').strip() or False}
    # decouchage (nuit passee en deplacement) : coche par le salarie
    if 'hj_decouchage' in ctx:
        vals['x_decouchage'] = bool(int(ctx.get('hj_decouchage') or 0))
    if ex:
        ex.write(vals)
    else:
        HJ.create(vals)
    # Synchronisation Presences : la saisie web vaut pointage kiosque.
    tzp = timezone('Europe/Paris')
    utcz = timezone('UTC')
    day0 = tzp.localize(datetime.datetime(d.year, d.month, d.day)).astimezone(utcz).replace(tzinfo=None)
    day1 = tzp.localize(datetime.datetime(d.year, d.month, d.day) + datetime.timedelta(days=1)).astimezone(utcz).replace(tzinfo=None)
    ATT = env['hr.attendance'].sudo()
    ATT.search([('employee_id', '=', emp.id), ('check_in', '>=', day0.strftime('%Y-%m-%d %H:%M:%S')), ('check_in', '<', day1.strftime('%Y-%m-%d %H:%M:%S'))]).unlink()
    if typ == 'travail' or partiel:
        for (h1, h2) in [(md, mf), (ad, af)]:
            if h2 > h1:
                ci = tzp.localize(datetime.datetime(d.year, d.month, d.day) + datetime.timedelta(hours=h1)).astimezone(utcz).replace(tzinfo=None)
                co = tzp.localize(datetime.datetime(d.year, d.month, d.day) + datetime.timedelta(hours=h2)).astimezone(utcz).replace(tzinfo=None)
                ATT.create({'employee_id': emp.id, 'check_in': ci.strftime('%Y-%m-%d %H:%M:%S'), 'check_out': co.strftime('%Y-%m-%d %H:%M:%S')})
    action = {'hj_ok': 1, 'heures': heures, 'theo': theo, 'hs': hs, 'partiel': 1 if partiel else 0}


# --- Récup : mouvements d'heures saisis par le salarié (ou le bureau) ---
if ctx.get('recup_add') or ctx.get('recup_del'):
    emp2 = env['hr.employee'].sudo().browse(int(ctx.get('ra_emp') or 0))
    tok2 = (ctx.get('ra_token') or '')
    adm2 = (ctx.get('hj_k') or '')
    adm_ref2 = env['ir.config_parameter'].sudo().get_param('maquignon.rh_admin_key') or ''
    if not (emp2.exists() and ((adm2 and adm2 == adm_ref2) or (tok2 and emp2.x_heures_token and tok2 == emp2.x_heures_token))):
        raise UserError('Lien invalide — demandez votre lien personnel à votre responsable.')
    RL = env['x_recup_ligne'].sudo()
    is_adm2 = bool(adm2 and adm2 == adm_ref2)
    verrou2 = env['ir.config_parameter'].sudo().get_param('maquignon.heures_verrou') or ''
    if ctx.get('recup_del'):
        lg = RL.browse(int(ctx.get('ra_id') or 0))
        if not lg.exists() or lg.x_employee_id.id != emp2.id:
            raise UserError('Ligne introuvable.')
        if not is_adm2 and verrou2 and lg.x_date.strftime('%Y-%m-%d') <= verrou2:
            raise UserError('Cette ligne porte sur une période verrouillée (paie établie). Contactez le bureau.')
        lg.unlink()
        action = {'ok': 1, 'del': 1}
    else:
        try:
            dr = datetime.datetime.strptime(str(ctx.get('ra_date'))[:10], '%Y-%m-%d').date()
        except Exception:
            raise UserError('Date invalide.')
        try:
            hres = float(ctx.get('ra_h'))
        except Exception:
            raise UserError("Nombre d'heures invalide.")
        if hres < 0.25 or hres > 12:
            raise UserError('Heures à mettre en récup : entre 0,25 et 12 h.')
        if dr > datetime.date.today():
            raise UserError('La date ne peut pas être dans le futur.')
        if not is_adm2 and verrou2 and dr.strftime('%Y-%m-%d') <= verrou2:
            raise UserError("Les feuilles d'heures de cette période sont verrouillées (paie établie). Contactez le bureau.")
        lg = RL.create({'x_employee_id': emp2.id, 'x_date': dr.strftime('%Y-%m-%d'),
                        'x_heures': hres, 'x_note': (ctx.get('ra_note') or '')[:200]})
        action = {'ok': 1, 'id': lg.id}
