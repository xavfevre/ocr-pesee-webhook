# -*- coding: utf-8 -*-
"""Tarifs SARL MAQUIGNON v3 (factures validées 2026) :
 - PRO 2027 = prix pro observé (chaque client compte pour un) × (1 + hausse) ;
 - PARTICULIER 2027 = PRO 2027 ÷ (1 − remise pro de la famille) : une logique de remise unique par famille ;
 - un onglet par client à prix spécifiques (prix différent du pro observé de plus de 2 %) avec sa colonne +hausse.
Usage : python grilles_v3.py [hausse%] [remise pierres%] [remise granulats%] [remise transport%] [remise prestations%]"""
import os, ssl, sys, re, xmlrpc.client, collections, datetime, statistics
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
sys.stdout.reconfigure(encoding='utf-8')
args = [float(a.replace(',', '.')) for a in sys.argv[1:]]
HAUSSE = args[0] if args else 10.0
PART_MODE = os.environ.get('PART_MODE', 'remise')
PRO_MODE = os.environ.get('PRO_MODE', 'pratique')   # 'ecart' : pro = particulier cible × (1 − remise), plancher pratiqué + hausse
PART_FIXE = dict(kv.split('=') for kv in os.environ.get('PART_FIXE', '').split(',') if '=' in kv)   # ex. TUF0000-PS=1500   # 'fiche' : particulier = prix fiche +hausse, avec un écart minimum avec le pro
FAMS = ['Pierres', 'Granulats / terre', 'Transport / location', 'Prestations / divers']
REMISE = dict(zip(FAMS, [8.0, 5.0, 0.0, 5.0]))
for i, f in enumerate(FAMS):
    if len(args) > i + 1:
        REMISE[f] = args[i + 1]
DEPUIS = '2026-01-01'
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
ctx = {'allowed_company_ids': [1], 'active_test': False}
today = datetime.date.today(); today_s = today.isoformat()
PUBLIC, PRO = 302, 299
LISTES_CLIENT = [1678, 1680, 1681, 1691, 1692, 306, 1676, 74, 158, 159, 160, 286, 287, 288, 289, 290, 295, 296]


def famille(n):
    n = n.lower()
    if any(t in n for t in ('pré-sciée', 'pre-sciee', 'tranche', 'bloc', 'tuffeau', 'haims', 'migné', 'richemont', 'tervoux', 'sireuil')):
        return 'Pierres'
    if any(t in n for t in ('transport', 'location', 'transfert')):
        return 'Transport / location'
    if any(t in n for t in ('gobetage', 'gravier', 'concass', 'sable', 'terre', 'décharge', 'béton', 'remblai')):
        return 'Granulats / terre'
    return 'Prestations / divers'


def arrondi(v, fam, unite=''):
    """Prix sans virgule, sauf les granulats et tout ce qui se vend à la tonne (au 0,05 €)."""
    if v is None:
        return None
    if fam == 'Granulats / terre' or str(unite).lower().startswith('tonne') or str(unite).lower() == 't':
        return round(v * 20) / 20
    return float(round(v))


# ---------- articles + Tarif Pro 2026 (repli)
prods = x('product.product', 'search_read', [['sale_ok', '=', True], ['company_id', 'in', [1, False]]],
          fields=['default_code', 'display_name', 'lst_price', 'standard_price', 'categ_id', 'uom_id', 'product_tmpl_id', 'active'], limit=5000, context=ctx)
prod = {pr['id']: pr for pr in prods}
prod_by_code = {pr['default_code']: pr for pr in prods if pr['default_code']}
items = x('product.pricelist.item', 'search_read', [['pricelist_id', 'in', [PUBLIC, PRO]]],
          fields=['pricelist_id', 'applied_on', 'product_tmpl_id', 'product_id', 'categ_id', 'compute_price', 'fixed_price', 'percent_price', 'base',
                  'base_pricelist_id', 'price_discount', 'price_surcharge', 'price_round', 'min_quantity', 'date_start', 'date_end'], limit=20000, context=ctx)
