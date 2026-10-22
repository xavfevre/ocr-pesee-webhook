# -*- coding: utf-8 -*-
"""Borne à béton EasyBéton (Distri Béton) <-> Odoo : page /borne et ses services (Xavier, 22/10/2026).

La borne (PC 192.168.1.200, serveur FTP FileZilla) écrit chaque soir à 20 h un CSV par prise de béton dans /Exports
(BLSnnnnn.csv) et relit le fichier clients /Imports/Contact (res.partner).csv à chaque modification (export Odoo standard).
Un agent PowerShell sur un PC du réseau (docs/borne_agent.ps1) fait la navette avec ce relais :
  - prises : les CSV sont déposés ici (api/depot) -> enregistrements x_borne_bon « à valider » ; Delphine les valide sur la
    page /borne (api/valider) -> commandes Odoo Distri Béton ; le fichier est déplacé dans /Exports/Sauv ;
  - clients : dès qu'un client Distri Béton change dans Odoo (api/etat), l'agent récupère le fichier complet (api/clients.csv,
    même format que l'export Odoo) et le dépose sur la borne, puis consigne le résultat (api/export-journal -> x_borne_export).
Accès : ?k=<clé maquignon.borne_key>. Modèles manuels x_borne_bon et x_borne_export (pa_test/borne_setup.py).
"""
import csv
import hashlib
import io
import json
import os
import re
import threading
import time
import xmlrpc.client
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import Blueprint, Response, jsonify, request, send_from_directory

bp = Blueprint('borne', __name__)
ICI = os.path.dirname(os.path.abspath(__file__))
PARIS = ZoneInfo('Europe/Paris')

BORNE = {
    'company_id': 2,                                  # SAS Distri Béton Vienne
    'nom': 'Distri Béton',
    'fichier_clients': 'Contact (res.partner).csv',   # nom attendu par la borne dans /Imports (modèle d'import calé sur l'export Odoo)
    'colonnes_clients': ['Référence', 'Nom', 'Société', 'Téléphone', 'E-mail', 'Rue', 'Rue 2', 'Code postal', 'Ville', 'Pays',
                         'Conditions de paiement du client', 'Type de société', 'Liste de prix/Nom de la liste de prix'],
    'clients_minimum': 100,       # garde-fou : jamais un fichier quasi vide (un fichier incomplet efface les clients de la borne)
    'baisse_maxi': 0.10,          # garde-fou : refus si la liste a perdu plus de 10 % de clients depuis le dernier dépôt
    'confirmer': True,            # commandes confirmées à la validation (la marchandise est partie)
    'champs_commande': {          # champs Studio de sale.order remplis à l'import (mappage historique de Delphine)
        'badge': 'x_studio_num_badge', 'badge_nom': 'x_studio_nom_badge', 'date': 'x_studio_date_de_distribution', 'chantier': 'x_studio_ref_chantier'},
}

COLONNES_BON = ['CARDCOD', 'CARDNOM', 'CARDIMAT', 'CLINOM', 'CLIPRO', 'CLICOD', 'RECNOM', 'RECCOD', 'RECTAG', 'ORDVOL', 'ORDHT', 'ORDREP1',
                'ORDREP2', 'ORDREMISE1', 'ORDREMISE2', 'ORDTHT', 'ORDTVA1', 'ORDTVA2', 'ORDTTC', 'ORDCOD', 'ORDDAT', 'ORDREF1',
                'ORDREF1FILTRE', 'ORDCODFILTRE']
CHAMPS_BON = ['x_name', 'x_fichier', 'x_date', 'x_clicod', 'x_clinom', 'x_clipro', 'x_partner_id', 'x_reccod', 'x_recnom', 'x_product_id',
              'x_volume', 'x_ht', 'x_tht', 'x_ttc', 'x_badge', 'x_badge_nom', 'x_immat', 'x_chantier', 'x_etat', 'x_anomalie',
              'x_sale_order_id', 'x_valide_par', 'x_valide_le', 'create_date']
