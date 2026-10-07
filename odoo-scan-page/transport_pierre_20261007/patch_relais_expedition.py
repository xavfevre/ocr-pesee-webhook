# -*- coding: utf-8 -*-
"""Relais Render : action 2104 « Expédition » (départ des palettes au scan du bon de colisage).
Insère le bloc dans web_actions.py (avant la section EPI 2110), l'ajoute au dispatcher `executer` et à la liste
WEB_ACTIONS_AUTORISEES d'app.py.   python patch_relais_expedition.py"""
import io, os, sys, ast
sys.stdout.reconfigure(encoding='utf-8')
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
lire = lambda p: io.open(p, encoding='utf-8', newline='').read()
ecrire = lambda p, s: io.open(p, 'w', encoding='utf-8', newline='').write(s)

BLOC = r'''
# ─── 2104 · Expédition : départ des palettes au scan du bon de colisage (page /expedition) ─────────────────────
# Xavier, 07/10/2026 : le chargeur choisit le mode (nos camions / transporteur extérieur / enlèvement client),
# scanne les bons de colisage (code-barre PACK…), valide le départ. Palettes : statut, mode, transporteur, camion,
# chauffeur, date, chargé par, n° de chargement. Par commande : note dans le fil, tâche « Commande Pierres » en
# « Expédié » quand tout est parti, mail au bureau avec la liste de chargement (/expedition/liste?lot=…).
EXP_CAT_TRANSPORTEUR = 13
EXP_PROJET_PIERRE = 13
EXP_CHAMPS = COLIS_CHAMPS + ['x_commande_id', 'x_studio_client', 'x_exp_statut', 'x_exp_mode', 'x_exp_transporteur_id',
                             'x_exp_camion', 'x_exp_chauffeur', 'x_exp_date', 'x_exp_par_id', 'x_exp_lot', 'x_exp_lettre',
                             'x_studio_tche_commande_pierre']
EXP_PARTIS = ('chargee', 'enlevee', 'livree')


def _exp_maintenant():
    """Heure de Paris (n° de chargement, affichage) et heure UTC pour Odoo."""
    import datetime as _dt
    utc = _dt.datetime.utcnow().replace(microsecond=0)
    try:
        from zoneinfo import ZoneInfo
        local = utc.replace(tzinfo=_dt.timezone.utc).astimezone(ZoneInfo('Europe/Paris')).replace(tzinfo=None)
    except Exception:  # noqa: BLE001
        local = utc + _dt.timedelta(hours=2)
    return local, utc


def _exp_lire(call, code='', colis_id=0):
    if colis_id:
        rows = call('stock.package', 'search_read', [['id', '=', int(colis_id)]], fields=EXP_CHAMPS, limit=1)
    else:
        nom = (code or '').strip()
        if nom.isdigit():
            nom = 'PACK%07d' % int(nom)
        rows = call('stock.package', 'search_read', [['name', '=ilike', nom]], fields=EXP_CHAMPS, limit=1) if nom else []
    return rows[0] if rows else None


def _exp_adresse(call, partner_id):
    if not partner_id:
        return ''
    pa = call('res.partner', 'read', [partner_id], fields=['name', 'street', 'street2', 'zip', 'city'])[0]
    return ', '.join(t for t in [pa['name'], pa['street'], pa['street2'], ' '.join(t2 for t2 in [pa['zip'], pa['city']] if t2)] if t)


def _exp_palette(call, colis):
    """Fiche palette pour l'écran : contenu, commande, client, adresse, mode prévu au devis, état d'expédition."""
    items = _scan_items(call, colis)
    so = None
    if colis.get('x_commande_id'):
        so = call('sale.order', 'read', [colis['x_commande_id'][0]],
                  fields=['name', 'partner_id', 'partner_shipping_id', 'x_mode_transport', 'x_transporteur_id', 'state'])[0]
    qui = colis['x_exp_transporteur_id'][1] if colis.get('x_exp_transporteur_id') else (colis.get('x_exp_camion') or colis.get('x_exp_chauffeur') or '')
    return {'id': colis['id'], 'name': colis['name'], 'zone': colis['x_studio_zone'] or '',
            'cloturee': 1 if colis['x_studio_cloturee'] else 0, 'ton': round(colis['x_studio_tonnage'] or 0),
            'cub': round(colis['x_studio_cubage'] or 0, 3), 'n': len(items),
            'contenu': ', '.join(i['name'] + ((' x%d' % i['qte']) if i.get('kind') == 'line' and i.get('qte') else '') for i in items[:15]),
            'commande': so['name'] if so else '', 'commande_id': so['id'] if so else 0,
            'client': (so['partner_id'][1] if so else (colis.get('x_studio_client') or '')) or '',
            'adresse': _exp_adresse(call, so['partner_shipping_id'][0]) if so and so['partner_shipping_id'] else '',
            'mode_devis': (so.get('x_mode_transport') or '') if so else '',
            'transporteur_devis_id': so['x_transporteur_id'][0] if so and so.get('x_transporteur_id') else 0,
            'transporteur_devis': so['x_transporteur_id'][1] if so and so.get('x_transporteur_id') else '',
            'statut': colis.get('x_exp_statut') or 'stock', 'exp_date': (colis.get('x_exp_date') or '')[:16],
            'exp_lot': colis.get('x_exp_lot') or '', 'exp_qui': qui,
            'tache_id': colis['x_studio_tche_commande_pierre'][0] if colis.get('x_studio_tche_commande_pierre') else 0,
            'op_nom': colis['x_operateur_id'][1] if colis.get('x_operateur_id') else ''}


def _exp_controle(p):
    if not p['cloturee']:
        raise WebErreur("⚠️ %s n'est pas clôturée : clôturez-la (poste de scan ou tablette) avant de l'expédier." % p['name'])
    if p['statut'] in EXP_PARTIS:
        raise WebErreur('⛔ %s est déjà partie le %s (%s, chargement %s).' % (p['name'], p['exp_date'] or '?', p['exp_qui'] or '?', p['exp_lot'] or '?'))
    if not p['n']:
        raise WebErreur('⚠️ %s est vide : rien à expédier.' % p['name'])


def _exp_lots(call, jours=3):
    import datetime as _dt
    depuis = (_dt.datetime.utcnow() - _dt.timedelta(days=int(jours or 3))).strftime('%Y-%m-%d 00:00:00')
    rows = call('stock.package', 'search_read', [['x_exp_lot', '!=', False], ['x_exp_date', '>=', depuis]],
                fields=EXP_CHAMPS, order='x_exp_date desc, name')
    lots = {}
    for c in rows:
        l = lots.setdefault(c['x_exp_lot'], {'lot': c['x_exp_lot'], 'date': (c['x_exp_date'] or '')[:16], 'mode': c.get('x_exp_mode') or '',
                                              'qui': (c['x_exp_transporteur_id'][1] if c.get('x_exp_transporteur_id') else (c.get('x_exp_camion') or c.get('x_exp_chauffeur') or '')),
                                              'statut': c.get('x_exp_statut') or '', 'n': 0, 'ton': 0, 'palettes': [], 'clients': set()})
        l['n'] += 1; l['ton'] += round(c['x_studio_tonnage'] or 0); l['palettes'].append({'id': c['id'], 'name': c['name']})
        if c.get('x_studio_client'):
            l['clients'].add(c['x_studio_client'])
    out = []
    for l in lots.values():
        l['clients'] = ', '.join(sorted(l['clients'])); out.append(l)
    return {'lots': out}


def _exp_valider(call, ctx):
    ids = [int(i) for i in (ctx.get('palettes') or []) if int(i)]
    if not ids:
        raise WebErreur('Scannez au moins une palette.')
    mexp = (ctx.get('exp_mode') or '').strip()
    if mexp not in ('camions', 'exterieur', 'client'):
        raise WebErreur('Choisissez le mode : nos camions, transporteur extérieur ou enlèvement par le client.')
    tr_id = int(ctx.get('transporteur_id') or 0)
    camion = (ctx.get('camion') or '').strip()[:80]
    chauffeur = (ctx.get('chauffeur') or '').strip()[:80]
    par = int(ctx.get('charge_par') or 0)
    lettre = (ctx.get('lettre') or '').strip()[:80]
    if mexp == 'exterieur' and not tr_id:
        raise WebErreur('Indiquez le transporteur.')
    if mexp == 'camions' and not camion:
        raise WebErreur('Indiquez le camion.')
    if mexp == 'client' and not chauffeur:
        raise WebErreur("Indiquez le nom de la personne qui enlève la marchandise.")
    palettes = []
    for i in ids:
        colis = _exp_lire(call, colis_id=i)
        if not colis:
            raise WebErreur('Palette introuvable (%s).' % i)
        p = _exp_palette(call, colis); _exp_controle(p); palettes.append(p)
    local, utc = _exp_maintenant()
    lot = local.strftime('CHG-%Y%m%d-%H%M')
    tr_nom = call('res.partner', 'read', [tr_id], fields=['name'])[0]['name'] if tr_id else ''
    par_nom = call('hr.employee', 'read', [par], fields=['name'])[0]['name'] if par else ''
    qui = {'camions': 'nos camions (%s%s)' % (camion, (', ' + chauffeur) if chauffeur else ''),
           'exterieur': 'transporteur %s%s' % (tr_nom, (' (' + camion + ')') if camion else ''),
           'client': 'enlèvement par le client (%s%s)' % (chauffeur, (', ' + camion) if camion else '')}[mexp]
    statut = 'enlevee' if mexp == 'client' else 'chargee'
    call('stock.package', 'write', ids, {'x_exp_statut': statut, 'x_exp_mode': mexp, 'x_exp_transporteur_id': tr_id or False,
                                         'x_exp_camion': camion, 'x_exp_chauffeur': chauffeur, 'x_exp_date': utc.strftime('%Y-%m-%d %H:%M:%S'),
                                         'x_exp_par_id': par or False, 'x_exp_lot': lot, 'x_exp_lettre': lettre})
    # par commande : note dans le fil, tâche Commande Pierres
    par_cde = {}
    for p in palettes:
        par_cde.setdefault(p['commande_id'], []).append(p)
    stage_exp = call('project.task.type', 'search', [['name', '=', 'Expédié'], ['project_ids', 'in', [EXP_PROJET_PIERRE]]], limit=1)
    details = []
    for so_id, grp in par_cde.items():
        noms = ', '.join(p['name'] for p in grp); ton = sum(p['ton'] for p in grp)
        if not so_id:
            details.append(('(sans commande)', grp[0]['client'], noms, ton, '')); continue
        so = call('sale.order', 'read', [so_id], fields=['name'])[0]
        reste_of = call('mrp.production', 'search_count', [['origin', '=', so['name']], ['state', 'not in', ['done', 'cancel']]])
        reste_pal = call('stock.package', 'search_count', [['x_commande_id', '=', so_id], ['x_studio_cloturee', '=', True], '|', ['x_exp_statut', '=', False], ['x_exp_statut', 'not in', list(EXP_PARTIS)]])
        complet = (reste_of == 0 and reste_pal == 0)
        etat = 'commande entièrement expédiée' if complet else ('expédition partielle : %d OF en fabrication, %d palette(s) encore en stock' % (reste_of, reste_pal))
        _note(call, 'sale.order', so_id, '🚚 Départ %s%s : %s (%d kg) — %s%s — chargé par %s. %s.' % (
            lot, (' / ' + lettre) if lettre else '', noms, ton, qui, (', ' + grp[0]['adresse']) if grp[0]['adresse'] else '', par_nom or '?', etat))
        tache = next((p['tache_id'] for p in grp if p['tache_id']), 0)
        if tache:
            if complet and stage_exp:
                _sur(lambda: call('project.task', 'write', [tache], {'stage_id': stage_exp[0]}))
            _note(call, 'project.task', tache, '🚚 %s : %s partie(s) — %s (%s)' % (lot, noms, qui, etat))
        details.append((so['name'], grp[0]['client'], noms, ton, etat))
    # mail au bureau
    dest = _param(call, 'maquignon.palettes_alerte_email', '')
    if dest and not int(ctx.get('sans_mail') or 0):
        lignes = ''.join('<tr><td>%s</td><td>%s</td><td>%s</td><td style="text-align:right">%d kg</td><td>%s</td></tr>' % d for d in details)
        corps = ('<p>Départ enregistré le %s — <b>%s</b> — chargé par %s.</p>'
                 '<table border="1" cellpadding="4" style="border-collapse:collapse"><tr><th>Commande</th><th>Client</th><th>Palettes</th><th>Poids</th><th>État</th></tr>%s</table>'
                 '<p><a href="https://maquignon.odoo.com/expedition/liste?lot=%s">Liste de chargement %s</a></p>'
                 % (local.strftime('%d/%m/%Y %H:%M'), qui, par_nom or '?', lignes, lot, lot))
        try:
            _mail_bureau(call, 'Départ palettes %s : %s' % (lot, ', '.join(sorted({p['client'] for p in palettes if p['client']})) or '?'), dest, corps)
        except Exception:  # noqa: BLE001
            pass
    ton_tot = sum(p['ton'] for p in palettes); cub_tot = round(sum(p['cub'] for p in palettes), 3)
    return {'ok': 1, 'lot': lot, 'n': len(palettes), 'ton': ton_tot, 'cub': cub_tot, 'liste_url': '/expedition/liste?lot=%s' % lot,
            'msg': '🚚 Départ enregistré : %d palette(s), %d kg — chargement %s (%s)' % (len(palettes), ton_tot, lot, qui)}


def _exp_annuler(call, ctx):
    colis = _exp_lire(call, colis_id=int(ctx.get('palette_id') or 0))
    if not colis:
        raise WebErreur('Palette introuvable.')
    if (colis.get('x_exp_statut') or '') not in ('chargee', 'enlevee'):
        raise WebErreur("%s n'est pas en cours d'expédition (statut : %s)." % (colis['name'], colis.get('x_exp_statut') or 'en stock'))
    lot = colis.get('x_exp_lot') or ''
    call('stock.package', 'write', [colis['id']], {'x_exp_statut': False, 'x_exp_mode': False, 'x_exp_transporteur_id': False, 'x_exp_camion': '',
                                                   'x_exp_chauffeur': '', 'x_exp_date': False, 'x_exp_par_id': False, 'x_exp_lot': '', 'x_exp_lettre': ''})
    if colis.get('x_commande_id'):
        _note(call, 'sale.order', colis['x_commande_id'][0], '↩️ Départ annulé pour %s (chargement %s) : la palette est de nouveau en stock.' % (colis['name'], lot))
    return {'ok': 1, 'msg': '↩️ %s remise en stock (chargement %s annulé pour cette palette)' % (colis['name'], lot)}


def _expedition(call, ctx):
    mode = (ctx.get('mode') or 'scanner').strip()
    if mode == 'scanner':
        code = (ctx.get('code') or '').strip()
        if not code:
            raise WebErreur('⚠️ Rien à scanner')
        colis = _exp_lire(call, code)
        if not colis:
            raise WebErreur('❌ Palette inconnue : %s' % code)
        p = _exp_palette(call, colis); _exp_controle(p)
        return p
    if mode == 'valider':
        return _exp_valider(call, ctx)
    if mode == 'annuler':
        return _exp_annuler(call, ctx)
    if mode == 'lots':
        return _exp_lots(call, ctx.get('jours') or 3)
    raise WebErreur('Mode inconnu : %s' % mode)

'''

p = os.path.join(R, 'web_actions.py'); s = lire(p)
if '_expedition(' in s:
    print('web_actions.py : déjà patché')
else:
    anchor = "\n# ─── 2110 · 2111 · 2112 · EPI"
    assert s.count(anchor) == 1, 'ancre EPI introuvable'
    s = s.replace(anchor, BLOC + anchor, 1)
    old = "            2101: _palettiser, 2102: _scan, 2103: _alerte_palettes,\n"
    assert s.count(old) == 1
    s = s.replace(old, "            2101: _palettiser, 2102: _scan, 2103: _alerte_palettes, 2104: _expedition,\n", 1)
    ast.parse(s); ecrire(p, s); print('web_actions.py : action 2104 ajoutée (syntaxe ok)')
p = os.path.join(R, 'app.py'); s = lire(p)
if '2104,' in s:
    print('app.py : déjà patché')
else:
    old = "    2103,  # alerte hebdo palettes (bureau) — envoi manuel possible\n"
    assert s.count(old) == 1
    s = s.replace(old, old + "    2104,  # expédition : départ des palettes au scan du bon de colisage (page /expedition)\n", 1)
    ast.parse(s); ecrire(p, s); print('app.py : 2104 autorisée')