byp = collections.defaultdict(list)
for it in items:
    byp[it['pricelist_id'][0]].append(it)
cats = {ct['id']: ct['parent_path'] for ct in x('product.category', 'search_read', [], fields=['parent_path'], context=ctx)}
ORDER = {'0_product_variant': 0, '1_product': 1, '2_product_category': 2, '3_global': 3}


def prix(pl_id, pr, depth=0):
    if depth > 5:
        return pr['lst_price']
    its = [it for it in byp[pl_id] if (not it['date_start'] or it['date_start'][:10] <= today_s) and (not it['date_end'] or it['date_end'][:10] >= today_s) and (it['min_quantity'] or 0) <= 1]
    for it in sorted(its, key=lambda it: (ORDER[it['applied_on']], -(it['min_quantity'] or 0), -(it['categ_id'][0] if it['categ_id'] else 0), -it['id'])):
        a = it['applied_on']
        if a == '0_product_variant' and (not it['product_id'] or it['product_id'][0] != pr['id']):
            continue
        if a == '1_product' and (not it['product_tmpl_id'] or it['product_tmpl_id'][0] != pr['product_tmpl_id'][0]):
            continue
        if a == '2_product_category' and not (it['categ_id'] and pr['categ_id'] and cats.get(pr['categ_id'][0], '').startswith(cats.get(it['categ_id'][0], '#'))):
            continue
        base = it.get('base') or 'list_price'
        bp = prix(it['base_pricelist_id'][0], pr, depth + 1) if (base == 'pricelist' and it.get('base_pricelist_id')) else (pr['standard_price'] if base == 'standard_price' else pr['lst_price'])
        if it['compute_price'] == 'fixed':
            return it['fixed_price'] or 0.0
        if it['compute_price'] == 'percentage':
            return bp * (1 - (it['percent_price'] or 0) / 100)
        v = bp * (1 - (it.get('price_discount') or 0) / 100)
        if it.get('price_round'):
            v = round(v / it['price_round']) * it['price_round']
        return v + (it.get('price_surcharge') or 0)
    return pr['lst_price']


# ---------- factures
aml = x('account.move.line', 'search_read', [['move_id.move_type', '=', 'out_invoice'], ['parent_state', '=', 'posted'], ['company_id', '=', 1], ['date', '>=', DEPUIS],
                                             ['display_type', '=', 'product'], ['product_id', '!=', False], ['quantity', '>', 0]],
        fields=['product_id', 'quantity', 'price_subtotal', 'product_uom_id', 'partner_id'], limit=200000, context=ctx)
pids = sorted({l['partner_id'][0] for l in aml if l['partner_id']})
CIV = 'x_studio_civilit_type_socit'
pfields = ['name', 'is_company', 'vat', 'commercial_partner_id', CIV, 'specific_property_product_pricelist']
parts = {pt['id']: pt for pt in x('res.partner', 'read', pids, fields=pfields, context=ctx)} if pids else {}
cps = sorted({pt['commercial_partner_id'][0] for pt in parts.values()} - set(parts))
for pt in (x('res.partner', 'read', cps, fields=pfields, context=ctx) if cps else []):
    parts[pt['id']] = pt
PART_CIV = {'M.', 'Mme', 'M. & Mme', 'M', 'Mr', 'Mlle', 'M. et Mme', 'Monsieur', 'Madame', 'Melle'}


def groupe(cp):
    civ = (cp.get(CIV) or '').strip()
    if civ:
        return 'Particulier' if civ in PART_CIV else 'Professionnel'
    return 'Professionnel' if (cp['is_company'] or cp['vat']) else 'Particulier'


