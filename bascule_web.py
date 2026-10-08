# -*- coding: utf-8 -*-
"""Pont-bascule -> Odoo : page web /bascule (Chrome, Web Serial) et ses services (Xavier, 08/10/2026).

La page (bascule_page.html) tourne dans Chrome sur le PC de caisse du site : elle lit l'indicateur par le câble USB-série
(Web Serial, protocole Bilanciai DD700 pour Chatel), gère la double pesée par immatriculation, imprime le ticket sur
l'imprimante Epson ePOS du site et enregistre chaque pesée dans Odoo (modèle manuel x_pesee, menu Logistiques >
Pesées pont-bascule) via ces services. Accès : ?site=<code>&k=<clé maquignon.bascule_key>.
Multi-sites : un bloc par site dans SITES (société, imprimante, en-tête du ticket, protocole, séquence).
"""
import os
import re
import threading
import time
import xmlrpc.client
from datetime import datetime

from flask import Blueprint, jsonify, request, send_from_directory

bp = Blueprint('bascule', __name__)
ICI = os.path.dirname(os.path.abspath(__file__))

SITES = {
    'chatel': {
        'nom': "Chatel'Granulats", 'company_id': 3, 'sequence': 'x_pesee.chatel',
        'imprimante': '192.168.1.20',
        'entete': ["CHATEL'GRANULATS", 'Le Pautron - 86100 Châtellerault', 'Tél. 05 49 90 57 62'],
        'instrument': 'Bilanciai DD700 - pont 48 t - échelon 20 kg', 'protocole': 'bilanciai_dd700', 'bauds': 9600,
    },
}

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
          'x_p1', 'x_p1_date', 'x_p2', 'x_p2_date', 'x_net', 'x_net_t', 'x_poste', 'x_imprime', 'x_note', 'create_date']


def _lire(site, ids):
    rows = _call('x_pesee', 'read', ids, CHAMPS, **_ctx(site)) if ids else []
    for r in rows:
        for f in ('x_partner_id', 'x_product_id'):
            r[f] = r[f][0] if r[f] else None
    return rows


@bp.route('/')
def page():
    return send_from_directory(ICI, 'bascule_page.html')


@bp.route('/api/config')
def api_config():
    g = _garde()
    if g:
        return g
    site = _site(); cfg = SITES[site]
    prods = _call('product.product', 'search_read', [['available_in_pos', '=', True], ['sale_ok', '=', True], ['uom_id.name', 'ilike', 'tonne'],
                                                     '|', ['company_id', '=', cfg['company_id']], ['company_id', '=', False]],
                  fields=['name', 'default_code', 'list_price'], order='id', **_ctx(site))
    prods = sorted(({'id': p['id'], 'nom': p['name'], 'prix': p['list_price']} for p in prods), key=lambda p: p['nom'].lower())
    return jsonify({'site': site, 'nom': cfg['nom'], 'imprimante': cfg['imprimante'], 'entete': cfg['entete'], 'instrument': cfg['instrument'],
                    'protocole': cfg['protocole'], 'bauds': cfg['bauds'], 'produits': prods, 'serveur': _maintenant()})


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
    if action in ('p1', 'simple'):
        if poids <= 0:
            return jsonify({'error': 'poids nul : attendre que la pesée soit stable'}), 400
        numero = _call('ir.sequence', 'next_by_code', SITES[site]['sequence'])
        vals = {'x_name': numero, 'x_site': site, 'x_company_id': SITES[site]['company_id'], 'x_sens': d.get('sens') or 'vente',
                'x_immat': (d.get('immat') or '').strip().upper(), 'x_client': (d.get('client') or '').strip(), 'x_partner_id': d.get('partner_id') or False,
                'x_produit': (d.get('produit') or '').strip(), 'x_product_id': d.get('product_id') or False,
                'x_p1': poids, 'x_p1_date': _maintenant(), 'x_poste': (d.get('poste') or '')[:60], 'x_note': d.get('note') or False}
        if action == 'simple':
            vals.update(x_etat='terminee', x_sens='simple', x_net=poids, x_net_t=round(poids / 1000.0, 3))
        else:
            vals.update(x_etat='ouverte')
        rid = _call('x_pesee', 'create', vals, **_ctx(site))
        rid = rid[0] if isinstance(rid, list) else rid
        return jsonify({'pesee': _lire(site, [rid])[0]})
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
        for champ, cle in (('x_client', 'client'), ('x_produit', 'produit'), ('x_immat', 'immat')):
            if d.get(cle):
                vals[champ] = d[cle].strip().upper() if cle == 'immat' else d[cle].strip()
        for champ, cle in (('x_partner_id', 'partner_id'), ('x_product_id', 'product_id')):
            if d.get(cle):
                vals[champ] = d[cle]
        _call('x_pesee', 'write', [rid], vals, **_ctx(site))
    elif action == 'annuler':
        _call('x_pesee', 'write', [rid], {'x_etat': 'annulee'}, **_ctx(site))
    elif action == 'imprime':
        _call('x_pesee', 'write', [rid], {'x_imprime': True}, **_ctx(site))
    elif action == 'note':
        _call('x_pesee', 'write', [rid], {'x_note': d.get('note') or False}, **_ctx(site))
    else:
        return jsonify({'error': 'action inconnue'}), 400
    return jsonify({'pesee': _lire(site, [rid])[0]})
