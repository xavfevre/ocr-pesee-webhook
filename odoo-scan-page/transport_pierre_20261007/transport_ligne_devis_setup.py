# -*- coding: utf-8 -*-
"""Ligne « Transport de pierres » ajoutée automatiquement en fin de devis (Xavier, 07/10/2026) :
  - dès que le mode de transport vaut « Nos camions » ou « Transporteur extérieur » et que le devis n'a pas encore de ligne
    Transport de pierres : ligne « Transport de pierres (Forfait Palettes) » créée en dernière position, quantité 1,
    prix = prix d'achat transport s'il est connu, sinon 0 (Céline ajuste et change la variante si besoin) ;
  - « Enlèvement par le client » : une ligne transport encore vide (0 ou 1 €) est retirée ;
  - quand le transporteur est retenu (demande de prix confirmée), une ligne transport encore vide prend le prix d'achat.
Automatisation sur sale.order (champ Mode de transport) + extension de l'action 2119 (automatisation 102).
Base : ODOO_URL / ODOO_DB (défaut production).   python transport_ligne_devis_setup.py dry | apply | test <S…>"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = os.environ.get('ODOO_URL', 'https://maquignon.odoo.com'); D = os.environ.get('ODOO_DB', 'maquignon')
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
assert uid, 'authentification refusée sur ' + U
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)


def x(mo, me, *a, **k):
    ctx = {'allowed_company_ids': [1]}; ctx.update(k.pop('context', {})); k['context'] = ctx
    try:
        return m.execute_kw(D, uid, p, mo, me, list(a), k)
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in str(e):
            return None
        raise


one = lambda v: v[0] if isinstance(v, list) else v
NOM_AUTO = 'Devis : ligne Transport de pierres automatique'
MODEL_SO = x('ir.model', 'search', [['model', '=', 'sale.order']])[0]
F_MODE = x('ir.model.fields', 'search', [['model', '=', 'sale.order'], ['name', '=', 'x_mode_transport']])[0]
VARIANTES = x('product.product', 'search', [['product_tmpl_id.name', '=', 'Transport de pierres']])
_noms = {q['id']: q['display_name'] for q in x('product.product', 'read', VARIANTES, ['display_name'])}
DEFAUT = next((i for i, n in _noms.items() if 'Forfait Palettes' in n), VARIANTES[0])
PRODUIT_ACHAT = x('product.product', 'search', [['name', '=', 'Transport affrété (achat transporteur)']], limit=1)[0]
print('base %s | variantes transport %s (défaut %s) | article achat %s' % (U, VARIANTES, DEFAUT, PRODUIT_ACHAT))

CODE_LIGNE = '''# Ligne « Transport de pierres » en fin de devis selon le mode de transport (Xavier, 07/10/2026).
VARIANTES = %(variantes)s
DEFAUT = %(defaut)d
for so in records:
    if so.state not in ('draft', 'sent', 'sale'):
        continue
    existantes = so.order_line.filtered(lambda l: not l.display_type and l.product_id.id in VARIANTES)
    if so.x_mode_transport in ('camions', 'exterieur') and not existantes:
        # juste après la dernière ligne produit ; l'éco-contribution et les notes de fin (prix départ, acompte) sont décalées après
        produits = so.order_line.filtered(lambda l: not l.display_type and 'Eco-contribution' not in (l.name or ''))
        seq = max(produits.mapped('sequence') or [10]) + 1
        for l in so.order_line.filtered(lambda l: l.sequence >= seq):
            l.write({'sequence': l.sequence + 1})
        prix = so.x_transport_achat if (so.x_mode_transport == 'exterieur' and so.x_transport_achat) else 0.0
        nom = 'Transport de pierres (Forfait Palettes)' + ((' - ' + so.x_transporteur_id.name) if (so.x_mode_transport == 'exterieur' and so.x_transporteur_id) else '')
        so.write({'order_line': [(0, 0, {'product_id': DEFAUT, 'name': nom, 'product_uom_qty': 1.0, 'price_unit': prix, 'sequence': seq})]})
        so.message_post(body="Ligne « Transport de pierres » ajoutée en fin de devis (%%s) : prix de vente à ajuster par Céline%%s." %% (
            'nos camions' if so.x_mode_transport == 'camions' else 'transporteur extérieur',
            (' - prix d achat reporté : %%.2f EUR HT' %% prix) if prix else ''))
    elif so.x_mode_transport == 'client' and existantes and all(l.price_unit in (0.0, 1.0) for l in existantes):
        existantes.unlink()
        so.message_post(body="Enlèvement par le client : ligne « Transport de pierres » vide retirée du devis.")
'''

CODE_102_AJOUT = '''
    # ligne « Transport de pierres » du devis : prend le prix d'achat si elle est encore vide, créée en fin de devis sinon
    VARIANTES = %(variantes)s
    DEFAUT = %(defaut)d
    existantes = so.order_line.filtered(lambda l: not l.display_type and l.product_id.id in VARIANTES)
    vides = existantes.filtered(lambda l: l.price_unit in (0.0, 1.0))
    if vides:
        vides.write({'price_unit': po.amount_untaxed, 'name': 'Transport de pierres (Forfait Palettes) - ' + po.partner_id.name})
        so.message_post(body="Ligne « Transport de pierres » : prix d achat %%.2f EUR HT reporté, prix de vente à ajuster." %% po.amount_untaxed)
    elif not existantes:
        produits = so.order_line.filtered(lambda l: not l.display_type and 'Eco-contribution' not in (l.name or ''))
        seq = max(produits.mapped('sequence') or [10]) + 1
        for l in so.order_line.filtered(lambda l: l.sequence >= seq):
            l.write({'sequence': l.sequence + 1})
        so.write({'order_line': [(0, 0, {'product_id': DEFAUT, 'name': 'Transport de pierres (Forfait Palettes) - ' + po.partner_id.name,
                                         'product_uom_qty': 1.0, 'price_unit': po.amount_untaxed, 'sequence': seq})]})
        so.message_post(body="Ligne « Transport de pierres » ajoutée en fin de devis au prix d achat %%.2f EUR HT : prix de vente à ajuster." %% po.amount_untaxed)
'''

auto = x('base.automation', 'search', [['name', '=', NOM_AUTO]])
a102 = x('base.automation', 'search', [['name', '=', 'Achat transport confirmé -> transporteur retenu sur le devis']])
act102 = x('base.automation', 'read', a102, ['action_server_ids'])[0]['action_server_ids'] if a102 else []
code102 = x('ir.actions.server', 'read', act102, ['code'])[0]['code'] if act102 else ''
print('état : automatisation ligne %s | automatisation 102 %s (action %s, ligne déjà gérée : %s)' % (auto, a102, act102, 'VARIANTES' in code102))
params = {'variantes': VARIANTES, 'defaut': DEFAUT}

if mode == 'apply':
    if auto:
        a = x('base.automation', 'read', auto, ['action_server_ids'])[0]
        x('ir.actions.server', 'write', a['action_server_ids'], {'code': CODE_LIGNE % params})
        auto_id = auto[0]
    else:
        auto_id = one(x('base.automation', 'create', [{'name': NOM_AUTO, 'model_id': MODEL_SO, 'trigger': 'on_create_or_write', 'trigger_field_ids': [[6, 0, [F_MODE]]], 'active': True,
                                                        'action_server_ids': [[0, 0, {'name': NOM_AUTO, 'model_id': MODEL_SO, 'state': 'code', 'code': CODE_LIGNE % params, 'usage': 'base_automation'}]]}]))
    print('automatisation ligne transport :', auto_id)
    if act102:
        anchor = "    so.message_post(body=\"Transporteur retenu"
        base102 = code102.split("\n    # ligne « Transport de pierres » du devis")[0] if 'VARIANTES' in code102 else code102
        if 'VARIANTES' in code102:
            # réinstallation : on repart du code sans le bloc ligne transport (le reste de l'action est après l'ancre)
            base102 = base102 + "\n" + code102[code102.index(anchor):]
        assert anchor in base102, 'ancre introuvable dans l action 102'
        nouveau = base102.replace(anchor, (CODE_102_AJOUT % params) + anchor, 1)
        x('ir.actions.server', 'write', act102, {'code': nouveau})
        print('action 102 : bloc ligne transport (ré)installé')
    sys.exit(0)

if mode == 'test':
    so_name = sys.argv[2]
    so = x('sale.order', 'search_read', [['name', '=', so_name]], fields=['id', 'state', 'x_mode_transport', 'x_transporteur_id', 'x_transport_achat', 'order_line'])[0]
    lignes = lambda: x('sale.order.line', 'search_read', [['order_id', '=', so['id']]], fields=['name', 'sequence', 'price_unit', 'product_id', 'product_uom_qty'], order='sequence, id')
    av = lignes(); print('%s : %s, mode %s, transporteur %s, achat %s | %d lignes, dernière : %s' % (so_name, so['state'], so['x_mode_transport'], so['x_transporteur_id'] and so['x_transporteur_id'][1], so['x_transport_achat'], len(av), (av[-1]['name'][:40], av[-1]['sequence'])))
    # déclenchement : réécriture du mode (même valeur)
    x('sale.order', 'write', [so['id']], {'x_mode_transport': so['x_mode_transport']})
    ap = lignes(); nouv = [l for l in ap if l['id'] not in {q['id'] for q in av}]
    print('après : %d lignes | nouvelle(s) : %s | dernière : %s' % (len(ap), [(l['name'][:50], l['sequence'], l['price_unit'], l['product_uom_qty']) for l in nouv], (ap[-1]['name'][:40], ap[-1]['sequence'])))
    import re
    print('notes :', [re.sub(r'<[^>]+>', '', q['body'])[:140] for q in x('mail.message', 'search_read', [['model', '=', 'sale.order'], ['res_id', '=', so['id']], ['message_type', '=', 'comment']], fields=['body'], order='id desc', limit=2)])
    sys.exit(0)
print('simulation : rien modifié')
