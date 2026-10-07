# Demande de prix transport confirmée : transporteur retenu, prix d'achat et ordre de transport sur le devis ;
# les autres demandes de la même commande sont annulées.
PRODUIT = 8586
for po in records:
    if po.state != 'purchase' or PRODUIT not in po.order_line.product_id.ids or not po.origin:
        continue
    so = env['sale.order'].sudo().search([('name', '=', po.origin)], limit=1)
    if not so:
        continue
    so.write({'x_transporteur_id': po.partner_id.id, 'x_transport_achat': po.amount_untaxed, 'x_ordre_transport_id': po.id})
    autres = env['purchase.order'].sudo().search([('origin', '=', so.name), ('id', '!=', po.id), ('state', 'in', ['draft', 'sent']),
                                                  ('order_line.product_id', '=', PRODUIT)])
    if autres:
        autres.button_cancel()
    so.message_post(body="Transporteur retenu : %s - %.2f EUR HT (ordre de transport %s).%s" % (
        po.partner_id.name, po.amount_untaxed, po.name,
        (' Autres demandes annulées : %s.' % ', '.join(autres.mapped('partner_id.name'))) if autres else ''))
