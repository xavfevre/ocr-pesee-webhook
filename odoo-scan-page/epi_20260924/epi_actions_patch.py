# -*- coding: utf-8 -*-
"""Ajoute au relais Render (ocr/web_actions.py + ocr/app.py) les actions de la page EPI :
  2110 remise d'un EPI à un salarié, 2111 entrée en stock (réception), 2112 annulation d'une remise."""
import io, sys, py_compile
sys.stdout.reconfigure(encoding='utf-8')

CODE = r'''

# ─── 2110 · 2111 · 2112 · EPI : remise à un salarié, entrée en stock, annulation (page /epi) ────────────
# La page /epi (vue website, clé maquignon.epi_key) crée des transferts Odoo validés :
#   réception  : Fournisseurs -> Maq/Stock EPI (type « Réception EPI »)
#   dotation   : Maq/Stock EPI -> « EPI remis aux salariés » (type « Dotation EPI »), salarié sur le transfert et
#                sur le mouvement (x_employee_id) -> consommation par salarié, onglet EPI de la fiche salarié
#   annulation : mouvement inverse (remis -> Stock EPI) sur le même salarié, référence « Annulation EPI/… »
def _epi_cfg(call, ctx):
    k = (ctx.get('epi_k') or '').strip()
    ref = call('ir.config_parameter', 'get_param', 'maquignon.epi_key') or ''
    if not k or not ref or k != ref:
        raise WebErreur("Lien invalide : demandez le lien de la page EPI au bureau.")
    cfg = {}
    for cle in ('categ', 'loc_stock', 'loc_conso', 'pt_dot', 'pt_rec'):
        try:
            cfg[cle] = int(call('ir.config_parameter', 'get_param', 'maquignon.epi_' + cle) or 0)
        except (TypeError, ValueError):
            cfg[cle] = 0
    if not all(cfg.values()):
        raise WebErreur("Configuration EPI incomplète (paramètres maquignon.epi_*).")
    return cfg


def _epi_produit(call, cfg, pid):
    try:
        pid = int(pid or 0)
    except (TypeError, ValueError):
        pid = 0
    pr = call('product.product', 'search_read',
              [['id', '=', pid], ['categ_id', 'child_of', cfg['categ']], ['active', '=', True]],
              fields=['display_name', 'is_storable', 'standard_price', 'uom_id'], limit=1)
    if not pr:
        raise WebErreur("Choisissez un EPI dans la liste (article de la catégorie EPI).")
    if not pr[0]['is_storable']:
        raise WebErreur("L'article %s n'est pas suivi en stock : cochez « Suivre le stock » sur sa fiche." % pr[0]['display_name'])
    return pr[0]


def _epi_stock(call, cfg, pid):
    q = call('stock.quant', 'search_read', [['product_id', '=', pid], ['location_id', '=', cfg['loc_stock']]], fields=['quantity'])
    return sum(r['quantity'] for r in q)


def _epi_qte(ctx):
    try:
        qty = float(str(ctx.get('qty') or '0').replace(',', '.'))
    except ValueError:
        qty = 0.0
    if qty <= 0 or qty > 200:
        raise WebErreur("Quantité : entre 1 et 200.")
    return qty


def _epi_date(ctx):
    d = (ctx.get('date') or '').strip()
    if not d:
        return datetime.date.today().strftime('%Y-%m-%d')
    try:
        datetime.datetime.strptime(d, '%Y-%m-%d')
    except ValueError:
        raise WebErreur("Date invalide.")
    if d > datetime.date.today().strftime('%Y-%m-%d'):
        raise WebErreur("La date ne peut pas être dans le futur.")
    return d


def _epi_transfert(call, cfg, pt, src, dst, pr, qty, date, emp_id, note, origin):
    """Crée et valide un transfert d'une ligne ; renvoie (id, référence)."""
    vals_move = {'name': pr['display_name'], 'product_id': pr['id'], 'product_uom_qty': qty, 'product_uom': pr['uom_id'][0],
                 'location_id': src, 'location_dest_id': dst, 'x_employee_id': emp_id or False, 'date': date + ' 12:00:00'}
    pick = _creer(call, 'stock.picking', {
        'picking_type_id': pt, 'location_id': src, 'location_dest_id': dst, 'origin': origin,
        'x_employee_id': emp_id or False, 'note': note or False, 'scheduled_date': date + ' 12:00:00',
        'move_ids': [(0, 0, vals_move)]})
    call('stock.picking', 'action_confirm', [pick])
    moves = call('stock.move', 'search', [['picking_id', '=', pick]])
    call('stock.move', 'write', moves, {'quantity': qty, 'picked': True})
    call('stock.picking', 'button_validate', [pick],
         context={'skip_backorder': True, 'skip_immediate': True, 'skip_sms': True, 'skip_overprocessed_check': True})
    st = call('stock.picking', 'read', [pick], ['state', 'name'])[0]
    if st['state'] != 'done':
        raise WebErreur("Le transfert %s n'a pas pu être validé (état %s)." % (st['name'], st['state']))
    if date != datetime.date.today().strftime('%Y-%m-%d'):
        # antidatage : la date des mouvements est celle de la remise réelle
        try:
            call('stock.move', 'write', moves, {'date': date + ' 12:00:00'})
            lines = call('stock.move.line', 'search', [['move_id', 'in', moves]])
            if lines:
                call('stock.move.line', 'write', lines, {'date': date + ' 12:00:00'})
        except Exception:  # noqa: BLE001
            pass
    return pick, st['name']


def _epi_dotation(call, ctx):
    cfg = _epi_cfg(call, ctx)
    try:
        emp_id = int(ctx.get('emp') or 0)
    except (TypeError, ValueError):
        emp_id = 0
    emp = call('hr.employee', 'search_read', [['id', '=', emp_id], ['active', '=', True]], fields=['name'], limit=1)
    if not emp:
        raise WebErreur("Choisissez le salarié.")
    pr = _epi_produit(call, cfg, ctx.get('product'))
    qty = _epi_qte(ctx)
    date = _epi_date(ctx)
    stock = _epi_stock(call, cfg, pr['id'])
    if stock < qty and not int(ctx.get('force') or 0):
        raise WebErreur("STOCK|Stock insuffisant : %s en stock pour %s. Enregistrez d'abord l'entrée en stock (📦), ou confirmez la remise quand même."
                        % (_fmt3(stock), pr['display_name']))
    pick, ref = _epi_transfert(call, cfg, cfg['pt_dot'], cfg['loc_stock'], cfg['loc_conso'], pr, qty, date, emp[0]['id'],
                               (ctx.get('note') or '').strip(), 'EPI %s' % emp[0]['name'])
    return {'ok': 1, 'ref': ref, 'picking': pick, 'produit': pr['display_name'], 'salarie': emp[0]['name'],
            'qty': qty, 'stock': _epi_stock(call, cfg, pr['id'])}


def _epi_reception(call, ctx):
    cfg = _epi_cfg(call, ctx)
    pr = _epi_produit(call, cfg, ctx.get('product'))
    qty = _epi_qte(ctx)
    date = _epi_date(ctx)
    pick, ref = _epi_transfert(call, cfg, cfg['pt_rec'], 4, cfg['loc_stock'], pr, qty, date, 0,
                               (ctx.get('note') or '').strip(), 'Entrée EPI (page)')
    return {'ok': 1, 'ref': ref, 'picking': pick, 'produit': pr['display_name'], 'qty': qty, 'stock': _epi_stock(call, cfg, pr['id'])}


def _epi_annulation(call, ctx):
    cfg = _epi_cfg(call, ctx)
    try:
        mid = int(ctx.get('move') or 0)
    except (TypeError, ValueError):
        mid = 0
    mv = call('stock.move', 'search_read', [['id', '=', mid], ['state', '=', 'done'], ['location_dest_id', '=', cfg['loc_conso']]],
              fields=['product_id', 'quantity', 'x_employee_id', 'reference', 'date'], limit=1)
    if not mv:
        raise WebErreur("Remise introuvable ou déjà annulée.")
    mv = mv[0]
    if call('stock.picking', 'search_count', [['origin', '=', 'Annulation %s' % mv['reference']], ['state', '!=', 'cancel']]):
        raise WebErreur("Cette remise (%s) a déjà été annulée." % mv['reference'])
    pr = call('product.product', 'read', [mv['product_id'][0]], ['display_name', 'is_storable', 'standard_price', 'uom_id'])[0]
    emp_id = mv['x_employee_id'] and mv['x_employee_id'][0] or 0
    pick, ref = _epi_transfert(call, cfg, cfg['pt_dot'], cfg['loc_conso'], cfg['loc_stock'], pr, mv['quantity'],
                               datetime.date.today().strftime('%Y-%m-%d'), emp_id, 'Annulation de %s' % mv['reference'],
                               'Annulation %s' % mv['reference'])
    return {'ok': 1, 'ref': ref, 'annule': mv['reference'], 'stock': _epi_stock(call, cfg, pr['id'])}
'''

