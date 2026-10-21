# -*- coding: utf-8 -*-
"""Site « devis instantané » Chatel'Granulats (Xavier, 21/10/2026 : « l'équivalent de koncrete.fr »).

Site public monté sous /devis (domaine prévu : devis.chatelgranulats.com, CNAME vers Render) : accueil, parcours
de devis en 4 étapes (service, produit, volume, récapitulatif) et pages annexes. Odoo (société 3) sert de base :
articles vendus à la tonne, prix de la liste « Particuliers », création d'un devis brouillon + e-mail au bureau.
Choix de Xavier : 4 services (livraison, évacuation de déblais, affrètement, location de benne), transport en
€/km/tonne depuis Le Pautron (zone 50 km), prix publics en fourchette, tout en devis (pas de paiement en ligne).
Réglages : paramètre Odoo `chatel.devis_cfg` (JSON fusionné avec CFG_DEFAUT, relu toutes les 10 min).
Catalogue et images en cache mémoire (10 min) : aucune page ne dépend d'Odoo en temps réel sauf l'envoi.
"""
import base64
import hashlib
import hmac
import html
import json
import math
import os
import re
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
import xmlrpc.client
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, Response, abort, jsonify, redirect, render_template, request, url_for

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo('Europe/Paris')
except Exception:  # noqa: BLE001
    TZ = timezone(timedelta(hours=1))

bp = Blueprint('chatel_devis', __name__, template_folder='templates', static_folder='static', static_url_path='/static')
PARAM_CFG = 'chatel.devis_cfg'
HOTES = ('devis.chatelgranulats.com',)

CFG_DEFAUT = {
    'societe': 3,
    'liste_public': 3,                       # « Particuliers Avril 2026 »
    'depart': {'nom': "Le Pautron, 86100 Châtellerault", 'lat': 46.7798, 'lon': 0.5483},
    'zone_km': 50, 'km_mini': 5, 'coef_route': 1.3,
    # transport = tonnes facturées × (fixe_t + eur_km_t × km aller), tonnes facturées >= mini_t
    'camions': [
        {'code': '6x4', 'nom': 'Porteur 6x4', 'charge': 13, 'mini_t': 8, 'fixe_t': 2.0, 'eur_km_t': 0.16},
        {'code': '8x4', 'nom': 'Porteur 8x4', 'charge': 17, 'mini_t': 12, 'fixe_t': 1.8, 'eur_km_t': 0.14},
        {'code': 'semi', 'nom': 'Semi-benne', 'charge': 28, 'mini_t': 20, 'fixe_t': 1.5, 'eur_km_t': 0.11},
    ],
    'forfait_mini': 0,
    'article_transport': 2575,               # « Transport à la tonne »
    'article_evacuation': 2574,              # « Reprise deblais inerte »
    'article_affretement': 3228,             # location semi
    'contributions': [],                     # [{"id": 123, "nom": "Eco contribution", "eur_t": 0.5}] ajoutées par tonne
    'exclure': r'(?i)contribution|transport|reprise|location|livraison|forfait|acompte|remise|consigne',
    'exclure_ids': [],
    'affretement': [                         # prix HT ; null = sur devis
        {'code': '6x4', 'nom': 'Porteur 6x4 + chauffeur', 'demi': None, 'jour': None},
        {'code': '8x4', 'nom': 'Porteur 8x4 + chauffeur', 'demi': None, 'jour': None},
        {'code': 'semi', 'nom': 'Semi-benne + chauffeur', 'demi': None, 'jour': None},
    ],
    'bennes': [                              # prix HT de la rotation (pose + enlèvement) ; null = sur devis
        {'code': 'b8', 'nom': 'Benne 8 m³', 'prix': None, 'jour_sup': None},
        {'code': 'b15', 'nom': 'Benne 15 m³', 'prix': None, 'jour_sup': None},
        {'code': 'b30', 'nom': 'Benne 30 m³', 'prix': None, 'jour_sup': None},
    ],
    'deblais': ['Terre végétale / terre de déblai', 'Gravats inertes (béton, briques, tuiles)', 'Mélange terre + cailloux'],
    'delai_jours': 2, 'jours': [0, 1, 2, 3, 4], 'nb_dates': 12,
    'creneaux': ['6 h 30 – 9 h', '9 h – 12 h', '13 h – 16 h 30'],
    'densites': {'Sable': 1.6, 'Gravier': 1.5, 'Caillou': 1.5, 'Grave': 1.9, 'Terre': 1.4, 'Galets': 1.6,
                 'Concassé déco': 1.5, 'Ardoise et schiste': 1.4, 'Dallage et pavage': 1.6, 'Divers': 1.5, 'Déblais': 1.6},
    'familles_ordre': ['Sable', 'Gravier', 'Caillou', 'Grave', 'Terre', 'Concassé déco', 'Galets', 'Ardoise et schiste',
                       'Dallage et pavage', 'Divers', 'Déstockage'],
    'usages': [   # [nom, regex sur nom d'article ou de catégorie]
        ['Béton & maçonnerie', r'(?i)(sable.*0/4|0/4.*sable|4/10|4/20|6/10|6/14|10/20|gravillon|béton|maçon)'],
        ['Tranchée canalisation', r'(?i)(sable|0/4|0/6|2/4|4/6|enrobage)'],
        ['Tranchée technique & remblai', r'(?i)(grave|0/20|0/31|0/63|0/80|tout.?venant|remblai|gnt)'],
        ['Drainage', r'(?i)(20/40|20/60|40/80|40/70|drain|ballast|caillou|cailloux)'],
        ['Allée & cour', r'(?i)(allée|0/20|6/10|10/14|concassé|calcaire|gravier)'],
        ['Décoration jardin', r'(?i)(déco|galet|ardoise|schiste|marbre|paillage|blanc|rose|noir|ocre)'],
        ['Terrassement & espaces verts', r'(?i)(terre|végétale)'],
        ['Dallage & pavage', r'(?i)(dall|pavé|pavage|pas japonais|bordure)'],
    ],
    'tva': 20,
    'email_bureau': 'granulats@maquignon.com',
    'accuse_client': True,
    'avis_google': 'https://www.google.com/maps/search/?api=1&query=Chatel%27Granulats%20Le%20Pautron%20Ch%C3%A2tellerault',
    'site_principal': 'https://www.chatelgranulats.com',
    'test': False,                           # True : aucune écriture dans Odoo, la demande est seulement renvoyée
}

