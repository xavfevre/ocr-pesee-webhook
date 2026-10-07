# Ligne « Transport de pierres » en fin de devis selon le mode de transport (Xavier, 07/10/2026).
VARIANTES = [5897, 5898, 5899, 5900]
DEFAUT = 5899
for so in records:
    if so.state not in ('draft', 'sent', 'sale'):
        continue
    existantes = so.order_line.filtered(lambda l: not l.display_type and l.product_id.id in VARIANTES)
    if so.x_mode_transport in ('camions', 'exterieur') and not existantes:
        # juste après la dernière ligne produit ; l'éco-contribution et les notes de fin (prix départ, acompte) sont décalées après
        produits = so.order_line.filtered(lambda l: not l.display_type and 'Eco-contribution' not in (l.name or ''))
        seq = max(produits.mapped('sequence') or [10]) + 1
        for l in so.order_line.filtered(lambda l: l.sequence >= seq):
            l.write({'sequence': l.sequence + 1})
        marge = 1.0 + float(env['ir.config_parameter'].sudo().get_param('maquignon.transport_marge_pct', '40') or 0) / 100.0
        prix = round(so.x_transport_achat * marge, 2) if (so.x_mode_transport == 'exterieur' and so.x_transport_achat) else 0.0
        nom = 'Transport de pierres (Forfait Palettes)' + ((' - ' + so.x_transporteur_id.name) if (so.x_mode_transport == 'exterieur' and so.x_transporteur_id) else '')
        so.write({'order_line': [(0, 0, {'product_id': DEFAUT, 'name': nom, 'product_uom_qty': 1.0, 'price_unit': prix, 'sequence': seq})]})
        so.message_post(body="Ligne « Transport de pierres » ajoutée en fin de devis (%s) : prix de vente à ajuster par Céline%s." % (
            'nos camions' if so.x_mode_transport == 'camions' else 'transporteur extérieur',
            (' - prix d achat + %.0f %% = %.2f EUR HT' % ((marge - 1) * 100, prix)) if prix else ''))
    elif so.x_mode_transport == 'client' and existantes and all(l.price_unit in (0.0, 1.0) for l in existantes):
        existantes.unlink()
        so.message_post(body="Enlèvement par le client : ligne « Transport de pierres » vide retirée du devis.")
