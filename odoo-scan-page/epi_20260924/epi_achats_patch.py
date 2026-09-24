# -*- coding: utf-8 -*-
"""Relais : 2113 stock mini / maxi d'un EPI (règle de réapprovisionnement sur Maq/Stock EPI),
2114 demandes de prix aux fournisseurs référencés pour les EPI sous leur stock mini (une demande de prix par fournisseur)."""
import io, sys, py_compile
sys.stdout.reconfigure(encoding='utf-8')

CODE = r'''

# ─── 2113 · 2114 · EPI : stock mini / maxi et demandes de prix aux fournisseurs référencés ─────────────
ORIGINE_DP = 'EPI stock mini'


def _epi_orderpoint(call, cfg, pid):
    op = call('stock.warehouse.orderpoint', 'search_read', [['product_id', '=', pid], ['location_id', '=', cfg['loc_stock']]],
              fields=['product_min_qty', 'product_max_qty'], limit=1)
    return op[0] if op else None


def _epi_mini(call, ctx):
    """Stock mini / maxi d'un EPI = règle de réapprovisionnement (déclenchement manuel) sur Maq/Stock EPI."""
    cfg = _epi_cfg(call, ctx)
    pr = _epi_produit(call, cfg, ctx.get('product'))
    try:
        mini = float(str(ctx.get('mini') if ctx.get('mini') not in (None, '') else 0).replace(',', '.'))
        maxi = float(str(ctx.get('maxi') if ctx.get('maxi') not in (None, '') else 0).replace(',', '.'))
    except ValueError:
        raise WebErreur("Stock mini / maxi : nombres attendus.")
    if mini < 0 or maxi < 0 or mini > 999 or maxi > 999:
        raise WebErreur("Stock mini / maxi : entre 0 et 999.")
    if maxi < mini:
        maxi = mini
    op = _epi_orderpoint(call, cfg, pr['id'])
    if mini == 0 and maxi == 0:
        if op:
            call('stock.warehouse.orderpoint', 'unlink', [op['id']])
        return {'ok': 1, 'mini': 0, 'maxi': 0, 'produit': pr['display_name']}
    vals = {'product_min_qty': mini, 'product_max_qty': maxi, 'trigger': 'manual'}
    if op:
        call('stock.warehouse.orderpoint', 'write', [op['id']], vals)
    else:
        vals.update({'product_id': pr['id'], 'location_id': cfg['loc_stock'], 'warehouse_id': 1, 'company_id': 1})
        _creer(call, 'stock.warehouse.orderpoint', vals)
    return {'ok': 1, 'mini': mini, 'maxi': maxi, 'produit': pr['display_name'], 'stock': _epi_stock(call, cfg, pr['id'])}


def _epi_demandes_prix(call, ctx):
    """EPI sous leur stock mini -> une demande de prix (brouillon) par fournisseur référencé sur l'article,
    avec la quantité qui ramène le stock au maxi. ctx.apercu = 1 : calcul seulement."""
    cfg = _epi_cfg(call, ctx)
    apercu = bool(int(ctx.get('apercu') or 0))
    ops = call('stock.warehouse.orderpoint', 'search_read', [['location_id', '=', cfg['loc_stock']]],
               fields=['product_id', 'product_min_qty', 'product_max_qty'])
    besoins = []
    for op in ops:
        pid = op['product_id'][0]
        stock = _epi_stock(call, cfg, pid)
        mini, maxi = op['product_min_qty'], max(op['product_max_qty'], op['product_min_qty'])
        if mini <= 0 or stock >= mini:
            continue
        pr = call('product.product', 'search_read', [['id', '=', pid], ['active', '=', True], ['categ_id', 'child_of', cfg['categ']]],
                  fields=['display_name', 'product_tmpl_id', 'uom_id', 'standard_price'], limit=1)
        if not pr:
            continue
        pr = pr[0]
        qte = int(-(-(maxi - stock) // 1))   # arrondi supérieur
        vend = call('product.supplierinfo', 'search_read',
                    [['product_tmpl_id', '=', pr['product_tmpl_id'][0]], '|', ['product_id', '=', False], ['product_id', '=', pid],
                     '|', ['company_id', '=', False], ['company_id', '=', 1]],
                    fields=['partner_id', 'price', 'min_qty', 'delay', 'product_code'], order='sequence, id')
        vus, fournisseurs = set(), []
        for v in vend:
            if v['partner_id'][0] in vus:
                continue
            vus.add(v['partner_id'][0])
            fournisseurs.append({'id': v['partner_id'][0], 'nom': v['partner_id'][1], 'prix': v['price'], 'min_qty': v['min_qty'], 'delai': v['delay'], 'ref': v['product_code'] or ''})
        besoins.append({'pid': pid, 'produit': pr['display_name'], 'stock': stock, 'mini': mini, 'maxi': maxi, 'qte': qte,
                        'uom': pr['uom_id'][0], 'cout': pr['standard_price'], 'fournisseurs': fournisseurs})
    par_f = {}
    sans = []
    for b in besoins:
        if not b['fournisseurs']:
            sans.append(b['produit']); continue
        for f in b['fournisseurs']:
            par_f.setdefault(f['id'], {'nom': f['nom'], 'lignes': []})['lignes'].append((b, f))
    res = {'ok': 1, 'apercu': 1 if apercu else 0, 'nb_epi': len(besoins),
           'fournisseurs': [{'id': fid, 'nom': d['nom'], 'nb': len(d['lignes'])} for fid, d in par_f.items()],
           'sans_fournisseur': sans, 'commandes': []}
    if apercu or not par_f:
        return res
    for fid, d in par_f.items():
        po = call('purchase.order', 'search_read',
                  [['partner_id', '=', fid], ['origin', '=', ORIGINE_DP], ['state', 'in', ['draft', 'sent']], ['company_id', '=', 1]],
                  fields=['name', 'order_line'], order='id desc', limit=1)
        lignes_exist = {}
        if po:
            po = po[0]
            for l in call('purchase.order.line', 'read', po['order_line'], ['product_id', 'product_qty']):
                if l['product_id']:
                    lignes_exist[l['product_id'][0]] = l
        nouvelles = []
        for b, f in d['lignes']:
            qte = max(b['qte'], f['min_qty'] or 0)
            vals = {'product_id': b['pid'], 'product_qty': qte, 'product_uom_id': b['uom'],
                    'price_unit': f['prix'] or b['cout'] or 0.0,
                    'name': ('[%s] ' % f['ref'] if f['ref'] else '') + b['produit']}
            if po and b['pid'] in lignes_exist:
                call('purchase.order.line', 'write', [lignes_exist[b['pid']]['id']], {'product_qty': qte})
            else:
                nouvelles.append(vals)
        if po:
            if nouvelles:
                call('purchase.order', 'write', [po['id']], {'order_line': [(0, 0, v) for v in nouvelles]})
            res['commandes'].append({'id': po['id'], 'nom': po['name'], 'fournisseur': d['nom'], 'nb': len(d['lignes']), 'maj': 1})
        else:
            pid_po = _creer(call, 'purchase.order', {'partner_id': fid, 'origin': ORIGINE_DP, 'picking_type_id': cfg['pt_rec'], 'company_id': 1,
                                                     'order_line': [(0, 0, v) for v in nouvelles]})
            nom = call('purchase.order', 'read', [pid_po], ['name'])[0]['name']
            res['commandes'].append({'id': pid_po, 'nom': nom, 'fournisseur': d['nom'], 'nb': len(nouvelles), 'maj': 0})
    return res
'''

