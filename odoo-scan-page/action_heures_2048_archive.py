# Page personnelle : mise a jour des coordonnees du salarie (lien signe)
ctx = env.context
emp_id = ctx.get('co_emp')
if emp_id:
    emp = env['hr.employee'].sudo().browse(int(emp_id))
    tok = (ctx.get('co_token') or '')
    if not (tok and tok == (emp.x_heures_token or '')):
        raise UserError('Lien invalide — demandez votre lien personnel à votre responsable.')
    ALLOWED = {'co_mobile': ('private_phone', 'Portable'),
               'co_email': ('private_email', 'Email perso'),
               'co_rue': ('private_street', 'Adresse'),
               'co_cp': ('private_zip', 'Code postal'),
               'co_ville': ('private_city', 'Ville'),
               'co_urg_nom': ('emergency_contact', 'Contact urgence'),
               'co_urg_tel': ('emergency_phone', 'Tél. urgence')}
    vals = {}
    changes = []
    for k, (f, lbl) in ALLOWED.items():
        if k in ctx:
            new = (ctx.get(k) or '').strip()
            old = emp[f] or ''
            if new != old:
                vals[f] = new or False
                changes.append('%s : « %s » → « %s »' % (lbl, old or '—', new or '—'))
    if vals:
        emp.write(vals)
        emp.message_post(body='📇 Coordonnées mises à jour par le salarié depuis sa page personnelle — ' + ' ; '.join(changes))
    action = {'ok': 1, 'changed': len(vals)}
