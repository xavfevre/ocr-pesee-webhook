notes, html, total_vol = [], [], 0.0
for rec in records:
    cli, ref, prod = rec.x_studio_nom_du_client or '', rec.x_studio_ref_pierre or '', rec.product_id.display_name or ''
    L, l, h, n, v = float(rec.x_studio_long_m_1 or 0), float(rec.x_studio_larg_m_1 or 0), float(rec.x_studio_haut_m_1 or 0), int(rec.x_studio_nbr or 0), float(rec.x_studio_vol_total or 0)
    total_vol += v
    notes.append("--- OF : %s ---\nProduit : %s\nClient : %s   Ref. Pierre : %s\nNbr. : %s   Long. (m) : %.2f   Larg. (m) : %.2f   Haut. (m) : %.2f" % (rec.name, prod, cli, ref, n, L, l, h))
    rows = [('Produit', prod), ('Client', cli), ('Ref. Pierre', ref), ('Nbr.', n), ('Dimensions', 'L. <b>%.2f m</b> x l. <b>%.2f m</b> x H. <b>%.2f m</b>' % (L, l, h)), ('Vol. total', '<b>%.4f m3</b>' % v)]
    html.append("<table style='border-collapse:collapse;margin-bottom:12px;width:100%%;font-size:13px;'><tr style='background-color:#2d6a6f;color:white;'><td colspan='2' style='padding:6px 10px;font-weight:bold;font-size:14px;'>OF : %s</td></tr>" % rec.name
                + ''.join("<tr%s><td style='padding:4px 10px;font-weight:bold;%s'>%s</td><td style='padding:4px 10px;'>%s</td></tr>" % (" style='background-color:#f5f5f5;'" if i % 2 == 0 else '', 'width:130px;' if i == 0 else '', k, val) for i, (k, val) in enumerate(rows)) + "</table>")
combined_note = "\n\n".join(notes)
first = records[0]
prefix = ''   # préfixe pierre, ex. "HAIMS" depuis "HAIMS0005-PS"
for c in (first.product_id.default_code or ''):
    if c in '0123456789':
        break
    prefix += c
tr = env['product.product'].search([('default_code', '=', prefix + '2135-TR')], limit=1)   # article tranches de la pierre
clients = list(dict.fromkeys(r.x_studio_nom_du_client for r in records if r.x_studio_nom_du_client))
refs = list(dict.fromkeys(r.x_studio_ref_pierre for r in records if r.x_studio_ref_pierre))
vals_of = {'company_id': first.company_id.id, 'product_id': tr.id if tr else first.product_id.id, 'product_uom_id': tr.uom_id.id if tr else first.product_uom_id.id,
           'product_qty': total_vol, 'log_note': combined_note, 'x_detail_tranches': combined_note, 'x_studio_vol_total': total_vol,
           'x_studio_nom_du_client': ', '.join(clients)[:120], 'x_studio_ref_pierre': ', '.join(refs)[:120], 'x_studio_nbr': sum(int(r.x_studio_nbr or 0) for r in records),
           'x_studio_ref_commande_client': ([r.x_studio_ref_commande_client for r in records if r.x_studio_ref_commande_client] or [''])[0],
           'x_note_atelier': 'Tranches pour %d pierre(s) : %s — détail sur la carte' % (len(records), ', '.join(records.mapped('name'))[:80])}
taches = [r.x_studio_tche_commande_pierre.id for r in records if r.x_studio_tche_commande_pierre]
if taches:
    vals_of['x_studio_tche_commande_pierre'] = taches[0]
new_of = env['mrp.production'].create(vals_of)
raw_html = "<p style='font-size:14px;font-weight:bold;margin-bottom:12px;'>OF recapitulatif cree depuis %s ordre(s) - Vol. total : %.4f m3 :</p>%s" % (len(records), total_vol, "".join(html))
new_of.message_post(body=env['mail.message'].new({'body': raw_html}).body, message_type='comment', subtype_xmlid='mail.mt_note')
action = {'type': 'ir.actions.act_window', 'res_model': 'mrp.production', 'res_id': new_of.id, 'view_mode': 'form', 'target': 'current'}
