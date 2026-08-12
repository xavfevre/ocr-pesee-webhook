# Action serveur 2081 — boutons « BC automatiques » de /planning-transport-mois
# (Longué+Lac, Prieuré, Besnault, Machefers, GSM, Châtel, Haims)

# Boutons transport (vue mois) : BC automatiques par recette client.
# Reproduit le geste manuel d'Isabelle : BC confirme + article(s) + section
# « Bon de pesee » composee directement au bon format (au lieu d'etre retouchee).
# Quantites : 'poids' = tonnage du bon de pesee ; 'un' = 1 (forfait/heure).
ctx = env.context
recette = (ctx.get('tb_recette') or '').strip()
du = (ctx.get('tb_du') or '').strip()
au = (ctx.get('tb_au') or '').strip()
if not (recette and du and au):
    raise UserError('Parametres manquants (tb_recette / tb_du / tb_au).')

RECETTES = {
    # partners, section ('sans_produit' | 'standard' | 'produit4' | 'label_avant_produit' | 'label_apres_produit')
    'longue_lac': {'partners': [15797, 15755], 'section': 'sans_produit',
                   'lignes': [(4414, 'poids', None), (5220, 'poids', None)]},
    'prieure':    {'partners': [18133], 'section': 'sans_produit',
                   'lignes': [(4414, 'poids', 'Tuffeau broyé 0/15 - 0/20 (en tonnes)'), (5220, 'poids', None)]},
    'besnault':   {'partners': [15689], 'section': 'sans_produit',
                   'lignes': [(5882, 'poids', None)]},
    'machefers':  {'partners': [16033], 'section': 'sans_produit',
                   'lignes': [(444, 'un', None)]},
    'gsm':        {'partners': [18889, 15837], 'section': 'standard',
                   'lignes': [(5903, 'poids', None)]},
    'chatel':     {'partners': [18838], 'section': 'dynamique', 'lignes': []},
    'haims':      {'partners': [15848, 18115], 'section': 'label_avant_produit', 'lignes': []},
}
if recette not in RECETTES:
    raise UserError('Recette inconnue : %s' % recette)
R = RECETTES[recette]

APPRO = [('BARRE', 5878), ('BAILLY', 5879), ('ROY', 5880), ('MORIN', 5881),
         ('LUCHE', 5882), ('HAIMS', 5884), ('MAQUIGNON', 5885), ('USSEAU', 5885),
         ('KIDIMAT', 5886), ('IMERYS', 5887), ('SAMIN', 5888), ('POUZZO', 5883)]

def _norm(s):
    s = (s or '').upper()
    for a, b in (('É', 'E'), ('È', 'E'), ('Ê', 'E'), ('À', 'A'), ('Â', 'A'), ('Î', 'I'), ('Ô', 'O'), ('Û', 'U'), ('Ç', 'C')):
        s = s.replace(a, b)
    return s

def _label_tache(nom):
    n = _norm(nom)
    for pref in ("CHATEL GRANULATS", "CHATEL'GRANULATS", 'CHATEL GRANULAT', "CARRIERE D'HAIMS", 'CARRIERE D HAIMS'):
        if n.startswith(pref):
            reste = nom[len(pref):]
            return reste.strip(' -–').strip()
    return nom.strip()

