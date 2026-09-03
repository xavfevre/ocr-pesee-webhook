# -*- coding: utf-8 -*-
"""Actions des pages web (parc, planning transport, poste de scan) portées
d'Odoo vers Render pour libérer le compteur de lignes de l'abonnement
(module payant « Maintenance par 100 lignes »), sur le modèle de
heures_actions.py. Les pages appellent /heures/rpc avec {action_id, ctx} et
reçoivent le dict « action » ; WebErreur joue le rôle du UserError.

Actions portées (originaux archivés dans odoo-scan-page/action_*.py) :
  1987  Tablette : déclarer un rebut (poste de scan, vue opérateur)
  2055  Parc auto : enregistrer une intervention (/parc-controles)
  2078  SEDE : générer les BC VEOLIA (planning transport mois)
  2081  Boutons transport : BC automatiques par recette (planning mois)
"""
import datetime


class WebErreur(Exception):
    """Message affiché tel quel par la page (équivalent UserError)."""


def executer(call, action_id, ctx):
    return {1987: _rebut, 2055: _parc_intervention,
            2078: _sede_veolia, 2081: _boutons_transport}[action_id](call, ctx)


# ─── 2055 · Parc auto : enregistrer une intervention ─────────────────────────

def _log_srv(call, vals):
    return call('fleet.vehicle.log.services', 'create', [vals])


def _parc_intervention(call, ctx):
    rid = int(ctx.get('pc_id'))
    date_val = (ctx.get('pc_date') or '').strip()
    cv_limite = (ctx.get('pc_cv_limite') or '').strip()
    cv_done = ctx.get('pc_cv_done')
    row = call('x_controle_vehicule', 'read', [rid],
               fields=['x_vehicule_id', 'x_type_id'])[0]
    ty = call('x_type_controle', 'read', [row['x_type_id'][0]],
              fields=['x_fleet_service_type_id', 'x_periodicite_mois'])[0]
    fst = ty['x_fleet_service_type_id'] and ty['x_fleet_service_type_id'][0]
    veh = row['x_vehicule_id'][0]

    if cv_limite:
        call('x_controle_vehicule', 'write', [rid], {'x_cv_limite': cv_limite})
        if fst:
            _log_srv(call, {'vehicle_id': veh, 'service_type_id': fst, 'date': cv_limite,
                            'state': 'new',
                            'notes': 'CONTRE-VISITE a passer avant cette date (planning des controles obligatoires)'})
        return {'ok': 1}
    if cv_done:
        dd = date_val or str(datetime.date.today())
        if fst:
            anciens = call('fleet.vehicle.log.services', 'search',
                           [['vehicle_id', '=', veh], ['service_type_id', '=', fst],
                            ['state', '=', 'new'], ['notes', 'like', 'CONTRE-VISITE']])
            if anciens:
                call('fleet.vehicle.log.services', 'write', anciens, {'state': 'cancelled'})
            _log_srv(call, {'vehicle_id': veh, 'service_type_id': fst, 'date': dd,
                            'state': 'done',
                            'notes': 'Contre-visite effectuee (planning des controles obligatoires)'})
        call('x_controle_vehicule', 'write', [rid], {'x_cv_limite': False})
        return {'ok': 1}

    cibles = [(rid, row['x_type_id'][0], veh)]
    if date_val and ctx.get('pc_combo_too'):
        v = call('fleet.vehicle', 'read', [veh], fields=['x_attelage_id'])[0]
        if v['x_attelage_id']:
            prow = call('x_controle_vehicule', 'search_read',
                        [['x_vehicule_id', '=', v['x_attelage_id'][0]],
                         ['x_type_id', '=', row['x_type_id'][0]]],
                        fields=['x_vehicule_id', 'x_type_id'], limit=1)
            if prow:
                cibles.append((prow[0]['id'], prow[0]['x_type_id'][0],
                               prow[0]['x_vehicule_id'][0]))
    for crid, ctyid, cveh in cibles:
        cty = call('x_type_controle', 'read', [ctyid],
                   fields=['x_fleet_service_type_id', 'x_periodicite_mois'])[0]
        cfst = cty['x_fleet_service_type_id'] and cty['x_fleet_service_type_id'][0]
        if cfst:
            planifies = call('fleet.vehicle.log.services', 'search',
                             [['vehicle_id', '=', cveh], ['service_type_id', '=', cfst],
                              ['state', '=', 'new']])
            if planifies:
                call('fleet.vehicle.log.services', 'write', planifies, {'state': 'cancelled'})
        if date_val:
            if cfst:
                # une correction fait foi : les « Terminé » datés APRÈS la
                # nouvelle date (saisie erronée) sont annulés, sinon l'affichage
                # (dernier Terminé) continuerait de montrer l'ancienne date
                errones = call('fleet.vehicle.log.services', 'search',
                               [['vehicle_id', '=', cveh], ['service_type_id', '=', cfst],
                                ['state', '=', 'done'], ['date', '>', date_val]])
                if errones:
                    call('fleet.vehicle.log.services', 'write', errones, {'state': 'cancelled'})
                _log_srv(call, {'vehicle_id': cveh, 'service_type_id': cfst, 'date': date_val,
                                'state': 'done',
                                'notes': 'Saisi depuis le planning des controles obligatoires (/parc-controles)'})
                prochaine = (datetime.datetime.strptime(date_val, '%Y-%m-%d').date()
                             + datetime.timedelta(days=30 * cty['x_periodicite_mois']))
                _log_srv(call, {'vehicle_id': cveh, 'service_type_id': cfst,
                                'date': prochaine.isoformat(), 'state': 'new',
                                'notes': 'Prochain controle planifie automatiquement (planning des controles obligatoires)'})
            call('x_controle_vehicule', 'write',
                 [crid], {'x_derniere_date': date_val, 'x_cv_limite': False})
        else:
            call('x_controle_vehicule', 'write',
                 [crid], {'x_derniere_date': False, 'x_cv_limite': False})
    return {'ok': 1, 'nb': len(cibles)}


