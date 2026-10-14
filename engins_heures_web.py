# -*- coding: utf-8 -*-
"""« Rbt taxes GNR » : heures de fonctionnement des engins non routiers, page web /heures-engins (Xavier, 14/10/2026).
Sert au remboursement partiel de l'accise sur le GNR (extraction, circulaire du 11/04/2025) : demande annuelle, par
engin, avec relevés d'horomètre. Les réglages GNR par engin (éligible, type d'engin de la circulaire, % éligible) sont
gardés dans le paramètre Odoo `maquignon.gnr_engins` (JSON), réglables depuis la page.

Source : relevés d'horamètre du Parc automobile Odoo (fleet.vehicle.odometer ; pour les engins l'unité « miles » tient
lieu d'heures). Engins = catégories Pelle, Chargeuse, Tombereau, Chariot élévateur, ou compteur en « miles ».
Tableau « déclaration » : une colonne par sous-période (mois, trimestre, semestre ou année) avec les HEURES consommées
dedans = différence entre le dernier relevé de la sous-période et le relevé de référence précédent ; relevé affiché en
petit ; en mode « prorata », les heures entre deux relevés éloignés sont réparties sur les sous-périodes au prorata des
jours. Export Excel ; saisie d'un nouveau relevé (écrit fleet.vehicle.odometer). Accès : ?k=<clé maquignon.engins_key>.
"""
import io
import json
import os
import re
import threading
import time
import xmlrpc.client
from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, request, send_file, send_from_directory

bp = Blueprint('engins_heures', __name__)
ICI = os.path.dirname(os.path.abspath(__file__))
CATEGORIES = ('Pelle', 'Chargeuse', 'Tombereau', 'Chariot élévateur')
# Types d'engins de la circulaire du 11/04/2025 (remboursement d'accise, extraction de minéraux) et % présumé éligible
TYPES_GNR = [('pelle_chenille', 'Pelle chenille', 100), ('pelle_pneus', 'Pelle pneus', 90), ('chargeuse_pneus', 'Chargeuse sur pneus', 90),
             ('bulldozer', 'Bulldozer', 100), ('foreuse', 'Foreuse', 100), ('compresseur', 'Compresseur', 100), ('groupe_electrogene', 'Groupe électrogène', 100),
             ('groupe_mobile', 'Groupe mobile (concasseur, crible)', 100), ('nacelle', 'Nacelle', 100), ('haveuse', 'Haveuse', 100), ('purgeuse', 'Purgeuse', 100),
             ('bourreuse', 'Bourreuse explosif', 100), ('taupeur', 'Engin taupeur', 50), ('terrassement', 'Autre engin de terrassement', 100), ('autre', 'Autre / non éligible', 0)]
PCT_GNR = {c: p for c, _l, p in TYPES_GNR}
PARAM_GNR = 'maquignon.gnr_engins'
MOIS_COURT = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']
MAX_H_JOUR = 24.0
CTX = {'context': {'allowed_company_ids': [1, 3, 4], 'active_test': False}}

_CONN = {}
_LOCK = threading.Lock()
_CLE = {'val': '', 't': 0.0}
_LOCK_GNR = threading.Lock()


def _call(model, method, *params, **kw):
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


def _cle_ok():
    now = time.time()
    if now - _CLE['t'] > 600 or not _CLE['val']:
        try:
            _CLE['val'] = _call('ir.config_parameter', 'get_param', 'maquignon.engins_key', '') or ''
        except Exception:  # noqa: BLE001
            pass
        _CLE['t'] = now
    k = request.args.get('k') or (request.get_json(silent=True) or {}).get('k') or ''
    return bool(_CLE['val']) and k == _CLE['val']


def _fmt(d):
    return d.strftime('%d/%m/%Y')


def _gnr_lire():
    """Réglages GNR par engin : {id: {'eligible': bool, 'type': code, 'pct': int}} (paramètre Odoo, JSON)."""
    try:
        return {int(k): v for k, v in json.loads(_call('ir.config_parameter', 'get_param', PARAM_GNR, '') or '{}').items()}
    except (ValueError, AttributeError):
        return {}


def _gnr_defaut(v):
    """Proposition d'après la catégorie Odoo, tant que rien n'a été réglé dans la page."""
    cat = (v['category_id'] and v['category_id'][1]) or ''
    if cat == 'Pelle':
        t = 'pelle_pneus' if 'PNEUS' in (v['name'] or '').upper() else 'pelle_chenille'
        return {'eligible': True, 'type': t, 'pct': PCT_GNR[t], 'defaut': True}
    if cat == 'Chargeuse':
        return {'eligible': True, 'type': 'chargeuse_pneus', 'pct': 90, 'defaut': True}
    if cat == 'Tombereau':
        return {'eligible': False, 'type': 'terrassement', 'pct': 100, 'defaut': True}
    return {'eligible': False, 'type': 'autre', 'pct': 0, 'defaut': True}