# pictogramme et teinte de fond des familles (vignette quand l'article n'a pas de photo dans Odoo)
DECO = {'Sable': ('🏖️', '#EADFC4'), 'Gravier': ('🪨', '#DDD8CF'), 'Caillou': ('🪨', '#D3CCC0'), 'Grave': ('🛣️', '#D2C8B8'),
        'Terre': ('🌱', '#D9C7AE'), 'Concassé déco': ('✨', '#ECE5DA'), 'Galets': ('⚪', '#E6E0D6'), 'Ardoise et schiste': ('⬛', '#CDD1D4'),
        'Dallage et pavage': ('🔲', '#DCD6CC'), 'Divers': ('📦', '#E3DED6'), 'Déstockage': ('🏷️', '#F0DCCB')}

_CONN = {}
_LOCK = threading.Lock()
_CACHE = {}            # nom -> (t, valeur)
_CACHE_LOCK = threading.Lock()
_IMG = {}              # tmpl_id -> (t, bytes, mimetype)
_DIST = {}             # (lat, lon) arrondis -> km
_ENVOIS = {}           # ip -> [t, ...]


# ---------------------------------------------------------------- Odoo
def _call(model, method, *params, **kw):
    with _LOCK:
        if 'uid' not in _CONN:
            url, db, user, pwd = (os.environ.get(k) for k in ('ODOO_URL', 'ODOO_DB', 'ODOO_USER', 'ODOO_PASSWORD'))
            uid = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True).authenticate(db, user, pwd, {})
            if not uid:
                raise ValueError('authentification Odoo refusée')
            _CONN.update(uid=uid, url=url, db=db, pwd=pwd)
        c = dict(_CONN)
    # un proxy par appel : ServerProxy n'est pas sûr entre threads
    proxy = xmlrpc.client.ServerProxy(f"{c['url']}/xmlrpc/2/object", allow_none=True)
    try:
        return proxy.execute_kw(c['db'], c['uid'], c['pwd'], model, method, list(params), kw)
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in str(e):
            return None
        raise


def _ctx(soc):
    return {'context': {'allowed_company_ids': [soc], 'lang': 'fr_FR'}}


def _creer(model, vals, soc):
    r = _call(model, 'create', vals, **_ctx(soc))
    return r[0] if isinstance(r, list) else r


def _cache(nom, duree, fn):
    """Valeur en cache ; périmée -> recalcul en arrière-plan, l'ancienne valeur reste servie."""
    now = time.time()
    with _CACHE_LOCK:
        c = _CACHE.get(nom)
        if c and now - c[0] < duree:
            return c[1]
        if c and not c[2]:
            _CACHE[nom] = (c[0], c[1], True)

            def maj():
                try:
                    v = fn()
                    with _CACHE_LOCK:
                        _CACHE[nom] = (time.time(), v, False)
                except Exception:  # noqa: BLE001
                    with _CACHE_LOCK:
                        _CACHE[nom] = (c[0], c[1], False)
            threading.Thread(target=maj, daemon=True).start()
            return c[1]
        if c:
            return c[1]
    v = fn()
    with _CACHE_LOCK:
        _CACHE[nom] = (time.time(), v, False)
    return v


def cfg():
    def lire():
        c = json.loads(json.dumps(CFG_DEFAUT))
        try:
            c.update(json.loads(_call('ir.config_parameter', 'get_param', PARAM_CFG, '') or '{}'))
        except Exception:  # noqa: BLE001
            pass
        return c
    try:
        return _cache('cfg', 600, lire)
    except Exception:  # noqa: BLE001
        return CFG_DEFAUT


def societe():
    def lire():
        s = cfg()['societe']
        r = _call('res.company', 'read', [s], ['name', 'street', 'street2', 'zip', 'city', 'phone', 'email', 'vat', 'company_registry'])[0]
        return {k: (v or '') for k, v in r.items()}
    try:
        return _cache('societe', 3600, lire)
    except Exception:  # noqa: BLE001
        return {'name': "CHATEL'GRANULATS", 'street': 'Le Pautron', 'zip': '86100', 'city': 'Châtellerault',
                'phone': '05 49 90 57 62', 'email': 'granulats@maquignon.com', 'vat': '', 'company_registry': ''}


# ---------------------------------------------------------------- catalogue
def _sans_accent(t):
    return unicodedata.normalize('NFKD', t or '').encode('ascii', 'ignore').decode().lower()


def _famille(nom, categ):
    """Famille affichée (colonne de gauche du parcours) d'après la catégorie Odoo et le nom de l'article."""
    n, c = _sans_accent(nom), _sans_accent(categ)
    if 'destock' in c or 'declass' in n:
        return 'Déstockage'
    if 'sable' in c and 'granulat' in c:
        for mot, fam in (('sable', 'Sable'), ('grave', 'Grave'), ('tout venant', 'Grave'), ('terre', 'Terre'),
                         ('caillou', 'Caillou'), ('ballast', 'Caillou'), ('enrochement', 'Caillou'), ('galet', 'Galets')):
            if n.startswith(mot) or f' {mot}' in n[:25]:
                return fam
        return 'Gravier'
    for mot, fam in (('galet', 'Galets'), ('ardoise', 'Ardoise et schiste'), ('schiste', 'Ardoise et schiste'),
                     ('dallage', 'Dallage et pavage'), ('pavage', 'Dallage et pavage'), ('concasse', 'Concassé déco'),
                     ('deco', 'Concassé déco'), ('terre', 'Terre')):
        if mot in c:
            return fam
    return 'Divers'