CHAMPS_EXPORT = ['x_name', 'x_date', 'x_resultat', 'x_nb_clients', 'x_nb_nouveaux', 'x_nouveaux', 'x_sha', 'x_detail', 'x_poste']

_CONN = {}
_LOCK = threading.Lock()
_CLE = {'val': '', 't': 0.0}
_AGENT = {'poste': '', 'vu': 0.0, 'ecrit': 0.0}
_TYPES = {}


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


def _ctx(**extra):
    c = {'allowed_company_ids': [BORNE['company_id']], 'active_test': True}
    c.update(extra)
    return {'context': c}


def _cle_ok():
    now = time.time()
    if now - _CLE['t'] > 600 or not _CLE['val']:
        try:
            _CLE['val'] = _call('ir.config_parameter', 'get_param', 'maquignon.borne_key', '') or ''
        except Exception:  # noqa: BLE001
            pass
        _CLE['t'] = now
    k = request.args.get('k') or (request.get_json(silent=True) or {}).get('k') or ''
    return bool(_CLE['val']) and k == _CLE['val']


def _garde():
    return None if _cle_ok() else (jsonify({'error': 'clé invalide'}), 401)


def _maintenant():
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')


def _un(v):
    """id d'un many2one lu par XML-RPC ([id, nom] -> id)."""
    return v[0] if isinstance(v, list) else (v or None)


def _nom(v):
    return v[1] if isinstance(v, list) else ''


def _types(model):
    """Types des champs d'un modèle (cache) : sert à écrire une date ou un datetime selon la définition Studio."""
    if model not in _TYPES:
        _TYPES[model] = {k: v.get('type') for k, v in _call(model, 'fields_get', attributes=['type']).items()}
    return _TYPES[model]


def _agent_vu(poste):
    """Dernier passage de l'agent : mémoire du relais + paramètre Odoo (toutes les 5 min) pour survivre aux redémarrages."""
    _AGENT['poste'], _AGENT['vu'] = (poste or _AGENT['poste'] or '?'), time.time()
    if time.time() - _AGENT['ecrit'] > 300:
        _AGENT['ecrit'] = time.time()
        try:
            _call('ir.config_parameter', 'set_param', 'maquignon.borne_agent', json.dumps({'poste': _AGENT['poste'], 'vu': _maintenant()}))
        except Exception:  # noqa: BLE001
            pass


def _agent_etat():
    if _AGENT['vu']:
        return {'poste': _AGENT['poste'], 'vu': datetime.utcfromtimestamp(_AGENT['vu']).strftime('%Y-%m-%d %H:%M:%S'), 'depuis_s': int(time.time() - _AGENT['vu'])}
    try:
        d = json.loads(_call('ir.config_parameter', 'get_param', 'maquignon.borne_agent', '') or '{}')
    except Exception:  # noqa: BLE001
        d = {}
    if d.get('vu'):
        depuis = (datetime.utcnow() - datetime.strptime(d['vu'], '%Y-%m-%d %H:%M:%S')).total_seconds()
        return {'poste': d.get('poste', '?'), 'vu': d['vu'], 'depuis_s': int(depuis)}
    return {'poste': '', 'vu': '', 'depuis_s': None}


# ─── CLIENTS -> BORNE ────────────────────────────────────────────────────────
DOMAINE_CLIENTS = ['&', ['ref', '!=', False], ['ref', '!=', ''], '|', ['company_id', '=', BORNE['company_id']], ['ref', '=like', 'DIS%']]


def _clients_signature():
    """Signature rapide de la base clients (nombre + dernière modification) : l'agent la compare à chaque passage."""
    nb = _call('res.partner', 'search_count', DOMAINE_CLIENTS, **_ctx())
    der = _call('res.partner', 'search_read', DOMAINE_CLIENTS, fields=['write_date'], limit=1, order='write_date desc', **_ctx())
    maj = der[0]['write_date'] if der else ''
    return {'nb': nb, 'maj': maj, 'sig': '%d-%s' % (nb, maj)}