obs = collections.defaultdict(list)          # article -> [(pu, qté, client_id, groupe, montant)]
ca_client = collections.Counter(); cp_name = {}
for l in aml:
    pr = prod.get(l['product_id'][0])
    if not pr or not l['partner_id']:
        continue
    if l['product_uom_id'] and pr['uom_id'] and l['product_uom_id'][0] != pr['uom_id'][0]:
        continue
    cp = parts.get(parts[l['partner_id'][0]]['commercial_partner_id'][0], parts[l['partner_id'][0]])
    pu = round(l['price_subtotal'] / l['quantity'], 2)
    obs[pr['id']].append((pu, l['quantity'], cp['id'], groupe(cp), l['price_subtotal']))
    ca_client[cp['id']] += l['price_subtotal']; cp_name[cp['id']] = cp['name']
print('lignes retenues :', sum(len(v) for v in obs.values()), '| articles :', len(obs), '| clients :', len(ca_client))


def par_client(o):
    d = collections.defaultdict(list)
    for v in o:
        d[v[2]].append(v)
    return {k: (collections.Counter(v[0] for v in vs).most_common(1)[0][0], len(vs)) for k, vs in d.items()}


def observe(o):
    """(prix retenu, nb clients) : prix partagé par le plus de clients (>= 2 et 30 %), sinon médiane des prix par client ;
    1-2 clients : médiane des lignes ; rien : None."""
    if not o:
        return None, 0
    cli = par_client(o)
    if len(cli) >= 3:
        cprix = sorted(v[0] for v in cli.values())
        cmode, cfreq = collections.Counter(cprix).most_common(1)[0]
        return (cmode if (cfreq >= 2 and cfreq / len(cli) >= 0.3) else round(statistics.median(cprix), 2)), len(cli)
    if len(o) >= 3:
        return round(statistics.median(v[0] for v in o), 2), len(cli)
    return None, len(cli)


# ---------- grille
grille = {}
ratios = collections.defaultdict(list)
for pid_, o in obs.items():
    pr = prod[pid_]; fam = famille(pr['display_name'])
    ep = re.search(r'\((\d+) cm\)', pr['display_name'])
    coef = int(ep.group(1)) / 100 if (ep and pr['uom_id'][1] == 'm³') else 1
    unite = 'm²' if coef != 1 else pr['uom_id'][1]
    fiche = round(pr['lst_price'] * coef, 2); pro_liste = round(prix(PRO, pr) * coef, 2)
    o_part = [v for v in o if v[3] == 'Particulier']; o_pro = [v for v in o if v[3] == 'Professionnel']
    part_obs, n_part = observe(o_part); pro_obs, n_pro = observe(o_pro); tous_obs, n_tous = observe(o)
    if n_part >= 3 and n_pro >= 3 and part_obs and pro_obs:
        ratios[fam].append(pro_obs / part_obs)
    rem = REMISE[fam] / 100
    # base pro : observé pros, sinon observé tous clients, sinon Tarif Pro 2026 (si différent de la fiche), sinon fiche
    base_pro = pro_obs if pro_obs else (tous_obs if tous_obs else (pro_liste if abs(pro_liste - fiche) > 0.005 else fiche))
    origine = 'pros facturés' if pro_obs else ('tous clients facturés' if tous_obs else ('Tarif Pro 2026' if abs(pro_liste - fiche) > 0.005 else 'prix fiche'))
    pro27 = arrondi(base_pro * (1 + HAUSSE / 100), fam, unite) if base_pro else None
    part_min = arrondi(pro27 / (1 - rem), fam, unite) if (pro27 and rem < 1) else None
    if PART_MODE == 'fiche' and fiche > 1 and pro27:
        code = pr['default_code'] or ''
        coef_fixe = None
        for k, v in PART_FIXE.items():
            ref = prod_by_code.get(k)
            if ref and code[:3] == k[:3] and code.endswith('-PS') and k.endswith('-PS') and ref['lst_price']:
                coef_fixe = float(v) / ref['lst_price']            # même coefficient que le massif imposé, appliqué à la fiche
        if coef_fixe:
            cible = float(PART_FIXE[code]) if code in PART_FIXE else arrondi(fiche * coef_fixe, fam, unite)
            part27 = max(cible, part_min or 0)
            base_part = ('prix imposé' if code in PART_FIXE else 'même coefficient que le tuffeau massif imposé (fiche × %.3f)' % coef_fixe) if cible >= (part_min or 0) else 'mini %g %% au-dessus du pro' % REMISE[fam]
        else:
            part27 = max(arrondi(fiche * (1 + HAUSSE / 100), fam, unite), part_min or 0)
            base_part = 'prix fiche +%g %% (mini %g %% au-dessus du pro)' % (HAUSSE, REMISE[fam]) if arrondi(fiche * (1 + HAUSSE / 100), fam, unite) >= (part_min or 0) else 'mini %g %% au-dessus du pro' % REMISE[fam]
        if PRO_MODE == 'ecart' and rem > 0:
            # écart fixe : le pro = particulier cible × (1 − remise), sans descendre sous le pratiqué +hausse ; le particulier suit
            cible_part = part27
            pro_ecart = arrondi(cible_part * (1 - rem), fam, unite)
            if pro_ecart > pro27:
                pro27 = pro_ecart
                base_part = base_part.replace(' (mini %g %% au-dessus du pro)' % REMISE[fam], '') + ' ; pro = particulier − %g %%' % REMISE[fam]
            else:
                base_part = 'pro pratiqué +%g %% ÷ (1 − %g %%)' % (HAUSSE, REMISE[fam])
            part27 = arrondi(pro27 / (1 - rem), fam, unite)
    else:
        part27 = part_min; base_part = 'pro ÷ (1 − remise)'
    grille[pid_] = {'nom': pr['display_name'] + ('' if pr['active'] else ' (archivé)'), 'unite': unite, 'fam': fam, 'ca': sum(v[4] for v in o), 'nc': n_tous,
                    'tous': tous_obs, 'part': part_obs, 'npart': n_part, 'pro': pro_obs, 'npro': n_pro, 'fiche': fiche, 'pro_liste': pro_liste,
                    'base': base_pro, 'origine': origine, 'pro27': pro27, 'part27': part27, 'base_part': base_part, 'cli': par_client(o)}
