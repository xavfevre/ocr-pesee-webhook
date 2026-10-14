# -*- coding: utf-8 -*-
"""Tarifs 2027 SARL Maquignon, PIERRES seulement, en deux vagues (Xavier, 14/10/2026 : « deux vagues d'augmentation
jusqu'en janvier », « on va faire que la pierre »). Source : fichier d'Isabelle du 07/10/2026
(…_v3_sans_non_vendus.xlsx, onglet « Grille 2027 (2) » avec la colonne « PRO 01/11/2026 », + onglets clients).

Ce qui est créé dans Odoo (société 1) :
  - liste « Tarif Pro 2027 » : repli = formule 0 % sur « Tarif Pro 2026 » (299) -> rien ne change avant le 1er novembre
    ni sur les autres familles ; pour chaque variante pierre : prix fixe vague 1 du 01/11 au 31/12/2026 (PRO 01/11/2026)
    puis prix fixe vague 2 à partir du 01/01/2027 (PRO 2027) ;
  - liste « Tarif Particulier 2027 » : repli = formule 0 % sur le prix fiche ; pierres : vague 1 = PARTICULIER 2027 ÷ 1,1
    (01/11 -> 31/12), vague 2 = PARTICULIER 2027 (dès 01/01/2027) ;
  - onglets clients (lignes pierres seulement) : sur la liste propre du client (créée si besoin, repli -> Tarif Pro 2027) :
    prix fixe sans date = prix client 2026 (inchangé jusqu'au 31/12) et prix fixe CLIENT 2027 (+10 %) dès 01/01/2027 ;
  - les clients de « Tarif Pro 2026 » passent sur « Tarif Pro 2027 », ceux de « Tarif Public 2026 » sur « Tarif
    Particulier 2027 », la liste par défaut de la société devient « Tarif Particulier 2027 ».
Les articles à 1 € dans la grille (à l'unité, sur devis) sont ignorés.
   python tarifs_pierres_2027.py dry     -> montre tout, n'écrit rien
   python tarifs_pierres_2027.py apply   -> crée (état enregistré dans tarifs_pierres_2027_etat.json)
   python tarifs_pierres_2027.py etat    -> vérifie ce qui est en place
   python tarifs_pierres_2027.py retour  -> annule tout (listes, règles, clients remis sur leur ancienne liste)
Identifiants attendus dans l'environnement : ODOO_USER, ODOO_PWD. Fichier source : argument 2 ou v3.xlsx à côté du script."""
import os, sys, re, json, xmlrpc.client
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8')
from openpyxl import load_workbook

ICI = os.path.dirname(os.path.abspath(__file__))
MODE = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
FICHIER = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ICI, 'v3.xlsx')
ETAT = os.path.join(ICI, 'tarifs_pierres_2027_etat.json')
SOC = 1
LISTE_PRO_2026, LISTE_PUBLIC_2026 = 299, 302
NOM_PRO, NOM_PART = 'Tarif Pro 2027', 'Tarif Particulier 2027'
# bornes en UTC (Paris = UTC+1 en hiver)
V1_DEBUT, V1_FIN, V2_DEBUT = '2026-10-31 23:00:00', '2026-12-31 22:59:59', '2026-12-31 23:00:00'

U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common').authenticate(D, us, p, {})
assert uid, 'authentification refusée'
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object')
CTX = {'allowed_company_ids': [SOC], 'company_id': SOC, 'active_test': False}


def x(mo, me, *a, **k):
    k = dict(k); ctx = dict(CTX); ctx.update(k.pop('context', {})); k['context'] = ctx
    try:
        return m.execute_kw(D, uid, p, mo, me, list(a), k)
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in str(e):
            return None
        raise


one = lambda v: v[0] if isinstance(v, list) else v


def nombre(v):
    return v if isinstance(v, (int, float)) else None


# ---------------------------------------------------------------- lecture du fichier
wb = load_workbook(FICHIER, data_only=False)
w = wb['Grille 2027 (2)']
pierres, cat = [], None
for r in range(2, w.max_row + 1):
    a = w.cell(r, 1).value
    if isinstance(a, str) and '›' in a:
        cat = a; continue
    if not a or not cat or not cat.startswith('PIERRES'):
        continue
    K, L, M, O = (w.cell(r, c).value for c in (11, 12, 13, 15))
    if isinstance(L, str) and L.startswith('='):
        L = (M / 1.1) if ('/1.1' in L and nombre(M)) else (K * 1.03 if nombre(K) else None)
    pierres.append({'art': a, 'cat': cat.split('›')[-1].strip(), 'pro_2026': nombre(K), 'pro_v1': nombre(L), 'pro_2027': nombre(M), 'part_2027': nombre(O)})

