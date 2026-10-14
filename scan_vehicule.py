# -*- coding: utf-8 -*-
"""Scanner -> fiche véhicule Odoo : page web /scan-vehicule et ses services (Xavier, 14/10/2026).

Principe : Isabelle scanne avec le Brother DS-740D (iPrint&Scan enregistre un PDF dans un dossier du PC) ; un petit
veilleur PowerShell sur son PC (odoo-scan-page/scan_vehicule_20261014/poste/) envoie chaque nouveau fichier ici
(api/upload). Le relais l'attache au véhicule « cible » du poste, c'est-à-dire celui affiché sur la page
/scan-vehicule ouverte depuis la fiche véhicule (action « Scanner un document ») : pièce jointe nommée
« <Type>_<immat>_<date>.pdf » + note dans le fil du véhicule ; le module Documents (dossier Fleet) la reprend
automatiquement. Sans cible fraîche, le fichier est gardé « à classer » (pièce jointe fleet.vehicle sans res_id)
et la page propose de le classer. Accès : ?veh=<id>&k=<clé maquignon.scan_key>.
"""
import base64
import json
import os
import re
import threading
import time
import xmlrpc.client
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, send_from_directory

bp = Blueprint('scan_vehicule', __name__)
ICI = os.path.dirname(os.path.abspath(__file__))
ODOO_WEB = 'https://maquignon.odoo.com'
MODELE = 'fleet.vehicle'
CIBLE_VALIDE_S = 180               # la page ouverte se signale toutes les 20 s ; 3 min sans signe de vie = plus de cible (page fermée)
PREFIXE_ATTENTE = 'A CLASSER - '
MARQUE = 'Scan Odoo'              # début du champ description des pièces jointes créées ici (= « ajouté par le scanner »)
TYPES = {                          # code -> libellé (préfixe du nom de fichier)
    'cg': 'Carte grise', 'ass': 'Assurance', 'ct': 'Contrôle technique', 'fac': 'Facture',
    'ent': 'Entretien', 'doc': 'Document',
}
MIMES = {'.pdf': 'application/pdf', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.tif': 'image/tiff', '.tiff': 'image/tiff'}

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


CTX = {'context': {'allowed_company_ids': [1, 3, 4], 'active_test': False}}


def _cle_ok():
    now = time.time()
    if now - _CLE['t'] > 600 or not _CLE['val']:
        try:
            _CLE['val'] = _call('ir.config_parameter', 'get_param', 'maquignon.scan_key', '') or ''
        except Exception:  # noqa: BLE001
            pass
        _CLE['t'] = now
    k = request.args.get('k') or (request.get_json(silent=True) or {}).get('k') or ''
    return bool(_CLE['val']) and k == _CLE['val']


def _poste(src=None):
    p = (src or request.args.get('poste') or (request.get_json(silent=True) or {}).get('poste') or '').strip().lower()
    return re.sub(r'[^a-z0-9_-]', '', p)[:30] or 'poste'


RE_PLAQUE = re.compile(r'^([A-Z]{2}-?\d{3}-?[A-Z]{2}|\d{1,4}[\s-]?[A-Z]{1,3}[\s-]?\d{2})$')   # SIV AA-123-AA ou ancien 1234-AB-86


def _libelle(nom, plaque):
    """Ce qui identifie le véhicule : la plaque si c'en est une, sinon le modèle (les engins ont souvent l'année en guise
    de plaque : « HITACHI/MINI PELLE ZX50U-2/2008 » -> « MINI PELLE ZX50U-2 »)."""
    p = (plaque or '').strip().upper()
    if RE_PLAQUE.match(p):
        return p
    parts = [s.strip() for s in (nom or '').split('/') if s.strip()]
    return parts[1] if len(parts) >= 3 else (parts[0] if parts else p or 'vehicule')


def _vehicule(vid):
    v = _call(MODELE, 'read', [vid], ['name', 'license_plate', 'driver_id', 'company_id', 'model_id', 'active'], **CTX)
    if not v:
        return None
    v = v[0]
    return {'id': v['id'], 'nom': v['name'], 'immat': v['license_plate'] or '', 'libelle': _libelle(v['name'], v['license_plate']),
            'chauffeur': v['driver_id'] and v['driver_id'][1] or '',
            'societe': v['company_id'] and v['company_id'][1] or '', 'modele': v['model_id'] and v['model_id'][1] or '', 'actif': v['active']}


def _pieces(vid):
    rows = _call('ir.attachment', 'search_read', [['res_model', '=', MODELE], ['res_id', '=', vid]],
                 fields=['name', 'create_date', 'file_size', 'mimetype', 'description'], order='create_date desc', limit=30, **CTX)
    recent = (datetime.utcnow() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    return [{'id': r['id'], 'nom': r['name'], 'date': r['create_date'], 'taille': r['file_size'], 'mime': r['mimetype'],
             'url': f"{ODOO_WEB}/web/content/{r['id']}",
             'scan': bool((r['description'] or '').startswith(MARQUE) and r['create_date'] >= recent)} for r in rows]


def _attente():
    rows = _call('ir.attachment', 'search_read', [['res_model', '=', MODELE], ['res_id', '=', 0], ['name', 'like', PREFIXE_ATTENTE + '%']],
                 fields=['name', 'create_date', 'file_size'], order='create_date desc', limit=20, **CTX)
    return [{'id': r['id'], 'nom': r['name'], 'date': r['create_date'], 'taille': r['file_size'], 'url': f"{ODOO_WEB}/web/content/{r['id']}"} for r in rows]


def _cible_lire(poste):
    raw = _call('ir.config_parameter', 'get_param', f'maquignon.scan_cible_{poste}', '') or ''
    try:
        c = json.loads(raw)
    except ValueError:
        return None
    if not c.get('veh') or time.time() - float(c.get('t', 0)) > CIBLE_VALIDE_S:
        return None
    return c


def _nom_fichier(type_code, veh, nom_origine):
    ext = os.path.splitext(nom_origine or '')[1].lower() or '.pdf'
    if ext not in MIMES:
        ext = '.pdf'
    immat = re.sub(r'[\\/:*?"<>|]+', '-', veh.get('libelle') or 'vehicule')
    return f"{TYPES.get(type_code, 'Document')}_{immat}_{datetime.now().strftime('%d.%m.%Y')}{ext}", MIMES[ext]


def _attacher(vid, type_code, nom_origine, data_b64, poste, mime=None):
    """Crée la pièce jointe sur le véhicule (Documents > Fleet la reprend) et une note dans son fil."""
    veh = _vehicule(vid)
    if not veh:
        raise ValueError('véhicule introuvable')
    nom, mime_ext = _nom_fichier(type_code, veh, nom_origine)
    att = _call('ir.attachment', 'create', [{'name': nom, 'res_model': MODELE, 'res_id': vid, 'datas': data_b64, 'mimetype': mime or mime_ext,
                                            'description': f"{MARQUE} · poste {poste} · {TYPES.get(type_code, 'Document')} · {datetime.now().strftime('%d/%m/%Y %H:%M')}"}], **CTX)
    att = att[0] if isinstance(att, list) else att
    try:
        _call(MODELE, 'message_post', [vid], body=f"📎 {TYPES.get(type_code, 'Document')} scanné (poste {poste})", attachment_ids=[att],
              message_type='comment', subtype_xmlid='mail.mt_note', **CTX)
    except Exception:  # noqa: BLE001  (la pièce jointe est déjà là ; la note est un plus)
        pass
    return {'id': att, 'nom': nom, 'veh': veh}


@bp.route('/')
def page():
    return send_from_directory(ICI, 'scan_vehicule_page.html')


POSTE_DIR = os.path.join(ICI, 'odoo-scan-page', 'scan_vehicule_20261014', 'poste')
POSTE_FICHIERS = ('installer.ps1', 'scan_odoo_veilleur.ps1')


@bp.route('/poste/<nom>')
def poste_fichier(nom):
    """Fichiers d'installation du veilleur (PowerShell) à télécharger sur le PC qui scanne ; pas de secret dedans."""
    if nom not in POSTE_FICHIERS:
        return jsonify({'error': 'fichier inconnu'}), 404
    return send_from_directory(POSTE_DIR, nom, mimetype='text/plain; charset=utf-8', as_attachment=True)


@bp.route('/api/vehicules')
def vehicules():
    if not _cle_ok():
        return jsonify({'error': 'clé invalide'}), 401
    q = (request.args.get('q') or '').strip()
    if len(q) < 2:
        return jsonify([])
    dom = ['|', '|', ['license_plate', 'ilike', q], ['name', 'ilike', q], ['driver_id.name', 'ilike', q]]
    rows = _call(MODELE, 'search_read', dom, fields=['name', 'license_plate', 'driver_id', 'company_id'], limit=15, order='name',
                 context={'allowed_company_ids': [1, 3, 4], 'active_test': True})
    return jsonify([{'id': r['id'], 'nom': r['name'], 'immat': r['license_plate'] or '', 'libelle': _libelle(r['name'], r['license_plate']),
                     'chauffeur': r['driver_id'] and r['driver_id'][1] or '', 'societe': r['company_id'] and r['company_id'][1] or ''} for r in rows])


@bp.route('/api/etat')
def etat():
    """Véhicule + ses pièces jointes + documents en attente de classement + cible courante du poste."""
    if not _cle_ok():
        return jsonify({'error': 'clé invalide'}), 401
    try:
        vid = int(request.args.get('veh') or 0)
    except ValueError:
        vid = 0
    veh = _vehicule(vid) if vid else None
    if vid and not veh:
        return jsonify({'error': 'véhicule introuvable'}), 404
    return jsonify({'vehicule': veh, 'pieces': _pieces(vid) if vid else [], 'attente': _attente(), 'types': TYPES,
                    'cible': _cible_lire(_poste())})


@bp.route('/api/cible', methods=['POST'])
def cible():
    """La page signale le véhicule affiché (et le type de document choisi) : c'est là que les scans iront."""
    if not _cle_ok():
        return jsonify({'error': 'clé invalide'}), 401
    d = request.get_json(silent=True) or {}
    poste = _poste(d.get('poste'))
    try:
        vid = int(d.get('veh') or 0)
    except ValueError:
        vid = 0
    if not vid:
        _call('ir.config_parameter', 'set_param', f'maquignon.scan_cible_{poste}', '')
        return jsonify({'ok': True, 'cible': None})
    typ = d.get('type') if d.get('type') in TYPES else 'doc'
    c = {'veh': vid, 'type': typ, 't': time.time()}
    _call('ir.config_parameter', 'set_param', f'maquignon.scan_cible_{poste}', json.dumps(c))
    return jsonify({'ok': True, 'cible': c})


@bp.route('/api/upload', methods=['POST'])
def upload():
    """Appelé par le veilleur du PC : corps = le fichier, ?k=&poste=&nom=. Attache au véhicule cible ou garde « à classer »."""
    if not _cle_ok():
        return jsonify({'ok': False, 'error': 'clé invalide'}), 401
    poste = _poste()
    nom = os.path.basename(request.args.get('nom') or 'scan.pdf')
    data = request.get_data()
    if not data or len(data) < 100:
        return jsonify({'ok': False, 'error': 'fichier vide'}), 400
    ext = os.path.splitext(nom)[1].lower()
    mime = MIMES.get(ext)
    if not mime:
        return jsonify({'ok': False, 'error': f'type de fichier non accepté ({ext})'}), 400
    b64 = base64.b64encode(data).decode('ascii')
    c = _cible_lire(poste)
    if c:
        try:
            r = _attacher(int(c['veh']), c.get('type', 'doc'), nom, b64, poste, mime)
            v = r['veh']
            return jsonify({'ok': True, 'id': r['id'], 'nom': r['nom'], 'veh': v['id'],
                            'message': f"{r['nom']} attaché au véhicule {v['libelle']}"})
        except Exception as e:  # noqa: BLE001
            return jsonify({'ok': False, 'error': f'Odoo : {str(e)[-200:]}'}), 500
    att = _call('ir.attachment', 'create', [{'name': PREFIXE_ATTENTE + f"{datetime.now().strftime('%d.%m.%Y %Hh%M')} - {nom}", 'res_model': MODELE, 'res_id': 0,
                                            'datas': b64, 'mimetype': mime, 'description': f"{MARQUE} · poste {poste} · à classer"}], **CTX)
    att = att[0] if isinstance(att, list) else att
    return jsonify({'ok': True, 'id': att, 'veh': None,
                    'message': "aucun véhicule affiché sur la page Scanner : document gardé « à classer », ouvrez la page pour le classer"})


@bp.route('/api/classer', methods=['POST'])
def classer():
    """Classe un document « à classer » dans le véhicule affiché (copie sur le véhicule puis suppression de l'attente)."""
    if not _cle_ok():
        return jsonify({'error': 'clé invalide'}), 401
    d = request.get_json(silent=True) or {}
    try:
        vid, aid = int(d.get('veh') or 0), int(d.get('att') or 0)
    except ValueError:
        return jsonify({'error': 'paramètres'}), 400
    typ = d.get('type') if d.get('type') in TYPES else 'doc'
    src = _call('ir.attachment', 'read', [aid], ['name', 'datas', 'mimetype', 'res_model', 'res_id'], **CTX)
    if not src or src[0]['res_model'] != MODELE or src[0]['res_id']:
        return jsonify({'error': 'document introuvable ou déjà classé'}), 404
    nom = src[0]['name'].split(' - ', 2)[-1] if src[0]['name'].startswith(PREFIXE_ATTENTE) else src[0]['name']
    r = _attacher(vid, typ, nom, src[0]['datas'], _poste(d.get('poste')), src[0]['mimetype'])
    _call('ir.attachment', 'unlink', [aid], **CTX)
    return jsonify({'ok': True, 'id': r['id'], 'nom': r['nom']})


@bp.route('/api/retirer', methods=['POST'])
def retirer():
    """Retire d'Odoo un document attaché par le scanner (et sa note) ; la copie reste dans le dossier « Envoyés » du PC."""
    if not _cle_ok():
        return jsonify({'error': 'clé invalide'}), 401
    d = request.get_json(silent=True) or {}
    try:
        aid = int(d.get('att') or 0)
    except ValueError:
        return jsonify({'error': 'paramètres'}), 400
    a = _call('ir.attachment', 'read', [aid], ['name', 'res_model', 'res_id', 'description'], **CTX)
    if not a or a[0]['res_model'] != MODELE:
        return jsonify({'error': 'document introuvable'}), 404
    a = a[0]
    if not (a['description'] or '').startswith(MARQUE):
        return jsonify({'error': "ce document n'a pas été ajouté par le scanner : le retirer depuis Odoo"}), 403
    msgs = _call('mail.message', 'search', [['model', '=', MODELE], ['res_id', '=', a['res_id']], ['attachment_ids', 'in', [aid]]], **CTX) if a['res_id'] else []
    if msgs:
        _call('mail.message', 'unlink', msgs, **CTX)
    _call('ir.attachment', 'unlink', [aid], **CTX)
    return jsonify({'ok': True, 'nom': a['name']})