# ─── 1987 · Tablette : déclarer un rebut ─────────────────────────────────────

def _sur(fn):
    """Les méthodes Odoo renvoyant None/action lèvent « cannot marshal None »
    côté serveur alors que l'opération a réussi."""
    try:
        return fn()
    except Exception as e:
        if 'cannot marshal None' not in str(e):
            raise


def _rebut(call, ctx):
    ofid = int(ctx.get('active_id') or 0)
    n = int(ctx.get('rebut_n') or 0)
    motif = (ctx.get('rebut_motif') or '').strip()
    ofs = call('mrp.production', 'read', [ofid],
               fields=['name', 'state', 'origin', 'product_id', 'product_qty',
                       'product_uom_id', 'company_id', 'bom_id', 'workorder_ids',
                       'x_studio_nbr', 'x_studio_rebut_nb', 'x_studio_relance_of',
                       'x_studio_vol_total', 'x_studio_colis', 'x_studio_catgorie',
                       'x_studio_palette', 'date_deadline', 'x_studio_date_de_commande',
                       'x_studio_haut_m', 'x_studio_larg_m', 'x_studio_long_m',
                       'x_studio_n_de_bc']) if ofid else []
    if not ofs or n <= 0:
        raise WebErreur('Rebut : nombre de pierres invalide')
    of = ofs[0]
    tot = int(of['x_studio_nbr'] or 0) or 1
    if n > tot:
        raise WebErreur('Rebut : maximum %s pierre(s) sur cet OF' % tot)
    deja = int(of['x_studio_rebut_nb'] or 0)
    if deja + n > tot:
        raise WebErreur('Rebut deja declare sur cet OF (%s pierre(s), OF de relance %s). '
                        'Rien a refaire : l OF de relance est dans la liste.'
                        % (deja, of['x_studio_relance_of'] or '-'))
    vol_unit = (of['x_studio_vol_total'] or 0.0) / tot
    vol_reb = vol_unit * n

    # 1) retirer les pierres cassées du colis (entier ou répartition)
    colis_note = ''
    if of['x_studio_colis']:
        colis_id, colis_nom = of['x_studio_colis']
        call('mrp.production', 'write', [ofid], {'x_studio_colis': False})
        if n < tot:
            call('x_repartition_palette', 'create',
                 [{'x_studio_of_id': ofid, 'x_studio_colis_id': colis_id,
                   'x_studio_qte': tot - n}])
        colis_note = ' · retire du colis %s' % colis_nom
    else:
        reps = call('x_repartition_palette', 'search_read',
                    [['x_studio_of_id', '=', ofid]],
                    fields=['x_studio_qte', 'x_studio_colis_id'])
        rem = n
        for rp in reps:
            if rem <= 0:
                break
            q = int(rp['x_studio_qte'] or 0)
            cn = rp['x_studio_colis_id'] and rp['x_studio_colis_id'][1]
            if q <= rem:
                rem -= q
                call('x_repartition_palette', 'unlink', [rp['id']])
            else:
                call('x_repartition_palette', 'write', [rp['id']], {'x_studio_qte': q - rem})
                rem = 0
            colis_note = ' · repartition reduite (%s)' % cn

    # 2) sortie de stock si la production était terminée
    scrap_note = ''
    if of['state'] == 'done' and vol_reb > 0:
        try:
            sc = call('stock.scrap', 'create',
                      [{'product_id': of['product_id'][0], 'scrap_qty': vol_reb,
                        'product_uom_id': of['product_uom_id'][0], 'production_id': ofid,
                        'company_id': of['company_id'][0]}])
            _sur(lambda: call('stock.scrap', 'action_validate', [sc]))
            etat = call('stock.scrap', 'read', [sc], fields=['state', 'location_id',
                                                               'product_uom_id'])[0]
            if etat['state'] != 'done':
                wiz = call('stock.warn.insufficient.qty.scrap', 'create',
                           [{'product_id': of['product_id'][0],
                             'location_id': etat['location_id'][0], 'scrap_id': sc,
                             'quantity': vol_reb,
                             'product_uom_name': etat['product_uom_id'][1]}])
                _sur(lambda: call('stock.warn.insufficient.qty.scrap', 'action_done', [wiz]))
            scrap_note = ' · %.3f m3 sortis du stock (rebut)' % vol_reb
        except Exception:
            scrap_note = ' · (sortie de stock impossible, a regulariser)'

    # 3) OF de relance
    new_id = call('mrp.production', 'copy', [ofid],
                  default={'product_qty': vol_reb or of['product_qty'],
                           'origin': of['origin'],
                           'product_id': of['product_id'][0],
                           'bom_id': of['bom_id'][0] if of['bom_id'] else False})
    if isinstance(new_id, list):
        new_id = new_id[0]
    vals = {'x_studio_nbr': n, 'x_studio_origine_rebut': of['name'], 'priority': '1'}
    if of['x_studio_catgorie']:
        vals['x_studio_catgorie'] = of['x_studio_catgorie'][0]
    if of['x_studio_palette']:
        vals['x_studio_palette'] = of['x_studio_palette']
    for f in ('date_deadline', 'x_studio_date_de_commande', 'x_studio_haut_m',
              'x_studio_larg_m', 'x_studio_long_m', 'x_studio_n_de_bc'):
        if of.get(f):
            vals[f] = of[f]
    call('mrp.production', 'write', [new_id], vals)
    _sur(lambda: call('mrp.production', 'action_confirm', [new_id]))
    # assigner les opérateurs de l'OF d'origine pour que la relance apparaisse
    # dans « Ma production » (sinon l'opérateur croit que rien ne s'est passé)
    new = call('mrp.production', 'read', [new_id], fields=['name', 'workorder_ids'])[0]
    wo_new = call('mrp.workorder', 'read', [new['workorder_ids']],
                  fields=['name']) if new['workorder_ids'] else []
    wo_src = call('mrp.workorder', 'read', [of['workorder_ids']],
                  fields=['name', 'employee_assigned_ids']) if of['workorder_ids'] else []
    for w in wo_new:
        src = [s for s in wo_src if s['name'] == w['name']] or wo_src[:1]
        if src and src[0]['employee_assigned_ids']:
            call('mrp.workorder', 'write',
                 [w['id']], {'employee_assigned_ids': [(6, 0, src[0]['employee_assigned_ids'])]})

    # 4) traçabilité
    call('mrp.production', 'write',
         [ofid], {'x_studio_rebut_nb': deja + n, 'x_studio_rebut_motif': motif or 'Rebut',
                  'x_studio_relance_of': new['name']})
    _sur(lambda: call('mrp.production', 'message_post', [ofid],
                      body='💥 Rebut : %s pierre(s)%s%s · motif : %s · OF de relance : %s'
                           % (n, colis_note, scrap_note, motif or '-', new['name'])))
    return {'rebut_ok': True, 'new_of': new['name']}


