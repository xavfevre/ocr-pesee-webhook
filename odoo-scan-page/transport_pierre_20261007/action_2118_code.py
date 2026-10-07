# Devis pierre : une demande de prix par transporteur à consulter, envoyée par mail, puis liste des demandes.
PRODUIT = 8586
TPL = 27
for so in records:
    if so.x_mode_transport != 'exterieur':
        raise UserError("Mettez d'abord « Mode de transport » sur « Transporteur extérieur ».")
    if not so.x_transporteurs_ids:
        raise UserError("Cochez au moins un transporteur à consulter.")
    lignes = so.order_line.filtered(lambda l: not l.display_type and l.product_id and l.product_id.type != 'service')
    poids = sum((l.x_studio_poids or 0.0) for l in lignes)
    vol = sum((l.x_studio_vol or 0.0) for l in lignes)
    palettes = sorted({(l.x_studio_palettes or '').strip() for l in lignes if (l.x_studio_palettes or '').strip()})
    adr = so.partner_shipping_id or so.partner_id
    adresse = ', '.join([t for t in [adr.name, adr.street, adr.street2, ' '.join([t2 for t2 in [adr.zip, adr.city] if t2])] if t])
    date = so.x_studio_date_de_livraison_souhait or so.commitment_date
    desc = ("Transport de pierres - commande %s (%s)\n"
            "Enlèvement : Carrières Maquignon, 51 rue du Prieuré, 86230 Usseau\n"
            "Livraison : %s\n"
            "Palettes : %s\n"
            "Poids total estimé : %.0f kg - volume : %.2f m³\n"
            "Date de livraison souhaitée : %s\n"
            "Merci de nous indiquer votre tarif HT et votre délai.") % (
            so.name, so.partner_id.name, adresse,
            ('%d (%s)' % (len(palettes), ', '.join(palettes))) if palettes else ('environ %d (sur la base de 1 500 kg par palette)' % max(1, -(-int(poids) // 1500))),
            poids, vol, date.strftime('%d/%m/%Y') if date else 'à convenir')
    PO = env['purchase.order'].sudo()
    envoyes, crees = [], PO
    for t in so.x_transporteurs_ids:
        deja = PO.search([('origin', '=', so.name), ('partner_id', '=', t.id), ('state', 'in', ['draft', 'sent'])], limit=1)
        if deja:
            continue
        po = PO.create({'partner_id': t.id, 'origin': so.name, 'company_id': so.company_id.id,
                        'order_line': [(0, 0, {'product_id': PRODUIT, 'name': desc, 'product_qty': 1.0, 'price_unit': 0.0})]})
        crees |= po
        if t.email:
            # copie à Céline (paramètre maquignon.transport_tarif_cc) et à la personne qui envoie
            cc = [a.strip() for a in (env['ir.config_parameter'].sudo().get_param('maquignon.transport_tarif_cc', 'celine@maquignon.com') or '').split(',') if a.strip()]
            if env.user.email and env.user.email not in cc:
                cc.append(env.user.email)
            env['mail.template'].sudo().browse(TPL).send_mail(po.id, force_send=True, email_values={'email_cc': ', '.join(cc)})
            po.write({'state': 'sent'})
            envoyes.append(t.name)
    if crees:
        so.message_post(body="Demandes de tarif transport créées : %s%s" % (
            ', '.join(crees.mapped('partner_id.name')),
            (' (envoyées par mail à : %s, copie à %s)' % (', '.join(envoyes), ', '.join(cc))) if envoyes else " (aucun mail : pas d'adresse e-mail sur la fiche transporteur)"))
    action = {'type': 'ir.actions.act_window', 'res_model': 'purchase.order', 'name': 'Tarifs transport %s' % so.name,
              'view_mode': 'list,form', 'domain': [('origin', '=', so.name)], 'context': {'create': False}}