p = 'ocr/web_actions.py'
s = io.open(p, encoding='utf-8').read()
assert '_epi_dotation' not in s
old = """            2101: _palettiser, 2102: _scan, 2103: _alerte_palettes}[action_id](call, ctx)"""
new = """            2101: _palettiser, 2102: _scan, 2103: _alerte_palettes,
            2110: _epi_dotation, 2111: _epi_reception, 2112: _epi_annulation}[action_id](call, ctx)"""
assert s.count(old) == 1
s = s.replace(old, new)
old2 = """  2103  Alerte hebdo palettes : pierres non palettisées par opérateur, palettes dormantes (mail au bureau)
\"\"\""""
new2 = """  2103  Alerte hebdo palettes : pierres non palettisées par opérateur, palettes dormantes (mail au bureau)
  2110  EPI : remise d'un EPI à un salarié (page /epi, clé maquignon.epi_key)
  2111  EPI : entrée en stock (réception)
  2112  EPI : annulation d'une remise (mouvement inverse)
\"\"\""""
assert s.count(old2) == 1
s = s.replace(old2, new2) + CODE
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
py_compile.compile(p, doraise=True)
print('web_actions.py : actions 2110-2112 ajoutées, compilation OK')

p = 'ocr/app.py'
s = io.open(p, encoding='utf-8').read()
old = """    2102,  # poste de scan : palette active du poste (scan / quantité / retrait / clôture / transfert)"""
assert s.count(old) == 1
s = s.replace(old, old + """
    2110,  # EPI : remise à un salarié (page /epi)
    2111,  # EPI : entrée en stock
    2112,  # EPI : annulation d'une remise""")
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
py_compile.compile(p, doraise=True)
print('app.py : 2110-2112 autorisées, compilation OK')
