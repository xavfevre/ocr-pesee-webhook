# -*- coding: utf-8 -*-
"""Pont-bascule -> Odoo : page web /bascule (Chrome, Web Serial) et ses services (Xavier, 08/10/2026).

La page (bascule_page.html) tourne dans Chrome sur le PC de caisse du site : elle lit l'indicateur par le câble USB-série
(Web Serial, protocole Bilanciai DD700 pour Chatel), gère la double pesée par immatriculation, imprime le ticket sur
l'imprimante Epson ePOS du site et enregistre chaque pesée dans Odoo (modèle manuel x_pesee, menu Logistiques >
Pesées pont-bascule) via ces services. Accès : ?site=<code>&k=<clé maquignon.bascule_key>.
Multi-sites : un bloc par site dans SITES (société, imprimante, en-tête du ticket, protocole, séquence).
"""
import json
import os
import re
import tempfile
import threading
import time
import xmlrpc.client
from datetime import datetime

from flask import Blueprint, Response, jsonify, request, send_from_directory

bp = Blueprint('bascule', __name__)
ICI = os.path.dirname(os.path.abspath(__file__))

SITES = {
    'chatel': {
        'nom': "Chatel'Granulats", 'company_id': 3, 'sequence': 'x_pesee.chatel',
        'imprimante': '192.168.1.20',
        'entete': ["CHATEL'GRANULATS", 'Le Pautron - 86100 Châtellerault', 'Tél. 05 49 90 57 62'],
        'instrument': 'Bilanciai DD700 (48 t, e = 20 kg)', 'protocole': 'bilanciai_dd700', 'bauds': 9600,
        'client_comptoir_id': 35137,   # « Comptoir Chatel Granulats » : client de passage pour les tickets de caisse sans fiche
        'caisse': True,                # point de vente Odoo sur le site : destination « ticket de caisse » possible
        # enregistreur Dahua XVR7104 (192.168.1.208) : voie 1 = dôme du portail (pont), voie 2 = caméra IP de la borne Easy Béton
        'cameras': ['Caméra du portail (pont)', 'Borne Easy Béton'],
        'cameras_urls': ['http://192.168.1.208/cgi-bin/snapshot.cgi?channel=1', 'http://192.168.1.208/cgi-bin/snapshot.cgi?channel=2'],
        'cameras_user': 'delphine',    # compte de l'enregistreur ; le mot de passe est demandé à l'installation sur le PC
    },
    'maquignon': {
        'nom': 'SARL MAQUIGNON', 'company_id': 1, 'sequence': 'x_pesee.maquignon',
        'imprimante': '',              # pas d'imprimante ePOS connue sur le pont d'Usseau (réglable par poste dans la page)
        'entete': ['SARL MAQUIGNON', '51 rue du Prieuré - 86230 Usseau', 'Tél. 05 49 02 72 63'],
        'instrument': 'Bilanciai D400 (48 t, e = 20 kg)', 'protocole': 'bilanciai_dd700', 'bauds': 9600,   # mêmes commandes XB/XN/XT/XZ que le DD700 (sonde du 21/10/2026)
        'caisse': False,               # pas de point de vente : bon de commande journalier ou pesée seule
        'cameras': ['Caméra du pont', 'Seconde caméra'],
        # articles proposés : vendables à la tonne, de la société ou communs, hors contributions (le point de vente ne sert pas de filtre ici)
        'produits_domaine': [['sale_ok', '=', True], ['type', '=', 'consu'], '|', ['uom_id.name', 'ilike', 'tonne'], ['uom_id.name', 'ilike', 'kg'], ['categ_id.name', 'not in', ['Contribution Energie', 'Eco Contribution']]],
    },
}

# produits proposés à la pesée : marchandises (pas de service) vendables, à la tonne ou au kg
PRODUITS_POIDS = [['sale_ok', '=', True], ['type', '=', 'consu'], '|', ['uom_id.name', 'ilike', 'tonne'], ['uom_id.name', 'ilike', 'kg']]

_CONN = {}
_LOCK = threading.Lock()
_CLE = {'val': '', 't': 0.0}


