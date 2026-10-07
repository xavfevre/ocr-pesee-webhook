# -*- coding: utf-8 -*-
"""Test hors ligne du relais patché (web_actions.py) avec un faux Odoo en mémoire :
tablette 2101 (confirmation demandée, pose confirmée, propre palette) et poste de scan 2102 (refus avec
demande de confirmation, pose confirmée avec quantité, garde-fou).   python test_palette_autre_mock.py"""
import os, sys, copy
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import web_actions as W


class FauxOdoo:
    def __init__(self):
        self.data = {
            'hr.employee': {479: {'id': 479, 'name': 'DURAND Mickaël', 'x_palette_scan_id': False},
                            628: {'id': 628, 'name': 'GUERIN Frédéric', 'x_palette_scan_id': False}},
            'stock.package': {10: {'id': 10, 'name': 'PACK0000010', 'x_studio_cloturee': False, 'x_operateur_id': [479, 'DURAND Mickaël'],
                                   'x_operateur_ids': [479], 'x_studio_zone': '', 'x_studio_cubage': 0.2, 'x_studio_tonnage': 310.0},
                              11: {'id': 11, 'name': 'PACK0000011', 'x_studio_cloturee': False, 'x_operateur_id': [628, 'GUERIN Frédéric'],
                                   'x_operateur_ids': [628], 'x_studio_zone': '', 'x_studio_cubage': 0.0, 'x_studio_tonnage': 0.0}},
            'mrp.production': {500: {'id': 500, 'name': 'WH/OF/12862', 'state': 'done', 'origin': 'S12311', 'product_id': [1, 'TUFFEAU'],
                                     'move_finished_ids': [], 'workorder_ids': [900], 'write_date': '2026-10-07 08:00:00',
                                     'x_studio_nbr': 3, 'x_studio_colis': False, 'x_studio_nom_du_client': 'LEFEVRE', 'x_studio_ref_commande_client': '56',
                                     'x_studio_palette': 'Palette n° 1', 'x_studio_ref_pierre': 'SG5', 'x_note_atelier': '', 'x_studio_long_m_1': 0.5,
                                     'x_studio_larg_m_1': 0.2, 'x_studio_haut_m_1': 0.1, 'x_studio_surf_total': 0.0, 'x_studio_vol_total': 0.03}},
            'mrp.workorder': {900: {'id': 900, 'sequence': 10, 'employee_assigned_ids': [628], 'state': 'done'}},
            'x_repartition_palette': {},
            'ir.config_parameter': {},
        }
        self.journal = []      # (model, method, args)
        self.seq = 1000

    def _match(self, rec, dom):
        for cond in dom:
            if not isinstance(cond, (list, tuple)) or len(cond) != 3:
                continue
            f, op, v = cond
            val = rec.get(f, False)
            if isinstance(val, list) and len(val) == 2 and isinstance(val[0], int) and isinstance(val[1], str):
                val = val[0]
            if op == '=' and not (val == v): return False
            if op == '!=' and not (val != v): return False
            if op == 'in' and not (val in v): return False
            if op == '=ilike' and not (str(val).lower() == str(v).lower()): return False
            if op == 'ilike' and not (str(v).lower() in str(val).lower()): return False
        return True

    def __call__(self, model, method, *args, **kw):
        self.journal.append((model, method, copy.deepcopy(args), copy.deepcopy(kw)))
        store = self.data.setdefault(model, {})
        if method == 'get_param':
            return args[1] if len(args) > 1 else False
        if method in ('search_read', 'search', 'search_count'):
            dom = args[0] if args else []
            rows = [r for r in store.values() if self._match(r, dom)]
            if method == 'search': return [r['id'] for r in rows]
            if method == 'search_count': return len(rows)
            return [copy.deepcopy(r) for r in rows][: (kw.get('limit') or 10**6)]
        if method == 'read':
            return [copy.deepcopy(store[i]) for i in args[0]]
        if method == 'write':
            for i in args[0]:
                for f, v in args[1].items():
                    if isinstance(v, list) and v and isinstance(v[0], list) and v[0][0] == 4:
                        store[i][f] = list(store[i].get(f) or []) + [c[1] for c in v]
                    elif f == 'x_operateur_id' or f == 'x_palette_scan_id' or f == 'x_studio_colis' or f == 'x_studio_colis_id':
                        if v:
                            lab = {'x_operateur_id': 'hr.employee', 'x_palette_scan_id': 'stock.package', 'x_studio_colis': 'stock.package', 'x_studio_colis_id': 'stock.package'}[f]
                            store[i][f] = [v, self.data[lab][v]['name']]
                        else:
                            store[i][f] = False
                    else:
                        store[i][f] = v
            return True
        if method == 'create':
            vals = args[0] if isinstance(args[0], dict) else args[0][0]
            self.seq += 1; rec = dict(vals); rec['id'] = self.seq
            for f in ('x_studio_colis_id', 'x_studio_of_id'):
                if f in rec and isinstance(rec[f], int):
                    lab = 'stock.package' if f == 'x_studio_colis_id' else 'mrp.production'
                    rec[f] = [rec[f], self.data[lab][rec[f]]['name']]
            rec.setdefault('write_date', '2026-10-07 09:00:00')
            store[self.seq] = rec
            return self.seq
        if method == 'message_post':
            return 1
        raise Exception('méthode non simulée : %s.%s' % (model, method))

    def ecritures(self):
        return [(m, me, a[0], a[1] if len(a) > 1 else None) for m, me, a, k in self.journal if me in ('write', 'create', 'message_post')]


