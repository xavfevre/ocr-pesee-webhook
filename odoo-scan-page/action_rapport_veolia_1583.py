# Rapport de service VEOLIA envoyé à la clôture de la tâche.
# (La copie automatique en « Nouvelle demande » a été retirée le 26/08/2026 :
#  elle créait des demandes non voulues — le planning crée déjà les tâches.)
for record in records:
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