tasks = env['project.task'].sudo().search([
    ('partner_id', 'in', R['partners']),
    ('project_id.name', '=', 'Demande de transport'),
    ('planned_date_begin', '>=', du + ' 00:00:00'),
    ('planned_date_begin', '<=', au + ' 23:59:59'),
], order='planned_date_begin')
faits, deja, annulees, sans_bon, a_verifier, futurs = [], 0, 0, [], [], 0
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
    nom_n = _norm(t.name or '')
    lignes = list(R['lignes'])
    section_mode = R['section']
    if recette == 'chatel':
        prod_appro = None
        for mot, pid in APPRO:
            if mot in nom_n:
                prod_appro = pid
                break
        if 'DEBLAIS' in nom_n:
            lignes = [(5903, 'poids', None)]           # granulats (Tonne) — arbitrage Isabelle
            section_mode = 'standard'
        elif prod_appro:
            lignes = [(prod_appro, 'poids', None)]
            section_mode = 'produit4'
        else:
            lignes = [(5904, 'un', None)]              # livraison : granulats (Forfait), qte 1
            section_mode = 'label_apres_produit'
    elif recette == 'haims':
        if 'TRANSFERT' in nom_n:
            lignes = [(5912, 'un', None)]              # Transfert de materiel (Heure), qte 1 a ajuster
        else:
            lignes = [(5903, 'poids', None)]
    # bon de pesee (derniere feuille de la tache)
    ws = env['x_project_task_worksheet_template_1'].sudo().search(
        [('x_project_task_id', '=', t.id)], limit=1, order='create_date desc')
    poids_t = round(ws.x_studio_poids_net / 1000, 3) if (ws and ws.x_studio_poids_net) else 0.0
    so = env['sale.order'].sudo().create({
        'partner_id': t.partner_id.id,
        'company_id': t.company_id.id,
        'origin': t.name,
        # date du BC = date du transport : les validites de tarifs (listes de
        # prix datees) s'appliquent au jour de la prestation, pas au jour du clic
        'date_order': t.planned_date_begin,
    })
    for pid, qmode, libcli in lignes:
        qte = poids_t if (qmode == 'poids' and poids_t) else 1
        vals = {'order_id': so.id, 'product_id': pid, 'product_uom_qty': qte, 'task_id': t.id}
        if libcli:
            vals['x_studio_libell_client'] = libcli
        env['sale.order.line'].sudo().create(vals)
    so.action_confirm()
    if t.planned_date_begin:
        # action_confirm remet la date du jour : on recale sur la date du
        # transport pour que les tarifs dates s'appliquent au bon jour
        so.write({'date_order': t.planned_date_begin})
    t.write({'sale_order_id': so.id})
    for l0 in so.order_line:
        if not l0.display_type and not l0.price_unit:
            # forfaits de livraison & co : prix a poser a la main
            a_verifier.append('%s (%s) : prix a saisir (ligne a 0)' % ((t.name or '').strip()[:40], so.name))
            break
    if ws and (ws.x_studio_numero_bon or ws.x_studio_client_pesee or ws.x_studio_vehicule):
        poids_str = ('%s T' % poids_t) if poids_t else 'Poids N/A'
        parts = ['Bon n°%s' % (ws.x_studio_numero_bon or ''), '%s' % (ws.x_studio_date_bon or '')]
        produit = '%s' % (ws.x_studio_produit_pesee or '')
        veh = '%s' % (ws.x_studio_vehicule or '')
        label = _label_tache(t.name or '')
        if section_mode == 'sans_produit':
            parts += [veh, poids_str]
        elif section_mode == 'produit4':
            parts += [produit[:4], veh, poids_str]
        elif section_mode == 'label_avant_produit':
            parts += [label, produit, veh, poids_str]
        elif section_mode == 'label_apres_produit':
            parts += [produit, label, veh, poids_str]
        else:
            parts += [produit, veh, poids_str]
        first_line = env['sale.order.line'].sudo().search(
            [('order_id', '=', so.id), ('display_type', '=', False)], order='sequence asc', limit=1)
        env['sale.order.line'].sudo().create({
            'order_id': so.id, 'display_type': 'line_section', 'name': ' | '.join(parts),
            'sequence': (first_line.sequence - 1) if first_line else 10,
        })
        so.message_post(body='<b>Données bon de pesée</b><br/>N° Bon : %s<br/>Date : %s<br/>Véhicule : %s<br/>Produit : %s<br/>Poids net : %s kg<br/><i>BC généré par le bouton « %s » (planning transport)</i>' % (
            ws.x_studio_numero_bon or '-', ws.x_studio_date_bon or '-',
            ws.x_studio_vehicule or '-', ws.x_studio_produit_pesee or '-',
            ws.x_studio_poids_net or 0, recette))
    else:
        sans_bon.append('%s (%s)' % ((t.name or t.id), so.name))
    if recette == 'haims' and 'TRANSFERT' in nom_n:
        a_verifier.append('%s (%s) : transfert facturé à l heure — ajuster la quantité' % ((t.name or '').strip()[:40], so.name))
    if 'poids' in [l[1] for l in lignes] and not poids_t:
        a_verifier.append('%s (%s) : pas de poids sur le bon — quantité laissée à 1' % ((t.name or '').strip()[:40], so.name))
    faits.append(so.name)
action = {'ok': 1, 'faits': len(faits), 'bons': faits[:100], 'deja': deja,
          'annulees': annulees, 'sans_bon': sans_bon[:40], 'a_verifier': a_verifier[:40], 'futurs': futurs}