def check(cond, msg):
    print(('  ✅ ' if cond else '  ❌ ') + msg)
    if not cond:
        raise SystemExit('ÉCHEC : ' + msg)


print('=== Tablette 2101 : palette d un autre opérateur, sans confirmation ===')
o = FauxOdoo()
r = W.executer(o, 2101, {'op': 628, 'of_id': 500, 'colis_id': 10, 'qte': 0})
check(r.get('confirmer') == 1 and r['proprietaire'] == 'DURAND Mickaël' and r['qte'] == 3 and r['of'] == 'WH/OF/12862', 'réponse « confirmer » avec propriétaire, OF et quantité (%s)' % r)
check(not o.ecritures(), 'aucune écriture tant que l opérateur n a pas confirmé')

print('=== Tablette 2101 : pose confirmée ===')
r = W.executer(o, 2101, {'op': 628, 'of_id': 500, 'colis_id': 10, 'qte': 0, 'confirme_autre': 1})
check(r.get('ok') == 1 and r.get('autre') == 1 and 'confirmé' in r['msg'] and r['entier'] == 1, 'pose faite en entier, marquée « autre » : %s' % r['msg'])
pk = o.data['stock.package'][10]
check(pk['x_operateur_id'][0] == 479 and 628 in pk['x_operateur_ids'], 'responsable inchangé (Mickaël), Frédéric ajouté comme co-opérateur')
check(o.data['mrp.production'][500]['x_studio_colis'][0] == 10, 'OF lié à la palette PACK0000010')
check(o.data['hr.employee'][628]['x_palette_scan_id'] is False and o.data['hr.employee'][479]['x_palette_scan_id'] is False, 'palette active de personne modifiée')
check(any(m == 'stock.package' and me == 'message_post' for m, me, *_ in o.ecritures()), 'note postée dans le fil de la palette')

print('=== Tablette 2101 : sa propre palette (chemin normal inchangé) ===')
o = FauxOdoo()
r = W.executer(o, 2101, {'op': 628, 'of_id': 500, 'colis_id': 11, 'qte': 0})
check(r.get('ok') == 1 and not r.get('confirmer') and not r.get('autre'), 'pose directe sur sa palette : %s' % r['msg'])
check(o.data['hr.employee'][628]['x_palette_scan_id'][0] == 11, 'palette active de Frédéric = PACK0000011')

