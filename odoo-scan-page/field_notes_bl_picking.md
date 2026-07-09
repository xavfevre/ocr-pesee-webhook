# Champ calculé `x_studio_notes_bl` — stock.picking (id 53729)

Affiche les lignes de note de la commande liée dans la vue BL Odoo
(la liste des opérations ne peut pas contenir les notes, qui sont des
sale.order.line, pas des stock.move).

- ttype: text · store: False · depends: sale_id
- compute:
```
for record in self:
    notes = False
    if record.sale_id:
        parts = [l.name for l in record.sale_id.order_line if l.display_type == "line_note" and l.name]
        notes = (chr(10)).join(parts) or False
    record["x_studio_notes_bl"] = notes
```
Affiché en lecture seule au-dessus de `move_ids` dans la vue 6616
(invisible s'il n'y a pas de note).