p = 'ocr/web_actions.py'
s = io.open(p, encoding='utf-8').read()
assert '_epi_mini' not in s
old = """            2110: _epi_dotation, 2111: _epi_reception, 2112: _epi_annulation}[action_id](call, ctx)"""
new = """            2110: _epi_dotation, 2111: _epi_reception, 2112: _epi_annulation,
            2113: _epi_mini, 2114: _epi_demandes_prix}[action_id](call, ctx)"""
assert s.count(old) == 1
s = s.replace(old, new)
old2 = """  2112  EPI : annulation d'une remise (mouvement inverse)
\"\"\""""
new2 = """  2112  EPI : annulation d'une remise (mouvement inverse)
  2113  EPI : stock mini / maxi (règle de réapprovisionnement sur Maq/Stock EPI)
  2114  EPI : demandes de prix aux fournisseurs référencés (EPI sous le mini)
\"\"\""""
assert s.count(old2) == 1
s = s.replace(old2, new2) + CODE
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
py_compile.compile(p, doraise=True)
print('web_actions.py : 2113-2114 ajoutées, compilation OK')

p = 'ocr/app.py'
s = io.open(p, encoding='utf-8').read()
old = """    2112,  # EPI : annulation d'une remise"""
assert s.count(old) == 1
s = s.replace(old, old + """
    2113,  # EPI : stock mini / maxi
    2114,  # EPI : demandes de prix aux fournisseurs""")
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
py_compile.compile(p, doraise=True)
print('app.py : 2113-2114 autorisées')