# ─── helpers communs transport (2078 / 2081) ─────────────────────────────────

def _taches_transport(call, partners, du, au):
    return call('project.task', 'search_read',
                [['partner_id', 'in' if isinstance(partners, list) else 'child_of', partners],
                 ['project_id.name', '=', 'Demande de transport'],
                 ['planned_date_begin', '>=', du + ' 00:00:00'],
                 ['planned_date_begin', '<=', au + ' 23:59:59']],
                fields=['name', 'partner_id', 'company_id', 'planned_date_begin',
                        'stage_id', 'state', 'sale_order_id', 'sale_line_id',
                        'description', 'x_studio_adresse_de_chargement',
                        'x_studio_adresse_de_livraison_3'],
                order='planned_date_begin')


def _feuille_tache(call, tid):
    ws = call('x_project_task_worksheet_template_1', 'search_read',
              [['x_project_task_id', '=', tid]],
              fields=['x_studio_numero_bon', 'x_studio_client_pesee', 'x_studio_vehicule',
                      'x_studio_date_bon', 'x_studio_produit_pesee', 'x_studio_poids_net',
                      'x_studio_type_document', 'x_studio_contrat_sap',
                      'x_studio_code_destinataire'],
              limit=1, order='create_date desc')
    return ws[0] if ws else None