def _fin_mois(a, m):
    return date(a + (m == 12), m % 12 + 1, 1) - timedelta(days=1)


def _sous_periodes(periodicite, annee):
    """Liste de (debut, fin, libellé court, libellé long)."""
    if periodicite == 'mensuel':
        return [(date(annee, m, 1), _fin_mois(annee, m), '%s %d' % (MOIS_COURT[m - 1], annee), '%s %d' % (MOIS_COURT[m - 1], annee)) for m in range(1, 13)]
    if periodicite == 'semestriel':
        return [(date(annee, 1, 1), date(annee, 6, 30), 'S1 %d' % annee, '1er semestre %d' % annee), (date(annee, 7, 1), date(annee, 12, 31), 'S2 %d' % annee, '2e semestre %d' % annee)]
    if periodicite == 'annuel':
        return [(date(annee, 1, 1), date(annee, 12, 31), 'année %d' % annee, 'année %d' % annee)]
    return [(date(annee, 3 * t - 2, 1), _fin_mois(annee, 3 * t), 'T%d %d' % (t, annee), '%s trimestre %d' % ('1er' if t == 1 else '%de' % t, annee)) for t in range(1, 5)]


def _engins(archives=False):
    rows = _call('fleet.vehicle', 'search_read', [], fields=['name', 'license_plate', 'category_id', 'odometer', 'odometer_unit', 'company_id', 'active', 'model_id', 'vin_sn'], limit=1000, **CTX)
    eng = [v for v in rows if (v['odometer_unit'] == 'miles' or (v['category_id'] and v['category_id'][1] in CATEGORIES)) and (archives or v['active'])]
    eng.sort(key=lambda v: ((v['company_id'] and v['company_id'][1]) or '', (v['category_id'] and v['category_id'][1]) or 'zzz', v['name']))
    return eng


def _releves(ids, jusqua):
    rows = _call('fleet.vehicle.odometer', 'search_read', [['vehicle_id', 'in', ids], ['date', '<=', jusqua.strftime('%Y-%m-%d')]],
                 fields=['vehicle_id', 'date', 'value'], limit=20000, order='date, id', **CTX)
    par = {}
    for r in rows:
        par.setdefault(r['vehicle_id'][0], []).append((datetime.strptime(r['date'], '%Y-%m-%d').date(), float(r['value'])))
    return par


def _nettoie(pts):
    """Relevés triés -> (segments croissants, anomalies). Faute de frappe (baisse rattrapée ensuite, ou > 24 h/jour)
    = relevé ignoré ; baisse jamais rattrapée = remise à zéro = nouvelle série."""
    pts = sorted(pts); segs, cur, anomalies = [], [], []
    for i, (d, v) in enumerate(pts):
        if cur:
            dp, vp = cur[-1]; jours = max((d - dp).days, 1); suite = pts[i + 1:]
            if v < vp:
                if any(s[1] >= vp for s in suite):
                    anomalies.append((d, v, 'relevé %s du %s inférieur au précédent (%s), ignoré : faute de frappe probable' % (int(v), _fmt(d), int(vp)))); continue
                anomalies.append((d, v, 'compteur en baisse le %s (%s -> %s) : remise à zéro ou erreur, nouvelle série' % (_fmt(d), int(vp), int(v))))
                segs.append(cur); cur = [(d, v)]; continue
            if v - vp > MAX_H_JOUR * jours + 24:
                coherent = [s for s in suite if 0 <= s[1] - vp <= MAX_H_JOUR * max((s[0] - dp).days, 1) + 24]
                if coherent or not suite:
                    anomalies.append((d, v, 'relevé %s du %s impossible (+%s h en %d j), ignoré : faute de frappe probable' % (int(v), _fmt(d), int(v - vp), jours))); continue
                anomalies.append((d, v, '+%s h en %d j le %s : > 24 h/jour, à vérifier' % (int(v - vp), jours, _fmt(d))))
        cur.append((d, v))
    if cur:
        segs.append(cur)
    return segs, anomalies


