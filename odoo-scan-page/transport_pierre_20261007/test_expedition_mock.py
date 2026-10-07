# -*- coding: utf-8 -*-
"""Test hors ligne de l'action 2104 « Expédition » avec un faux Odoo en mémoire.   python test_expedition_mock.py"""
import os, sys, copy
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import web_actions as W


class Faux:
    def __init__(self):
        self.data = {
            'stock.package': {
                445: {'id': 445, 'name': 'PACK0000475', 'x_studio_cloturee': True, 'x_operateur_id': [479, 'DURAND Mickaël'], 'x_operateur_ids': [479], 'x_studio_zone': 'Stock Atelier',
                      'x_studio_cubage': 0.46656, 'x_studio_tonnage': 1306.368, 'x_commande_id': [42821, 'S11731'], 'x_studio_client': "LEZ'ARTS DECO & PIERRE",
                      'x_exp_statut': False, 'x_exp_mode': False, 'x_exp_transporteur_id': False, 'x_exp_camion': '', 'x_exp_chauffeur': '', 'x_exp_date': False,
                      'x_exp_par_id': False, 'x_exp_lot': '', 'x_exp_lettre': '', 'x_studio_tche_commande_pierre': [6531, 'LEZART - 31/08/26 socles']},
                446: {'id': 446, 'name': 'PACK0000476', 'x_studio_cloturee': False, 'x_operateur_id': False, 'x_operateur_ids': [], 'x_studio_zone': '', 'x_studio_cubage': 0.1, 'x_studio_tonnage': 200,
                      'x_commande_id': [42821, 'S11731'], 'x_studio_client': "LEZ'ARTS DECO & PIERRE", 'x_exp_statut': False, 'x_exp_mode': False, 'x_exp_transporteur_id': False,
                      'x_exp_camion': '', 'x_exp_chauffeur': '', 'x_exp_date': False, 'x_exp_par_id': False, 'x_exp_lot': '', 'x_exp_lettre': '', 'x_studio_tche_commande_pierre': False}},
            'mrp.production': {500: {'id': 500, 'name': 'WH/OF/12862', 'state': 'done', 'origin': 'S11731', 'x_studio_colis': [445, 'PACK0000475'], 'x_studio_nbr': 3, 'sale_line_id': [7001, 'ligne'], 'write_date': '2026-10-01 10:00:00',
                                     'product_id': [1, 'TUFFEAU'], 'move_finished_ids': [], 'workorder_ids': [], 'x_studio_nom_du_client': "LEZ'ARTS", 'x_studio_ref_commande_client': '',
                                     'x_studio_palette': 'Palette 1', 'x_studio_ref_pierre': 'SG5', 'x_note_atelier': '', 'x_studio_long_m_1': 0.5, 'x_studio_larg_m_1': 0.2, 'x_studio_haut_m_1': 0.1,
                                     'x_studio_surf_total': 0.0, 'x_studio_vol_total': 0.03}},
            'x_repartition_palette': {},
            'sale.order': {42821: {'id': 42821, 'name': 'S11731', 'partner_id': [15897, "LEZ'ARTS DECO & PIERRE"], 'partner_shipping_id': [15897, "LEZ'ARTS DECO & PIERRE"],
                                   'x_mode_transport': 'exterieur', 'x_transporteur_id': [18880, 'GENDRON TRANSPORTS'], 'state': 'sale'}},
            'res.partner': {15897: {'id': 15897, 'name': "LEZ'ARTS DECO & PIERRE", 'street': '12 rue des Pierres', 'street2': False, 'zip': '86000', 'city': 'POITIERS'},
                            18880: {'id': 18880, 'name': 'GENDRON TRANSPORTS'}},
            'project.task.type': {99: {'id': 99, 'name': 'Expédié', 'project_ids': [13], 'sequence': 60}, 50: {'id': 50, 'name': 'Prêt à expédier', 'project_ids': [13], 'sequence': 50}},
            'project.task': {6531: {'id': 6531, 'name': 'LEZART - 31/08/26 socles', 'stage_id': [50, 'Prêt à expédier']}},
            'hr.employee': {478: {'id': 478, 'name': 'DESPUJOLS Loïc'}},
            'res.company': {1: {'id': 1, 'email': 'contact@maquignon.com'}},
            'res.users': {2: {'id': 2, 'partner_id': [3, 'Isabelle']}},
            'mail.mail': {},
            'sale.order.line': {7001: {'id': 7001, 'product_uom_qty': 0.09, 'qty_delivered': 0.0}},
            'stock.picking': {800: {'id': 800, 'name': 'WH/OUT/00800', 'sale_id': [42821, 'S11731'], 'state': 'confirmed', 'picking_type_code': 'outgoing', 'move_ids': [8001, 8002], 'carrier_id': False, 'carrier_tracking_ref': False, 'backorder_ids': []}},
            'stock.move': {8001: {'id': 8001, 'picking_id': [800, 'WH/OUT/00800'], 'sale_line_id': [7001, 'ligne'], 'product_uom_qty': 0.09, 'quantity': 0.0, 'picked': False, 'state': 'confirmed'},
                           8002: {'id': 8002, 'picking_id': [800, 'WH/OUT/00800'], 'sale_line_id': [7002, 'ligne 2'], 'product_uom_qty': 0.05, 'quantity': 0.0, 'picked': False, 'state': 'confirmed'}},
            'delivery.carrier': {4: {'id': 4, 'name': 'SEMI GE-106-QS'}},
            'ir.config_parameter': {},
        }
        self.journal = []

    def _match(self, rec, dom):
        i = 0
        for cond in dom:
            if cond in ('|', '&', '!'):
                continue
            f, op, v = cond
            val = rec.get(f, False)
            if isinstance(val, list) and len(val) == 2 and isinstance(val[0], int):
                val = val[0]
            ok = {'=': lambda: val == v, '!=': lambda: val != v,
                  'in': lambda: (any(e in v for e in val) if isinstance(val, list) else val in v),
                  'not in': lambda: (not any(e in v for e in val) if isinstance(val, list) else val not in v),
                  '=ilike': lambda: str(val).lower() == str(v).lower(), '>=': lambda: bool(val) and str(val) >= str(v)}[op]()
            if not ok:
                # gestion minimale du « | » : si la condition précédente était un « | », on tolère un échec
                if i > 0 and dom[i - 1] == '|' or (i + 1 < len(dom) and False):
                    pass
                else:
                    return False
            i += 1
        return True

    def __call__(self, model, method, *args, **kw):
        self.journal.append((model, method, copy.deepcopy(args), copy.deepcopy(kw)))
        store = self.data.setdefault(model, {})
        if method == 'get_param':
            return 'celine@maquignon.com' if args[0] == 'maquignon.palettes_alerte_email' else (args[1] if len(args) > 1 else False)
        if method in ('search_read', 'search', 'search_count'):
            rows = [r for r in store.values() if self._match(r, args[0] if args else [])]
            if method == 'search': return [r['id'] for r in rows][: (kw.get('limit') or 10**6)]
            if method == 'search_count': return len(rows)
            return [copy.deepcopy(r) for r in rows][: (kw.get('limit') or 10**6)]
        if method == 'read':
            return [copy.deepcopy(store[i]) for i in args[0]]
        if method == 'write':
            for i in args[0]:
                for f, v in args[1].items():
                    store[i][f] = ([v, 'x'] if (isinstance(v, int) and f.endswith('_id') and v) else v)
            return True
        if method == 'create':
            vals = args[0] if isinstance(args[0], dict) else args[0][0]
            nid = 9000 + len(store); store[nid] = dict(vals, id=nid); return nid
        if method in ('message_post', 'send'):
            return 1
        if method == 'button_validate':
            pk = store[args[0][0]]; mvs = [self.data['stock.move'][i] for i in pk['move_ids']]
            reste = [(v['product_uom_qty'] - (v['quantity'] if v['picked'] else 0.0)) for v in mvs]
            for v in mvs:
                if v['picked']: v['state'] = 'done'
                else: v['state'] = 'cancel'
            if any(r > 0.0005 for r in reste):
                bid = 801; store[bid] = {'id': bid, 'name': pk['name'] + '-1', 'sale_id': pk['sale_id'], 'state': 'confirmed', 'picking_type_code': pk['picking_type_code'], 'move_ids': [], 'carrier_id': False, 'carrier_tracking_ref': False, 'backorder_ids': []}
                pk['backorder_ids'] = [bid]
            pk['state'] = 'done'; return True
        raise Exception('non simulé : %s.%s' % (model, method))


