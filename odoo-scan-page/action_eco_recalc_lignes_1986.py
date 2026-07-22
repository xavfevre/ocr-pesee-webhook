
orders = env['sale.order'].browse(list(set(records.mapped('order_id').ids)))
TARIF_REP = 4.16  # EUR/m3
rep_product = env['product.product'].search([('name', '=', 'ECO CONTRIBUTION')], limit=1)
for order in orders:
    if not rep_product: continue
    rep_tax = env['account.tax'].search(
        [('name', '=', 'REP Tuffeau'), ('company_id', '=', order.company_id.id)], limit=1)
    if not rep_tax: continue
    volume_total = 0.0
    max_seq = 0
    for line in order.order_line:
        if not line.product_id: continue
        if line.product_id.id == rep_product.id: continue
        if line.sequence > max_seq:
            max_seq = line.sequence
        if rep_tax.id in line.tax_ids.ids:
            volume_total += (line.x_studio_vol or 0.0)
    rep_sequence = max(max_seq + 1, 9999)
    montant_rep = round(volume_total * TARIF_REP, 2)
    existing_rep = order.order_line.filtered(lambda l: l.product_id.id == rep_product.id)
    if montant_rep <= 0:
        if existing_rep: existing_rep.unlink()
        continue
    libelle = 'Eco-contribution REP Tuffeau (%.3f m3)' % volume_total
    rep_taxes = rep_product.taxes_id.filtered(lambda t: t.company_id.id == order.company_id.id)
    if existing_rep:
        if len(existing_rep) > 1: existing_rep[1:].unlink()
        if (abs(existing_rep[0].price_unit - montant_rep) < 0.01
                and existing_rep[0].name == libelle
                and existing_rep[0].sequence >= max_seq): continue
        existing_rep[0].write({
            'price_unit': montant_rep, 'product_uom_qty': 1.0,
            'name': libelle, 'sequence': rep_sequence})
    else:
        env['sale.order.line'].create({
            'order_id': order.id, 'product_id': rep_product.id,
            'product_uom_qty': 1.0, 'price_unit': montant_rep,
            'name': libelle, 'sequence': rep_sequence,
            'tax_ids': [Command.set(rep_taxes.ids)]})