def _clients_lignes():
    """Clients Distri Béton au format de l'export Odoo (une liste par ligne, dans l'ordre des colonnes)."""
    rows = _call('res.partner', 'search_read', DOMAINE_CLIENTS,
                 fields=['ref', 'name', 'company_id', 'phone', 'email', 'street', 'street2', 'zip', 'city', 'country_id',
                         'property_payment_term_id', 'company_type', 'property_product_pricelist', 'write_date', 'create_date'],
                 order='name', **_ctx())
    # nom de la liste de prix sans la devise (« Tarif Pro 2026 », pas « Tarif Pro 2026 (EUR) ») : comme l'export Odoo
    pl_ids = list({_un(r['property_product_pricelist']) for r in rows if r['property_product_pricelist']})
    pl = {x['id']: x['name'] for x in _call('product.pricelist', 'read', pl_ids, ['name'], **_ctx())} if pl_ids else {}
    lignes = []
    for r in sorted(rows, key=lambda r: (r['name'] or '').lower()):
        lignes.append([r['ref'] or '', r['name'] or '', _nom(r['company_id']), r['phone'] or '', r['email'] or '', r['street'] or '',
                       r['street2'] or '', r['zip'] or '', r['city'] or '', _nom(r['country_id']), _nom(r['property_payment_term_id']),
                       'Société' if r['company_type'] == 'company' else 'Particulier', pl.get(_un(r['property_product_pricelist']), '')])
    return lignes, rows


def _clients_csv(lignes):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL, lineterminator='\r\n')
    w.writerow(BORNE['colonnes_clients'])
    for l in lignes:
        w.writerow(l)
    return buf.getvalue().encode('utf-8')


def _dernier_export(resultats=('depose',)):
    rows = _call('x_borne_export', 'search_read', [['x_resultat', 'in', list(resultats)]], fields=CHAMPS_EXPORT, limit=1, order='x_date desc', **_ctx())
    return rows[0] if rows else None


def _controles(lignes, forcer=False):
    """Garde-fous avant dépôt : codes uniques, fichier complet. Renvoie la liste des problèmes bloquants."""
    pb = []
    vus, doublons = {}, set()
    for l in lignes:
        if l[0] in vus:
            doublons.add(l[0])
        vus[l[0]] = l[1]
    if doublons:
        pb.append('codes en double : ' + ', '.join(sorted(doublons)))
    if len(lignes) < BORNE['clients_minimum']:
        pb.append('seulement %d clients (minimum %d)' % (len(lignes), BORNE['clients_minimum']))
    if not forcer:
        der = _dernier_export()
        if der and der['x_nb_clients'] and len(lignes) < der['x_nb_clients'] * (1 - BORNE['baisse_maxi']):
            pb.append('la liste est passée de %d à %d clients : vérifier, puis forcer le dépôt depuis la page' % (der['x_nb_clients'], len(lignes)))
    return pb


def _nouveaux_depuis(rows, depuis):
    """Clients créés ou modifiés depuis la date (UTC) du dernier dépôt."""
    if not depuis:
        return []
    return sorted(('%s %s' % (r['ref'], r['name']) for r in rows if (r['write_date'] or '') > depuis), key=str.lower)


@bp.route('/')
def page():
    return send_from_directory(ICI, 'borne_page.html')


@bp.route('/api/etat')
def api_etat():
    """Pour l'agent (toutes les minutes) et la page : signature des clients, nombre de prises à valider, dernier export."""
    g = _garde()
    if g:
        return g
    if request.args.get('agent'):
        _agent_vu(request.args.get('poste'))
    sig = _clients_signature()
    der = _dernier_export()
    a_valider = _call('x_borne_bon', 'search_count', [['x_etat', '=', 'a_valider']], **_ctx())
    return jsonify({'clients': sig, 'a_valider': a_valider, 'agent': _agent_etat(), 'serveur': _maintenant(), 'forcer': _forcer_lu(),
                    'dernier_export': {'date': der['x_date'], 'nb': der['x_nb_clients'], 'sha': der['x_sha']} if der else None})


