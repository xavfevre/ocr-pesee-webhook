# Action serveur Odoo 1671 — « Export journal Caisse pour Sage »
# Modèle : Journal — ARCHIVE avant suppression (02/09/2026)
# Remplacée par l'interface web /export-compta (Render).

if not record:
    raise UserError("Aucun enregistrement sélectionné")

# Utiliser le journal sélectionné (CLO, CAIS ou autre)
cais_journal = record

# Domaine sur les lignes d'écriture (account.move.line)
domain = [
    ('journal_id', '=', cais_journal.id),
    ('parent_state', '=', 'posted'),
]    
try:
    if record.x_studio_date_de_debut:
        domain.append(('date', '>=', record.x_studio_date_de_debut))
except:
    pass

try:
    if record.x_studio_date_de_fin:
        domain.append(('date', '<=', record.x_studio_date_de_fin))
except:
    pass

move_lines = env['account.move.line'].search(domain, order='date asc, move_id asc, id asc')

if not move_lines:
    date_info = ""
    try:
        if record.x_studio_date_de_debut:
            date_info += " à partir du %s" % record.x_studio_date_de_debut
    except:
        pass
    try:
        if record.x_studio_date_de_fin:
            date_info += " jusqu'au %s" % record.x_studio_date_de_fin
    except:
        pass
    raise UserError("Aucun ticket comptoir trouvé pour le journal Cloture CAISSE%s" % date_info)

base_url = env['ir.config_parameter'].sudo().get_param('web.base.url')
content_lines = []
content_lines.append("Numéro de pièce;Numéro facture;Code journal;Date facture;Code client;Référence client;Nom client;Code compte;Libellé compte;Date échéance;Débit;Crédit;URL Facture;Plan;Analytique;Type écriture")

for line in move_lines:
    entry = line.move_id
    journal_code = cais_journal.code or ''
    invoice_number = entry.name or ''
    piece_number = ''.join(filter(str.isdigit, invoice_number))[-7:] if invoice_number else ''
    invoice_date = line.date.strftime('%d%m%y') if line.date else ''
    due_date = entry.invoice_date_due.strftime('%d%m%y') if entry.invoice_date_due else ''
    account_code = line.account_id.code or ''
    debit = line.debit or 0
    credit = line.credit or 0

    # Analytique
    analytic_name = ''
    try:
        if line.analytic_distribution:
            analytic_ids = list(line.analytic_distribution.keys())
            if analytic_ids:
                analytic_accounts = env['account.analytic.account'].browse([int(a) for a in analytic_ids])
                analytic_name = ' | '.join(analytic_accounts.mapped('name'))
    except:
        pass

    # Partenaire et code client uniquement sur les comptes 411
    # Pas d'URL de facture pour les tickets comptoir (ventes anonymes)
    partner = line.partner_id

    invoice_url = ''
    if account_code.startswith('411'):
        partner_code = partner.ref or ''
        partner_name = (partner.name or '').replace(';', ',')
    else:
        partner_code = ''
        partner_name = ''

    # Libellé compte : si vide, chercher le nom du partenaire (ligne, écriture, ou lignes sœurs)
    raw_label = (line.name or '').replace(';', ',')
    if not raw_label:
        label_partner = partner or entry.partner_id
        if not label_partner:
            for sib in entry.line_ids:
                if sib.partner_id:
                    label_partner = sib.partner_id
                    break
        if label_partner:
            raw_label = (label_partner.name or '').replace(';', ',')
    account_label = raw_label

    # Ligne générale
    content_lines.append(
        "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%.2f;%.2f;%s;1;%s;G" % (
            piece_number,
            invoice_number,
            journal_code,
            invoice_date,
            partner_code,
            invoice_number,
            partner_name,
            account_code,
            account_label,
            due_date,
            debit,
            credit,
            invoice_url,
            analytic_name
        )
    )
    # Ligne analytique uniquement pour les comptes de vente (7xxx) avec analytique
    if analytic_name and account_code.startswith('7'):
        content_lines.append(
            "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%.2f;%.2f;%s;1;%s;A" % (
                piece_number,
                invoice_number,
                journal_code,
                invoice_date,
                partner_code,
                invoice_number,
                partner_name,
                account_code,
                account_label,
                due_date,
                debit,
                credit,
                invoice_url,
                analytic_name
            )
        )

file_content = '\n'.join(content_lines)
encoded_content = b64encode(file_content.encode('cp1252', errors='replace')).decode('ascii')

filename_parts = ["export_tickets_comptoir"]
try:
    if record.company_id:
        company_name = record.company_id.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        filename_parts.append(company_name)
except:
    pass
try:
    if record.x_studio_date_de_debut:
        filename_parts.append("du_%s" % str(record.x_studio_date_de_debut).replace('-', ''))
except:
    pass
try:
    if record.x_studio_date_de_fin:
        filename_parts.append("au_%s" % str(record.x_studio_date_de_fin).replace('-', ''))
except:
    pass

filename = "_".join(filename_parts) + ".txt"

attachment = env['ir.attachment'].create({
    'name': filename,
    'type': 'binary',
    'datas': encoded_content,
    'mimetype': 'text/plain',
    'res_model': 'account.journal',
    'res_id': record.id,
    'public': False,
})

action = {
    'type': 'ir.actions.act_url',
    'url': '/web/content/%s?download=true' % attachment.id,
    'target': 'new',
}