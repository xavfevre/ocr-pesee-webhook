# Action serveur Odoo 2081 — ARCHIVE avant suppression (03/09/2026) — portée vers Render (web_actions.py)
# Compteur de lignes de l'abonnement Odoo (« Maintenance par 100 lignes »).

# Boutons transport (vue mois) : BC automatiques par recette client.
# Regles communes : tache du mois affiche, NON annulee, SANS BC existant,
# NON future, et A L'ETAT « Fait » (etat kanban) — sinon comptee/ignoree.
# Quantites : 'poids' = tonnage du bon de pesee ; 'un' = 1 (forfait/heure).
ctx = env.context
recette = (ctx.get('tb_recette') or '').strip()
du = (ctx.get('tb_du') or '').strip()
au = (ctx.get('tb_au') or '').strip()
if not (recette and du and au):
    raise UserError('Parametres manquants (tb_recette / tb_du / tb_au).')

RECETTES = {
    'longue_lac': {'partners': [15797, 15755], 'section': 'sans_produit',
                   'lignes': [(4414, 'poids', None), (5220, 'poids', None)]},
    'prieure':    {'partners': [18133], 'section': 'sans_produit',
                   'lignes': [(4414, 'poids', 'Tuffeau broyé 0/15 - 0/20 (en tonnes)'), (5220, 'poids', None)]},
    'besnault':   {'partners': [15689], 'section': 'besnault',
                   'lignes': [(5882, 'poids', None)]},
    'machefers':  {'partners': [16033], 'section': 'machefers',
                   'lignes': [(444, 'un', None)]},
    'gsm':        {'partners': [18889, 15837], 'section': 'gsm',
                   'lignes': [(5903, 'poids', None)]},
    'chatel':     {'partners': [18838], 'section': 'dynamique', 'lignes': []},
    'haims':      {'partners': [15848, 18115], 'section': 'label_avant_produit', 'lignes': []},
    'eco':        {'partners': [18289], 'section': 'eco', 'lignes': []},
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
    for pref in ("CHATEL GRANULATS", "CHATEL'GRANULATS", 'CHATEL GRANULAT', "CARRIERE D'HAIMS", 'CARRIERE D HAIMS', 'ECO CONCEPT'):
        if n.startswith(pref):
            reste = nom[len(pref):]
            return reste.strip(' -–').strip()
    return nom.strip()

def _adresse(txt):
    # « premiere ligne + ville embellie » : BIMBO QRS PLESSIS / ZA... / 86100
    # CHATELLERAULT -> « BIMBO QRS PLESSIS CHATELLERAULT (86) »
    lignes = [l.strip() for l in (txt or '').split('\n') if l.strip()]
    if not lignes:
        return ''
    if len(lignes) == 1:
        return lignes[0]
    prem, der = lignes[0], lignes[-1]
    mots = der.split()
    if mots and mots[0].isdigit() and len(mots[0]) == 5:
        der = ' '.join(mots[1:]) + ' (' + mots[0][:2] + ')'
    return (prem + ' ' + der).strip()

def _ville(txt):
    # extrait la ville : mots qui suivent le code postal (5 chiffres) ;
    # a defaut, premiere ligne du champ
    lignes = [l.strip() for l in (txt or '').split('\n') if l.strip()]
    if not lignes:
        return ''
    for l in lignes:
        mots = l.replace('-', ' ').split()
        i = 0
        for m in mots:
            i += 1
            if m.isdigit() and len(m) == 5:
                ville = ' '.join(mots[i:]).strip()
                if ville:
                    return ville
    return lignes[0]

def _seg_adresses(t):
    # « VILLE CHARGEMENT à VILLE LIVRAISON » si les deux champs sont remplis, sinon ''
    charg = _ville(t.x_studio_adresse_de_chargement)
    livr = _ville(t.x_studio_adresse_de_livraison_3)
    return ('%s à %s' % (charg, livr)) if (charg and livr) else ''

def _descr_ligne1(t):
    # 1ere ligne non vide de la description (HTML) ; espace insere apres
    # les 4 premiers caracteres : « 0/20BLEU » -> « 0/20 BLEU »
    brut = t.description or ''
    out = []
    dedans = False
    for c in brut:
        if c == '<':
            dedans = True
        elif c == '>':
            dedans = False
            out.append('\n')
        elif not dedans:
            out.append(c)
    txt = ''.join(out)
    for a, b in (('&nbsp;', ' '), ('&amp;', '&'), ('&#39;', "'"), ('&quot;', '"')):
        txt = txt.replace(a, b)
    lignes = [l.strip() for l in txt.split('\n') if l.strip()]
    if not lignes:
        return ''
    l1 = lignes[0]
    if len(l1) > 4 and l1[4] != ' ':
        l1 = l1[:4] + ' ' + l1[4:]
    return l1

tasks = env['project.task'].sudo().search([
    ('partner_id', 'in', R['partners']),
    ('project_id.name', '=', 'Demande de transport'),
    ('planned_date_begin', '>=', du + ' 00:00:00'),
    ('planned_date_begin', '<=', au + ' 23:59:59'),
], order='planned_date_begin')
faits, deja, annulees, sans_bon, a_verifier, futurs, non_faits = [], 0, 0, [], [], 0, 0
for t in tasks:
    st = (t.stage_id.name or '').lower()
    if 'annul' in st or 'cancel' in st or t.state == '1_canceled':
        annulees += 1
        continue
    if t.sale_order_id or t.sale_line_id:
        deja += 1
        continue
    if t.planned_date_begin and t.planned_date_begin > datetime.datetime.now():
        futurs += 1
        continue
    if t.state != '1_done':
        # regle commune : le transport doit etre a l'etat « Fait »
        non_faits += 1
        continue
    nom_n = _norm(t.name or '')
    lignes = list(R['lignes'])
    section_mode = R['section']
    eco_milieu = None
    if recette == 'chatel':
        prod_appro = None
        for mot, pid in APPRO:
            if mot in nom_n:
                prod_appro = pid
                break
        if 'DEBLAIS' in nom_n:
            lignes = [(5903, 'poids', None)]
            section_mode = 'standard'
        elif prod_appro:
            lignes = [(prod_appro, 'poids', None)]
            section_mode = 'produit4'
        else:
            lignes = [(5904, 'un', None)]
            section_mode = 'label_apres_produit'
    elif recette == 'haims':
        if 'TRANSFERT' in nom_n:
            lignes = [(5912, 'un', None)]
        else:
            lignes = [(5903, 'poids', None)]
    elif recette == 'eco':
        # ordre de priorite de la procedure ECO CONCEPT (FMA prime sur Bouresse)
        charg = _adresse(t.x_studio_adresse_de_chargement)
        livr = _adresse(t.x_studio_adresse_de_livraison_3)
        regle = None
        if 'LAVAGE DE 3 BENNES' in nom_n:
            regle = (5902, '%s - Lavage de 3 bennes' % charg)
        elif 'ENTREE DE BENNE' in nom_n or 'REMISE EN PLACE' in nom_n:
            regle = (5831, '%s - Remise en place de la benne pâte' % charg)
        elif 'INVERSION DE BENNE' in nom_n:
            regle = (5889, '%s - Inversion benne pâte' % charg)
        elif 'SORTIE DE BENNE' in nom_n:
            regle = (5889, '%s - Sortie de benne pour lavage' % charg)
        elif ('FMA' in nom_n or 'VENDEE' in nom_n or 'JEANDINET' in nom_n or 'ELEVAGE DU BREUIL' in nom_n
              or 'EARL REBA' in nom_n or 'VICQ' in nom_n or 'AINAY' in nom_n):
            regle = (5910, ('FMA %s -> %s' % (charg, livr)) if livr else ('FMA %s' % charg))
        elif 'BENNE PAIN' in nom_n or ('ENLEVEMENT' in nom_n and 'VIDAGE' in nom_n):
            regle = (5829, ('Enlèvement + vidage benne pain - %s -> %s' % (charg, livr)) if livr else ('Enlèvement + vidage benne pain - %s' % charg))
        elif 'BOURESSE' in nom_n or 'BOURRESSE' in nom_n or 'BENNES PATE' in nom_n or 'BENNE PATE' in nom_n:
            regle = (5830, ('Transport 2 bennes pâte - %s -> %s' % (charg, livr)) if livr else ('Transport 2 bennes pâte - %s' % charg))
        if not regle:
            a_verifier.append('%s : aucune règle reconnue — BC non créé' % (t.name or t.id))
            continue
        lignes = [(regle[0], 'un', None)]
        eco_milieu = regle[1]
        if regle[0] in (5910, 5829, 5830) and not livr:
            a_verifier.append('%s : adresse de livraison absente sur la tâche' % (t.name or t.id))
    # bon de pesee (derniere feuille de la tache)
    ws = env['x_project_task_worksheet_template_1'].sudo().search(
        [('x_project_task_id', '=', t.id)], limit=1, order='create_date desc')
    poids_t = round(ws.x_studio_poids_net / 1000, 3) if (ws and ws.x_studio_poids_net) else 0.0
    so = env['sale.order'].sudo().create({
        'partner_id': t.partner_id.id,
        'company_id': t.company_id.id,
        'origin': t.name,
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
        so.write({'date_order': t.planned_date_begin})
    t.write({'sale_order_id': so.id})
    if recette == 'chatel':
        # etiquette « Autres informations » du BC selon l'article
        prod0 = env['product.product'].sudo().browse(lignes[0][0])
        etiquette = 'Appro CG' if 'APPRO' in _norm(prod0.name or '') else 'Liv Client CG'
        tag = env['crm.tag'].sudo().search([('name', '=', etiquette)], limit=1)
        if not tag:
            tag = env['crm.tag'].sudo().create({'name': etiquette})
        so.write({'tag_ids': [(4, tag.id)]})
    for l0 in so.order_line:
        if not l0.display_type and not l0.price_unit:
            a_verifier.append('%s (%s) : prix a saisir (ligne a 0)' % ((t.name or '').strip()[:40], so.name))
            break
    if ws and (ws.x_studio_numero_bon or ws.x_studio_client_pesee or ws.x_studio_vehicule):
        poids_str = ('%s T' % poids_t) if poids_t else 'Poids N/A'
        num = '%s' % (ws.x_studio_numero_bon or '')
        type_doc = ('%s' % (ws.x_studio_type_document or '')).strip().lower()
        if 'LVN' in num.upper() or type_doc == 'lettre_voiture':
            part0 = 'LVN n°' + num.upper().replace('LVN', '').replace('N°', '').strip(' °')
        else:
            part0 = 'Bon n°' + num
        parts = [part0, '%s' % (ws.x_studio_date_bon or '')]
        produit = '%s' % (ws.x_studio_produit_pesee or '')
        veh = '%s' % (ws.x_studio_vehicule or '')
        label = _label_tache(t.name or '')
        seg_adr = _seg_adresses(t)
        if section_mode == 'gsm' and ws.x_studio_contrat_sap:
            parts[0] = 'BL SAP PR0 n°%s - Transport n°%s' % (ws.x_studio_contrat_sap, num)
        if section_mode == 'eco':
            parts += [eco_milieu or produit, veh]      # sans poids (qte = 1)
        elif section_mode == 'sans_produit':
            # Longue/Lac, Prieure : adresses inserees si les 2 champs remplis
            if seg_adr:
                parts += [seg_adr]
            parts += [veh, poids_str]
        elif section_mode == 'besnault':
            # produit repris de la description + adresses
            prod_descr = _descr_ligne1(t)
            if prod_descr:
                parts += [prod_descr]
            if seg_adr:
                parts += [seg_adr]
            parts += [veh, poids_str]
        elif section_mode == 'machefers':
            # rien entre la date et l'immat
            parts += [veh, poids_str]
        elif section_mode == 'gsm':
            # produit sur 4 caracteres + code destinataire marchandise (OCR)
            parts += [produit[:4]]
            if ws.x_studio_code_destinataire:
                parts += ['%s' % ws.x_studio_code_destinataire]
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
          'annulees': annulees, 'sans_bon': sans_bon[:40],
          'a_verifier': a_verifier[:40], 'futurs': futurs, 'non_faits': non_faits}