# ---------- clients à prix spécifiques
spec = set()
for cid, pt in parts.items():
    if pt['commercial_partner_id'][0] != cid:
        continue
    nom = pt['name'].lower()
    if 'cazy' in nom or (('lefevre' in nom or 'lefèvre' in nom) and groupe(pt) == 'Professionnel') or (pt['specific_property_product_pricelist'] and pt['specific_property_product_pricelist'][0] in LISTES_CLIENT):
        spec.add(cid)
ecarts = collections.defaultdict(list)     # client -> [(article_id, prix client, n lignes)]
exclus = 0
for pid_, g in grille.items():
    ref = g['pro'] or g['tous']
    # hors prix spécifiques : prestations et forfaits (prix au devis) et articles aux prix pros dispersés
    o_pro = sorted(v[0] for v in obs[pid_] if v[3] == 'Professionnel')
    disperse = len(o_pro) >= 4 and (o_pro[int(0.75 * (len(o_pro) - 1))] - o_pro[int(0.25 * (len(o_pro) - 1))]) / (statistics.median(o_pro) or 1) > 0.25
    if g['fam'] == 'Prestations / divers' or 'forfait' in g['nom'].lower() or g['unite'].lower() == 'forfait' or disperse:
        exclus += 1
        continue
    for cid, (pu, n) in g['cli'].items():
        if ref and n >= 3 and abs(pu - ref) / ref > 0.02 and groupe(parts[cid]) == 'Professionnel':
            ecarts[cid].append((pid_, pu, n))