def _regle(regles, prod, categs):
    for filtre in (lambda r: r['applied_on'] == '0_product_variant' and r['product_id'] and r['product_id'][0] == prod['id'],
                   lambda r: r['applied_on'] == '1_product' and r['product_tmpl_id'] and r['product_tmpl_id'][0] == prod['product_tmpl_id'][0],
                   lambda r: r['applied_on'] == '2_product_category' and r['categ_id'] and r['categ_id'][0] in categs,
                   lambda r: r['applied_on'] == '3_global'):
        cand = [r for r in regles if filtre(r)]
        if cand:
            return sorted(cand, key=lambda r: -r['id'])[0]
    return None


def _prix_liste(listes, liste_id, prod, categs, prof=0):
    """Prix HT/t d'un article sur une liste (variante > modèle > catégorie > globale ; fixe, %, formule)."""
    if not liste_id or prof > 4 or liste_id not in listes:
        return prod['lst_price']
    r = _regle(listes[liste_id], prod, categs)
    if not r:
        return prod['lst_price']
    if r['compute_price'] == 'fixed':
        return r['fixed_price']
    base = _prix_liste(listes, r['base_pricelist_id'][0], prod, categs, prof + 1) if (r['base'] == 'pricelist' and r['base_pricelist_id']) else prod['lst_price']
    if r['compute_price'] == 'percentage':
        return base * (1 - (r['percent_price'] or 0) / 100.0)
    return base * (1 - (r['price_discount'] or 0) / 100.0) + (r['price_surcharge'] or 0)


def _lire_catalogue():
    c = cfg(); soc = c['societe']; ctx = _ctx(soc)
    prods = _call('product.product', 'search_read',
                  [['sale_ok', '=', True], ['active', '=', True], ['company_id', 'in', [soc, False]]],
                  fields=['display_name', 'name', 'lst_price', 'uom_id', 'categ_id', 'product_tmpl_id', 'company_id', 'description_sale'], **ctx)
    excl = re.compile(c['exclure'])
    prods = [p for p in prods if re.match(r'(?i)^(t|tonnes?)$', (p['uom_id'] or [0, ''])[1].strip())
             and not excl.search(p['name'] or '') and p['id'] not in c['exclure_ids']]
    # listes de prix utiles (publique + ses listes de base)
    listes, a_lire = {}, [c['liste_public']]
    while a_lire:
        lid = a_lire.pop()
        if lid in listes:
            continue
        listes[lid] = _call('product.pricelist.item', 'search_read', [['pricelist_id', '=', lid]],
                            fields=['applied_on', 'product_id', 'product_tmpl_id', 'categ_id', 'compute_price', 'fixed_price',
                                    'percent_price', 'price_discount', 'price_surcharge', 'base', 'base_pricelist_id',
                                    'date_start', 'date_end', 'min_quantity'], **ctx)
        auj = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        listes[lid] = [r for r in listes[lid] if (not r['date_start'] or r['date_start'] <= auj)
                       and (not r['date_end'] or r['date_end'] >= auj) and (r['min_quantity'] or 0) <= 1]
        a_lire += [r['base_pricelist_id'][0] for r in listes[lid] if r['base'] == 'pricelist' and r['base_pricelist_id']]
    cat_ids = list({p['categ_id'][0] for p in prods if p['categ_id']})
    parents = {k['id']: [int(i) for i in (k['parent_path'] or '').strip('/').split('/') if i]
               for k in _call('product.category', 'read', cat_ids, ['parent_path'])} if cat_ids else {}
    tmpl_ids = list({p['product_tmpl_id'][0] for p in prods})
    try:
        avec_img = set(_call('product.template', 'search', [['id', 'in', tmpl_ids], ['image_1920', '!=', False]], **ctx))
    except Exception:  # noqa: BLE001
        avec_img = set(tmpl_ids)
    usages = [(u, re.compile(rx)) for u, rx in c['usages']]
    out = []
    for p in prods:
        categ = p['categ_id'][1].split('/')[-1].strip() if p['categ_id'] else ''
        prix = _prix_liste(listes, c['liste_public'], p, parents.get(p['categ_id'][0], []) if p['categ_id'] else [])
        if not prix or prix <= 0:
            continue
        nom = re.sub(r'^\[[^\]]+\]\s*', '', p['display_name'] or p['name'])
        fam = _famille(nom, categ)
        out.append({'id': p['id'], 'tmpl': p['product_tmpl_id'][0], 'nom': nom, 'famille': fam, 'categ': categ,
                    'prix_t': round(prix, 2), 'img': p['product_tmpl_id'][0] in avec_img,
                    'declasse': fam == 'Déstockage' or 'déclass' in nom.lower(),
                    'usages': [u for u, rx in usages if rx.search(nom) or rx.search(categ)],
                    'densite': c['densites'].get(fam, 1.5), 'desc': (p['description_sale'] or '').strip()[:300]})
    ordre = {f: i for i, f in enumerate(c['familles_ordre'])}
    out.sort(key=lambda q: (ordre.get(q['famille'], 99), _sans_accent(q['nom'])))
    # prix d'évacuation (article Reprise déblais)
    evac = None
    try:
        e = _call('product.product', 'read', [c['article_evacuation']], ['lst_price', 'display_name'], **ctx)[0]
        evac = {'id': e['id'], 'nom': e['display_name'], 'prix_t': e['lst_price']}
    except Exception:  # noqa: BLE001
        pass
    return {'produits': out, 'evacuation': evac, 'maj': datetime.now(TZ).strftime('%d/%m/%Y %H:%M')}


def catalogue():
    return _cache('catalogue', 600, _lire_catalogue)


def produit(pid):
    return next((p for p in catalogue()['produits'] if p['id'] == pid), None)


