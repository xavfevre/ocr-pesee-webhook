# Action serveur 2078 — bouton « ⚡ SEDE » de /planning-transport-mois

# SEDE : pour chaque transport VEOLIA AGRICULTURE du mois sans BC, reproduit la
# procédure manuelle d'Isabelle : BC confirmé avec l'article « Location de
# matériel Transport (Semi Fond-mouvant - par jours) » en quantité 1 (location
# à la journée — PAS d'écrasement par le tonnage) + section « Bon de pesée »
# reprise de la feuille de travail (même logique que le bouton 1615).
ctx = env.context
du = (ctx.get('sede_du') or '').strip()
au = (ctx.get('sede_au') or '').strip()
if not (du and au):
    raise UserError('Période manquante (sede_du / sede_au).')
PARTNER_ID = 16001   # VEOLIA AGRICULTURE FRANCE
PRODUIT_ID = 5828    # Location de matériel Transport (Semi Fond-mouvant - par jours)
tasks = env['project.task'].sudo().search([
    ('partner_id', 'child_of', PARTNER_ID),
    ('project_id.name', '=', 'Demande de transport'),
    ('planned_date_begin', '>=', du + ' 00:00:00'),
    ('planned_date_begin', '<=', au + ' 23:59:59'),
], order='planned_date_begin')
faits = []
deja = 0
annulees = 0
sans_bon = []
for t in tasks:
    st = (t.stage_id.name or '').lower()
    if 'annul' in st or 'cancel' in st:
        annulees += 1
        continue
    if t.sale_order_id or t.sale_line_id:
        deja += 1
        continue
    if t.planned_date_begin and t.planned_date_begin > datetime.datetime.now():
        # transport pas encore realise : pas de bon de pesee, on attend
        futurs += 1
        continue
    so = env['sale.order'].sudo().create({
        'partner_id': t.partner_id.id,
        'company_id': t.company_id.id,
        'origin': t.name,
        # date du BC = date du transport : les validites de tarifs (listes de
        # prix datees) s'appliquent au jour de la prestation, pas au jour du clic
        'date_order': t.planned_date_begin,
    })
    env['sale.order.line'].sudo().create({
        'order_id': so.id,
        'product_id': PRODUIT_ID,
        'product_uom_qty': 1,
        'task_id': t.id,
    })
    so.action_confirm()
    if t.planned_date_begin:
        # action_confirm remet la date du jour : on recale sur la date du
        # transport pour que les tarifs dates s'appliquent au bon jour
        so.write({'date_order': t.planned_date_begin})
    t.write({'sale_order_id': so.id})
    ws = env['x_project_task_worksheet_template_1'].sudo().search(
        [('x_project_task_id', '=', t.id)], limit=1, order='create_date desc')
    if ws and (ws.x_studio_numero_bon or ws.x_studio_client_pesee or ws.x_studio_vehicule):
        poids_str = ('%s T' % round(ws.x_studio_poids_net / 1000, 3)) if ws.x_studio_poids_net else 'Poids N/A'
        section_name = 'Bon n°%s | %s | %s | %s | %s' % (
            ws.x_studio_numero_bon or '', ws.x_studio_date_bon or '',
            ws.x_studio_produit_pesee or '', ws.x_studio_vehicule or '', poids_str)
        first_line = env['sale.order.line'].sudo().search(
            [('order_id', '=', so.id), ('display_type', '=', False)], order='sequence asc', limit=1)
        env['sale.order.line'].sudo().create({
            'order_id': so.id, 'display_type': 'line_section', 'name': section_name,
            'sequence': (first_line.sequence - 1) if first_line else 10,
        })
        so.message_post(body='<b>Données bon de pesée</b><br/>N° Bon : %s<br/>Date : %s<br/>Véhicule : %s<br/>Produit : %s<br/>Poids net : %s kg<br/><i>BC généré par le bouton SEDE (planning transport)</i>' % (
            ws.x_studio_numero_bon or '-', ws.x_studio_date_bon or '-',
            ws.x_studio_vehicule or '-', ws.x_studio_produit_pesee or '-', ws.x_studio_poids_net or 0))
    else:
        sans_bon.append('%s (%s)' % (t.name or t.id, so.name))
    faits.append(so.name)
action = {'ok': 1, 'faits': len(faits), 'bons': faits[:100], 'deja': deja,
          'annulees': annulees, 'sans_bon': sans_bon[:40], 'futurs': futurs}

