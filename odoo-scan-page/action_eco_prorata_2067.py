# Eco-contribution REP Tuffeau au prorata du volume de CHAQUE facture.
# Se declenche a la creation d'une facture client depuis une commande.
# Garde-fou : la somme des eco facturees sur toutes les factures d'une commande
# ne depasse jamais l'eco totale de la commande (pas de double facturation,
# y compris pour les commandes historiques ou tout etait sur la 1re facture).
TARIF_REP = 4.16  # EUR/m3
for move in records:
    if move.move_type != 'out_invoice':
        continue
    rep_product = env['product.product'].search([('name', '=', 'ECO CONTRIBUTION')], limit=1)
    if not rep_product:
        continue
    rep_tax = env['account.tax'].search([('name', '=', 'REP Tuffeau'), ('company_id', '=', move.company_id.id)], limit=1)
    if not rep_tax:
        continue
    vol = 0.0
    orders = env['sale.order']
    for aml in move.invoice_line_ids:
        if aml.display_type != 'product' or not aml.sale_line_ids:
            continue
        sol = aml.sale_line_ids[0]
        orders |= sol.order_id
        if sol.product_id and sol.product_id.id != rep_product.id and rep_tax.id in sol.tax_ids.ids and sol.x_studio_vol:
            part = (aml.quantity / sol.product_uom_qty) if sol.product_uom_qty else 1.0
            vol += sol.x_studio_vol * part
    if not orders:
        continue
    cible = round(vol * TARIF_REP, 2)
    total_eco = 0.0
    deja = 0.0
    for o in orders:
        for l in o.order_line:
            if l.product_id and l.product_id.id == rep_product.id:
                total_eco += l.price_unit
        for inv in o.invoice_ids:
            if inv.id == move.id or inv.state == 'cancel':
                continue
            sign = -1.0 if inv.move_type == 'out_refund' else 1.0
            for aml in inv.invoice_line_ids:
                if aml.product_id and aml.product_id.id == rep_product.id:
                    deja += sign * aml.price_subtotal
    cible = max(0.0, min(cible, round(total_eco - deja, 2)))
    eco_amls = move.invoice_line_ids.filtered(lambda l: l.product_id and l.product_id.id == rep_product.id)
    libelle = 'ECO CONTRIBUTION\nEco-contribution REP Tuffeau (%.3f m3)' % vol
    if cible <= 0:
        if eco_amls:
            eco_amls.unlink()
        continue
    if eco_amls:
        if len(eco_amls) > 1:
            eco_amls[1:].unlink()
        eco_amls[0].write({'quantity': 1.0, 'price_unit': cible, 'name': libelle})
    else:
        taxes = rep_product.taxes_id.filtered(lambda t: t.company_id.id == move.company_id.id)
        env['account.move.line'].create({
            'move_id': move.id,
            'product_id': rep_product.id,
            'quantity': 1.0,
            'price_unit': cible,
            'name': libelle,
            'sequence': 9999,
            'tax_ids': [(6, 0, taxes.ids)],
        })