def _cree_bc(call, t, lignes):
    """BC confirmé daté du transport, lignes produits, tâche rattachée."""
    so = call('sale.order', 'create',
              [{'partner_id': t['partner_id'][0], 'company_id': t['company_id'][0],
                'origin': t['name'],
                # date du BC = date du transport : les validités de tarifs (listes
                # de prix datées) s'appliquent au jour de la prestation
                'date_order': t['planned_date_begin']}])
    for vals in lignes:
        vals['order_id'] = so
        call('sale.order.line', 'create', [vals])
    _sur(lambda: call('sale.order', 'action_confirm', [so]))
    if t['planned_date_begin']:
        # action_confirm remet la date du jour : on recale sur la date du transport
        call('sale.order', 'write', [so], {'date_order': t['planned_date_begin']})
    call('project.task', 'write', [t['id']], {'sale_order_id': so})
    nom = call('sale.order', 'read', [so], fields=['name'])[0]['name']
    return so, nom


def _section_bc(call, so_id, nom_section):
    first = call('sale.order.line', 'search_read',
                 [['order_id', '=', so_id], ['display_type', '=', False]],
                 fields=['sequence'], order='sequence asc', limit=1)
    call('sale.order.line', 'create',
         [{'order_id': so_id, 'display_type': 'line_section', 'name': nom_section,
           'sequence': (first[0]['sequence'] - 1) if first else 10}])


def _post_bon(call, so_id, ws, pied):
    _sur(lambda: call('sale.order', 'message_post', [so_id],
                      body='<b>Données bon de pesée</b><br/>N° Bon : %s<br/>Date : %s<br/>'
                           'Véhicule : %s<br/>Produit : %s<br/>Poids net : %s kg<br/><i>%s</i>'
                           % (ws['x_studio_numero_bon'] or '-', ws['x_studio_date_bon'] or '-',
                              ws['x_studio_vehicule'] or '-', ws['x_studio_produit_pesee'] or '-',
                              ws['x_studio_poids_net'] or 0, pied)))


# ─── 2078 · SEDE : générer les BC VEOLIA ─────────────────────────────────────