def _forcer_lu():
    try:
        return (_call('ir.config_parameter', 'get_param', 'maquignon.borne_forcer', '') or '') == '1'
    except Exception:  # noqa: BLE001
        return False


@bp.route('/api/forcer', methods=['POST'])
def api_forcer():
    """Depuis la page : le prochain passage de l'agent dépose le fichier même si un garde-fou le bloque (drapeau levé une fois)."""
    g = _garde()
    if g:
        return g
    _call('ir.config_parameter', 'set_param', 'maquignon.borne_forcer', '1')
    return jsonify({'ok': True})


@bp.route('/api/clients.csv')
def api_clients_csv():
    """Le fichier clients complet, format export Odoo. 409 + motifs si un garde-fou bloque (sauf ?forcer=1)."""
    g = _garde()
    if g:
        return g
    lignes, rows = _clients_lignes()
    pb = _controles(lignes, forcer=request.args.get('forcer') == '1')
    if pb:
        return jsonify({'error': 'dépôt refusé', 'motifs': pb, 'nb': len(lignes)}), 409
    data = _clients_csv(lignes)
    der = _dernier_export()
    nouveaux = _nouveaux_depuis(rows, der['x_date'] if der else '')
    sig = _clients_signature()
    r = Response(data, mimetype='text/csv')
    r.headers['X-Nb-Clients'] = str(len(lignes)); r.headers['X-Sha'] = hashlib.sha256(data).hexdigest()
    r.headers['X-Signature'] = sig['sig']; r.headers['X-Nb-Nouveaux'] = str(len(nouveaux))
    r.headers['X-Nouveaux'] = json.dumps(nouveaux[:40], ensure_ascii=True); r.headers['X-Fichier'] = BORNE['fichier_clients']
    return r


@bp.route('/api/clients/apercu')
def api_clients_apercu():
    """Pour la page : ce qui partira au prochain export (clients modifiés depuis le dernier dépôt) et les garde-fous."""
    g = _garde()
    if g:
        return g
    lignes, rows = _clients_lignes()
    der = _dernier_export()
    sans_dis = sorted(l[1] for l in lignes if not l[0].startswith('DIS'))
    return jsonify({'nb': len(lignes), 'problemes': _controles(lignes), 'nouveaux': _nouveaux_depuis(rows, der['x_date'] if der else ''),
                    'hors_dis': sans_dis[:20], 'signature': _clients_signature()['sig'], 'dernier': der})


@bp.route('/api/export-journal', methods=['POST'])
def api_export_journal():
    """L'agent consigne chaque tentative de dépôt du fichier clients : déposé / inchangé / refusé / erreur."""
    g = _garde()
    if g:
        return g
    d = request.get_json(silent=True) or {}
    res = d.get('resultat') if d.get('resultat') in ('depose', 'inchange', 'refuse', 'erreur') else 'erreur'
    if res == 'inchange' and not d.get('consigner'):
        _agent_vu(d.get('poste'))
        return jsonify({'ok': True, 'consigne': False})
    vals = {'x_name': datetime.now(PARIS).strftime('%d/%m/%Y %H:%M'), 'x_date': _maintenant(), 'x_resultat': res,
            'x_nb_clients': int(d.get('nb_clients') or 0), 'x_nb_nouveaux': int(d.get('nb_nouveaux') or 0),
            'x_nouveaux': '\n'.join(d.get('nouveaux') or []) or False, 'x_sha': (d.get('sha') or '')[:64] or False,
            'x_detail': (d.get('detail') or '')[:2000] or False, 'x_poste': (d.get('poste') or '')[:60] or False}
    rid = _call('x_borne_export', 'create', vals, **_ctx())
    if res == 'depose':
        _call('ir.config_parameter', 'set_param', 'maquignon.borne_forcer', '0')
    _agent_vu(d.get('poste'))
    return jsonify({'ok': True, 'id': _un(rid) if isinstance(rid, list) else rid})