prods = x('product.product', 'search_read', [['product_tmpl_id.company_id', 'in', [SOC, False]]], fields=['default_code', 'display_name', 'lst_price', 'active'], limit=5000)
by_code = {pr['default_code']: pr for pr in prods if pr['default_code']}
nom_net = lambda s: re.sub(r'^\[[^\]]+\] ', '', s).replace(' (archivé)', '').strip()
by_name = {}
for pr in prods:
    by_name.setdefault(nom_net(pr['display_name']), []).append(pr)


def apparier(art):
    mm = re.match(r'\[([^\]]+)\] ', art)
    if mm and mm.group(1) in by_code:
        return by_code[mm.group(1)]
    c = by_name.get(nom_net(art), [])
    c = [pr for pr in c if pr['active']] or c
    return c[0] if len(c) == 1 else None


ignores, actifs = [], []
for q in pierres:
    pr = apparier(q['art'])
    if not pr:
        ignores.append((q['art'], 'article Odoo introuvable')); continue
    if not q['pro_2027'] or q['pro_2027'] <= 1 or not q['part_2027'] or q['part_2027'] <= 1:
        ignores.append((q['art'], 'prix à 1 € = sur devis')); continue
    q.update(pid=pr['id'], fiche=pr['lst_price'], actif=pr['active'], pro_v1=round(q['pro_v1']), pro_v2=round(q['pro_2027']),
             part_v1=round(q['part_2027'] / 1.1), part_v2=round(q['part_2027']))
    actifs.append(q)
pids = {q['pid'] for q in actifs}

# onglets clients : lignes pierres seulement
clients = []
for s in wb.sheetnames:
    if s in ('Grille 2027', 'Grille 2027 (2)', 'Méthode', 'Remarques', 'Remises', 'Lisez-moi'):
        continue
    ws = wb[s]; lignes = []
    for r in range(2, ws.max_row + 1):
        a = ws.cell(r, 1).value
        if not isinstance(a, str) or a.startswith('CA 2026'):
            continue
        pr = apparier(a)
        if not pr or pr['id'] not in pids:
            continue
        p26, p27 = nombre(ws.cell(r, 4).value), nombre(ws.cell(r, 8).value)
        if p26 and p27:
            lignes.append({'art': a, 'pid': pr['id'], 'prix_2026': round(p26, 2), 'prix_2027': round(p27)})
    if lignes:
        clients.append({'onglet': s, 'lignes': lignes})

# ---------------------------------------------------------------- partenaires des onglets clients
def partenaire(onglet):
    nom = onglet.strip()
    cands = x('res.partner', 'search_read', [['name', '=ilike', nom + '%'], ['is_company', '=', True]], fields=['name', 'specific_property_product_pricelist'], limit=5)
    if not cands:
        cands = x('res.partner', 'search_read', [['name', 'ilike', nom[:20]], ['parent_id', '=', False]], fields=['name', 'specific_property_product_pricelist'], limit=5)
    return cands


for c in clients:
    c['partenaires'] = partenaire(c['onglet'])
    if len(c['partenaires']) > 1:
        def nb_fact(pp):
            return x('account.move', 'search_count', [['partner_id', 'child_of', pp['id']], ['move_type', '=', 'out_invoice'], ['state', '=', 'posted'], ['invoice_date', '>=', '2026-01-01']])
        c['partenaires'] = sorted(c['partenaires'], key=lambda pp: -nb_fact(pp))[:1]

listes = {l['id']: l for l in x('product.pricelist', 'search_read', [['company_id', 'in', [SOC, False]]], fields=['name', 'active', 'item_ids', 'currency_id'])}
n_pro = x('res.partner', 'search_count', [['specific_property_product_pricelist', '=', LISTE_PRO_2026]])
n_pub = x('res.partner', 'search_count', [['specific_property_product_pricelist', '=', LISTE_PUBLIC_2026]])

print('Pierres : %d lignes dans la grille, %d chargées, %d ignorées' % (len(pierres), len(actifs), len(ignores)))
for a, why in ignores:
    print('   ignoré : %s (%s)' % (a, why))