print('=== Tablette 2101 : palette d un autre opérateur mais clôturée ===')
o = FauxOdoo(); o.data['stock.package'][10]['x_studio_cloturee'] = True
try:
    W.executer(o, 2101, {'op': 628, 'of_id': 500, 'colis_id': 10, 'qte': 0, 'confirme_autre': 1}); check(False, 'clôturée refusée')
except W.WebErreur as e:
    check('clôturée' in str(e), 'clôturée refusée même confirmée : %s' % e)

print('=== Poste de scan 2102 : scan OF sur la palette d un autre opérateur ===')
o = FauxOdoo()
r = W.executer(o, 2102, {'mode': 'scan', 'colis_id': 10, 'code': 'WH/OF/12862'})
check(r['ok'] == 0 and r.get('demande_autre', {}).get('of_id') == 500 and r['demande_autre']['proprietaire'] == 'DURAND Mickaël' and 'GUERIN' in r['demande_autre']['pour'], 'refus avec demande de confirmation : %s' % r['msg'])
check(not o.ecritures(), 'aucune écriture')
r = W.executer(o, 2102, {'mode': 'placer', 'colis_id': 10, 'of_id': 500, 'qte': 2})
check(r['ok'] == 0 and 'demande_autre' in r, 'garde-fou : « placer » sans autre_ok reste refusé')
check(not o.ecritures(), 'toujours aucune écriture')

print('=== Poste de scan 2102 : « Poser quand même » puis quantité ===')
r = W.executer(o, 2102, {'mode': 'placer_autre', 'colis_id': 10, 'of_id': 500, 'qte': 0})
check(r['ok'] == 1 and r.get('demande_qte', {}).get('autre_ok') == 1 and r['demande_qte']['remaining'] == 3, 'quantité demandée, avec autre_ok transmis : %s' % r['msg'])
check(not o.ecritures(), 'aucune écriture avant la quantité')
r = W.executer(o, 2102, {'mode': 'placer', 'colis_id': 10, 'of_id': 500, 'qte': 2, 'autre_ok': 1})
check(r['ok'] == 1 and 'confirmé' in r['msg'] and 'reste 1 / 3' in r['msg'], 'pose de 2 pièces faite : %s' % r['msg'])
pk = o.data['stock.package'][10]
check(pk['x_operateur_id'][0] == 479 and 628 in pk['x_operateur_ids'], 'responsable inchangé, opérateur de la pierre ajouté comme co-opérateur')
check(o.data['hr.employee'][628]['x_palette_scan_id'] is False and o.data['hr.employee'][479]['x_palette_scan_id'] is False, 'palettes actives inchangées')
check(len(o.data['x_repartition_palette']) == 1 and list(o.data['x_repartition_palette'].values())[0]['x_studio_qte'] == 2, 'ligne de répartition de 2 pièces créée')
check(r['colis']['op_nom'] == 'DURAND Mickaël' and len(r['items']) == 1, 'état renvoyé : palette de Mickaël avec 1 OF')

print('=== Poste de scan 2102 : chemin normal (OF de l opérateur propriétaire) ===')
o = FauxOdoo(); o.data['mrp.workorder'][900]['employee_assigned_ids'] = [479]
r = W.executer(o, 2102, {'mode': 'scan', 'colis_id': 10, 'code': 'WH/OF/12862'})
check(r['ok'] == 1 and 'demande_qte' in r and r['demande_qte']['autre_ok'] == 0, 'quantité demandée sans confirmation : %s' % r['msg'])
r = W.executer(o, 2102, {'mode': 'placer', 'colis_id': 10, 'of_id': 500, 'qte': 3})
check(r['ok'] == 1 and 'confirmé' not in r['msg'] and o.data['hr.employee'][479]['x_palette_scan_id'][0] == 10, 'pose normale, palette active de Mickaël mise à jour : %s' % r['msg'])
print('\nTOUS LES TESTS PASSENT')