def _declaration(periodicite, annee, prorata, archives, societes=None, eligibles=False):
    sp = _sous_periodes(periodicite, annee)
    debut, fin = sp[0][0], sp[-1][1]
    tous = _engins(archives)
    gnr = _gnr_lire()
    for v in tous:
        v['gnr'] = gnr.get(v['id']) or _gnr_defaut(v)
    dispo = sorted({(v['company_id'][0], v['company_id'][1]) for v in tous if v['company_id']}, key=lambda c: c[1])
    eng = [v for v in tous if (not societes or (v['company_id'] and v['company_id'][0] in societes)) and (not eligibles or v['gnr']['eligible'])]
    rel = _releves([v['id'] for v in eng], fin) if eng else {}
    lignes = []
    for v in eng:
        pts = rel.get(v['id'], [])
        segs, anomalies = _nettoie(pts)
        cells = [{'h': None, 'releve': None, 'depuis': None, 'estime': False} for _ in sp]
        for d, val in pts:                                   # relevé affiché : le dernier de chaque sous-période (brut)
            for i, (a, b, _l, _ll) in enumerate(sp):
                if a <= d <= b:
                    cells[i]['releve'] = {'date': _fmt(d), 'valeur': round(val)}
        for seg in segs:
            for (d1, v1), (d2, v2) in zip(seg, seg[1:]):
                if d2 < debut or d1 > fin:
                    continue
                h = v2 - v1
                if prorata:
                    total_j = max((d2 - d1).days, 1)
                    for i, (a, b, _l, _ll) in enumerate(sp):
                        lo, hi = max(d1 + timedelta(days=1), a), min(d2, b)       # jours (d1, d2] qui tombent dans la sous-période
                        if lo > hi:
                            continue
                        part = h * ((hi - lo).days + 1) / total_j
                        cells[i]['h'] = (cells[i]['h'] or 0) + part
                        if not (a <= d1 and d2 <= b):
                            cells[i]['estime'] = True
                else:
                    for i, (a, b, _l, _ll) in enumerate(sp):
                        if a <= d2 <= b:
                            cells[i]['h'] = (cells[i]['h'] or 0) + h
                            if i > 0 and d1 < sp[i - 1][0] or i == 0 and d1 < a - timedelta(days=45):
                                cells[i]['depuis'] = _fmt(d1)
                            elif i == 0 and d1 < a:
                                pass
        for c in cells:
            if c['h'] is not None:
                c['h'] = round(c['h'])
        rem = [t for _d, _v, t in anomalies]
        if v['odometer_unit'] != 'miles':
            rem.append("unité « %s » dans Odoo (un engin doit être en « miles » = heures)" % v['odometer_unit'])
        if not pts:
            rem.append('aucun relevé de compteur')
        total = sum(c['h'] for c in cells if c['h'] is not None) if any(c['h'] is not None for c in cells) else None
        avant = [p for p in pts if p[0] < debut]
        g = v['gnr']; elig, pctv = bool(g.get('eligible')), int(g.get('pct') or 0)
        for c in cells:
            c['he'] = round(c['h'] * pctv / 100) if (elig and c['h'] is not None) else None
        lignes.append({'id': v['id'], 'nom': v['name'], 'categorie': (v['category_id'] and v['category_id'][1]) or '', 'societe': (v['company_id'] and v['company_id'][1]) or '',
                       'actif': v['active'], 'serie': v.get('vin_sn') or '', 'eligible': elig, 'type': g.get('type') or '', 'pct': pctv, 'gnr_defaut': bool(g.get('defaut')),
                       'total_elig': round(total * pctv / 100) if (elig and total is not None) else None,
                       'debut': {'date': _fmt(avant[-1][0]), 'valeur': round(avant[-1][1])} if avant else None,
                       'cellules': cells, 'total': total, 'remarques': rem,
                       'dernier': {'date': _fmt(pts[-1][0]), 'valeur': round(pts[-1][1])} if pts else None})
    colonnes = [{'court': l, 'long': ll, 'debut': _fmt(a), 'fin': _fmt(b)} for a, b, l, ll in sp]
    totaux, totaux_elig = {}, {}
    for l in lignes:
        t = totaux.setdefault(l['societe'], [0] * len(sp) + [0]); te = totaux_elig.setdefault(l['societe'], [0] * len(sp) + [0])
        for i, c in enumerate(l['cellules']):
            if c['h'] is not None:
                t[i] += c['h']
            if c['he'] is not None:
                te[i] += c['he']
        if l['total'] is not None:
            t[-1] += l['total']
        if l['total_elig'] is not None:
            te[-1] += l['total_elig']
    general = [sum(t[i] for t in totaux.values()) for i in range(len(sp) + 1)]
    general_elig = [sum(t[i] for t in totaux_elig.values()) for i in range(len(sp) + 1)]
    libelle = {'mensuel': 'Heures par mois, %d' % annee, 'trimestriel': 'Heures par trimestre, %d' % annee, 'semestriel': 'Heures par semestre, %d' % annee, "annuel": "Heures de l'année %d" % annee}[periodicite if periodicite in ('mensuel', 'semestriel', 'annuel') else 'trimestriel']
    return {'periode': {'periodicite': periodicite, 'annee': annee, 'prorata': prorata, 'libelle': libelle, 'debut': _fmt(debut), 'fin': _fmt(fin),
                        'societes': [n for i, n in dispo if not societes or i in societes]},
            'societes_dispo': [{'id': i, 'nom': n} for i, n in dispo], 'colonnes': colonnes, 'lignes': lignes, 'totaux': totaux, 'general': general,
            'totaux_elig': totaux_elig, 'general_elig': general_elig, 'types_gnr': [{'code': c, 'nom': l, 'pct': p} for c, l, p in TYPES_GNR]}