print('%-62s %8s | pro 2026 %8s -> 01/11 %6s -> 2027 %6s | part 01/11 %6s -> 2027 %6s' % ('article', 'fiche', '', '', '', '', ''))
for q in actifs:
    print('%-62s %8.2f | pro 2026 %8s -> 01/11 %6d -> 2027 %6d | part 01/11 %6d -> 2027 %6d%s' % (q['art'][:62], q['fiche'] or 0, q['pro_2026'], q['pro_v1'], q['pro_v2'], q['part_v1'], q['part_v2'], '' if q['actif'] else '  (archivé)'))
print('\nOnglets clients avec des lignes pierres : %d' % len(clients))
for c in clients:
    print('  %s -> partenaire : %s' % (c['onglet'], [(pp['id'], pp['name'][:40], (pp['specific_property_product_pricelist'] and pp['specific_property_product_pricelist'][1][:28]) or 'aucune liste', 'liste propre conservée' if (pp['specific_property_product_pricelist'] and pp['specific_property_product_pricelist'][0] not in (LISTE_PRO_2026, LISTE_PUBLIC_2026, 12)) else ('nouvelle liste, repli ' + ('Particulier 2027' if (pp['specific_property_product_pricelist'] and pp['specific_property_product_pricelist'][0] == LISTE_PUBLIC_2026) else 'Pro 2027'))) for pp in c['partenaires']]))
    for l in c['lignes']:
        print('      %-58s 2026 %8.2f -> 2027 %6d' % (l['art'][:58], l['prix_2026'], l['prix_2027']))
print('\nClients à déplacer : %d de « Tarif Pro 2026 » -> « %s », %d de « Tarif Public 2026 » -> « %s »' % (n_pro, NOM_PRO, n_pub, NOM_PART))
print('Règles à créer : pro %d, particulier %d, clients %d' % (2 * len(actifs), 2 * len(actifs), 2 * sum(len(c['lignes']) for c in clients)))

if MODE == 'etat':
    if os.path.exists(ETAT):
        e = json.load(open(ETAT, encoding='utf-8'))
        for k in ('liste_pro', 'liste_part'):
            l = x('product.pricelist', 'read', [e[k]], ['name', 'item_ids'])[0]; print('%s : %s, %d règles, %d clients' % (k, l['name'], len(l['item_ids']), x('res.partner', 'search_count', [['specific_property_product_pricelist', '=', e[k]]])))
        print('défaut société :', x('ir.default', 'read', [222], ['json_value']))
    else:
        print('rien de chargé (pas de fichier état)')
    sys.exit()
if MODE == 'retour':
    assert os.path.exists(ETAT), 'rien à annuler'
    e = json.load(open(ETAT, encoding='utf-8'))
    for pid_, old in e['partenaires'].items():
        x('res.partner', 'write', [int(pid_)], {'specific_property_product_pricelist': old or False})
    x('ir.default', 'write', [222], {'json_value': str(LISTE_PUBLIC_2026)})
    for lid, base in e.get('bases_clients', {}).items():
        x('product.pricelist.item', 'write', [int(lid)], {'base_pricelist_id': base})
    if e.get('regles_clients'):
        x('product.pricelist.item', 'unlink', e['regles_clients'])
    if e.get('listes_clients_creees'):
        x('product.pricelist', 'unlink', e['listes_clients_creees'])
    x('product.pricelist', 'unlink', [e['liste_pro'], e['liste_part']])
    os.remove(ETAT); print('tout annulé : listes et règles supprimées, %d clients remis sur leur ancienne liste' % len(e['partenaires']))
    sys.exit()
if MODE != 'apply':
    print('\nSimulation : rien écrit. Relancer avec « apply ».'); sys.exit()
assert not os.path.exists(ETAT), 'déjà chargé (fichier état présent) : « retour » d abord'
assert all(len(c['partenaires']) == 1 for c in clients), 'un onglet client ne correspond pas à un seul partenaire : corriger avant apply'

