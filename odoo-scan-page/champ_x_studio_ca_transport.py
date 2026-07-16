# Champ calculé stocké Odoo x_studio_ca_transport (id 53733) — modèle project.task
# float, store=True, depends: sale_order_id.amount_untaxed
# CA HT de la commande liée au bon de transport (1 commande = 1 bon, vérifié sur 2026 : 1603/1603).
# Alimente le pivot du dashboard « Transport — Rentabilité camions » (spreadsheet.dashboard 32).
for record in self:
    record['x_studio_ca_transport'] = record.sale_order_id.amount_untaxed if record.sale_order_id else 0.0