# ---------------------------------------------------------------- distance et prix
def _haversine(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def distance_km(lat, lon):
    """Distance routière aller depuis le départ (OSRM), repli = vol d'oiseau × coef_route."""
    c = cfg(); d = c['depart']
    cle = (round(lat, 4), round(lon, 4))
    if cle in _DIST:
        return _DIST[cle]
    km, source = None, 'route'
    try:
        u = f"https://router.project-osrm.org/route/v1/driving/{d['lon']},{d['lat']};{lon},{lat}?overview=false"
        with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'chatelgranulats-devis/1.0'}), timeout=4) as r:
            j = json.loads(r.read().decode())
        if j.get('code') == 'Ok':
            km = j['routes'][0]['distance'] / 1000.0
    except Exception:  # noqa: BLE001
        pass
    if km is None:
        km, source = _haversine((d['lat'], d['lon']), (lat, lon)) * c['coef_route'], 'estimation'
    res = {'km': round(km, 1), 'source': source, 'dans_zone': km <= c['zone_km']}
    if len(_DIST) > 5000:
        _DIST.clear()
    _DIST[cle] = res
    return res


def _camion(code):
    return next((k for k in cfg()['camions'] if k['code'] == code), None)


def transport_t(camion, km):
    c = cfg()
    return camion['fixe_t'] + camion['eur_km_t'] * max(km, c['km_mini'])


def contributions_t():
    return round(sum(x.get('eur_t') or 0 for x in cfg()['contributions']), 2)


def fourchette(prix_t, km):
    """Prix livré HT/t, du camion le plus économique au plus cher (pleins chargements)."""
    ts = [transport_t(k, km) for k in cfg()['camions']]
    base = prix_t + contributions_t()
    return math.floor(base + min(ts)), math.ceil(base + max(ts))


def camion_conseille(tonnes):
    """Le plus petit camion qui fait tout en un tour, sinon le plus gros."""
    ks = sorted(cfg()['camions'], key=lambda k: k['charge'])
    return next((k for k in ks if k['charge'] >= tonnes), ks[-1])


def estimer(d):
    """Devis détaillé (HT) d'une demande du parcours. Lève ValueError si incomplet."""
    c = cfg(); service = d.get('service')
    km = float(d.get('km') or 0)
    lignes, notes = [], []
    if service in ('livraison', 'evacuation'):
        t = float(d.get('tonnes') or 0)
        if t <= 0 or t > 2000:
            raise ValueError('quantité invalide')
        k = _camion(d.get('camion')) or camion_conseille(t)
        tours = math.ceil(t / k['charge'])
        t_fact = max(t, k['mini_t'])
        if service == 'livraison':
            p = produit(int(d.get('produit') or 0))
            if not p:
                raise ValueError('produit inconnu')
            lignes.append({'id': p['id'], 'nom': p['nom'], 'qte': t, 'unite': 't', 'pu': p['prix_t']})
            for x in c['contributions']:
                if x.get('eur_t'):
                    lignes.append({'id': x['id'], 'nom': x['nom'], 'qte': t, 'unite': 't', 'pu': x['eur_t']})
        else:
            e = catalogue()['evacuation'] or {'id': c['article_evacuation'], 'nom': 'Reprise de déblais inertes', 'prix_t': 8.75}
            lignes.append({'id': e['id'], 'nom': f"{e['nom']} — {d.get('deblais') or 'déblais inertes'}", 'qte': t, 'unite': 't', 'pu': e['prix_t']})
        pu_tr = round(transport_t(k, km), 2)
        lib = f"Transport {k['nom']} ({k['charge']} t) — {km:.0f} km — {tours} tour{'s' if tours > 1 else ''}"
        if t_fact > t:
            notes.append(f"Minimum de {k['mini_t']:g} t facturées en transport pour un {k['nom']}.")
        lignes.append({'id': c['article_transport'], 'nom': lib, 'qte': t_fact, 'unite': 't', 'pu': pu_tr, 'transport': True})
        if c['forfait_mini'] and t_fact * pu_tr < c['forfait_mini']:
            lignes[-1].update(qte=1, unite='forfait', pu=c['forfait_mini'])
            notes.append(f"Forfait transport minimum {c['forfait_mini']:.0f} € HT.")
        resume = {'camion': k['code'], 'tours': tours}
    elif service == 'affretement':
        k = next((a for a in c['affretement'] if a['code'] == d.get('camion')), None)
        duree = d.get('duree') if d.get('duree') in ('demi', 'jour') else 'jour'
        nb = max(1, min(int(d.get('nb') or 1), 30))
        if not k:
            raise ValueError('camion inconnu')
        lignes.append({'id': c['article_affretement'], 'nom': f"Affrètement {k['nom']} — {'demi-journée' if duree == 'demi' else 'journée'}",
                       'qte': nb, 'unite': 'demi-j.' if duree == 'demi' else 'j', 'pu': k.get(duree)})
        resume = {'camion': k['code'], 'duree': duree, 'nb': nb}
    elif service == 'benne':
        b = next((x for x in c['bennes'] if x['code'] == d.get('benne')), None)
        if not b:
            raise ValueError('benne inconnue')
        jours = max(1, min(int(d.get('nb') or 1), 60))
        lignes.append({'id': None, 'nom': f"Location {b['nom']} — pose et enlèvement", 'qte': 1, 'unite': 'rotation', 'pu': b.get('prix')})
        if jours > 1:
            lignes.append({'id': None, 'nom': f"{b['nom']} — jours supplémentaires", 'qte': jours - 1, 'unite': 'j', 'pu': b.get('jour_sup')})
        resume = {'benne': b['code'], 'nb': jours}
    else:
        raise ValueError('service inconnu')
    sur_devis = any(l['pu'] is None for l in lignes)
    for l in lignes:
        l['total'] = None if l['pu'] is None else round(l['qte'] * l['pu'], 2)
    ht = None if sur_devis else round(sum(l['total'] for l in lignes), 2)
    tva = None if ht is None else round(ht * c['tva'] / 100.0, 2)
    return {'lignes': lignes, 'ht': ht, 'tva': tva, 'ttc': None if ht is None else round(ht + tva, 2),
            'sur_devis': sur_devis, 'notes': notes, 'resume': resume, 'km': km}