def check(c, msg):
    print(('  ✅ ' if c else '  ❌ ') + msg)
    if not c:
        raise SystemExit('ÉCHEC : ' + msg)


o = Faux()
print('=== scanner une palette clôturée ===')
p = W.executer(o, 2104, {'mode': 'scanner', 'code': '475'})
check(p['name'] == 'PACK0000475' and p['commande'] == 'S11731' and p['n'] == 1 and p['mode_devis'] == 'exterieur' and p['transporteur_devis_id'] == 18880 and 'POITIERS' in p['adresse'], 'fiche palette : %s' % {k: p[k] for k in ('name', 'commande', 'client', 'ton', 'n', 'mode_devis', 'transporteur_devis')})
print('=== palette non clôturée refusée ===')
try:
    W.executer(o, 2104, {'mode': 'scanner', 'code': 'PACK0000476'}); check(False, 'refus attendu')
except W.WebErreur as e:
    check('clôturée' in str(e), 'refus : %s' % e)
print('=== validation sans mode refusée ===')
try:
    W.executer(o, 2104, {'mode': 'valider', 'palettes': [445]}); check(False, 'refus attendu')
except W.WebErreur as e:
    check('mode' in str(e), 'refus : %s' % e)
print('=== départ par transporteur extérieur ===')
r = W.executer(o, 2104, {'mode': 'valider', 'palettes': [445], 'exp_mode': 'exterieur', 'transporteur_id': 18880, 'camion': 'AB-123-CD', 'chauffeur': '', 'charge_par': 478, 'lettre': 'LV 4567'})
check(r['ok'] == 1 and r['n'] == 1 and r['ton'] == 1306 and r['lot'].startswith('CHG-'), 'départ : %s' % r['msg'])
pk = o.data['stock.package'][445]
check(pk['x_exp_statut'] == 'chargee' and pk['x_exp_mode'] == 'exterieur' and pk['x_exp_transporteur_id'][0] == 18880 and pk['x_exp_camion'] == 'AB-123-CD' and pk['x_exp_lot'] == r['lot'] and pk['x_exp_par_id'][0] == 478, 'palette mise à jour : statut chargée, transporteur, camion, lot, chargé par')
check(o.data['project.task'][6531]['stage_id'][0] == 99, 'tâche Commande Pierres passée en Expédié (tout est parti)')
check(any(m == 'sale.order' and me == 'message_post' for m, me, *_ in o.journal), 'note dans le fil de la commande')
check(any(m == 'mail.mail' and me == 'create' for m, me, *_ in o.journal), 'mail au bureau créé')
pk = o.data['stock.picking'][800]; mv1 = o.data['stock.move'][8001]
check(pk['state'] == 'done' and mv1['quantity'] == 0.09 and mv1['picked'] and mv1['state'] == 'done' and pk['backorder_ids'] == [801], 'BL validé pour la ligne de la palette (0,09 m³), reliquat créé pour le reste')
check('GENDRON' in (pk['carrier_tracking_ref'] or '') and 'PACK0000475' in pk['carrier_tracking_ref'], 'référence de suivi sur le BL : %s' % pk['carrier_tracking_ref'])
check(any(m == 'sale.order' and me == 'message_post' and 'validé pour 1 ligne' in str(k.get('body')) for m, me, a, k in o.journal), 'note BL dans le fil de la commande')
print('=== plan BL en lecture seule ===')
o2 = Faux(); pl = W.executer(o2, 2104, {'mode': 'bl_plan', 'palettes': [445]})
check(pl['plan'][0]['lignes'] == {'7001': 0.09} and 'WH/OUT/00800' in pl['plan'][0]['bl'] and not any(me in ('write', 'button_validate') for _, me, *_ in o2.journal), 'plan : %s' % pl['plan'][0])
print('=== même palette : déjà partie ===')
try:
    W.executer(o, 2104, {'mode': 'scanner', 'code': 'PACK0000475'}); check(False, 'refus attendu')
except W.WebErreur as e:
    check('déjà partie' in str(e) and r['lot'] in str(e), 'refus : %s' % e)
print('=== départs récents ===')
l = W.executer(o, 2104, {'mode': 'lots', 'jours': 3})
check(len(l['lots']) == 1 and l['lots'][0]['lot'] == r['lot'] and l['lots'][0]['n'] == 1, 'lot listé : %s' % l['lots'][0]['lot'])
print('=== annulation ===')
a = W.executer(o, 2104, {'mode': 'annuler', 'palette_id': 445})
check(a['ok'] == 1 and not o.data['stock.package'][445]['x_exp_statut'] and not o.data['stock.package'][445]['x_exp_lot'], 'palette remise en stock : %s' % a['msg'])
print('=== enlèvement client sans mail ===')
r2 = W.executer(o, 2104, {'mode': 'valider', 'palettes': [445], 'exp_mode': 'client', 'chauffeur': 'M. Lézart', 'camion': 'EF-456-GH', 'charge_par': 0, 'sans_mail': 1})
check(o.data['stock.package'][445]['x_exp_statut'] == 'enlevee' and 'enlèvement par le client' in r2['msg'], 'statut Enlevée : %s' % r2['msg'])
print('\nTOUS LES TESTS PASSENT')
