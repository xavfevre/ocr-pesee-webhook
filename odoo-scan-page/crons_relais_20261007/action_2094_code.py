# Alerte e-mail hebdomadaire : certifications (CACES, habilitations...) expirées ou expirant sous 90 jours
today = datetime.date.today()
lignes = env['hr.employee.skill'].sudo().search([('is_certification', '=', True), ('employee_id.active', '=', True)])
expirees, proches, sans_date = [], [], []
for l in lignes:
    if not l.valid_to:
        sans_date.append(l)
    elif l.valid_to < today:
        expirees.append(l)
    elif (l.valid_to - today).days <= 90:
        proches.append(l)
if env.context.get('test'):
    action = {'test': True, 'expirees': [(l.employee_id.name, l.skill_id.name, str(l.valid_to)) for l in expirees],
              'proches': [(l.employee_id.name, l.skill_id.name, str(l.valid_to)) for l in proches], 'sans_date': len(sans_date)}
elif not expirees and not proches:
    action = {'envoye': False, 'raison': 'rien a signaler'}
else:
    dest = env['ir.config_parameter'].sudo().get_param('maquignon.caces_alerte_email') or ''
    if not dest:
        action = {'envoye': False, 'raison': 'aucun destinataire configure (maquignon.caces_alerte_email)'}
    else:
        def ligne(l, couleur):
            return ('<tr><td style="padding:6px 10px;border-bottom:1px solid #eee;">%s</td>'
                    '<td style="padding:6px 10px;border-bottom:1px solid #eee;">%s</td>'
                    '<td style="padding:6px 10px;border-bottom:1px solid #eee;color:%s;font-weight:700;">%s</td></tr>'
                    % (l.employee_id.name, l.skill_id.name, couleur, l.valid_to.strftime('%d/%m/%Y')))
        entete = ('<tr><th style="text-align:left;padding:6px 10px;">Salarié</th><th style="text-align:left;padding:6px 10px;">Certification</th>'
                  '<th style="text-align:left;padding:6px 10px;">Fin de validité</th></tr>')
        corps = '<div style="font-family:Arial,sans-serif;font-size:13px;color:#0f172a;"><h3>🎓 CACES &amp; habilitations à surveiller</h3>'
        if expirees:
            corps += '<p><b style="color:#991b1b;">%d certification(s) expirée(s) :</b></p><table style="border-collapse:collapse;width:100%%;margin-bottom:14px;">' % len(expirees) + entete
            for l in sorted(expirees, key=lambda r: r.valid_to):
                corps += ligne(l, '#991b1b')
            corps += '</table>'
        if proches:
            corps += '<p><b style="color:#92400e;">%d certification(s) expirant sous 3 mois :</b></p><table style="border-collapse:collapse;width:100%%;margin-bottom:14px;">' % len(proches) + entete
            for l in sorted(proches, key=lambda r: r.valid_to):
                corps += ligne(l, '#92400e')
            corps += '</table>'
        if sans_date:
            corps += '<p style="color:#64748b;">%d certification(s) sans date de fin de validité renseignée.</p>' % len(sans_date)
        corps += ('<p style="margin-top:16px;"><a href="https://maquignon.odoo.com/odoo/action-hr_skills.hr_employee_skill_report_action" '
                  'style="background:#0f172a;color:#fff;padding:9px 16px;border-radius:8px;text-decoration:none;font-weight:700;">Ouvrir l\'analyse des compétences</a></p></div>')
        env['mail.mail'].sudo().create({
            'subject': '🎓 CACES / habilitations : %d expirée(s), %d sous 3 mois' % (len(expirees), len(proches)),
            'email_to': dest, 'body_html': corps}).send()
        action = {'envoye': True, 'expirees': len(expirees), 'proches': len(proches), 'dest': dest}
