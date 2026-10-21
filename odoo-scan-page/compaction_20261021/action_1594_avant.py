notes_parts = []
chatter_sections = []
total_vol = 0.0

for rec in records:
    nom_client = rec.x_studio_nom_du_client or ''
    ref_pierre = rec.x_studio_ref_pierre or ''
    long_val   = float(rec.x_studio_long_m_1 or 0)
    larg_val   = float(rec.x_studio_larg_m_1 or 0)
    epais_val  = float(rec.x_studio_haut_m_1 or 0)
    nbr_val    = int(rec.x_studio_nbr or 0)
    vol_val    = float(rec.x_studio_vol_total or 0)
    total_vol  += vol_val

    notes_parts.append(
        "--- OF : %s ---\n"
        "Produit : %s\n"
        "Client : %s   Ref. Pierre : %s\n"
        "Nbr. : %s   Long. (m) : %.2f   Larg. (m) : %.2f   Haut. (m) : %.2f"
        % (
            rec.name,
            rec.product_id.display_name or '',
            nom_client,
            ref_pierre,
            nbr_val, long_val, larg_val, epais_val,
        )
    )

    chatter_sections.append(
        "<table style='border-collapse:collapse;margin-bottom:12px;width:100%%;font-size:13px;'>"
        "<tr style='background-color:#2d6a6f;color:white;'>"
        "<td colspan='2' style='padding:6px 10px;font-weight:bold;font-size:14px;'>OF : %s</td>"
        "</tr>"
        "<tr style='background-color:#f5f5f5;'>"
        "<td style='padding:4px 10px;font-weight:bold;width:130px;'>Produit</td>"
        "<td style='padding:4px 10px;'>%s</td>"
        "</tr>"
        "<tr>"
        "<td style='padding:4px 10px;font-weight:bold;'>Client</td>"
        "<td style='padding:4px 10px;'>%s</td>"
        "</tr>"
        "<tr style='background-color:#f5f5f5;'>"
        "<td style='padding:4px 10px;font-weight:bold;'>Ref. Pierre</td>"
        "<td style='padding:4px 10px;'>%s</td>"
        "</tr>"
        "<tr>"
        "<td style='padding:4px 10px;font-weight:bold;'>Nbr.</td>"
        "<td style='padding:4px 10px;'>%s</td>"
        "</tr>"
        "<tr style='background-color:#f5f5f5;'>"
        "<td style='padding:4px 10px;font-weight:bold;'>Dimensions</td>"
        "<td style='padding:4px 10px;'>L. <b>%.2f m</b> x l. <b>%.2f m</b> x H. <b>%.2f m</b></td>"
        "</tr>"
        "<tr>"
        "<td style='padding:4px 10px;font-weight:bold;'>Vol. total</td>"
        "<td style='padding:4px 10px;'><b>%.4f m3</b></td>"
        "</tr>"
        "</table>"
        % (rec.name, rec.product_id.display_name or '', nom_client, ref_pierre,
           nbr_val, long_val, larg_val, epais_val, vol_val)
    )

combined_note = "\n\n".join(notes_parts)
first = records[0]

# Extrait le prefixe pierre (ex: "HAIMS" depuis "HAIMS0005-PS")
stone_prefix = ''
for c in (first.product_id.default_code or ''):
    if c in '0123456789':
        break
    stone_prefix += c

# Cherche le produit 2135-TR correspondant a la pierre
default_code_tr = stone_prefix + '2135-TR'
product_tr = env['product.product'].search([
    ('default_code', '=', default_code_tr)
], limit=1)

product_id = product_tr.id if product_tr else first.product_id.id
uom_id = product_tr.uom_id.id if product_tr else first.product_uom_id.id

# Infos visibles sur la tablette opérateur (client, réf. pierre, nb pièces, réf. commande, tâche)
clients = []
refs = []
nbr_total = 0
for rec in records:
    if rec.x_studio_nom_du_client and rec.x_studio_nom_du_client not in clients:
        clients.append(rec.x_studio_nom_du_client)
    if rec.x_studio_ref_pierre and rec.x_studio_ref_pierre not in refs:
        refs.append(rec.x_studio_ref_pierre)
    nbr_total += int(rec.x_studio_nbr or 0)
premier_ref_cde = ''
premiere_tache = False
for rec in records:
    if not premier_ref_cde and rec.x_studio_ref_commande_client:
        premier_ref_cde = rec.x_studio_ref_commande_client
    if not premiere_tache and rec.x_studio_tche_commande_pierre:
        premiere_tache = rec.x_studio_tche_commande_pierre.id
vals_of = {
    'company_id':          first.company_id.id,
    'product_id':          product_id,
    'product_uom_id':      uom_id,
    'product_qty':         total_vol,
    'log_note':            combined_note,
    'x_detail_tranches':   combined_note,
    'x_studio_vol_total':  total_vol,
    'x_studio_nom_du_client': ', '.join(clients)[:120],
    'x_studio_ref_pierre': ', '.join(refs)[:120],
    'x_studio_nbr': nbr_total,
    'x_studio_ref_commande_client': premier_ref_cde,
    'x_note_atelier': 'Tranches pour %d pierre(s) : %s — détail sur la carte' % (len(records), ', '.join(records.mapped('name'))[:80]),
}
if premiere_tache:
    vals_of['x_studio_tche_commande_pierre'] = premiere_tache
new_of = env['mrp.production'].create(vals_of)

raw_html = (
    "<p style='font-size:14px;font-weight:bold;margin-bottom:12px;'>"
    "OF recapitulatif cree depuis %s ordre(s) - Vol. total : %.4f m3 :"
    "</p>%s"
) % (len(records), total_vol, "".join(chatter_sections))

body_markup = env['mail.message'].new({'body': raw_html}).body

new_of.message_post(
    body=body_markup,
    message_type='comment',
    subtype_xmlid='mail.mt_note',
)

action = {
    'type': 'ir.actions.act_window',
    'res_model': 'mrp.production',
    'res_id': new_of.id,
    'view_mode': 'form',
    'target': 'current',
}