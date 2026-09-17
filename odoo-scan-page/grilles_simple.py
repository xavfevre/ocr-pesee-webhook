# -*- coding: utf-8 -*-
"""Grille simple SARL MAQUIGNON d'après les factures validées depuis DEPUIS : par article, prix observé, prix Particulier
et Professionnel proposés, puis une colonne par client à prix spécifique (prix habituel du client, surligné s'il diffère
du prix pro proposé). Lecture seule sur Odoo. Usage : python grilles_simple.py [AAAA-MM-JJ]"""
import os, ssl, sys, re, xmlrpc.client, collections, datetime, statistics
sys.stdout.reconfigure(encoding='utf-8')
DEPUIS = sys.argv[1] if len(sys.argv) > 1 else '2026-01-01'
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
ctx = {'allowed_company_ids': [1], 'active_test': False}
today = datetime.date.today(); today_s = today.isoformat()
PUBLIC, PRO = 302, 299
LISTES_CLIENT = [1678, 1680, 1681, 1691, 1692, 306, 1676, 74, 158, 159, 160, 286, 287, 288, 289, 290, 295, 296]
NOMS_DEMANDES = ['lefevre', 'lefèvre', 'cazy']
# ---------- articles + Tarif Pro 2026 actuel (évaluation locale des règles)
prods = x('product.product', 'search_read', [['sale_ok', '=', True], ['company_id', 'in', [1, False]]],
          fields=['default_code', 'display_name', 'lst_price', 'standard_price', 'categ_id', 'uom_id', 'product_tmpl_id', 'active'], limit=5000, context=ctx)
prod = {pr['id']: pr for pr in prods}
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


obs = collections.defaultdict(list)          # article -> [(pu, qté, client_id, groupe)]
ca_client = collections.Counter(); cp_name = {}
for l in aml:
    pr = prod.get(l['product_id'][0])
    if not pr or not l['partner_id']:
        continue
    if l['product_uom_id'] and pr['uom_id'] and l['product_uom_id'][0] != pr['uom_id'][0]:
        continue
    cp = parts.get(parts[l['partner_id'][0]]['commercial_partner_id'][0], parts[l['partner_id'][0]])
    pu = round(l['price_subtotal'] / l['quantity'], 2)
    obs[pr['id']].append((pu, l['quantity'], cp['id'], groupe(cp)))
    ca_client[cp['id']] += l['price_subtotal']; cp_name[cp['id']] = cp['name']
print('lignes retenues :', sum(len(v) for v in obs.values()), '| articles facturés :', len(obs), '| clients :', len(ca_client))


def par_client(o):
    d = collections.defaultdict(list)
    for v in o:
        d[v[2]].append(v)
    return {k: (collections.Counter(v[0] for v in vs).most_common(1)[0][0], len(vs)) for k, vs in d.items()}


def proposition(o, repli):
    """Prix partagé par le plus grand nombre de clients (>= 2 et 30 % des clients), sinon médiane des prix par client ;
    1 ou 2 clients : médiane des lignes ; aucune ligne : repli."""
    if not o:
        return repli
    cli = par_client(o)
    if len(cli) >= 3:
        cprix = sorted(v[0] for v in cli.values())
        cmode, cfreq = collections.Counter(cprix).most_common(1)[0]
        return cmode if (cfreq >= 2 and cfreq / len(cli) >= 0.3) else round(statistics.median(cprix), 2)
    if len(o) >= 3:
        return round(statistics.median(v[0] for v in o), 2)
    return repli


# ---------- clients à prix spécifiques
spec = set()
for cid, pt in parts.items():
    if pt['commercial_partner_id'][0] != cid:
        continue
    nom = pt['name'].lower()
    if 'cazy' in nom or (any(n in nom for n in NOMS_DEMANDES) and groupe(pt) == 'Professionnel') or (pt['specific_property_product_pricelist'] and pt['specific_property_product_pricelist'][0] in LISTES_CLIENT):
        spec.add(cid)
noms = x('res.partner', 'search_read', ['|', ['name', 'ilike', 'cazy'], ['name', 'ilike', 'lefevre'], ['parent_id', '=', False]], fields=['name'], context=ctx)
print('clients demandés trouvés dans Odoo :', [n['name'] for n in noms][:10])
# gros clients pros dont les prix s'écartent de la grille pro sur au moins un article significatif
grille = {}
for pid_, o in obs.items():
    pr = prod[pid_]
    ep = re.search(r'\((\d+) cm\)', pr['display_name'])
    coef = int(ep.group(1)) / 100 if (ep and pr['uom_id'][1] == 'm³') else 1
    fiche = round(pr['lst_price'] * coef, 2); pro_act = round(prix(PRO, pr) * coef, 2)
    o_part = [v for v in o if v[3] == 'Particulier']; o_pro = [v for v in o if v[3] == 'Professionnel']
    pro_p = proposition(o_pro, pro_act if abs(pro_act - fiche) > 0.005 else None)
    part_p = proposition(o_part, fiche)
    if (len(o_part) < 3) and fiche <= 1 and pro_p:
        part_p = pro_p
    grille[pid_] = {'unite': 'm²' if coef != 1 else pr['uom_id'][1], 'obs': proposition(o, fiche), 'part': part_p, 'pro': pro_p, 'ca': sum(v[0] * v[1] for v in o), 'n': len(o), 'nc': len({v[2] for v in o}), 'cli': par_client(o)}