print('articles hors prix spécifiques (prestations, forfaits, prix dispersés) :', exclus)
gros = [cid for cid, ca in ca_client.most_common(40) if len(ecarts.get(cid, [])) >= 1 and groupe(parts[cid]) == 'Professionnel']
spec |= set(gros[:15])
spec = [cid for cid in sorted(spec, key=lambda cid: -ca_client.get(cid, 0)) if ecarts.get(cid)]
print('clients avec prix spécifiques (%d) :' % len(spec), [(cp_name[cid][:24], len(ecarts[cid])) for cid in spec])
# ---------- classeur
wb = openpyxl.Workbook()
H = Font(bold=True, color='FFFFFF'); HF = PatternFill('solid', fgColor='01666B'); JAUNE = PatternFill('solid', fgColor='FFF2CC'); VERT = PatternFill('solid', fgColor='E2EFDA'); ORANGE = PatternFill('solid', fgColor='F8CBAD')


def entete(ws, cols, widths, freeze='B2'):
    ws.append(cols)
    for i, cell in enumerate(ws[1], 1):
        cell.font = H; cell.fill = HF; cell.alignment = Alignment(wrap_text=True, vertical='center')
        ws.column_dimensions[get_column_letter(i)].width = widths[i - 1]
    ws.row_dimensions[1].height = 46; ws.freeze_panes = freeze


ws = wb.active; ws.title = 'Grille 2027'
entete(ws, ['Article', 'Unité', 'Famille', 'CA 2026', 'Nb clients', 'Prix observé (tous)', 'Particuliers observé', 'Pros observé', 'Prix fiche actuel', 'Base pro retenue', 'Origine de la base',
            'Écart mini pro %', 'PRO 2027', 'PARTICULIER 2027', 'Origine du prix particulier', 'Écart réel %', 'Hausse pro réelle % (vs pratiqué 2026)'], (50, 7, 20, 10, 8, 11, 11, 11, 11, 11, 20, 9, 13, 14, 34, 9, 12), 'B2')
for pid_ in sorted(grille, key=lambda k: -grille[k]['ca']):
    g = grille[pid_]
    ws.append([g['nom'], g['unite'], g['fam'], round(g['ca']), g['nc'], g['tous'], g['part'], g['pro'], g['fiche'] if g['fiche'] > 1 else None, g['base'], g['origine'], REMISE[g['fam']], g['pro27'], g['part27'], g['base_part'], round((1 - g['pro27'] / g['part27']) * 100, 1) if (g['pro27'] and g['part27']) else None, round((g['pro27'] / g['base'] - 1) * 100, 1) if (g['pro27'] and g['base']) else None])
    r = ws.max_row; ws.cell(r, 13).fill = VERT; ws.cell(r, 14).fill = VERT
ws.auto_filter.ref = ws.dimensions
wr = wb.create_sheet('Remises')
entete(wr, ['Famille', 'Remise pro retenue %', 'Rapport pro / particulier observé (médiane)', 'Articles comparables', 'Lecture'], (24, 14, 22, 12, 70), 'A2')
for f in FAMS:
    rs = ratios.get(f, [])
    med = statistics.median(rs) if rs else None
    wr.append([f, REMISE[f], round((1 - med) * 100, 1) if med else None, len(rs), 'écart pro/particulier réellement pratiqué en 2026 : %s' % ('%.1f %% de remise' % ((1 - med) * 100) if med else 'pas assez de données')])
    wr.cell(wr.max_row, 2).fill = JAUNE