def dates_livraison():
    c = cfg(); j = datetime.now(TZ).date(); n = 0; out = []
    while n < c['delai_jours']:
        j += timedelta(days=1)
        if j.weekday() in c['jours']:
            n += 1
    while len(out) < c['nb_dates']:
        if j.weekday() in c['jours']:
            out.append(j.isoformat())
        j += timedelta(days=1)
    return out


# ---------------------------------------------------------------- anti-abus
def _secret():
    return hashlib.sha256(('chatel-devis' + (os.environ.get('WEBHOOK_SECRET') or os.environ.get('ODOO_PASSWORD') or '')).encode()).digest()


def jeton_formulaire():
    t = str(int(time.time()))
    return t + '.' + hmac.new(_secret(), t.encode(), hashlib.sha256).hexdigest()[:16]


def _controle_envoi(d):
    """Pot de miel, délai mini de 4 s depuis l'affichage, 6 envois / heure / IP."""
    if d.get('site_web'):
        raise PermissionError('refusé')
    try:
        t, sig = (d.get('jeton') or '').split('.')
        ok = hmac.compare_digest(sig, hmac.new(_secret(), t.encode(), hashlib.sha256).hexdigest()[:16])
        age = time.time() - int(t)
    except Exception:  # noqa: BLE001
        ok, age = False, 0
    if not ok or age < 4 or age > 86400:
        raise PermissionError('formulaire expiré, rechargez la page')
    ip = (request.headers.get('X-Forwarded-For') or request.remote_addr or '').split(',')[0].strip()
    now = time.time()
    h = [x for x in _ENVOIS.get(ip, []) if now - x < 3600]
    if len(h) >= 6:
        raise PermissionError('trop de demandes, appelez-nous au ' + (societe().get('phone') or ''))
    _ENVOIS[ip] = h + [now]


RE_MAIL = re.compile(r'^[^@\s]+@[^@\s]+\.[a-z]{2,}$', re.I)


def _client_valide(cl):
    cl = {k: (str(v).strip()[:200] if v is not None else '') for k, v in (cl or {}).items()}
    if not cl.get('nom') or not RE_MAIL.match(cl.get('email', '')) or len(re.sub(r'\D', '', cl.get('tel', ''))) < 9:
        raise ValueError('nom, e-mail et téléphone sont obligatoires')
    return cl


# ---------------------------------------------------------------- Odoo : devis + e-mails
def _partenaire(cl, adresse, soc):
    dom = [['email', '=ilike', cl['email']], ['company_id', 'in', [soc, False]], ['type', '=', 'contact']]
    ids = _call('res.partner', 'search', dom, limit=1, order='customer_rank desc, id', **_ctx(soc))
    if ids:
        pid = ids[0]
    else:
        nom = cl.get('societe') or cl['nom']
        vals = {'name': nom, 'email': cl['email'], 'phone': cl['tel'], 'company_id': soc, 'is_company': bool(cl.get('societe')),
                'street': adresse.get('rue') or '', 'zip': adresse.get('cp') or '', 'city': adresse.get('ville') or '',
                'comment': 'Créé par le site devis.chatelgranulats.com'}
        if cl.get('societe'):
            vals['comment'] += f"\nContact : {cl['nom']}"
        pid = _creer('res.partner', vals, soc)
    livr = _creer('res.partner', {'parent_id': pid, 'type': 'delivery', 'name': f"Chantier {adresse.get('ville') or ''}".strip(),
                                  'street': adresse.get('rue') or adresse.get('label') or '', 'zip': adresse.get('cp') or '',
                                  'city': adresse.get('ville') or '', 'phone': cl['tel'], 'company_id': soc}, soc)
    return pid, livr


def _mail(sujet, dest, corps, soc):
    s = societe()
    exp = s.get('email') or cfg()['email_bureau']
    mid = _creer('mail.mail', {'subject': sujet, 'email_to': dest, 'email_from': f"Chatel'Granulats <{exp}>", 'reply_to': exp,
                               'body_html': corps, 'auto_delete': False}, soc)
    try:
        _call('mail.mail', 'send', [mid])
    except Exception:  # noqa: BLE001
        pass   # reste en file, envoyé par le cron d'Odoo
    return mid


def _eur(v):
    return '—' if v is None else f"{v:,.2f} €".replace(',', ' ').replace('.', ',')


def _tableau(est):
    e = html.escape
    lignes = ''.join(f"<tr><td style='padding:4px 8px'>{e(l['nom'])}</td><td style='padding:4px 8px;text-align:right'>{l['qte']:g} {e(l['unite'])}</td>"
                     f"<td style='padding:4px 8px;text-align:right'>{_eur(l['pu'])}</td><td style='padding:4px 8px;text-align:right'>{_eur(l['total'])}</td></tr>"
                     for l in est['lignes'])
    pied = (f"<tr><td colspan='3' style='padding:4px 8px;text-align:right'><b>Total HT</b></td><td style='padding:4px 8px;text-align:right'><b>{_eur(est['ht'])}</b></td></tr>"
            f"<tr><td colspan='3' style='padding:4px 8px;text-align:right'>TVA</td><td style='padding:4px 8px;text-align:right'>{_eur(est['tva'])}</td></tr>"
            f"<tr><td colspan='3' style='padding:4px 8px;text-align:right'>Total TTC</td><td style='padding:4px 8px;text-align:right'>{_eur(est['ttc'])}</td></tr>") \
        if est['ht'] is not None else "<tr><td colspan='4' style='padding:4px 8px'><i>Prix confirmé par notre équipe</i></td></tr>"
    return (f"<table style='border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px' border='1' bordercolor='#ddd'>"
            f"<tr style='background:#f3f1ec'><th style='padding:4px 8px;text-align:left'>Désignation</th><th style='padding:4px 8px'>Qté</th>"
            f"<th style='padding:4px 8px'>PU HT</th><th style='padding:4px 8px'>Total HT</th></tr>{lignes}{pied}</table>")


SERVICES = {'livraison': 'Livraison de granulats', 'evacuation': 'Évacuation de déblais inertes',
            'affretement': 'Affrètement de camion', 'benne': 'Location de benne'}


