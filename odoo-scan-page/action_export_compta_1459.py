# Action serveur Odoo 1459 — « Export journal pour logiciel compta extérieur »
# Modèle : Journal — ARCHIVE avant suppression (02/09/2026)
# Remplacée par l'interface web /export-compta (Render).

if not record:
    raise UserError("Aucun enregistrement sélectionné")
if record.type not in ('sale', 'cash', 'bank'):
        raise UserError("Cette action est réservée aux journaux de vente, caisse ou banque")
domain = [
    ('journal_id', '=', record.id),
    ('state', '=', 'posted')
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

entries = env['account.move'].search(domain)
if not entries:
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
    raise UserError("Aucune écriture trouvée pour ce journal%s" % date_info)

base_url = env['ir.config_parameter'].sudo().get_param('web.base.url')

content_lines = []
content_lines.append("Numéro de pièce;Numéro facture;Code journal;Date facture;Code client;Référence client;Nom client;Code compte;Libellé compte;Date échéance;Débit;Crédit;URL Facture;Plan;Analytique;Type écriture")

for entry in entries:
    journal_code = record.code or ''
    invoice_number = entry.name or ''
    piece_number = ''.join(filter(str.isdigit, invoice_number))[-7:] if invoice_number else ''
    invoice_date = entry.date.strftime('%d%m%y') if entry.date else ''
    due_date = entry.invoice_date_due.strftime('%d%m%y') if entry.invoice_date_due else ''

    # Regroupement par compte
    grouped = {}
    for line in entry.line_ids:
        debit = line.debit or 0
        credit = line.credit or 0
        if debit == 0 and credit == 0:
            continue

        account_code = line.account_id.code or ''
        if not account_code:
            continue

        # Récupérer l'analytique
        analytic_name = ''
        try:
            if line.analytic_distribution:
                analytic_ids = list(line.analytic_distribution.keys())
                if analytic_ids:
                    analytic_accounts = env['account.analytic.account'].browse([int(a) for a in analytic_ids])
                    analytic_name = ' | '.join(analytic_accounts.mapped('name'))
        except:
            pass

        # Clé de regroupement : compte + analytique (pour ne pas mélanger des analytiques différents)
        key = (account_code, analytic_name)

        if key not in grouped:
            partner = line.partner_id
            if account_code.startswith('411'):
                partner_code = partner.ref or ''
                invoice_url = "%s/report/pdf/account.report_invoice/%s" % (base_url, entry.id)
            else:
                partner_code = ''
                invoice_url = ''

            grouped[key] = {
                'partner_code': partner_code,
                'partner_ref': line.ref or '',
                'partner_name': partner.name or '',
                'account_code': account_code,
                'account_label': line.account_id.name or '',
                'invoice_url': invoice_url,
                'analytic_name': analytic_name,
                'debit': 0,
                'credit': 0,
            }

        grouped[key]['debit'] += debit
        grouped[key]['credit'] += credit

    # Générer les lignes depuis le regroupement
    for (account_code, analytic_name), g in grouped.items():
        enriched_label = "%s %s" % (invoice_number, g['partner_name'])

        # Si débit ET crédit sont tous deux non nuls, on dédouble la ligne
        if g['debit'] > 0 and g['credit'] > 0:
            amounts = [(g['debit'], 0), (0, g['credit'])]
        else:
            amounts = [(g['debit'], g['credit'])]

        for debit, credit in amounts:
            # Ligne générale
            content_lines.append(
                "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%.2f;%.2f;%s;1;%s;G" % (
                    piece_number, invoice_number, journal_code, invoice_date,
                    g['partner_code'], g['partner_ref'], g['partner_name'],
                    account_code, enriched_label, due_date,
                    debit, credit, g['invoice_url'], analytic_name
                )
            )

            # Ligne analytique uniquement pour les comptes de vente (7xxx) avec analytique
            if analytic_name and account_code.startswith('7'):
                content_lines.append(
                    "%s;%s;%s;%s;%s;%s;%s;%s;%s;%s;%.2f;%.2f;%s;1;%s;A" % (
                        piece_number, invoice_number, journal_code, invoice_date,
                        g['partner_code'], g['partner_ref'], g['partner_name'],
                        account_code, enriched_label, due_date,
                        debit, credit, g['invoice_url'], analytic_name
                    )
                )

file_content = '\n'.join(content_lines)
encoded_content = b64encode(file_content.encode('cp1252')).decode('ascii')

filename_parts = ["export_journal"]

# Ajout du nom de la société
try:
    if record.company_id:
        company_name = record.company_id.name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        filename_parts.append(company_name)
except:
    pass

filename_parts.append(record.name.replace(' ', '_'))

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