@bp.route('/api/exports')
def api_exports():
    g = _garde()
    if g:
        return g
    rows = _call('x_borne_export', 'search_read', [], fields=CHAMPS_EXPORT, limit=int(request.args.get('n') or 40), order='x_date desc', **_ctx())
    return jsonify(rows)


# ─── PRISES DE BÉTON -> ODOO ─────────────────────────────────────────────────
def _nombre(s):
    try:
        return float(str(s or '0').replace(',', '.').strip() or 0)
    except ValueError:
        return 0.0


def _date_borne(s):
    """« 21/10/2026 15:26:44 » (heure de Paris) -> datetime UTC Odoo, ou None."""
    for fmt in ('%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%d/%m/%Y'):
        try:
            loc = datetime.strptime((s or '').strip(), fmt).replace(tzinfo=PARIS)
            return loc.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue
    return None


def _parser_bon(nom, contenu):
    """Un CSV de la borne (en-tête + 1 ligne, séparateur ;) -> dict des colonnes, ou lève ValueError."""
    txt = contenu.lstrip('﻿')
    rows = list(csv.DictReader(io.StringIO(txt), delimiter=';'))
    if len(rows) != 1:
        raise ValueError('%s : %d ligne(s) de données au lieu de 1' % (nom, len(rows)))
    r = {k.strip(): (v or '').strip() for k, v in rows[0].items() if k}
    manquantes = [c for c in ('ORDCOD', 'CLICOD', 'RECCOD', 'ORDVOL', 'ORDDAT') if c not in r]
    if manquantes:
        raise ValueError('%s : colonnes absentes %s' % (nom, manquantes))
    return r


def _trouver_partner(clicod):
    if not clicod:
        return None
    ids = _call('res.partner', 'search', [['ref', '=', clicod]], limit=2, **_ctx())
    return ids[0] if len(ids) == 1 else None


_PRODUITS = {'t': 0.0, 'par_code': {}, 'par_nom': {}, 'par_id': {}}


def _produits():
    """Articles vendables de Distri Béton, indexés par référence interne, par nom et par id (cache 10 min)."""
    if time.time() - _PRODUITS['t'] > 600:
        rows = _call('product.product', 'search_read', [['sale_ok', '=', True], '|', ['company_id', '=', BORNE['company_id']], ['company_id', '=', False]],
                     fields=['default_code', 'name', 'display_name', 'list_price', 'uom_id'], **_ctx())
        _PRODUITS['par_code'] = {(r['default_code'] or '').strip().upper(): r for r in rows if r['default_code']}
        _PRODUITS['par_nom'] = {re.sub(r'\s+', ' ', (r['name'] or '').strip().upper()): r for r in rows}
        _PRODUITS['par_id'] = {r['id']: r for r in rows}
        _PRODUITS['t'] = time.time()
    return _PRODUITS


def _trouver_produit(reccod, recnom):
    p = _produits()
    r = p['par_code'].get((reccod or '').strip().upper())
    if not r:
        r = p['par_nom'].get(re.sub(r'\s+', ' ', (recnom or '').strip().upper()))
    return r


