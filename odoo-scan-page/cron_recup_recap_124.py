# Cron Odoo 124 — « Heures : récap hebdo des récups au bureau » (lundis 05:00 UTC)
# Destinataire : ir.config_parameter maquignon.recup_alerte_email

# Récap hebdo au bureau : heures mises en récup par les salariés (7 derniers jours)
today = datetime.date.today()
depuis = today - datetime.timedelta(days=7)
lignes = env['x_recup_ligne'].sudo().search([('create_date', '>=', depuis.strftime('%Y-%m-%d 00:00:00'))], order='x_employee_id, x_date')
if not lignes:
    action = {'envoye': False, 'raison': 'aucune heure mise en recup cette semaine'}
else:
    dest = env['ir.config_parameter'].sudo().get_param('maquignon.recup_alerte_email') or ''
    if not dest:
        action = {'envoye': False, 'raison': 'aucun destinataire configure'}
    else:
        total = sum(lignes.mapped('x_heures'))
        emps = set(lignes.mapped('x_employee_id').ids)
        corps = '<div style="font-family:Arial,sans-serif;font-size:13px;color:#0f172a;">'
        corps += '<h3>🔄 Heures mises en récup cette semaine</h3>'
        corps += '<table style="border-collapse:collapse;width:100%;">'
        corps += '<tr><th style="text-align:left;padding:6px 10px;">Salarié</th><th style="text-align:left;padding:6px 10px;">Date</th><th style="text-align:left;padding:6px 10px;">Heures</th><th style="text-align:left;padding:6px 10px;">Note</th></tr>'
        for l in lignes:
            corps += ('<tr><td style="padding:6px 10px;border-bottom:1px solid #eee;">%s</td>'
                      '<td style="padding:6px 10px;border-bottom:1px solid #eee;">%s</td>'
                      '<td style="padding:6px 10px;border-bottom:1px solid #eee;font-weight:700;color:#0369a1;">+%g h</td>'
                      '<td style="padding:6px 10px;border-bottom:1px solid #eee;color:#64748b;">%s</td></tr>') % (
                l.x_employee_id.name, l.x_date.strftime('%d/%m/%Y'), l.x_heures, l.x_note or '')
        corps += '</table>'
        corps += '<p style="margin-top:12px;color:#64748b;">Ces heures s\'ajoutent au solde de récup de chaque salarié (visible sur sa page et sur /heures-admin). En cas d\'erreur, le salarié peut supprimer sa ligne, ou le bureau peut ajuster le solde arrêté sur la page ⏰ Horaires par défaut.</p>'
        corps += '</div>'
        env['mail.mail'].sudo().create({
            'subject': '🔄 Récup : %g h mises en récup par %d salarié(s) cette semaine' % (total, len(emps)),
            'email_to': dest,
            'body_html': corps,
        }).send()
        action = {'envoye': True, 'total': total, 'salaries': len(emps), 'dest': dest}