wr.append([]); wr.append(['Logique : PRO 2027 = prix pro observé en 2026 × (1 + %g %%), arrondi ; PARTICULIER 2027 = PRO 2027 ÷ (1 − remise de la famille), arrondi.' % HAUSSE])
wr.append(['Arrondis : pierres au m³ à l\'euro, au m² au dixième ; granulats et transport à la tonne à 0,05 €, forfaits à l\'euro ; prestations à l\'euro.'])
wr.append(['Les remises retenues sont une proposition (proche de l\'écart de 7,4 % entre le prix fiche et le Tarif Pro 2026 sur les pierres) : change la colonne jaune, je recalcule.'])
wr.append(['En pratique, particuliers et pros ont payé presque le même prix en 2026 (colonne « observé »), d\'où des prix particuliers 2027 au-dessus du pratiqué.'])
for cid in spec:
    nom = re.sub(r'[\[\]:*?/\\]', ' ', cp_name[cid])[:31].strip()
    wc = wb.create_sheet(nom)
    entete(wc, ['Article', 'Unité', 'Pro observé 2026', 'Prix client 2026', 'Écart %', 'Lignes 2026', 'PRO 2027', 'CLIENT 2027 (+%g %%)' % HAUSSE, 'Écart 2027 %'], (50, 7, 12, 12, 9, 9, 11, 14, 10), 'B2')
    for pid_, pu, n in sorted(ecarts[cid], key=lambda t: -grille[t[0]]['ca']):
        g = grille[pid_]; ref = g['pro'] or g['tous']; fam = g['fam']
        c27 = arrondi(pu * (1 + HAUSSE / 100), fam, g['unite'])
        wc.append([g['nom'], g['unite'], ref, pu, round((pu / ref - 1) * 100, 1), n, g['pro27'], c27, round((c27 / g['pro27'] - 1) * 100, 1) if g['pro27'] else None])
        r = wc.max_row; wc.cell(r, 8).fill = JAUNE
        if pu > ref:
            wc.cell(r, 5).fill = ORANGE
    wc.append([]); wc.append(['CA 2026 du client : %d €' % round(ca_client[cid]), '', '', '', '', '', '', 'Ligne à effacer = le client repasse au tarif pro.'])
wl = wb.create_sheet('Lisez-moi'); wl.column_dimensions['A'].width = 125
for line in ['Factures clients validées de SARL MAQUIGNON du %s au %s (hors avoirs), prix unitaires nets HT dans l\'unité facturée (pré-sciées et tranches fines au m²).' % (DEPUIS, today_s),
             'Onglet Grille 2027 : prix observés (chaque client compte pour un), base retenue pour le pro, remise de la famille, PRO 2027 et PARTICULIER 2027 (colonnes vertes) = la grille à charger.',
             'Onglet Remises : la remise pro par famille (jaune, modifiable) et ce qui était réellement pratiqué en 2026.',
             'Un onglet par client à prix spécifiques : seulement les articles où son prix 2026 s\'écarte de plus de 2 %% du prix pro observé ; CLIENT 2027 (jaune) = son prix +%g %%. Écart 2027 = position par rapport au nouveau prix pro. Orange = le client paie plus cher que le pro.' % HAUSSE,
             'Effacer une ligne d\'un onglet client = ce client repasse au tarif pro sur cet article. Effacer un onglet = plus de liste spécifique pour ce client.',
             'Chargement dans Odoo : Tarif Particulier (prix fixes), Tarif Professionnel (prix fixes), une liste par client = ses lignes + règle « tout le reste : Tarif Professionnel ».']:
    wl.append([line])
out = 'C:/Users/xavfe/Desktop/Maquignon/Tarifs_2027_Maquignon_%s%g%s_%s.xlsx' % ('fiche_mini' if PART_MODE == 'fiche' else 'remise', REMISE['Pierres'], ('_tuffeau' + list(PART_FIXE.values())[0] if PART_FIXE else '') + ('_ecartfixe' if PRO_MODE == 'ecart' else '') + '_entier', today.strftime('%Y-%m-%d'))
wb.save(out)
print('fichier :', out, '| articles :', len(grille), '| onglets clients :', len(spec))
print('rapports pro/particulier observés (médiane) :', {f: (round((1 - statistics.median(v)) * 100, 1), len(v)) for f, v in ratios.items()})
for r in list(ws.iter_rows(min_row=2, max_row=12, values_only=True)):
    print('   %-44s %-4s fiche %8s part.obs %8s pro.obs %8s -> PRO27 %8s PART27 %8s écart %5s %% (%s)' % (r[0][:44], r[1], r[8], r[6], r[7], r[12], r[13], r[15], r[14]))