def _sede_veolia(call, ctx):
    du = (ctx.get('sede_du') or '').strip()
    au = (ctx.get('sede_au') or '').strip()
    if not (du and au):
        raise WebErreur('Période manquante (sede_du / sede_au).')
    PARTNER_ID = 16001   # VEOLIA AGRICULTURE FRANCE
    PRODUIT_ID = 5828    # Location de matériel Transport (Semi Fond-mouvant - par jours)
    tasks = _taches_transport(call, PARTNER_ID, du, au)
    faits, sans_bon = [], []
    futurs = non_faits = deja = annulees = 0
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for t in tasks:
        st = (t['stage_id'] and t['stage_id'][1] or '').lower()
        if 'annul' in st or 'cancel' in st:
            annulees += 1
            continue
        if t['sale_order_id'] or t['sale_line_id']:
            deja += 1
            continue
        if t['state'] != '1_done':
            non_faits += 1
            continue
        if t['planned_date_begin'] and t['planned_date_begin'] > now:
            futurs += 1
            continue
        so, so_nom = _cree_bc(call, t, [{'product_id': PRODUIT_ID, 'product_uom_qty': 1,
                                         'task_id': t['id']}])
        ws = _feuille_tache(call, t['id'])
        if ws and (ws['x_studio_numero_bon'] or ws['x_studio_client_pesee'] or ws['x_studio_vehicule']):
            poids_str = ('%s T' % round(ws['x_studio_poids_net'] / 1000, 3)) \
                if ws['x_studio_poids_net'] else 'Poids N/A'
            _section_bc(call, so, 'Bon n°%s | %s | %s | %s | %s' % (
                ws['x_studio_numero_bon'] or '', ws['x_studio_date_bon'] or '',
                ws['x_studio_produit_pesee'] or '', ws['x_studio_vehicule'] or '', poids_str))
            _post_bon(call, so, ws, 'BC généré par le bouton SEDE (planning transport)')
        else:
            sans_bon.append('%s (%s)' % (t['name'] or t['id'], so_nom))
        faits.append(so_nom)
    return {'ok': 1, 'faits': len(faits), 'bons': faits[:100], 'deja': deja,
            'annulees': annulees, 'sans_bon': sans_bon[:40], 'futurs': futurs,
            'non_faits': non_faits}


# ─── 2081 · Boutons transport : BC automatiques par recette ──────────────────

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
APPRO = [('BARRE', 5878), ('BAILLY', 5879), ('ROY', 5880), ('MORIN', 5881),
         ('LUCHE', 5882), ('HAIMS', 5884), ('MAQUIGNON', 5885), ('USSEAU', 5885),
         ('KIDIMAT', 5886), ('IMERYS', 5887), ('SAMIN', 5888), ('POUZZO', 5883)]


def _norm(s):
    s = (s or '').upper()
    for a, b in (('É', 'E'), ('È', 'E'), ('Ê', 'E'), ('À', 'A'), ('Â', 'A'),
                 ('Î', 'I'), ('Ô', 'O'), ('Û', 'U'), ('Ç', 'C')):
        s = s.replace(a, b)
    return s


def _label_tache(nom):
    n = _norm(nom)
    for pref in ("CHATEL GRANULATS", "CHATEL'GRANULATS", 'CHATEL GRANULAT',
                 "CARRIERE D'HAIMS", 'CARRIERE D HAIMS', 'ECO CONCEPT'):
        if n.startswith(pref):
            return nom[len(pref):].strip(' -–').strip()
    return nom.strip()


def _adresse(txt):
    # « première ligne + ville embellie » : BIMBO QRS PLESSIS / ZA... /
    # 86100 CHATELLERAULT -> « BIMBO QRS PLESSIS CHATELLERAULT (86) »
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
    # à défaut, première ligne du champ
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
    charg = _ville(t['x_studio_adresse_de_chargement'])
    livr = _ville(t['x_studio_adresse_de_livraison_3'])
    return ('%s à %s' % (charg, livr)) if (charg and livr) else ''


def _descr_ligne1(t):
    # 1ère ligne non vide de la description (HTML) ; espace inséré après
    # les 4 premiers caractères : « 0/20BLEU » -> « 0/20 BLEU »
    brut = t['description'] or ''
    out, dedans = [], False
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