ecarts = collections.Counter()
for pid_, g in grille.items():
    for cid, (pu, n) in g['cli'].items():
        if g['pro'] and n >= 3 and abs(pu - g['pro']) / g['pro'] > 0.02:
            ecarts[cid] += 1
gros = [cid for cid, ca in ca_client.most_common(40) if ecarts.get(cid, 0) >= 1 and groupe(parts[cid]) == 'Professionnel']
spec |= set(gros[:15])
spec = sorted(spec, key=lambda cid: -ca_client.get(cid, 0))
spec = [cid for cid in spec if ca_client.get(cid, 0) > 0][:24]
print('clients à prix spécifiques retenus (%d) :' % len(spec), [(cp_name.get(cid, parts[cid]['name'])[:22], round(ca_client.get(cid, 0)), ecarts.get(cid, 0)) for cid in spec])
# ---------- classeur
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
wb = Workbook(); ws = wb.active; ws.title = 'Grille'
H = Font(bold=True, color='FFFFFF'); HF = PatternFill('solid', fgColor='01666B'); JAUNE = PatternFill('solid', fgColor='FFF2CC'); ORANGE = PatternFill('solid', fgColor='F8CBAD'); GRIS = PatternFill('solid', fgColor='EDEDED')
cols = ['Article', 'Unité', 'CA 2026', 'Nb clients', 'Prix observé', 'PARTICULIER proposé', 'PRO proposé'] + [cp_name.get(cid, parts[cid]['name'])[:30] for cid in spec]
ws.append(cols)
for i, cell in enumerate(ws[1], 1):
    cell.font = H; cell.fill = HF; cell.alignment = Alignment(wrap_text=True, vertical='center')
    ws.column_dimensions[get_column_letter(i)].width = 50 if i == 1 else (7 if i == 2 else (11 if i <= 7 else 13))
ws.row_dimensions[1].height = 48; ws.freeze_panes = 'C2'
for pid_ in sorted(grille, key=lambda k: -grille[k]['ca']):
    g = grille[pid_]; pr = prod[pid_]
    row = [pr['display_name'] + ('' if pr['active'] else ' (archivé)'), g['unite'], round(g['ca']), g['nc'], g['obs'], g['part'], g['pro']]
    for cid in spec:
        row.append(g['cli'][cid][0] if cid in g['cli'] else None)
    ws.append(row)
    r = ws.max_row
    ws.cell(r, 6).fill = JAUNE; ws.cell(r, 7).fill = JAUNE
    for j, cid in enumerate(spec, start=8):
        v = ws.cell(r, j).value
        if v is None:
            ws.cell(r, j).fill = GRIS
        elif g['pro'] and abs(v - g['pro']) / g['pro'] > 0.02:
            ws.cell(r, j).fill = ORANGE
ws.auto_filter.ref = ws.dimensions
w2 = wb.create_sheet('Lisez-moi'); w2.column_dimensions['A'].width = 120
for line in ['Factures clients validées de SARL MAQUIGNON depuis le %s (hors avoirs). Prix unitaires nets HT, dans l\'unité facturée (les pré-sciées et tranches à épaisseur unique sont facturées au m²).' % DEPUIS,
             'Prix observé = prix payé par le plus grand nombre de clients (chaque client compte pour un). PARTICULIER / PRO proposés = même calcul sur les particuliers (civilité M., Mme) et sur les professionnels.',
             'Sans facture d\'un groupe : prix actuel (fiche pour Particulier, Tarif Pro 2026 pour Pro) ; particulier sans facture ni prix fiche : aligné sur le prix pro.',
             'Colonnes clients = prix habituel du client sur l\'article (son prix le plus fréquent). Orange : s\'écarte de plus de 2 % du prix pro proposé, c\'est un prix spécifique à garder ou à supprimer. Gris : jamais acheté.',
             'Clients retenus : Lefèvre, Cazy, ceux qui ont déjà une liste de prix à leur nom, et les gros clients pros dont au moins un prix s\'écarte de la grille.',
             'Colonnes jaunes à corriger, puis renvoie-moi le fichier : je crée Tarif Particulier, Tarif Professionnel et une liste par client pour les cases orange conservées.']:
    w2.append([line])
out = 'C:/Users/xavfe/Desktop/Maquignon/Grille_simple_Maquignon_%s.xlsx' % today.strftime('%Y-%m-%d')
wb.save(out)
print('fichier :', out, '| lignes :', ws.max_row - 1, '| colonnes clients :', len(spec))
