# Rapport de service VEOLIA à la clôture + recréation des demandes Mâchefers.
# Règle (02/09/2026, demande Xavier) : il doit toujours rester TROIS tâches
# VEOLIA - LES MACHEFERS en « Nouvelle demande » (3 rotations) — on complète.
for record in records:
    nouvelle_demande = env['project.task.type'].search([('name', '=', 'Nouvelle demande'), ('project_ids', 'in', record.project_id.id)], limit=1)
    en_attente = env['project.task'].search_count([
        ('project_id', '=', record.project_id.id),
        ('name', 'ilike', 'VEOLIA - LES MACHEFERS'),
        ('state', 'not in', ['1_done', '1_canceled']),
        ('stage_id', '=', nouvelle_demande.id if nouvelle_demande else 0),
        ('id', '!=', record.id),
    ])
    for _i in range(max(0, 3 - en_attente)):
        new_task = record.copy({'stage_id': nouvelle_demande.id if nouvelle_demande else False, 'state': '01_in_progress', 'date_deadline': False, 'planned_date_begin': False, 'x_studio_chauffeur': False, 'x_studio_operateurs': [(5, 0, 0)]})
        new_task.write({'name': record.name})
    destinataires = 'exploitation.86.sou@veolia.com, vanessa.leon@veolia.com, franck@maquignon.com'
    try:
        report = env['ir.actions.report'].search([('report_name', '=', 'industry_fsm.worksheet_custom')], limit=1)
        if not report:
            raise UserError('Rapport industry_fsm.worksheet_custom introuvable')
        pdf_content, _ = report._render_qweb_pdf(report.report_name, record.ids)
        attachment = env['ir.attachment'].create({'name': 'Rapport_service_' + record.name + '.pdf', 'type': 'binary', 'raw': pdf_content, 'res_model': 'project.task', 'res_id': record.id, 'mimetype': 'application/pdf'})
        body = '<p>Bonjour,</p><p>Veuillez trouver ci-joint le rapport de service pour :</p><ul><li><b>Tâche :</b> ' + record.name + '</li><li><b>Client :</b> ' + (record.partner_id.name or '') + '</li></ul><p>Cordialement,<br/>Carrières Maquignon</p>'
        env['mail.mail'].create({'subject': 'Rapport de service - ' + record.name, 'body_html': body, 'email_to': destinataires, 'email_from': env.company.email or 'noreply@maquignon.fr', 'attachment_ids': [Command.set([attachment.id])]}).send()
        record.message_post(body='📧 Rapport de service envoyé par email à : ' + destinataires, subject='Rapport de service envoyé', attachment_ids=[attachment.id], message_type='comment', subtype_xmlid='mail.mt_note')
    except Exception as e:
        record.message_post(body='⚠️ Échec envoi du rapport VEOLIA (à renvoyer manuellement) : ' + str(e), subject='Rapport de service - échec', subtype_xmlid='mail.mt_note')
