# Alerte email hebdomadaire : controles vehicules en retard ou sous 30 jours
today = datetime.date.today()
rows = env['x_controle_vehicule'].sudo().search([])
retard = []
proche = []
cv = []
for r in rows:
    if r.x_cv_limite:
        cv.append((r, r.x_cv_limite))
    if not r.x_derniere_date:
        continue
    ech = r.x_derniere_date + datetime.timedelta(days=30 * r.x_type_id.x_periodicite_mois)
    if ech < today:
        retard.append((r, ech))
    elif (ech - today).days <= 30:
        proche.append((r, ech))

if not retard and not proche and not cv:
    action = {'envoye': False, 'raison': 'rien a signaler'}
else:
    dest = env['ir.config_parameter'].sudo().get_param('maquignon.parc_alerte_email') or ''
    if not dest:
        action = {'envoye': False, 'raison': 'aucun destinataire configure'}
    else:
        def ligne(r, ech, couleur):
            return (
                '<tr><td style="padding:6px 10px;border-bottom:1px solid #eee;">%s</td>'
                '<td style="padding:6px 10px;border-bottom:1px solid #eee;">%s</td>'
                '<td style="padding:6px 10px;border-bottom:1px solid #eee;color:%s;font-weight:700;">%s</td></tr>'
            ) % (r.x_vehicule_id.name, r.x_type_id.x_name, couleur, ech.strftime('%d/%m/%Y'))
        corps = '<div style="font-family:Arial,sans-serif;font-size:13px;color:#0f172a;">'
        corps += '<h3>🚛 Parc automobile — contrôles à surveiller</h3>'
        if retard:
            corps += '<p><b style="color:#991b1b;">%d contrôle(s) en retard :</b></p>' % len(retard)
            corps += '<table style="border-collapse:collapse;width:100%%;margin-bottom:14px;">'
            corps += '<tr><th style="text-align:left;padding:6px 10px;">Véhicule</th><th style="text-align:left;padding:6px 10px;">Contrôle</th><th style="text-align:left;padding:6px 10px;">Échéance dépassée le</th></tr>'
            for r, ech in sorted(retard, key=lambda x: x[1]):
                corps += ligne(r, ech, '#991b1b')
            corps += '</table>'
        if proche:
            corps += '<p><b style="color:#92400e;">%d contrôle(s) à échéance sous 30 jours :</b></p>' % len(proche)
            corps += '<table style="border-collapse:collapse;width:100%%;">'
            corps += '<tr><th style="text-align:left;padding:6px 10px;">Véhicule</th><th style="text-align:left;padding:6px 10px;">Contrôle</th><th style="text-align:left;padding:6px 10px;">Échéance</th></tr>'
            for r, ech in sorted(proche, key=lambda x: x[1]):
                corps += ligne(r, ech, '#92400e')
            corps += '</table>'
        if cv:
            corps += '<p><b style="color:#831843;">%d contre-visite(s) a passer :</b></p>' % len(cv)
            corps += '<table style="border-collapse:collapse;width:100%%;margin-bottom:14px;">'
            corps += '<tr><th style="text-align:left;padding:6px 10px;">V\xe9hicule</th><th style="text-align:left;padding:6px 10px;">Contr\xf4le</th><th style="text-align:left;padding:6px 10px;">Avant le</th></tr>'
            for r, lim in sorted(cv, key=lambda x: x[1]):
                corps += ligne(r, lim, '#831843')
            corps += '</table>'
        corps += '<p style="margin-top:16px;"><a href="https://maquignon.odoo.com/parc-controles" style="background:#0f172a;color:#fff;padding:9px 16px;border-radius:8px;text-decoration:none;font-weight:700;">Ouvrir le planning des contrôles</a></p>'
        corps += '</div>'
        env['mail.mail'].sudo().create({
            'subject': '🚛 Parc automobile : %d en retard, %d sous 30 j, %d contre-visite(s)' % (len(retard), len(proche), len(cv)),
            'email_to': dest,
            'body_html': corps,
        }).send()
        action = {'envoye': True, 'retard': len(retard), 'proche': len(proche), 'dest': dest}