def _bon_vals(nom, r):
    """Valeurs x_borne_bon à partir des colonnes du CSV, avec client / article résolus et anomalies détectées."""
    partner = _trouver_partner(r.get('CLICOD'))
    produit = _trouver_produit(r.get('RECCOD'), r.get('RECNOM'))
    anomalies = []
    if not partner:
        anomalies.append('client %s introuvable dans Odoo (code DIS)' % (r.get('CLICOD') or '?'))
    if not produit:
        anomalies.append('article %s / %s introuvable dans Odoo' % (r.get('RECCOD') or '?', r.get('RECNOM') or '?'))
    date = _date_borne(r.get('ORDDAT', ''))
    if not date:
        anomalies.append('date illisible : %s' % r.get('ORDDAT'))
    if _nombre(r.get('ORDVOL')) <= 0:
        anomalies.append('volume nul')
    etat = 'a_valider'
    ordcod = r.get('ORDCOD') or re.sub(r'^BL|\.csv$', '', nom, flags=re.I)
    deja = _call('sale.order', 'search_read', [['company_id', '=', BORNE['company_id']], ['origin', '=', 'Borne ' + ordcod]], fields=['name'], limit=1, **_ctx())
    if deja:
        etat = 'doublon'; anomalies.append('déjà importé : commande %s' % deja[0]['name'])
    elif partner and date:
        # même client, même date de distribution à la minute : import manuel antérieur probable
        champ = BORNE['champs_commande']['date']
        try:
            proche = _call('sale.order', 'search_read', [['company_id', '=', BORNE['company_id']], ['partner_id', '=', partner], [champ, '>=', date[:16] + ':00'], [champ, '<=', date[:16] + ':59']],
                           fields=['name'], limit=1, **_ctx())
            if proche:
                anomalies.append('doublon probable : commande %s du même client à la même heure' % proche[0]['name'])
        except xmlrpc.client.Fault:
            pass
    return {'x_name': ordcod, 'x_fichier': nom, 'x_date': date or False, 'x_clicod': r.get('CLICOD') or False, 'x_clinom': re.sub(r'\s+', ' ', r.get('CLINOM') or '') or False,
            'x_clipro': (r.get('CLIPRO') or '').lower() == 'true', 'x_partner_id': partner or False, 'x_reccod': r.get('RECCOD') or False,
            'x_recnom': r.get('RECNOM') or False, 'x_product_id': produit['id'] if produit else False, 'x_volume': _nombre(r.get('ORDVOL')),
            'x_ht': _nombre(r.get('ORDHT')), 'x_tht': _nombre(r.get('ORDTHT')), 'x_ttc': _nombre(r.get('ORDTTC')), 'x_badge': r.get('CARDCOD') or False,
            'x_badge_nom': r.get('CARDNOM') or False, 'x_immat': r.get('CARDIMAT') or False, 'x_chantier': r.get('ORDREF1') or False,
            'x_etat': etat, 'x_anomalie': ' ; '.join(anomalies) or False,
            'x_csv': ';'.join(COLONNES_BON) + '\n' + ';'.join(r.get(c, '') for c in COLONNES_BON)}


@bp.route('/api/depot', methods=['POST'])
def api_depot():
    """L'agent dépose les CSV lus dans /Exports : {fichiers: [{nom, contenu}], poste}. Réponse par fichier :
    cree | deja | erreur: ... (l'agent n'archive dans Sauv que cree et deja)."""
    g = _garde()
    if g:
        return g
    d = request.get_json(silent=True) or {}
    _agent_vu(d.get('poste'))
    res = {}
    for f in (d.get('fichiers') or [])[:200]:
        nom = os.path.basename(f.get('nom') or '')
        try:
            r = _parser_bon(nom, f.get('contenu') or '')
            ordcod = r.get('ORDCOD') or re.sub(r'^BL|\.csv$', '', nom, flags=re.I)
            if _call('x_borne_bon', 'search_count', [['x_name', '=', ordcod]], **_ctx()):
                res[nom] = 'deja'; continue
            _call('x_borne_bon', 'create', _bon_vals(nom, r), **_ctx())
            res[nom] = 'cree'
        except Exception as e:  # noqa: BLE001
            res[nom] = 'erreur: %s' % str(e)[:200]
    return jsonify({'resultats': res, 'serveur': _maintenant()})