def _call(model, method, *params, **kw):
    """XML-RPC sur la base de production (identifiants du relais), connexion partagée sous verrou."""
    with _LOCK:
        if 'uid' not in _CONN:
            url, db, user, pwd = os.environ.get('ODOO_URL'), os.environ.get('ODOO_DB'), os.environ.get('ODOO_USER'), os.environ.get('ODOO_PASSWORD')
            uid = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common').authenticate(db, user, pwd, {})
            if not uid:
                raise ValueError('authentification Odoo refusée')
            _CONN.update(uid=uid, models=xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object'), db=db, pwd=pwd)
        try:
            return _CONN['models'].execute_kw(_CONN['db'], _CONN['uid'], _CONN['pwd'], model, method, list(params), kw)
        except xmlrpc.client.Fault as e:
            if 'cannot marshal None' in str(e):
                return None
            raise


def _ctx(site):
    return {'context': {'allowed_company_ids': [SITES[site]['company_id']], 'active_test': True}}


def _cle_ok():
    now = time.time()
    if now - _CLE['t'] > 600 or not _CLE['val']:
        try:
            _CLE['val'] = _call('ir.config_parameter', 'get_param', 'maquignon.bascule_key', '') or ''
        except Exception:  # noqa: BLE001
            pass
        _CLE['t'] = now
    k = request.args.get('k') or (request.get_json(silent=True) or {}).get('k') or ''
    return bool(_CLE['val']) and k == _CLE['val']


def _site():
    s = (request.args.get('site') or (request.get_json(silent=True) or {}).get('site') or '').lower()
    return s if s in SITES else None


def _garde():
    """None si l'accès est bon, sinon la réponse d'erreur."""
    if not _cle_ok():
        return jsonify({'error': 'clé invalide'}), 401
    if not _site():
        return jsonify({'error': 'site inconnu'}), 400
    return None


def _maintenant():
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')


CHAMPS = ['x_name', 'x_site', 'x_etat', 'x_sens', 'x_immat', 'x_client', 'x_partner_id', 'x_produit', 'x_product_id',
          'x_p1', 'x_p1_date', 'x_p2', 'x_p2_date', 'x_net', 'x_net_t', 'x_poste', 'x_imprime', 'x_note', 'x_manuel', 'x_tare_memo',
          'x_vehicule_id', 'x_vehicule_type', 'x_destination', 'x_sale_order_id', 'x_sale_line_id', 'create_date']


def _commande(site, pesee_id, destination, ajout_bc=False):
    """Après une pesée terminée : ligne de commande Odoo selon la destination.
    journalier = devis du jour du client sur ce site (créé s'il n'existe pas), une ligne par pesée, à confirmer/facturer
    par le bureau ; ticket = un devis par pesée à régler tout de suite en caisse (bouton Commandes du point de vente),
    client de passage du site si la pesée n'a pas de client Odoo. Renvoie un avertissement texte si rien n'a pu être fait."""
    if destination not in ('journalier', 'ticket'):
        return None
    p = _lire(site, [pesee_id])[0]
    if p['x_etat'] != 'terminee' or p['x_sale_order_id']:
        return None
    cfg = SITES[site]
    partner = p['x_partner_id'] or (cfg.get('client_comptoir_id') if destination == 'ticket' else None)
    if not partner:
        return "pesée enregistrée sans commande : choisir un client Odoo (liste déroulante) pour le bon de commande journalier"
    if not p['x_product_id']:
        return "pesée enregistrée sans commande : choisir un article Odoo dans la liste des produits"
    if not p['x_net_t']:
        return "pesée enregistrée sans commande : net nul"
    jour = datetime.utcnow().strftime('%Y-%m-%d')
    ctx = _ctx(site)
    if destination == 'journalier':
        origine = 'BASCULE-%s-%s' % (site.upper(), jour)
        # fonctionnement normal (Xavier, 22/10/2026) : la pesée s'ajoute au devis du jour, le bureau confirme et valide le BL ;
        # case « ajout sur le BC en cours » cochée : on s'ajoute aussi à un bon déjà confirmé (non verrouillé) et on valide le BL
        dom = [['partner_id', '=', partner], ['company_id', '=', cfg['company_id']], ['origin', '=', origine]]
        dom += [['state', 'in', ['draft', 'sent', 'sale']], ['locked', '=', False]] if ajout_bc else [['state', 'in', ['draft', 'sent']]]
        so = _call('sale.order', 'search', dom, limit=1, order='id desc', **ctx)
        so_id = so[0] if so else None
    else:
        origine = 'BASCULE-%s-TICKET' % site.upper()
        so_id = None
    if not so_id:
        vals = {'partner_id': partner, 'company_id': cfg['company_id'], 'origin': origine,
                'note': 'Pesées pont-bascule %s du %s' % (cfg['nom'], jour) if destination == 'journalier' else 'Pesée pont-bascule %s, à régler en caisse' % p['x_name']}
        if destination == 'ticket':
            vals['client_order_ref'] = p['x_name']
        so_id = _call('sale.order', 'create', vals, **ctx)
        so_id = so_id[0] if isinstance(so_id, list) else so_id
    prod = _call('product.product', 'read', [p['x_product_id']], ['display_name'], **ctx)[0]['display_name']
    libelle = '%s - Pesée %s - %s - %s' % (prod, p['x_name'], p['x_immat'] or 'sans immat.', (p['x_p2_date'] or p['x_p1_date'] or '')[11:16])
    line_id = _call('sale.order.line', 'create', {'order_id': so_id, 'product_id': p['x_product_id'], 'product_uom_qty': p['x_net_t'], 'name': libelle}, **ctx)
    line_id = line_id[0] if isinstance(line_id, list) else line_id
    _call('x_pesee', 'write', [pesee_id], {'x_destination': destination, 'x_sale_order_id': so_id, 'x_sale_line_id': line_id}, **ctx)
    if destination == 'journalier' and ajout_bc:
        # case cochée sur la page : commande confirmée et bon de livraison validé tout de suite (marchandise partie avec le camion)
        try:
            return _livrer(site, so_id)
        except Exception as e:  # noqa: BLE001
            return 'commande créée mais BL non validé (%s) : à valider dans Odoo' % str(e)[:120]
    return None


def _livrer(site, so_id):
    """Confirme la commande si elle est encore en devis, puis valide chaque bon de livraison ouvert avec les quantités
    commandées (= pesées). Renvoie un avertissement texte si un BL reste à traiter, sinon None."""
    ctx = _ctx(site)
    so = _call('sale.order', 'read', [so_id], ['state', 'picking_ids', 'name'], **ctx)[0]
    if so['state'] in ('draft', 'sent'):
        _call('sale.order', 'action_confirm', [so_id], **ctx)
        so = _call('sale.order', 'read', [so_id], ['state', 'picking_ids', 'name'], **ctx)[0]
    restes = []
    for p in _call('stock.picking', 'search_read', [['id', 'in', so['picking_ids'] or []], ['state', 'not in', ['done', 'cancel']]], fields=['name', 'state', 'move_ids'], **ctx):
        if p['state'] == 'draft':
            _call('stock.picking', 'action_confirm', [p['id']], **ctx)
        for mv in _call('stock.move', 'read', p['move_ids'], ['product_uom_qty', 'state'], **ctx):
            if mv['state'] not in ('done', 'cancel'):
                _call('stock.move', 'write', [mv['id']], {'quantity': mv['product_uom_qty'], 'picked': True}, **ctx)
        res = _call('stock.picking', 'button_validate', [p['id']], **ctx)
        if isinstance(res, dict) and res.get('res_model') == 'stock.backorder.confirmation':
            # reliquat proposé : on livre sans reliquat (tout est pesé)
            wiz = _call('stock.backorder.confirmation', 'create', {'pick_ids': [(4, p['id'])]}, context=dict(ctx['context'], button_validate_picking_ids=[p['id']]))
            wiz = wiz[0] if isinstance(wiz, list) else wiz
            _call('stock.backorder.confirmation', 'process_cancel_backorder', [wiz], context=dict(ctx['context'], button_validate_picking_ids=[p['id']]))
        etat = _call('stock.picking', 'read', [p['id']], ['state'], **ctx)[0]['state']
        if etat != 'done':
            restes.append('%s (%s)' % (p['name'], etat))
    return ('BL à valider dans Odoo : %s' % ', '.join(restes)) if restes else None
CHAMPS_V = ['x_name', 'x_type', 'x_fleet_id', 'x_tare', 'x_tare_date', 'x_client', 'x_partner_id', 'x_produit', 'x_product_id', 'x_site', 'x_note', 'write_date']


def _immat(s):
    """Immatriculation normalisée : majuscules, lettres et chiffres seulement (AB-123-CD -> AB123CD)."""
    return re.sub(r'[^A-Z0-9]', '', (s or '').upper())


def _parc(site, q):
    """Véhicules du parc Odoo (module Parc automobile) dont la plaque contient q : {immat normalisée: (id, nom)}."""
    rows = _call('fleet.vehicle', 'search_read', [['license_plate', '!=', False]], fields=['license_plate', 'name'], limit=400,
                 context={'active_test': True, 'allowed_company_ids': [1, 2, 3, 4, 13]})
    return {_immat(r['license_plate']): (r['id'], r['name']) for r in rows if q in _immat(r['license_plate'])}


def _vehicule(site, immat):
    n = _immat(immat)
    if not n:
        return None
    rows = _call('x_vehicule', 'search_read', [['x_name', '=', n]], fields=CHAMPS_V, limit=1, **_ctx(site))
    if not rows:
        return None
    v = rows[0]
    for f in ('x_partner_id', 'x_product_id', 'x_fleet_id'):
        v[f] = v[f][0] if v[f] else None
    return v


def _vehicule_auto(site, immat, vals_pesee, tare=None):
    """Toute immatriculation pesée entre dans le fichier « Véhicules (tares) » (Xavier, 22/10/2026) : fiche créée si
    besoin (type entreprise si la plaque est au parc), client / produit recopiés s'ils manquent, tare mise à jour
    quand un poids à vide vient d'être mesuré (vente : pesée 1, réception : pesée 2)."""
    n = _immat(immat)
    if not n:
        return None
    v = _vehicule(site, n)
    vals = {}
    if not v:
        parc = _parc(site, n).get(n)
        vals = {'x_name': n, 'x_site': site, 'x_type': 'entreprise' if parc else 'client', 'x_fleet_id': parc[0] if parc else False, 'x_tare': 0}
    for champ in ('x_client', 'x_partner_id', 'x_produit', 'x_product_id'):
        if vals_pesee.get(champ) and (not v or not v.get(champ)):
            vals[champ] = vals_pesee[champ]
    if tare and tare > 0:
        vals['x_tare'] = tare; vals['x_tare_date'] = _maintenant()
    if vals:
        if v:
            _call('x_vehicule', 'write', [v['id']], vals, **_ctx(site))
        else:
            _call('x_vehicule', 'create', vals, **_ctx(site))
    return _vehicule(site, n)


def _vehicule_json(r):
    return {'immat': r['x_name'], 'type': r['x_type'] or 'client', 'fleet_id': r['x_fleet_id'] and (r['x_fleet_id'][0] if isinstance(r['x_fleet_id'], list) else r['x_fleet_id']),
            'tare': r['x_tare'], 'tare_date': r['x_tare_date'], 'client': r['x_client'] or '',
            'partner_id': r['x_partner_id'] and (r['x_partner_id'][0] if isinstance(r['x_partner_id'], list) else r['x_partner_id']),
            'produit': r['x_produit'] or '', 'product_id': r['x_product_id'] and (r['x_product_id'][0] if isinstance(r['x_product_id'], list) else r['x_product_id'])}


@bp.route('/api/vehicules')
def api_vehicules():
    """Recherche par début d'immatriculation : véhicules connus (tare mémorisée) + véhicules du parc de l'entreprise."""
    g = _garde()
    if g:
        return g
    q = _immat(request.args.get('q'))
    if len(q) < 2:
        return jsonify([])
    rows = _call('x_vehicule', 'search_read', [['x_name', 'ilike', q]], fields=CHAMPS_V, limit=10, order='x_name', **_ctx(_site()))
    res = [_vehicule_json(r) for r in rows]
    connus = {r['immat'] for r in res}
    for n, (fid, nom) in _parc(_site(), q).items():
        if n not in connus:
            res.append({'immat': n, 'type': 'entreprise', 'fleet_id': fid, 'tare': 0, 'tare_date': None, 'client': '', 'partner_id': None, 'produit': '', 'product_id': None, 'parc': nom})
    return jsonify(res[:12])


@bp.route('/api/vehicule', methods=['POST'])
def api_vehicule():
    """Mémorise (ou met à jour) la tare d'un véhicule : {immat, tare, client, partner_id, produit, product_id, note}."""
    g = _garde()
    if g:
        return g
    site = _site(); d = request.get_json(silent=True) or {}
    n = _immat(d.get('immat'))
    try:
        tare = float(d.get('tare') or 0)
    except (TypeError, ValueError):
        tare = 0.0
    if not n or tare <= 0:
        return jsonify({'error': 'immatriculation et tare (> 0) obligatoires'}), 400
    vals = {'x_name': n, 'x_tare': tare, 'x_tare_date': _maintenant(), 'x_site': site}
    parc = _parc(site, n).get(n)
    typ = d.get('type') if d.get('type') in ('client', 'entreprise') else ('entreprise' if parc else 'client')
    vals['x_type'] = typ
    vals['x_fleet_id'] = (d.get('fleet_id') or (parc and parc[0]) or False) if typ == 'entreprise' else False
    for champ, cle in (('x_client', 'client'), ('x_produit', 'produit'), ('x_note', 'note')):
        if d.get(cle):
            vals[champ] = d[cle].strip()
    for champ, cle in (('x_partner_id', 'partner_id'), ('x_product_id', 'product_id')):
        if d.get(cle):
            vals[champ] = d[cle]
    v = _vehicule(site, n)
    if v:
        _call('x_vehicule', 'write', [v['id']], vals, **_ctx(site))
    else:
        _call('x_vehicule', 'create', vals, **_ctx(site))
    return jsonify({'vehicule': _vehicule(site, n)})


def _lire(site, ids):
    rows = _call('x_pesee', 'read', ids, CHAMPS, **_ctx(site)) if ids else []
    for r in rows:
        for f in ('x_partner_id', 'x_product_id'):
            r[f] = r[f][0] if r[f] else None
    return rows


@bp.route('/')
def page():
    return send_from_directory(ICI, 'bascule_page.html')


@bp.route('/outils/bascule_passerelle.ps1')
def outil_passerelle():
    """La passerelle à jour, téléchargée par l'installateur des caméras (et utilisable à la main)."""
    return send_from_directory(os.path.join(ICI, 'docs'), 'bascule_passerelle.ps1', mimetype='text/plain', max_age=0)


def _installeur_cameras(site, cfg, cle, relais):
    """Texte du .cmd d'installation des caméras (voir outil_cameras) ; isolé pour pouvoir le relire hors Flask.
    Tout est entre guillemets simples côté PowerShell pour ne pas se battre avec cmd ; %MDP% est rempli par cmd à l'installation."""
    urls = cfg.get('cameras_urls') or []
    user = cfg.get('cameras_user', 'admin')
    params = '-Site %s -Port "" -Cle "%s" -Camera "%s"' % (site, cle, urls[0]) + (' -Camera2 "%s"' % urls[1] if len(urls) > 1 else '') + ' -CamUser %s -CamPwd "%%MDP%%"' % user
    ps_dl = "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%s/bascule/outils/bascule_passerelle.ps1' -OutFile '%%DIR%%\\bascule_passerelle.ps1' -UseBasicParsing" % relais
    ps_rac = ("$ws = New-Object -ComObject WScript.Shell; $r = $ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Startup')) 'Cameras pont-bascule.lnk')); "
              "$r.TargetPath = '%%DIR%%\\cameras_%s.cmd'; $r.WindowStyle = 7; $r.Description = 'Cameras du pont-bascule vers la page'; $r.Save(); "
              "Get-CimInstance Win32_Process -Filter 'Name = ''powershell.exe''' | Where-Object { $_.CommandLine -like '*bascule_passerelle.ps1*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }") % site
    lignes = [
        '@echo off', 'setlocal',
        'set "DIR=%LOCALAPPDATA%\\Maquignon"', 'if not exist "%DIR%" mkdir "%DIR%"',
        'echo Installation des cameras du pont-bascule (site %s) sur ce PC.' % site,
        'echo Les images partent vers la page Pont-bascule ; la passerelle redemarre seule a chaque ouverture de session.', 'echo.',
        'set /p MDP=Mot de passe camera (compte %s) : ' % user,
        'powershell -NoProfile -ExecutionPolicy Bypass -Command "%s"' % ps_dl,
        'if errorlevel 1 ( echo Telechargement de la passerelle impossible : verifier internet. & pause & exit /b 1 )',
        '> "%%DIR%%\\cameras_%s.cmd" echo @echo off' % site,
        '>> "%%DIR%%\\cameras_%s.cmd" echo powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "%%DIR%%\\bascule_passerelle.ps1" %s' % (site, params),
        'powershell -NoProfile -ExecutionPolicy Bypass -Command "%s"' % ps_rac,
        'start "" /min "%%DIR%%\\cameras_%s.cmd"' % site,
        'echo.', 'echo Passerelle cameras lancee. Journal : %TEMP%\\bascule_passerelle.log', 'echo Dans 10 secondes, les deux vues apparaissent sur la page Pont-bascule (F5).', 'pause',
    ]
    return '\r\n'.join(lignes) + '\r\n'


@bp.route('/outils/cameras.cmd')
def outil_cameras():
    """Installateur des caméras pour le PC où la page est ouverte : site, clé et adresses des caméras préremplis, mot de passe demandé.
    Télécharge la passerelle sur le relais, écrit le lanceur dans %LOCALAPPDATA%\\Maquignon, démarrage automatique à l'ouverture de session, lance tout de suite."""
    g = _garde()
    if g:
        return g
    site = _site(); cfg = SITES[site]
    urls = cfg.get('cameras_urls') or []
    if not urls:
        return jsonify({'error': 'pas de caméra configurée pour ce site'}), 404
    cle = request.args.get('k'); relais = request.url_root.rstrip('/')
    if relais.startswith('http://') and 'localhost' not in relais:
        relais = 'https://' + relais[7:]
    corps = _installeur_cameras(site, cfg, cle, relais)
    return Response(corps.encode('cp1252', errors='replace'), mimetype='application/octet-stream',
                    headers={'Content-Disposition': 'attachment; filename=installer_cameras_%s.cmd' % site, 'Cache-Control': 'no-store'})


@bp.route('/manifest.webmanifest')
def manifest():
    """Application installable sur téléphone (« Ajouter à l'écran d'accueil ») : un raccourci par site, plein écran."""
    site = (request.args.get('site') or 'chatel').lower()
    nom = SITES.get(site, {}).get('nom', 'Pont-bascule')
    data = {'name': 'Pont-bascule %s' % nom, 'short_name': 'Pont-bascule', 'start_url': '/bascule/?site=%s' % site, 'scope': '/bascule/',
            'display': 'standalone', 'orientation': 'portrait', 'background_color': '#f8fafc', 'theme_color': '#1d4ed8', 'lang': 'fr',
            'icons': [{'src': '/bascule/icone.png?taille=192', 'sizes': '192x192', 'type': 'image/png'},
                      {'src': '/bascule/icone.png?taille=512', 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any maskable'}]}
    return Response(json.dumps(data, ensure_ascii=False), mimetype='application/manifest+json', headers={'Cache-Control': 'public, max-age=3600'})


@bp.route('/icone.png')
def icone():
    taille = '512' if request.args.get('taille') == '512' else '192'
    return send_from_directory(ICI, 'bascule_icone_%s.png' % taille, mimetype='image/png', max_age=86400)


@bp.route('/api/config')
def api_config():
    g = _garde()
    if g:
        return g
    site = _site(); cfg = SITES[site]
    # produits au poids : marchandises vendables à la tonne ou au kg (Xavier, 22/10/2026 : recherche plein texte, plus de liste
    # déroulante ni de condition « disponible en point de vente »)
    dom = cfg.get('produits_domaine') or PRODUITS_POIDS
    prods = _call('product.product', 'search_read', dom + ['|', ['company_id', '=', cfg['company_id']], ['company_id', '=', False]],
                  fields=['display_name', 'default_code', 'list_price', 'uom_id'], order='id', **_ctx(site))
    prods = sorted(({'id': p['id'], 'nom': p['display_name'], 'prix': p['list_price'], 'unite': p['uom_id'][1] if p['uom_id'] else ''} for p in prods),
                   key=lambda p: p['nom'].lower())   # display_name : variantes distinguées (0/20 Bleu…)
    return jsonify({'site': site, 'nom': cfg['nom'], 'imprimante': cfg['imprimante'], 'entete': cfg['entete'], 'instrument': cfg['instrument'],
                    'protocole': cfg['protocole'], 'bauds': cfg['bauds'], 'caisse': bool(cfg.get('caisse')), 'produits': prods, 'serveur': _maintenant(),
                    'cameras': cfg.get('cameras') or ['Caméra du pont', 'Seconde caméra'], 'cameras_installables': bool(cfg.get('cameras_urls'))})


@bp.route('/api/clients')
def api_clients():
    g = _garde()
    if g:
        return g
    q = (request.args.get('q') or '').strip()
    if len(q) < 2:
        return jsonify([])
    rows = _call('res.partner', 'search_read', ['|', ['name', 'ilike', q], ['ref', 'ilike', q]],
                 fields=['name', 'ref', 'city'], limit=12, order='name', **_ctx(_site()))
    return jsonify([{'id': r['id'], 'nom': r['name'], 'ref': r['ref'] or '', 'ville': r['city'] or ''} for r in rows])


@bp.route('/api/pesees')
def api_pesees():
    g = _garde()
    if g:
        return g
    site = _site()
    jour = datetime.utcnow().strftime('%Y-%m-%d 00:00:00')
    ouvertes = _call('x_pesee', 'search', [['x_site', '=', site], ['x_etat', '=', 'ouverte']], order='id desc', limit=100, **_ctx(site))
    du_jour = _call('x_pesee', 'search', [['x_site', '=', site], ['x_etat', '!=', 'ouverte'], ['create_date', '>=', jour]], order='id desc', limit=200, **_ctx(site))
    return jsonify({'ouvertes': _lire(site, ouvertes), 'jour': _lire(site, du_jour)})


@bp.route('/api/pesee', methods=['POST'])
def api_pesee():
    """action = p1 (nouvelle pesée, 1er passage) | p2 (2e passage sur une pesée ouverte) | simple (une seule pesée, net = poids)
    | annuler | imprime (marque le ticket imprimé) | note."""
    g = _garde()
    if g:
        return g
    site = _site(); d = request.get_json(silent=True) or {}
    action = d.get('action')
    try:
        poids = float(d.get('poids') or 0)
    except (TypeError, ValueError):
        poids = 0.0
    if action in ('p1', 'simple', 'tare'):
        if poids <= 0:
            return jsonify({'error': 'poids nul : attendre que la pesée soit stable'}), 400
        vals = {'x_site': site, 'x_company_id': SITES[site]['company_id'], 'x_sens': d.get('sens') or 'vente',
                'x_immat': (d.get('immat') or '').strip().upper(), 'x_client': (d.get('client') or '').strip(), 'x_partner_id': d.get('partner_id') or False,
                'x_produit': (d.get('produit') or '').strip(), 'x_product_id': d.get('product_id') or False,
                'x_poste': (d.get('poste') or '')[:60], 'x_note': d.get('note') or False, 'x_manuel': bool(d.get('manuel'))}
        v = _vehicule_auto(site, d.get('immat'), vals)      # fiche véhicule créée ou complétée automatiquement
        if v:
            vals.update(x_vehicule_id=v['id'], x_vehicule_type=v['x_type'] or 'client')
        elif vals['x_immat'] and _parc(site, _immat(vals['x_immat'])).get(_immat(vals['x_immat'])):
            vals['x_vehicule_type'] = 'entreprise'
        elif vals['x_immat']:
            vals['x_vehicule_type'] = 'client'
        if action == 'tare':
            # une seule pesée : la tare mémorisée du véhicule tient lieu de pesée 1
            if not v or not v['x_tare']:
                return jsonify({'error': 'aucune tare mémorisée pour ce véhicule'}), 400
            if poids <= v['x_tare']:
                return jsonify({'error': 'poids (%d kg) inférieur ou égal à la tare mémorisée (%d kg)' % (poids, v['x_tare'])}), 400
            net = round(poids - v['x_tare'], 0)
            vals.update(x_p1=v['x_tare'], x_p1_date=v['x_tare_date'] or _maintenant(), x_p2=poids, x_p2_date=_maintenant(),
                        x_net=net, x_net_t=round(net / 1000.0, 3), x_etat='terminee', x_tare_memo=True)
            if not vals['x_client'] and v['x_client']:
                vals['x_client'] = v['x_client']; vals['x_partner_id'] = v['x_partner_id'] or False
            if not vals['x_produit'] and v['x_produit']:
                vals['x_produit'] = v['x_produit']; vals['x_product_id'] = v['x_product_id'] or False
        elif action == 'simple':
            vals.update(x_p1=poids, x_p1_date=_maintenant(), x_etat='terminee', x_sens='simple', x_net=poids, x_net_t=round(poids / 1000.0, 3))
        else:
            vals.update(x_p1=poids, x_p1_date=_maintenant(), x_etat='ouverte')
        vals['x_name'] = _call('ir.sequence', 'next_by_code', SITES[site]['sequence'])
        rid = _call('x_pesee', 'create', vals, **_ctx(site))
        rid = rid[0] if isinstance(rid, list) else rid
        avert = _commande(site, rid, d.get('destination'), bool(d.get('ajout_bc'))) if action in ('tare', 'simple') else None
        return jsonify({'pesee': _lire(site, [rid])[0], 'avertissement': avert})
    rid = int(d.get('id') or 0)
    if not rid:
        return jsonify({'error': 'id manquant'}), 400
    if action == 'p2':
        if poids <= 0:
            return jsonify({'error': 'poids nul : attendre que la pesée soit stable'}), 400
        cur = _lire(site, [rid])[0]
        if cur['x_etat'] != 'ouverte':
            return jsonify({'error': 'cette pesée n est plus ouverte'}), 400
        net = round(abs(poids - cur['x_p1']), 0)
        vals = {'x_p2': poids, 'x_p2_date': _maintenant(), 'x_net': net, 'x_net_t': round(net / 1000.0, 3), 'x_etat': 'terminee'}
        if d.get('manuel'):
            vals['x_manuel'] = True
        for champ, cle in (('x_client', 'client'), ('x_produit', 'produit'), ('x_immat', 'immat')):
            if d.get(cle):
                vals[champ] = d[cle].strip().upper() if cle == 'immat' else d[cle].strip()
        for champ, cle in (('x_partner_id', 'partner_id'), ('x_product_id', 'product_id')):
            if d.get(cle):
                vals[champ] = d[cle]
        _call('x_pesee', 'write', [rid], vals, **_ctx(site))
        # poids à vide mesuré (vente : pesée 1, réception : pesée 2) -> tare du véhicule mise à jour dans le fichier
        try:
            vide = cur['x_p1'] if cur['x_sens'] == 'vente' else (poids if cur['x_sens'] == 'reception' else None)
            _vehicule_auto(site, vals.get('x_immat') or cur['x_immat'], dict(cur, **vals), tare=vide)
        except Exception:  # noqa: BLE001
            pass
        avert = _commande(site, rid, d.get('destination'), bool(d.get('ajout_bc')))
        return jsonify({'pesee': _lire(site, [rid])[0], 'avertissement': avert})
    elif action == 'commande':
        # commande créée après coup depuis la liste du jour (pesée terminée sans commande)
        avert = _commande(site, rid, d.get('destination'), bool(d.get('ajout_bc')))
        return jsonify({'pesee': _lire(site, [rid])[0], 'avertissement': avert})
    elif action == 'annuler':
        _call('x_pesee', 'write', [rid], {'x_etat': 'annulee'}, **_ctx(site))
    elif action == 'imprime':
        _call('x_pesee', 'write', [rid], {'x_imprime': True}, **_ctx(site))
    elif action == 'note':
        _call('x_pesee', 'write', [rid], {'x_note': d.get('note') or False}, **_ctx(site))
    else:
        return jsonify({'error': 'action inconnue'}), 400
    return jsonify({'pesee': _lire(site, [rid])[0]})


# ─── Passerelle de la cabine : poids et image de la caméra transmis par le PC relié à l'indicateur (21/10/2026) ───
# Le programme docs/bascule_passerelle.ps1 tourne sur le PC de la cabine (qui tient le port série) et envoie le poids chaque
# seconde ; la page ouverte sur n'importe quel autre PC (accueil) l'affiche comme si la bascule était branchée dessus.
# État conservé dans des fichiers du dossier temporaire : partagés entre les workers gunicorn, perdus au redéploiement (sans gravité).
FRAICHEUR_POIDS = 5      # secondes : au-delà, la cabine est considérée muette
FRAICHEUR_IMAGE = 120    # secondes : au-delà, plus d'image proposée


def _fichier(site, ext):
    return os.path.join(tempfile.gettempdir(), 'bascule_%s.%s' % (site, ext))


def _ecrire_atomique(chemin, data):
    tmp = '%s.%d.tmp' % (chemin, os.getpid())
    with open(tmp, 'wb') as f:
        f.write(data)
    os.replace(tmp, chemin)


@bp.route('/api/passerelle', methods=['POST'])
def api_passerelle():
    """{site, k, poids (kg ou null), stable, etat (lettres de l'indicateur), brut (ligne lue), erreur, poste}."""
    g = _garde()
    if g:
        return g
    site = _site(); d = request.get_json(silent=True) or {}
    try:
        poids = float(d['poids']) if d.get('poids') is not None else None
    except (TypeError, ValueError, KeyError):
        poids = None
    etat = {'poids': poids, 'stable': bool(d.get('stable')), 'etat': str(d.get('etat') or '')[:10], 'brut': str(d.get('brut') or '')[:40],
            'erreur': str(d.get('erreur') or '')[:200], 'poste': str(d.get('poste') or '')[:60], 't': time.time(), 'horodatage': _maintenant()}
    _ecrire_atomique(_fichier(site, 'json'), json.dumps(etat).encode('utf-8'))
    return jsonify({'ok': True, 'serveur': etat['horodatage']})


def _ext_image():
    """Deux caméras par site : n=1 (pont) -> .jpg, n=2 (seconde vue) -> .jpg2."""
    return 'jpg2' if (request.args.get('n') or '1') == '2' else 'jpg'


@bp.route('/api/passerelle/image', methods=['POST'])
def api_passerelle_image():
    """Image JPEG d'une caméra (?n=1 pont, ?n=2 seconde vue), corps brut (Content-Type image/jpeg), 2 Mo maximum."""
    g = _garde()
    if g:
        return g
    data = request.get_data()
    if not data or len(data) > 2_000_000 or data[:2] != b'\xff\xd8':
        return jsonify({'error': 'image JPEG attendue (2 Mo maximum)'}), 400
    _ecrire_atomique(_fichier(_site(), _ext_image()), data)
    return jsonify({'ok': True})


def _direct(site):
    try:
        with open(_fichier(site, 'json'), 'rb') as f:
            etat = json.loads(f.read().decode('utf-8'))
    except (OSError, ValueError):
        return None
    etat['age'] = round(time.time() - float(etat.get('t') or 0), 1)
    etat['connecte'] = etat['age'] < FRAICHEUR_POIDS and not etat.get('erreur') and etat.get('poids') is not None
    for cle, ext in (('image_age', 'jpg'), ('image2_age', 'jpg2')):
        try:
            etat[cle] = round(time.time() - os.path.getmtime(_fichier(site, ext)), 1)
        except OSError:
            etat[cle] = None
    return etat


@bp.route('/api/direct')
def api_direct():
    """Dernier poids reçu de la passerelle : {poids, stable, etat, erreur, poste, age (s), connecte, image_age}."""
    g = _garde()
    if g:
        return g
    etat = _direct(_site())
    return jsonify(etat or {'poids': None, 'stable': False, 'erreur': '', 'poste': '', 'age': None, 'connecte': False, 'image_age': None, 'jamais': True})


@bp.route('/api/camera')
def api_camera():
    """Dernière image d'une caméra (?n=1 pont, ?n=2 seconde vue), 204 s'il n'y en a pas de récente, 304 si inchangée (If-None-Match)."""
    g = _garde()
    if g:
        return g
    chemin = _fichier(_site(), _ext_image())
    try:
        mtime = os.path.getmtime(chemin)
        if time.time() - mtime > FRAICHEUR_IMAGE:
            return '', 204
        etag = '"%d"' % int(mtime * 1000)
        if request.headers.get('If-None-Match') == etag:
            return '', 304
        with open(chemin, 'rb') as f:
            data = f.read()
    except OSError:
        return '', 204
    return Response(data, mimetype='image/jpeg', headers={'Cache-Control': 'no-store', 'ETag': etag})