def creer_demande(d):
    c = cfg(); soc = c['societe']; e = html.escape
    cl = _client_valide(d.get('client'))
    adr = {k: str(v)[:200] for k, v in (d.get('adresse') or {}).items() if v is not None}
    if not adr.get('label'):
        raise ValueError("adresse du chantier manquante")
    if d.get('service') in ('livraison', 'evacuation', 'benne', 'affretement') and adr.get('lat'):
        dist = distance_km(float(adr['lat']), float(adr['lon']))
        d['km'] = dist['km']
    est = estimer(d)
    jour = d.get('date') if d.get('date') in dates_livraison() else None
    creneau = d.get('creneau') if d.get('creneau') in c['creneaux'] else ''
    infos = [f"Demande web — {SERVICES.get(d['service'], d['service'])}",
             f"Chantier : {adr.get('label')} ({est['km']:.0f} km du Pautron)",
             f"Date souhaitée : {datetime.strptime(jour, '%Y-%m-%d').strftime('%d/%m/%Y') if jour else 'à convenir'} {creneau}",
             f"Client : {cl['nom']}{' — ' + cl['societe'] if cl.get('societe') else ''} — {cl['tel']} — {cl['email']}"
             + (' — se déclare PROFESSIONNEL' if cl.get('pro') in ('1', 'true', 'True', 'on') else '')]
    if d.get('service') == 'livraison' and d.get('m3'):
        infos.append(f"Saisi par le client : {float(d['m3']):g} m³ (converti en tonnes)")
    if cl.get('message'):
        infos.append('Message : ' + cl['message'][:1000])
    infos += est['notes']
    if c.get('test'):
        return {'ok': True, 'test': True, 'numero': 'TEST', 'estimation': est, 'infos': infos}
    pid, livr = _partenaire(cl, adr, soc)
    lignes = []
    for l in est['lignes']:
        v = {'name': l['nom'], 'product_uom_qty': l['qte'], 'price_unit': l['pu'] or 0}
        if l['id']:
            v['product_id'] = l['id']
        else:
            v.update(display_type='line_note', product_uom_qty=0, price_unit=0,
                     name=f"{l['nom']} — {l['qte']:g} {l['unite']} (prix à confirmer)")
        lignes.append((0, 0, v))
    vals = {'partner_id': pid, 'partner_invoice_id': pid, 'partner_shipping_id': livr, 'company_id': soc,
            'pricelist_id': c['liste_public'], 'origin': 'devis.chatelgranulats.com', 'client_order_ref': 'Demande web',
            'note': '<p>' + '<br/>'.join(e(x) for x in infos) + '</p>', 'order_line': lignes}
    if jour:
        h = {'6': 7, '9': 10, '13': 14}.get(creneau.split(' ')[0] if creneau else '', 8)
        vals['commitment_date'] = datetime.strptime(jour, '%Y-%m-%d').replace(hour=h, tzinfo=TZ).astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    oid = _creer('sale.order', vals, soc)
    num = _call('sale.order', 'read', [oid], ['name'], **_ctx(soc))[0]['name']
    lien = f"{os.environ.get('ODOO_URL', '').rstrip('/')}/odoo/action-sale.action_quotations_with_onboarding/{oid}"
    corps = (f"<div style='font-family:Arial,sans-serif;font-size:14px'><p><b>Nouvelle demande de devis web {e(num)}</b></p>"
             f"<p>{'<br/>'.join(e(x) for x in infos)}</p>{_tableau(est)}"
             f"<p><a href='{e(lien)}' style='background:#7A8B6E;color:#fff;padding:8px 14px;border-radius:6px;text-decoration:none'>Ouvrir le devis dans Odoo</a></p></div>")
    try:
        _mail(f"Demande de devis web {num} — {cl.get('societe') or cl['nom']}", c['email_bureau'], corps, soc)
        _call('sale.order', 'message_post', [oid], body=f"Demande reçue par le site devis.chatelgranulats.com.", **_ctx(soc))
    except Exception:  # noqa: BLE001
        pass
    if c.get('accuse_client'):
        s = societe()
        corps_cl = (f"<div style='font-family:Arial,sans-serif;font-size:14px'><p>Bonjour {e(cl['nom'])},</p>"
                    f"<p>Nous avons bien reçu votre demande <b>{e(num)}</b> ({e(SERVICES.get(d['service'], ''))}). "
                    f"Notre équipe la vérifie et vous confirme le prix et la date de livraison rapidement, en général le jour même.</p>"
                    f"{_tableau(est)}<p style='color:#666'>Estimation indicative HT, confirmée par Chatel'Granulats après vérification "
                    f"(accès chantier, disponibilité des camions).</p><p>Chatel'Granulats — {e(s.get('street', ''))} {e(s.get('zip', ''))} {e(s.get('city', ''))}"
                    f"<br/>{e(s.get('phone', ''))} — {e(s.get('email', ''))}</p></div>")
        try:
            _mail(f"Votre demande de devis {num} — Chatel'Granulats", cl['email'], corps_cl, soc)
        except Exception:  # noqa: BLE001
            pass
    return {'ok': True, 'numero': num, 'estimation': est}


# ---------------------------------------------------------------- domaine dédié
@bp.before_app_request
def _hote_dedie():
    h = (request.host or '').split(':')[0].lower()
    if h in HOTES and not request.path.startswith('/devis'):
        if request.path == '/robots.txt':
            return robots()
        if request.path == '/sitemap.xml':
            return sitemap()
        return redirect('/devis' + (request.full_path if request.query_string else request.path), code=301)
    return None


URL_PUBLIQUE = 'https://devis.chatelgranulats.com'


def url_publique(endpoint, **kw):
    """URL absolue sur le domaine public (balises canonical, sitemap, Open Graph), quel que soit l'hôte servi."""
    return URL_PUBLIQUE + url_for(endpoint, **kw)


@bp.route('/robots.txt')
def robots():
    return Response(f"User-agent: *\nAllow: /devis/\nDisallow: /devis/api/\nSitemap: {URL_PUBLIQUE}/sitemap.xml\n", mimetype='text/plain')