def _lire_bons(dom, limit=500, order='x_date desc'):
    rows = _call('x_borne_bon', 'search_read', dom, fields=CHAMPS_BON, limit=limit, order=order, **_ctx())
    for r in rows:
        r['partner'] = _nom(r['x_partner_id']); r['x_partner_id'] = _un(r['x_partner_id'])
        r['produit'] = _nom(r['x_product_id']); r['x_product_id'] = _un(r['x_product_id'])
        r['commande'] = _nom(r['x_sale_order_id']); r['x_sale_order_id'] = _un(r['x_sale_order_id'])
        p = _produits()['par_id'].get(r['x_product_id']) if r['x_product_id'] else None
        r['prix_odoo'] = p['list_price'] if p else None
    return rows


@bp.route('/api/bons')
def api_bons():
    """Prises à valider (+ ce mois-ci et le mois dernier d'importées / rejetées pour l'historique)."""
    g = _garde()
    if g:
        return g
    a_valider = _lire_bons([['x_etat', 'in', ['a_valider', 'doublon']]], order='x_date asc')
    mois = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    depuis = (mois.replace(month=mois.month - 1) if mois.month > 1 else mois.replace(year=mois.year - 1, month=12)).strftime('%Y-%m-%d %H:%M:%S')
    historique = _lire_bons([['x_etat', 'in', ['importe', 'rejete']], ['x_valide_le', '>=', depuis]], limit=400, order='x_valide_le desc')
    return jsonify({'a_valider': a_valider, 'historique': historique, 'serveur': _maintenant(), 'odoo': (os.environ.get('ODOO_URL') or '').rstrip('/')})