def _boutons_transport(call, ctx):
    recette = (ctx.get('tb_recette') or '').strip()
    du = (ctx.get('tb_du') or '').strip()
    au = (ctx.get('tb_au') or '').strip()
    if not (recette and du and au):
        raise WebErreur('Parametres manquants (tb_recette / tb_du / tb_au).')
    if recette not in RECETTES:
        raise WebErreur('Recette inconnue : %s' % recette)
    R = RECETTES[recette]
    tasks = _taches_transport(call, R['partners'], du, au)
    faits, sans_bon, a_verifier = [], [], []
    deja = annulees = futurs = non_faits = 0
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for t in tasks:
        st = (t['stage_id'] and t['stage_id'][1] or '').lower()
        if 'annul' in st or 'cancel' in st or t['state'] == '1_canceled':
            annulees += 1
            continue
        if t['sale_order_id'] or t['sale_line_id']:
            deja += 1
            continue
        if t['planned_date_begin'] and t['planned_date_begin'] > now:
            futurs += 1
            continue
        if t['state'] != '1_done':
            # règle commune : le transport doit être à l'état « Fait »
            non_faits += 1
            continue
        nom_n = _norm(t['name'] or '')
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
            lignes = [(5912, 'un', None)] if 'TRANSFERT' in nom_n else [(5903, 'poids', None)]
        elif recette == 'eco':
            # ordre de priorité de la procédure ECO CONCEPT (FMA prime sur Bouresse)
            charg = _adresse(t['x_studio_adresse_de_chargement'])
            livr = _adresse(t['x_studio_adresse_de_livraison_3'])
            regle = None
            if 'LAVAGE DE 3 BENNES' in nom_n:
                regle = (5902, '%s - Lavage de 3 bennes' % charg)
            elif 'ENTREE DE BENNE' in nom_n or 'REMISE EN PLACE' in nom_n:
                regle = (5831, '%s - Remise en place de la benne pâte' % charg)
            elif 'INVERSION DE BENNE' in nom_n:
                regle = (5889, '%s - Inversion benne pâte' % charg)
            elif 'SORTIE DE BENNE' in nom_n:
                regle = (5889, '%s - Sortie de benne pour lavage' % charg)
            elif ('FMA' in nom_n or 'VENDEE' in nom_n or 'JEANDINET' in nom_n
                  or 'ELEVAGE DU BREUIL' in nom_n or 'EARL REBA' in nom_n
                  or 'VICQ' in nom_n or 'AINAY' in nom_n):
                regle = (5910, ('FMA %s -> %s' % (charg, livr)) if livr else ('FMA %s' % charg))
            elif 'BENNE PAIN' in nom_n or ('ENLEVEMENT' in nom_n and 'VIDAGE' in nom_n):
                regle = (5829, ('Enlèvement + vidage benne pain - %s -> %s' % (charg, livr))
                         if livr else ('Enlèvement + vidage benne pain - %s' % charg))
            elif ('BOURESSE' in nom_n or 'BOURRESSE' in nom_n or 'BENNES PATE' in nom_n
                  or 'BENNE PATE' in nom_n):
                regle = (5830, ('Transport 2 bennes pâte - %s -> %s' % (charg, livr))
                         if livr else ('Transport 2 bennes pâte - %s' % charg))
            if not regle:
                a_verifier.append('%s : aucune règle reconnue — BC non créé' % (t['name'] or t['id']))
                continue
            lignes = [(regle[0], 'un', None)]
            eco_milieu = regle[1]
            if regle[0] in (5910, 5829, 5830) and not livr:
                a_verifier.append('%s : adresse de livraison absente sur la tâche' % (t['name'] or t['id']))
        # bon de pesée (dernière feuille de la tâche)
        ws = _feuille_tache(call, t['id'])
        poids_t = round(ws['x_studio_poids_net'] / 1000, 3) if (ws and ws['x_studio_poids_net']) else 0.0
        vals_lignes = []
        for pid, qmode, libcli in lignes:
            vals = {'product_id': pid,
                    'product_uom_qty': poids_t if (qmode == 'poids' and poids_t) else 1,
                    'task_id': t['id']}
            if libcli:
                vals['x_studio_libell_client'] = libcli
            vals_lignes.append(vals)
        so, so_nom = _cree_bc(call, t, vals_lignes)
        if recette == 'chatel':
            # étiquette « Autres informations » du BC selon l'article
            prod0 = call('product.product', 'read', [lignes[0][0]], fields=['name'])[0]
            etiquette = 'Appro CG' if 'APPRO' in _norm(prod0['name'] or '') else 'Liv Client CG'
            tag = call('crm.tag', 'search', [['name', '=', etiquette]], limit=1)
            tid = tag[0] if tag else call('crm.tag', 'create', [{'name': etiquette}])
            call('sale.order', 'write', [so], {'tag_ids': [(4, tid)]})
        for l0 in call('sale.order.line', 'search_read',
                       [['order_id', '=', so], ['display_type', '=', False]],
                       fields=['price_unit']):
            if not l0['price_unit']:
                a_verifier.append('%s (%s) : prix a saisir (ligne a 0)'
                                  % ((t['name'] or '').strip()[:40], so_nom))
                break
        if ws and (ws['x_studio_numero_bon'] or ws['x_studio_client_pesee'] or ws['x_studio_vehicule']):
            poids_str = ('%s T' % poids_t) if poids_t else 'Poids N/A'
            num = '%s' % (ws['x_studio_numero_bon'] or '')
            type_doc = ('%s' % (ws['x_studio_type_document'] or '')).strip().lower()
            if 'LVN' in num.upper() or type_doc == 'lettre_voiture':
                part0 = 'LVN n°' + num.upper().replace('LVN', '').replace('N°', '').strip(' °')
            else:
                part0 = 'Bon n°' + num
            parts = [part0, '%s' % (ws['x_studio_date_bon'] or '')]
            produit = '%s' % (ws['x_studio_produit_pesee'] or '')
            veh = '%s' % (ws['x_studio_vehicule'] or '')
            label = _label_tache(t['name'] or '')
            seg_adr = _seg_adresses(t)
            if section_mode == 'gsm' and ws['x_studio_contrat_sap']:
                parts[0] = 'BL SAP PR0 n°%s - Transport n°%s' % (ws['x_studio_contrat_sap'], num)
            if section_mode == 'eco':
                parts += [eco_milieu or produit, veh]      # sans poids (qté = 1)
            elif section_mode == 'sans_produit':
                if seg_adr:
                    parts += [seg_adr]
                parts += [veh, poids_str]
            elif section_mode == 'besnault':
                prod_descr = _descr_ligne1(t)
                if prod_descr:
                    parts += [prod_descr]
                if seg_adr:
                    parts += [seg_adr]
                parts += [veh, poids_str]
            elif section_mode == 'machefers':
                parts += [veh, poids_str]
            elif section_mode == 'gsm':
                parts += [produit[:4]]
                if ws['x_studio_code_destinataire']:
                    parts += ['%s' % ws['x_studio_code_destinataire']]
                parts += [veh, poids_str]
            elif section_mode == 'produit4':
                parts += [produit[:4], veh, poids_str]
            elif section_mode == 'label_avant_produit':
                parts += [label, produit, veh, poids_str]
            elif section_mode == 'label_apres_produit':
                parts += [produit, label, veh, poids_str]
            else:
                parts += [produit, veh, poids_str]
            _section_bc(call, so, ' | '.join(parts))
            _post_bon(call, so, ws, 'BC généré par le bouton « %s » (planning transport)' % recette)
        else:
            sans_bon.append('%s (%s)' % ((t['name'] or t['id']), so_nom))
        if recette == 'haims' and 'TRANSFERT' in nom_n:
            a_verifier.append('%s (%s) : transfert facturé à l heure — ajuster la quantité'
                              % ((t['name'] or '').strip()[:40], so_nom))
        if 'poids' in [l[1] for l in lignes] and not poids_t:
            a_verifier.append('%s (%s) : pas de poids sur le bon — quantité laissée à 1'
                              % ((t['name'] or '').strip()[:40], so_nom))
        faits.append(so_nom)
    return {'ok': 1, 'faits': len(faits), 'bons': faits[:100], 'deja': deja,
            'annulees': annulees, 'sans_bon': sans_bon[:40],
            'a_verifier': a_verifier[:40], 'futurs': futurs, 'non_faits': non_faits}
