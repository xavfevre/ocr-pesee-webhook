mailtemplate = env.ref('__custom__.sale.mail_template_demande_transport')
for record in records:
    # Info transport
    info_parts = []
    if record.x_studio_transport_urgence:
        info_parts.append(f"Urgence: {record.x_studio_transport_urgence}")
    if record.x_studio_transport_adresse:
        info_parts.append(f"Adresse: {record.x_studio_transport_adresse}")
    if record.x_studio_transport_commentaire:
        info_parts.append(f"Commentaires: {record.x_studio_transport_commentaire}")

    info_transport = chr(10).join(info_parts) if info_parts else "Informations standard"

    # Construire la liste des produits sans prix
    produits_liste = []
    for line in record.order_line:
        if line.name:
            produits_liste.append(f"• {line.name} - Qté: {line.product_uom_qty}")

    produits_text = chr(10).join(produits_liste) if produits_liste else "Aucun produit trouvé"

    # Récupérer les informations du client via search_read (accès dict, pas d'AttributeError)
    client = record.partner_id
    client_nom = client.name or "Non renseigné"
    _cd = env['res.partner'].sudo().search_read([('id', '=', client.id)], ['phone', 'street', 'street2', 'zip', 'city', 'country_id', 'email'], limit=1) if client.id else []
    _c = _cd[0] if _cd else {}
    client_telephone = _c.get('phone') or "Non renseigné"
    client_email = _c.get('email') or "Non renseigné"

    # Construire l'adresse complète
    adresse_parts = []
    if _c.get('street'):
        adresse_parts.append(_c['street'])
    if _c.get('street2'):
        adresse_parts.append(_c['street2'])
    if _c.get('zip') or _c.get('city'):
        ville_info = ((_c.get('zip') or '') + ' ' + (_c.get('city') or '')).strip()
        if ville_info:
            adresse_parts.append(ville_info)
    if _c.get('country_id'):
        adresse_parts.append(_c['country_id'][1] if isinstance(_c['country_id'], (list, tuple)) else str(_c['country_id']))

    client_adresse = chr(10).join(adresse_parts) if adresse_parts else "Non renseignée"

    # Récupérer la société émettrice
    company = record.company_id
    company_nom = company.name or "Non renseigné"

    # Nom de la tâche = société émettrice + nom du client
    task_name = company_nom + ' - ' + client_nom

    custom_body = '<html><body>'
    custom_body += '<h3>Demande de transport</h3>'
    custom_body += f'<p><strong>Commande :</strong> {record.name}</p>'
    custom_body += '<div style="margin: 20px 0; background-color: #e8f4f8; padding: 15px; border: 1px solid #b3d9e6;">'
    custom_body += '<h4 style="color: #0056b3; margin-top: 0;">Informations Client :</h4>'
    custom_body += f'<p><strong>Nom :</strong> {client_nom}</p>'
    custom_body += f'<p><strong>Adresse :</strong><br/>{client_adresse.replace(chr(10), "<br/>")}</p>'
    custom_body += f'<p><strong>Téléphone :</strong> {client_telephone}</p>'
    custom_body += f'<p><strong>Email :</strong> {client_email}</p>'
    custom_body += '</div>'
    custom_body += '<div style="margin: 20px 0; background-color: #f0f8ff; padding: 15px; border: 1px solid #ccc;">'
    custom_body += '<h4>Produits à transporter :</h4>'
    custom_body += f'<p style="white-space: pre-wrap; font-family: monospace;">{produits_text}</p>'
    custom_body += '</div>'
    custom_body += '<div style="background-color: #f8f9fa; padding: 15px; border: 2px solid #007bff; margin: 20px 0;">'
    custom_body += '<h4 style="color: #007bff; margin-top: 0;">Informations pour le transport :</h4>'
    custom_body += f'<p style="white-space: pre-wrap; font-size: 14px;">{info_transport}</p>'
    custom_body += '</div>'
    custom_body += '<p>Cordialement</p></body></html>'

    # Anti-doublon : une demande ouverte existe deja pour cette commande ?
    projet_dt = env['project.project'].sudo().search([('name', '=', 'Demande de transport')], limit=1)
    deja = env['project.task'].sudo().search([
        ('project_id', '=', projet_dt.id),
        ('state', 'not in', ['1_done', '1_canceled']),
        ('description', 'ilike', 'Commande :</strong> ' + record.name + '</p>'),
    ], limit=1) if projet_dt else env['project.task']
    if deja:
        deja.write({'description': custom_body})
        record.message_post(body='Demande de transport deja ouverte pour ' + record.name + ' : tache "' + deja.name + '" mise a jour - aucun doublon cree, e-mail non renvoye.')
        continue

    mailtemplate.send_mail(record.id, force_send=True, email_values={
        'email_to': 'transport@maquignon.com',
        'subject': task_name,
        'body_html': custom_body
    })

    # Calculer la date d'envoi
    date_envoi = datetime.date.today().strftime('%d/%m/%Y')

    # Remplir le champ Demande envoyée
    record.write({'x_studio_demande_envoye': 'Oui le ' + date_envoi})

    # Trouver le projet Demande de transport (sans filtre société)
    project = env['project.project'].sudo().search([('name', '=', 'Demande de transport')], limit=1)
    if project:
        # Chercher le partenaire de la société émettrice dans la société du projet
        partner_id = False
        preferred = env['res.partner'].sudo().search([('name', '=', company_nom + ' (Client+Fr Maquignon)'), ('company_id', '=', project.company_id.id)], limit=1)
        if preferred:
            partner_id = preferred.id
        partner_in_project_company = env['res.partner'].sudo().search([
            ('name', 'ilike', company_nom),
            ('company_id', '=', project.company_id.id)
        ], limit=1)
        if not partner_id and partner_in_project_company:
            partner_id = partner_in_project_company.id
        elif not partner_id:
            partner_in_any = env['res.partner'].sudo().search([
                ('name', 'ilike', company_nom)
            ], limit=1)
            if partner_in_any:
                partner_id = partner_in_any.id

        task_vals = {
            'name': task_name,
            'description': custom_body,
            'project_id': project.id,
        }
        if partner_id:
            task_vals['partner_id'] = partner_id

        env['project.task'].sudo().create(task_vals)

    # Poster un message dans le chatter
    record.message_post(body=f"Demande de transport envoyée à transport@maquignon.com - Tâche créée : {task_name}")