def _creer_commande(b):
    """Commande Distri Béton à partir d'une prise validée : client, article, volume, prix de la borne s'il est renseigné
    (particulier payé à la borne), badge / chantier / date de distribution dans les champs Studio, confirmée si réglé ainsi."""
    if not b['x_partner_id'] or not b['x_product_id']:
        raise ValueError('client ou article non résolu')
    cf = BORNE['champs_commande']; types = _types('sale.order')
    vals = {'partner_id': b['x_partner_id'], 'company_id': BORNE['company_id'], 'origin': 'Borne ' + b['x_name'],
            'date_order': b['x_date'] or _maintenant(), 'client_order_ref': b['x_chantier'] or False,
            'note': 'Prise de béton à la borne, bon %s du %s%s' % (b['x_name'], b['x_date'] or '?', (' — ' + b['x_anomalie']) if b.get('x_anomalie') else '')}
    for cle, champ in (('x_badge', cf['badge']), ('x_badge_nom', cf['badge_nom']), ('x_chantier', cf['chantier'])):
        if champ in types:
            vals[champ] = b.get(cle) or False
    if cf['date'] in types and b['x_date']:
        if types[cf['date']] == 'datetime':
            vals[cf['date']] = b['x_date']
        else:
            vals[cf['date']] = datetime.strptime(b['x_date'], '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).astimezone(PARIS).strftime('%Y-%m-%d')
    so = _call('sale.order', 'create', vals, **_ctx())
    so = _un(so) if isinstance(so, list) else so
    ligne = {'order_id': so, 'product_id': b['x_product_id'], 'product_uom_qty': b['x_volume']}
    if b['x_ht'] and b['x_ht'] > 0:
        ligne['price_unit'] = b['x_ht']
    _call('sale.order.line', 'create', ligne, **_ctx())
    if BORNE['confirmer']:
        _call('sale.order', 'action_confirm', [so], **_ctx())
    return so


@bp.route('/api/valider', methods=['POST'])
def api_valider():
    """Delphine valide une sélection : une commande Odoo par prise. {ids: [...], qui: 'Delphine'}."""
    g = _garde()
    if g:
        return g
    d = request.get_json(silent=True) or {}
    ids = [int(i) for i in (d.get('ids') or [])][:300]
    qui = (d.get('qui') or '')[:60]
    res = []
    for b in _lire_bons([['id', 'in', ids], ['x_etat', 'in', ['a_valider', 'doublon']]], limit=300, order='x_date asc'):
        try:
            so = _creer_commande(b)
            nom = _call('sale.order', 'read', [so], ['name'], **_ctx())[0]['name']
            _call('x_borne_bon', 'write', [b['id']], {'x_etat': 'importe', 'x_sale_order_id': so, 'x_valide_par': qui or False, 'x_valide_le': _maintenant()}, **_ctx())
            res.append({'id': b['id'], 'bon': b['x_name'], 'ok': True, 'commande': nom, 'commande_id': so})
        except Exception as e:  # noqa: BLE001
            res.append({'id': b['id'], 'bon': b['x_name'], 'ok': False, 'erreur': str(e)[:300]})
    return jsonify({'resultats': res, 'serveur': _maintenant()})


@bp.route('/api/rejeter', methods=['POST'])
def api_rejeter():
    g = _garde()
    if g:
        return g
    d = request.get_json(silent=True) or {}
    ids = [int(i) for i in (d.get('ids') or [])][:300]
    motif = (d.get('motif') or 'rejeté sur la page borne')[:200]
    bons = _call('x_borne_bon', 'search', [['id', 'in', ids], ['x_etat', 'in', ['a_valider', 'doublon']]], **_ctx())
    if bons:
        _call('x_borne_bon', 'write', bons, {'x_etat': 'rejete', 'x_anomalie': motif, 'x_valide_par': (d.get('qui') or '')[:60] or False, 'x_valide_le': _maintenant()}, **_ctx())
    return jsonify({'rejetes': len(bons)})


@bp.route('/api/corriger', methods=['POST'])
def api_corriger():
    """Correction avant validation : client (partner_id) ou article (product_id) d'une prise."""
    g = _garde()
    if g:
        return g
    d = request.get_json(silent=True) or {}
    vals = {}
    if d.get('partner_id'):
        vals['x_partner_id'] = int(d['partner_id'])
    if d.get('product_id'):
        vals['x_product_id'] = int(d['product_id'])
    if not vals or not d.get('id'):
        return jsonify({'error': 'rien à corriger'}), 400
    b = _call('x_borne_bon', 'read', [int(d['id'])], ['x_anomalie', 'x_etat'], **_ctx())[0]
    if b['x_etat'] not in ('a_valider', 'doublon'):
        return jsonify({'error': 'prise déjà traitée'}), 400
    reste = [a for a in (b['x_anomalie'] or '').split(' ; ') if a and not (('client' in a and 'x_partner_id' in vals) or ('article' in a and 'x_product_id' in vals))]
    vals['x_anomalie'] = ' ; '.join(reste) or False
    _call('x_borne_bon', 'write', [int(d['id'])], vals, **_ctx())
    return jsonify({'ok': True, 'bon': _lire_bons([['id', '=', int(d['id'])]])[0]})


@bp.route('/api/recherche')
def api_recherche():
    """Clients (q) ou articles (q, quoi=article) de Distri Béton pour corriger une prise."""
    g = _garde()
    if g:
        return g
    q = (request.args.get('q') or '').strip()
    if len(q) < 2:
        return jsonify([])
    if request.args.get('quoi') == 'article':
        out = []
        for r in _produits()['par_id'].values():
            if all(m in (r['display_name'] + ' ' + (r['default_code'] or '')).lower() for m in q.lower().split()):
                out.append({'id': r['id'], 'nom': r['display_name'], 'code': r['default_code'] or '', 'prix': r['list_price']})
        return jsonify(sorted(out, key=lambda x: x['nom'].lower())[:15])
    rows = _call('res.partner', 'search_read', ['|', ['name', 'ilike', q], ['ref', 'ilike', q]], fields=['name', 'ref', 'city'], limit=15, order='name', **_ctx())
    return jsonify([{'id': r['id'], 'nom': r['name'], 'ref': r['ref'] or '', 'ville': r['city'] or ''} for r in rows])