def _params():
    periodicite = request.args.get('periodicite') or 'annuel'          # défauts = dossier de remboursement : par année, année civile précédente
    if periodicite not in ('mensuel', 'trimestriel', 'semestriel', 'annuel'):
        periodicite = 'annuel'
    try:
        annee = int(request.args.get('annee') or (date.today().year - 1))
    except ValueError:
        annee = date.today().year - 1
    societes = [int(x) for x in re.findall(r'\d+', request.args.get('societes') or '')]
    return periodicite, annee, request.args.get('prorata') in ('1', 'true', 'oui'), request.args.get('archives') in ('1', 'true', 'oui'), societes, request.args.get('eligibles') in ('1', 'true', 'oui')


@bp.route('/')
def page():
    return send_from_directory(ICI, 'engins_heures_page.html')


@bp.route('/api/tableau')
def tableau():
    if not _cle_ok():
        return jsonify({'error': 'clé invalide'}), 401
    return jsonify(_declaration(*_params()))


@bp.route('/api/releve', methods=['POST'])
def releve():
    """Nouveau relevé d'horamètre : {veh, date 'AAAA-MM-JJ', valeur}. Refusé s'il est inférieur au dernier relevé (sauf forcer)."""
    if not _cle_ok():
        return jsonify({'error': 'clé invalide'}), 401
    d = request.get_json(silent=True) or {}
    try:
        vid = int(d.get('veh')); val = float(str(d.get('valeur')).replace(',', '.')); jour = datetime.strptime(d.get('date') or date.today().isoformat(), '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return jsonify({'error': 'relevé incomplet (engin, date, heures)'}), 400
    if val < 0 or val > 200000:
        return jsonify({'error': 'valeur invraisemblable'}), 400
    if jour > date.today():
        return jsonify({'error': 'date dans le futur'}), 400
    dern = _call('fleet.vehicle.odometer', 'search_read', [['vehicle_id', '=', vid], ['date', '<=', jour.strftime('%Y-%m-%d')]], fields=['date', 'value'], order='date desc, id desc', limit=1, **CTX)
    if dern and val < dern[0]['value'] and not d.get('forcer'):
        return jsonify({'error': 'inférieur au dernier relevé (%s h le %s). Vérifiez la valeur ; pour un compteur remis à zéro, cochez « forcer ».' % (round(dern[0]['value']), _fmt(datetime.strptime(dern[0]['date'], '%Y-%m-%d'))), 'confirmable': True}), 409
    rid = _call('fleet.vehicle.odometer', 'create', [{'vehicle_id': vid, 'date': jour.strftime('%Y-%m-%d'), 'value': val}], **CTX)
    return jsonify({'ok': True, 'id': rid[0] if isinstance(rid, list) else rid})


@bp.route('/api/engin', methods=['POST'])
def engin():
    """Réglage GNR d'un engin : {veh, eligible, type, pct} -> paramètre maquignon.gnr_engins (JSON partagé)."""
    if not _cle_ok():
        return jsonify({'error': 'clé invalide'}), 401
    d = request.get_json(silent=True) or {}
    try:
        vid = int(d.get('veh')); pctv = int(d.get('pct') if d.get('pct') not in (None, '') else 0)
    except (TypeError, ValueError):
        return jsonify({'error': 'paramètres'}), 400
    typ = d.get('type') if d.get('type') in PCT_GNR else 'autre'
    if not 0 <= pctv <= 100:
        return jsonify({'error': 'le pourcentage doit être entre 0 et 100'}), 400
    with _LOCK_GNR:
        g = _gnr_lire()
        g[vid] = {'eligible': bool(d.get('eligible')), 'type': typ, 'pct': pctv}
        _call('ir.config_parameter', 'set_param', PARAM_GNR, json.dumps({str(k): v for k, v in g.items()}))
    return jsonify({'ok': True, 'vals': g[vid]})


@bp.route('/api/export.xlsx')
def export():
    if not _cle_ok():
        return jsonify({'error': 'clé invalide'}), 401
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    t = _declaration(*_params())
    wb = Workbook(); ws = wb.active; ws.title = re.sub(r'[\\/*?:\[\]]', ' ', t['periode']['libelle'])[:31]
    gras = Font(bold=True); fond = PatternFill('solid', fgColor='EEF2FF'); gris = Font(color='64748B', size=9)
    ws['A1'] = 'Rbt taxes GNR · heures de fonctionnement des engins non routiers : %s · %s' % (t['periode']['libelle'], ', '.join(t['periode']['societes'])); ws['A1'].font = Font(bold=True, size=13)
    ws['A2'] = ("Heures = différence entre relevés d'horamètre (Parc automobile Odoo)%s. Généré le %s."
                % (', réparties au prorata des jours entre deux relevés' if t['periode']['prorata'] else ' ; une case vide = pas de relevé dans la sous-période, ses heures sont comptées dans la case du relevé suivant', _fmt(date.today())))
    n = len(t['colonnes'])
    noms_types = {c: l for c, l, _p in TYPES_GNR}
    ent = ['Société', 'Catégorie', 'Engin', 'N° de série / châssis', 'Éligible GNR', "Type d'engin (circulaire)", '% éligible', 'Relevé début', 'Date début']
    for c in t['colonnes']:
        ent += ['Fin %s' % c['court'], 'Date', 'Heures %s' % c['court']]
    ent += ['Total heures', 'Heures éligibles', 'Remarques']
    ws.append([]); ws.append(ent)
    for c in ws[4]:
        c.font = gras; c.fill = fond; c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    AV = 9   # colonnes avant les périodes
    for l in t['lignes']:
        ligne = [l['societe'], l['categorie'], l['nom'], l['serie'], 'oui' if l['eligible'] else 'non', noms_types.get(l['type'], ''), l['pct'] if l['eligible'] else '',
                 l['debut']['valeur'] if l['debut'] else '', l['debut']['date'] if l['debut'] else '']
        for c in l['cellules']:
            ligne += [c['releve']['valeur'] if c['releve'] else '', c['releve']['date'] if c['releve'] else '', c['h'] if c['h'] is not None else '']
        ligne += [l['total'] if l['total'] is not None else '', l['total_elig'] if l['total_elig'] is not None else '',
                  ' ; '.join(l['remarques'] + ['%s : heures comptées depuis le %s' % (t['colonnes'][i]['court'], c['depuis']) for i, c in enumerate(l['cellules']) if c['depuis']])]
        ws.append(ligne)
        r = ws.max_row
        for i, c in enumerate(l['cellules']):
            if c['depuis'] or c['estime']:
                ws.cell(r, AV + 3 + 3 * i).font = Font(color='B45309' if c['depuis'] else '1D4ED8', bold=True)
    ws.append([])

    def total_ligne(lib, tt, te):
        ligne = ['', '', lib] + [''] * (AV - 3)
        for i in range(n):
            ligne += ['', '', tt[i]]
        ws.append(ligne + [tt[-1], te[-1], ''])
        for cc in ws[ws.max_row]:
            cc.font = gras
    for soc in t['totaux']:
        total_ligne('TOTAL ' + soc, t['totaux'][soc], t['totaux_elig'][soc])
    total_ligne('TOTAL engins', t['general'], t['general_elig'])
    larg = [20, 16, 44, 18, 10, 26, 9, 11, 11] + [11, 11, 11] * n + [12, 12, 70]
    for i, w in enumerate(larg, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=5):
        for c in row[6:len(larg) - 1]:
            c.number_format = '# ##0'
        row[-1].alignment = Alignment(wrap_text=True, vertical='top')
    ws.freeze_panes = 'D5'
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    nom = 'Rbt_taxes_GNR_%s.xlsx' % re.sub(r'[^A-Za-z0-9]+', '_', t['periode']['libelle']).strip('_')
    return send_file(buf, as_attachment=True, download_name=nom, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