# ---------------------------------------------------------------- création
devise = listes[LISTE_PRO_2026]['currency_id'][0]
e = {'date': datetime.now().isoformat(), 'partenaires': {}, 'listes_clients_creees': [], 'regles_clients': [], 'bases_clients': {}}
e['liste_pro'] = one(x('product.pricelist', 'create', [{'name': NOM_PRO, 'company_id': SOC, 'currency_id': devise, 'sequence': 5}]))
e['liste_part'] = one(x('product.pricelist', 'create', [{'name': NOM_PART, 'company_id': SOC, 'currency_id': devise, 'sequence': 6}]))
regles = [{'pricelist_id': e['liste_pro'], 'applied_on': '3_global', 'compute_price': 'formula', 'base': 'pricelist', 'base_pricelist_id': LISTE_PRO_2026, 'price_discount': 0},
          {'pricelist_id': e['liste_part'], 'applied_on': '3_global', 'compute_price': 'formula', 'base': 'list_price', 'price_discount': 0}]
for q in actifs:
    for lid, v1, v2 in ((e['liste_pro'], q['pro_v1'], q['pro_v2']), (e['liste_part'], q['part_v1'], q['part_v2'])):
        regles.append({'pricelist_id': lid, 'applied_on': '0_product_variant', 'product_id': q['pid'], 'compute_price': 'fixed', 'fixed_price': v1, 'date_start': V1_DEBUT, 'date_end': V1_FIN})
        regles.append({'pricelist_id': lid, 'applied_on': '0_product_variant', 'product_id': q['pid'], 'compute_price': 'fixed', 'fixed_price': v2, 'date_start': V2_DEBUT})
x('product.pricelist.item', 'create', regles)
print('listes créées : pro %d, particulier %d, %d règles' % (e['liste_pro'], e['liste_part'], len(regles)))
# clients à prix spécifiques
for c in clients:
    pp = c['partenaires'][0]; cur = pp['specific_property_product_pricelist'] and pp['specific_property_product_pricelist'][0]
    if cur and cur not in (LISTE_PRO_2026, LISTE_PUBLIC_2026, 12, e['liste_pro'], e['liste_part']):
        lid = cur          # liste propre existante : on y ajoute seulement les règles pierres, sa base n'est pas touchée
    else:
        repli = e['liste_part'] if cur == LISTE_PUBLIC_2026 else e['liste_pro']
        lid = one(x('product.pricelist', 'create', [{'name': 'Tarif %s 2027' % pp['name'][:40], 'company_id': SOC, 'currency_id': devise, 'sequence': 7}]))
        e['listes_clients_creees'].append(lid)
        e['regles_clients'] += [one(x('product.pricelist.item', 'create', [{'pricelist_id': lid, 'applied_on': '3_global', 'compute_price': 'formula', 'base': 'pricelist', 'base_pricelist_id': repli, 'price_discount': 0}]))]
        e['partenaires'][str(pp['id'])] = cur
        x('res.partner', 'write', [pp['id']], {'specific_property_product_pricelist': lid})
    for l in c['lignes']:
        deja = x('product.pricelist.item', 'search', [['pricelist_id', '=', lid], ['product_id', '=', l['pid']], ['date_start', '=', False], ['compute_price', '=', 'fixed']])
        if not deja:
            e['regles_clients'].append(one(x('product.pricelist.item', 'create', [{'pricelist_id': lid, 'applied_on': '0_product_variant', 'product_id': l['pid'], 'compute_price': 'fixed', 'fixed_price': l['prix_2026']}])))
        e['regles_clients'].append(one(x('product.pricelist.item', 'create', [{'pricelist_id': lid, 'applied_on': '0_product_variant', 'product_id': l['pid'], 'compute_price': 'fixed', 'fixed_price': l['prix_2027'], 'date_start': V2_DEBUT}])))
    print('client %s : liste %d, %d lignes pierres' % (pp['name'][:40], lid, len(c['lignes'])))
# déplacement des clients
for old, new in ((LISTE_PRO_2026, e['liste_pro']), (LISTE_PUBLIC_2026, e['liste_part'])):
    ids = x('res.partner', 'search', [['specific_property_product_pricelist', '=', old]])
    for i in range(0, len(ids), 200):
        x('res.partner', 'write', ids[i:i + 200], {'specific_property_product_pricelist': new})
    for i in ids:
        e['partenaires'].setdefault(str(i), old)
    print('%d clients déplacés de %d vers %d' % (len(ids), old, new))
x('ir.default', 'write', [222], {'json_value': str(e['liste_part'])})
json.dump(e, open(ETAT, 'w', encoding='utf-8'), indent=1)
print('terminé ; état enregistré dans', ETAT)