@bp.route('/sitemap.xml')
def sitemap():
    urls = [(url_publique('chatel_devis.accueil'), '1.0'), (url_publique('chatel_devis.parcours'), '0.9'),
            (url_publique('chatel_devis.ressources'), '0.6')]
    urls += [(url_publique('chatel_devis.page', page=p), '0.8' if p in ('produits', 'services', 'usages') else '0.5')
             for p in PAGES if p not in ('mentions-legales', 'cgv', 'ressources')]
    urls += [(url_publique('chatel_devis.article', slug=a['slug']), '0.6') for a in ARTICLES]
    corps = ''.join(f'<url><loc>{html.escape(u)}</loc><priority>{p}</priority></url>' for u, p in urls)
    return Response(f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{corps}</urlset>',
                    mimetype='application/xml')


# ---------------------------------------------------------------- pages
PAGES = {
    'services': 'Nos services', 'usages': 'Usages', 'pour-qui': 'Pour qui ?', 'faq': 'Questions fréquentes',
    'contact': 'Contact', 'recrutement': 'Recrutement', 'espace-pro': 'Espace pro', 'mentions-legales': 'Mentions légales',
    'cgv': 'Conditions générales de vente', 'produits': 'Nos produits', 'ressources': 'Ressources',
}

ARTICLES = [
    {'slug': 'isdi-isdnd-isdd-differences', 'titre': 'ISDI, ISDND, ISDD : quelles différences ?',
     'chapo': "Inertes, non dangereux, dangereux : où vont vos déchets de chantier, et pourquoi ça change le prix."},
    {'slug': 'double-flux-livrer-evacuer', 'titre': 'Double flux : livrer puis évacuer avec le même camion',
     'chapo': "Le camion qui vous livre repart chargé de vos déblais : moins de rotations, moins de CO₂, une facture plus légère."},
    {'slug': 'calculer-tonnage-granulats', 'titre': 'Combien de tonnes commander ? Le calcul en 3 étapes',
     'chapo': "Surface × épaisseur × densité : la méthode simple pour ne commander ni trop ni trop peu."},
    {'slug': 'quel-granulat-pour-quel-usage', 'titre': 'Quel granulat pour quel usage ?',
     'chapo': "Sable 0/4, gravier 6/10, grave 0/31,5… le bon matériau pour un béton, une allée, une tranchée ou un drainage."},
]


# titre SEO (balise <title>, ~60 car.) et description (~155 car.) par page
SEO = {
    'accueil': ("Granulats livrés à Châtellerault, prix en 2 min | Chatel'Granulats",
                "Sable, gravier, grave, terre, galets livrés autour de Châtellerault (86). Prix livré en 2 minutes, livraison sous 48 h, évacuation de déblais."),
    'parcours': ("Devis granulats en ligne, prix livré | Chatel'Granulats",
                 "Calculez votre prix livré : choisissez le service, le matériau, la quantité et la date. Livraison de granulats et évacuation de déblais autour de Châtellerault."),
    'produits': ("Sable, gravier, galets : prix à la tonne | Chatel'Granulats",
                 "Sables, graviers, graves, terre végétale, galets, ardoise et pierres de décoration. Prix HT à la tonne, livrés ou départ carrière."),
    'services': ("Livraison granulats, évacuation déblais | Chatel'Granulats",
                 "Livraison de granulats en camion benne, reprise de déblais inertes, affrètement de camion avec chauffeur et location de benne autour de Châtellerault."),
    'usages': ("Granulats pour béton, allée, drainage | Chatel'Granulats",
               "Béton, allée, drainage, tranchée, remblai, décoration : trouvez le bon matériau pour votre projet et obtenez son prix livré."),
    'pour-qui': ("Granulats pour particuliers et pros du BTP | Chatel'Granulats",
                 "Particuliers, maçons, terrassiers, paysagistes, collectivités : livraison de granulats et évacuation de déblais adaptées à chaque besoin."),
    'faq': ("FAQ livraison de granulats et déblais | Chatel'Granulats", None),
    'contact': ("Contact — carrière du Pautron, Châtellerault | Chatel'Granulats", None),
    'recrutement': ("Recrutement chauffeurs PL, engins | Chatel'Granulats", None),
    'espace-pro': ("Compte pro : tarifs négociés, 30 jours | Chatel'Granulats", None),
    'ressources': ("Conseils granulats et déblais | Chatel'Granulats", None),
    'mentions-legales': ("Mentions légales | Chatel'Granulats", "Mentions légales et données personnelles du site Chatel'Granulats."),
    'cgv': ("Conditions générales de vente | Chatel'Granulats", "Conditions générales de vente de Chatel'Granulats."),
}


def _rendu(gabarit, cle=None, **kw):
    s = societe()
    seo = SEO.get(cle or '', (None, None))
    point = request.endpoint or 'chatel_devis.accueil'
    canon = URL_PUBLIQUE + request.path
    return render_template(f'chatel/{gabarit}', soc=s, c=cfg(), deco=DECO, pages=PAGES, articles=ARTICLES, jeton=jeton_formulaire(),
                           seo_titre=seo[0], seo_desc=seo[1], canonique=canon, point=point, url_publique=url_publique,
                           tel_lien='tel:+33' + re.sub(r'\D', '', s.get('phone') or '0549905762')[1:], **kw)


@bp.route('/')
def accueil():
    try:
        cat = catalogue()
    except Exception:  # noqa: BLE001
        cat = {'produits': []}
    familles = []
    for p in cat['produits']:
        f = next((x for x in familles if x['nom'] == p['famille']), None)
        if not f:
            familles.append({'nom': p['famille'], 'n': 1, 'img': p['tmpl'] if p['img'] else None, 'prix': p['prix_t']})
        else:
            f['n'] += 1; f['prix'] = min(f['prix'], p['prix_t'])
            f['img'] = f['img'] or (p['tmpl'] if p['img'] else None)
    return _rendu('accueil.html', 'accueil', familles=familles)


@bp.route('/parcours')
def parcours():
    return _rendu('parcours.html', 'parcours', titre='Devis en ligne')


@bp.route('/ressources')
def ressources():
    return _rendu('ressources.html', 'ressources', titre='Ressources')


@bp.route('/ressources/<slug>')
def article(slug):
    a = next((x for x in ARTICLES if x['slug'] == slug), None)
    if not a:
        abort(404)
    return _rendu(f'article_{slug.replace("-", "_")}.html', titre=a['titre'], article=a)


@bp.route('/<page>')
def page(page):
    if page not in PAGES:
        abort(404)
    return _rendu(f'{page.replace("-", "_")}.html', page, titre=PAGES[page])


# ---------------------------------------------------------------- API
@bp.route('/api/catalogue')
def api_catalogue():
    cat = catalogue(); c = cfg()
    km = request.args.get('km', type=float)
    prods = []
    for p in cat['produits']:
        q = dict(p)
        if km is not None:
            q['min'], q['max'] = fourchette(p['prix_t'], km)
        prods.append(q)
    r = jsonify({'produits': prods, 'usages': [u for u, _ in c['usages']], 'familles': c['familles_ordre'],
                 'camions': c['camions'], 'affretement': c['affretement'], 'bennes': c['bennes'], 'deblais': c['deblais'],
                 'creneaux': c['creneaux'], 'dates': dates_livraison(), 'zone_km': c['zone_km'], 'km_mini': c['km_mini'],
                 'evacuation': cat['evacuation'], 'contrib_t': contributions_t(), 'maj': cat['maj'], 'deco': DECO})
    r.headers['Cache-Control'] = 'public, max-age=120'
    return r


@bp.route('/api/distance')
def api_distance():
    lat, lon = request.args.get('lat', type=float), request.args.get('lon', type=float)
    if lat is None or lon is None or not (41 < lat < 52 and -6 < lon < 10):
        return jsonify({'erreur': 'adresse non localisée'}), 400
    return jsonify(distance_km(lat, lon))


@bp.route('/api/estimer', methods=['POST'])
def api_estimer():
    d = request.get_json(silent=True) or {}
    try:
        return jsonify(estimer(d))
    except ValueError as ex:
        return jsonify({'erreur': str(ex)}), 400


@bp.route('/api/demande', methods=['POST'])
def api_demande():
    d = request.get_json(silent=True) or {}
    try:
        _controle_envoi(d)
        return jsonify(creer_demande(d))
    except (ValueError, PermissionError) as ex:
        return jsonify({'erreur': str(ex)}), 400
    except Exception as ex:  # noqa: BLE001
        return jsonify({'erreur': "l'envoi a échoué, appelez-nous au " + (societe().get('phone') or ''), 'detail': str(ex)[:200]}), 500


@bp.route('/api/message', methods=['POST'])
def api_message():
    """Formulaires Contact / Espace pro / Recrutement : e-mail au bureau."""
    d = request.get_json(silent=True) or {}
    try:
        _controle_envoi(d)
        cl = _client_valide(d)
        objet = {'contact': 'Contact', 'pro': 'Demande de compte pro', 'emploi': 'Candidature'}.get(d.get('type'), 'Contact')
        e = html.escape
        corps = (f"<div style='font-family:Arial,sans-serif;font-size:14px'><p><b>{e(objet)} — site devis.chatelgranulats.com</b></p>"
                 + ''.join(f"<p><b>{e(k)}</b> : {e(str(v))[:2000]}</p>" for k, v in cl.items() if v) + '</div>')
        if cfg().get('test'):
            return jsonify({'ok': True, 'test': True})
        _mail(f"{objet} — {cl.get('societe') or cl['nom']}", cfg()['email_bureau'], corps, cfg()['societe'])
        return jsonify({'ok': True})
    except (ValueError, PermissionError) as ex:
        return jsonify({'erreur': str(ex)}), 400
    except Exception:  # noqa: BLE001
        return jsonify({'erreur': "l'envoi a échoué, appelez-nous au " + (societe().get('phone') or '')}), 500


_SVG_VIDE = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 120"><rect width="160" height="120" fill="#EDE8DF"/>'
             '<g fill="#C9BFAE">' + ''.join(f'<circle cx="{x}" cy="{y}" r="{r}"/>' for x, y, r in
                                            ((40, 80, 14), (70, 88, 10), (98, 78, 16), (124, 90, 9), (58, 62, 8), (88, 60, 7), (112, 64, 6))) + '</g></svg>')


@bp.route('/img/<int:tmpl>')
def image(tmpl):
    now = time.time()
    c = _IMG.get(tmpl)
    if not c or now - c[0] > 86400:
        data, mime = None, 'image/svg+xml'
        try:
            r = _call('product.template', 'read', [tmpl], ['image_512'], **_ctx(cfg()['societe']))
            if r and r[0].get('image_512'):
                data = base64.b64decode(r[0]['image_512'])
                mime = 'image/webp' if data[:4] == b'RIFF' else ('image/png' if data[:4] == b'\x89PNG' else 'image/jpeg')
        except Exception:  # noqa: BLE001
            pass
        c = (now, data or _SVG_VIDE.encode(), mime)
        if len(_IMG) > 400:
            _IMG.clear()
        _IMG[tmpl] = c
    return Response(c[1], mimetype=c[2], headers={'Cache-Control': 'public, max-age=86400'})


@bp.route('/api/rafraichir')
def api_rafraichir():
    """Vide le cache (après modification des prix ou du paramètre chatel.devis_cfg). Jeton : ?k=<maquignon.tarifs_key>."""
    k = request.args.get('k') or ''
    try:
        ok = bool(k) and k == (_call('ir.config_parameter', 'get_param', 'maquignon.tarifs_key', '') or '')
    except Exception:  # noqa: BLE001
        ok = False
    if not ok:
        abort(403)
    with _CACHE_LOCK:
        _CACHE.clear()
    _IMG.clear(); _DIST.clear()
    t = time.time(); n = len(catalogue()['produits'])
    return jsonify({'ok': True, 'produits': n, 'secondes': round(time.time() - t, 2)})
