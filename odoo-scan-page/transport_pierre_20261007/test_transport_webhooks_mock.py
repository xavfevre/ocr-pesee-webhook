# -*- coding: utf-8 -*-
"""Test hors ligne de transport_webhooks.py (actions 2118 / 2119 / 2122 portées sur le relais) avec un faux Odoo en mémoire.
  python test_transport_webhooks_mock.py"""
import os, sys, re
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import transport_webhooks as T


class Faux:
    def __init__(self):
        self.d = {
            'sale.order': {1: {'id': 1, 'name': 'S1', 'state': 'draft', 'x_mode_transport': 'camions', 'partner_id': [10, 'CLIENT SA'],
                               'partner_shipping_id': [11, 'CLIENT SA, Chantier'], 'company_id': [1, 'SARL MAQUIGNON'], 'x_transporteurs_ids': [20, 21],
                               'user_id': [12, 'Céline'], 'x_studio_date_de_livraison_souhait': '2026-10-15', 'commitment_date': False,
                               'x_transport_achat': 0.0, 'x_transporteur_id': False, 'x_ordre_transport_id': False, 'order_line': [101, 102, 103, 104]}},
            'sale.order.line': {101: {'id': 101, 'order_id': [1, 'S1'], 'display_type': False, 'product_id': [500, 'TUFFEAU'], 'name': 'Pierre A', 'sequence': 10, 'price_unit': 100.0, 'product_uom_qty': 2.0, 'x_studio_poids': 1000.0, 'x_studio_vol': 0.5, 'x_studio_palettes': 'P1'},
                                102: {'id': 102, 'order_id': [1, 'S1'], 'display_type': False, 'product_id': [501, 'Pose'], 'name': 'Pose', 'sequence': 11, 'price_unit': 50.0, 'product_uom_qty': 1.0, 'x_studio_poids': 999.0, 'x_studio_vol': 9.0, 'x_studio_palettes': 'ZZ'},
                                103: {'id': 103, 'order_id': [1, 'S1'], 'display_type': False, 'product_id': [502, 'Eco'], 'name': 'Eco-contribution mobilier', 'sequence': 12, 'price_unit': 1.5, 'product_uom_qty': 1.0, 'x_studio_poids': 0.0, 'x_studio_vol': 0.0, 'x_studio_palettes': ''},
                                104: {'id': 104, 'order_id': [1, 'S1'], 'display_type': 'line_note', 'product_id': False, 'name': 'Prix départ carrière', 'sequence': 10000, 'price_unit': 0.0, 'product_uom_qty': 0.0, 'x_studio_poids': 0.0, 'x_studio_vol': 0.0, 'x_studio_palettes': ''}},
            'product.product': {500: {'id': 500, 'type': 'consu'}, 501: {'id': 501, 'type': 'service'}, 502: {'id': 502, 'type': 'consu'}, 5899: {'id': 5899, 'type': 'consu'}},
            'res.partner': {10: {'id': 10, 'name': 'CLIENT SA', 'street': '1 rue A', 'street2': False, 'zip': '86000', 'city': 'POITIERS'},
                            11: {'id': 11, 'name': 'CLIENT SA, Chantier', 'street': '5 rue du Chantier', 'street2': 'Bât. B', 'zip': '44000', 'city': 'NANTES'},
                            20: {'id': 20, 'name': 'GENDRON TRANSPORTS', 'email': 'devis@gendron.fr'}, 21: {'id': 21, 'name': 'TRANSPORTS P. FRECHOT', 'email': False}},
            'res.users': {12: {'id': 12, 'email': 'xavier@maquignon.com'}},
            'purchase.order': {}, 'purchase.order.line': {},
            'ir.config_parameter': {'maquignon.transport_marge_pct': '40', 'maquignon.transport_tarif_cc': 'celine@maquignon.com'},
        }
        self.journal = []
        self.prochain = 9000

    def __call__(self, model, method, *params, **kw):
        return getattr(self, 'm_' + method)(model, *params, **kw)

    def _val(self, model, rec, champ):
        if '.' in champ:
            a, b = champ.split('.', 1)
            ids = rec.get(a) or []
            if isinstance(ids, list) and len(ids) == 2 and isinstance(ids[1], str):
                ids = [ids[0]]
            sous = {'purchase.order': 'purchase.order.line', 'sale.order': 'sale.order.line'}[model]
            return [v for i in ids for v in self._val(sous, self.d[sous][i], b)]
        v = rec.get(champ, False)
        if isinstance(v, list) and len(v) == 2 and isinstance(v[1], str):
            v = v[0]
        return v if isinstance(v, list) else [v]

    def _ok(self, model, rec, dom):
        for f, op, v in dom:
            vals = self._val(model, rec, f)
            if op == '=' and v not in vals:
                return False
            if op == '!=' and v in vals:
                return False
            if op == 'in' and not any(e in v for e in vals):
                return False
        return True

    def m_search(self, model, dom, limit=None, **kw):
        ids = [i for i, r in self.d[model].items() if self._ok(model, r, dom)]
        return ids[:limit] if limit else ids

    def m_search_read(self, model, dom, fields=None, order=None, limit=None, **kw):
        recs = [self.d[model][i] for i in self.m_search(model, dom, limit)]
        if order and 'sequence' in order:
            recs.sort(key=lambda r: (r['sequence'], r['id']))
        return [{f: r.get(f, False) for f in ['id'] + list(fields or r.keys())} for r in recs]

    def m_read(self, model, ids, fields, **kw):
        return [{f: self.d[model][i].get(f, False) for f in ['id'] + list(fields)} for i in ids]

    def m_write(self, model, ids, vals, **kw):
        for i in ids:
            self.d[model][i].update(vals)
        return True

    def m_create(self, model, vals, **kw):
        self.prochain += 1
        rid = self.prochain
        vals = dict(vals, id=rid)
        if model == 'purchase.order':
            vals['name'] = 'P%05d' % rid
            vals['partner_id'] = [vals['partner_id'], self.d['res.partner'][vals['partner_id']]['name']]
            vals.setdefault('state', 'draft')
            lignes = vals.pop('order_line', [])
            vals['order_line'] = []
            vals['amount_untaxed'] = 0.0
            for _, _, lv in lignes:
                self.prochain += 1
                lv = dict(lv, id=self.prochain, order_id=[rid, vals['name']], product_id=[lv['product_id'], 'art'])
                self.d['purchase.order.line'][self.prochain] = lv
                vals['order_line'].append(self.prochain)
                vals['amount_untaxed'] += lv['price_unit'] * lv['product_qty']
        if model == 'sale.order.line':
            vals['product_id'] = [vals['product_id'], 'Transport de pierres (Forfait Palettes)']
            vals['order_id'] = [vals['order_id'], 'S1']
            vals.setdefault('display_type', False)
            for f in ('x_studio_poids', 'x_studio_vol'):
                vals.setdefault(f, 0.0)
            vals.setdefault('x_studio_palettes', '')
            self.d['sale.order'][vals['order_id'][0]]['order_line'].append(rid)
        self.d[model][rid] = vals
        self.journal.append(('create', model, rid))
        return rid

    def m_unlink(self, model, ids, **kw):
        for i in ids:
            del self.d[model][i]
            if model == 'sale.order.line':
                for so in self.d['sale.order'].values():
                    if i in so['order_line']:
                        so['order_line'].remove(i)
        self.journal.append(('unlink', model, list(ids)))
        return True

    def m_get_param(self, model, cle, defaut=False, **kw):
        return self.d['ir.config_parameter'].get(cle, defaut)

    def m_message_post(self, model, ids, **kw):
        self.journal.append(('note', model, ids[0], re.sub(r'<[^>]+>', '', kw.get('body', ''))))
        return 1

    def m_send_mail(self, model, ids, res_id, **kw):
        self.journal.append(('mail', ids[0], res_id, kw.get('email_values', {}).get('email_cc')))
        return 77

    def m_button_cancel(self, model, ids, **kw):
        for i in ids:
            self.d[model][i]['state'] = 'cancel'
        self.journal.append(('cancel', model, list(ids)))
        return None


def notes(f):
    return [j[3] for j in f.journal if j[0] == 'note']


def lignes(f, so=1):
    return sorted(({'id': l['id'], 'seq': l['sequence'], 'nom': l['name'], 'prix': l['price_unit']} for l in f.d['sale.order.line'].values()), key=lambda l: (l['seq'], l['id']))


f = Faux()
T._param.__globals__['_PARAMS'].clear()
# 1. « Nos camions » : ligne à 0 juste après la dernière ligne produit, éco-contribution et note de fin décalées
r = T.mode_devis(f, 1)
ls = lignes(f)
print('1.', r, '|', [(l['seq'], l['nom'][:22], l['prix']) for l in ls])
assert r.startswith('ligne ajoutée (camions, 0.00)')
assert [(l['seq'], l['nom'][:9]) for l in ls] == [(10, 'Pierre A'), (11, 'Pose'), (12, 'Transport'), (13, 'Eco-contr'), (10001, 'Prix dépa')], ls
assert 'ajoutée en fin de devis (nos camions)' in notes(f)[-1]
# 2. seconde fois : rien
assert T.mode_devis(f, 1).startswith('rien à faire (camions, 1'), 'idempotence'
# 3. « Enlèvement par le client » : ligne vide retirée
f.d['sale.order'][1]['x_mode_transport'] = 'client'
r = T.mode_devis(f, 1); print('3.', r)
assert r == 'ligne vide retirée' and len(f.d['sale.order'][1]['order_line']) == 4
# 4. « Transporteur extérieur » avec prix d'achat connu : prix + 40 %, nom avec le transporteur
f.d['sale.order'][1].update({'x_mode_transport': 'exterieur', 'x_transport_achat': 300.0, 'x_transporteur_id': [20, 'GENDRON TRANSPORTS']})
r = T.mode_devis(f, 1); l = [l for l in lignes(f) if l['nom'].startswith('Transport')][0]
print('4.', r, '|', l)
assert l['prix'] == 420.0 and l['nom'] == 'Transport de pierres (Forfait Palettes) - GENDRON TRANSPORTS' and l['seq'] == 12
assert 'prix d achat + 40 % = 420.00 EUR HT' in notes(f)[-1]
# 5. état « done » ignoré
f.d['sale.order'][1]['state'] = 'done'
assert T.mode_devis(f, 1) == 'ignoré : état done'
f.d['sale.order'][1]['state'] = 'sent'
f.m_unlink('sale.order.line', [l['id']])
# 6. demande de tarif : 2 demandes de prix, 1 mail (copie Céline + vendeur), description sans la ligne de service
f.d['sale.order'][1]['x_transport_achat'] = 0.0
r = T.transport_webhook(f, 'tarif', {'_model': 'sale.order', '_id': 1})
pos = list(f.d['purchase.order'].values())
print('6.', r, '|', [(po['name'], po['partner_id'][1], po['state']) for po in pos])
assert r.startswith('2 demande(s) créée(s)') and [po['state'] for po in pos] == ['sent', 'draft']
desc = f.d['purchase.order.line'][pos[0]['order_line'][0]]['name']
print('   description :', desc.replace(chr(10), ' / '))
assert 'Palettes : 1 (P1)' in desc and 'Poids total estimé : 1000 kg - volume : 0.50 m³' in desc and 'Date de livraison souhaitée : 15/10/2026' in desc
assert 'Livraison : CLIENT SA, Chantier, 5 rue du Chantier, Bât. B, 44000 NANTES' in desc and 'Enlèvement : Carrières Maquignon' in desc
mails = [j for j in f.journal if j[0] == 'mail']
assert mails == [('mail', 27, pos[0]['id'], 'celine@maquignon.com, xavier@maquignon.com')], mails
assert 'Demandes de tarif transport créées' in notes(f)[-1] and 'GENDRON TRANSPORTS' in notes(f)[-1] and "pas d'adresse e-mail" in notes(f)[-1]
print('   note :', notes(f)[-1][:200])
# 7. second clic : rien à créer
assert T.tarif(f, 1) == 'rien à créer' and len(f.d['purchase.order']) == 2
# 8. mauvais mode / aucun transporteur
f.d['sale.order'][1]['x_mode_transport'] = 'camions'
assert T.tarif(f, 1) == 'refus : mode camions' and 'Transporteur extérieur' in notes(f)[-1]
f.d['sale.order'][1]['x_mode_transport'] = 'exterieur'; f.d['sale.order'][1]['x_transporteurs_ids'] = []
assert T.tarif(f, 1) == 'refus : aucun transporteur coché'
f.d['sale.order'][1]['x_transporteurs_ids'] = [20, 21]
# 9. demande GENDRON confirmée à 410 : devis renseigné, FRECHOT annulée, ligne transport créée à 574
po = pos[0]; po['state'] = 'purchase'; po['amount_untaxed'] = 410.0
f.d['purchase.order.line'][po['order_line'][0]]['price_unit'] = 410.0
r = T.transport_webhook(f, 'achat-confirme', {'_model': 'purchase.order', '_id': po['id']})
so = f.d['sale.order'][1]; l = [l for l in lignes(f) if l['nom'].startswith('Transport')]
print('9.', r, '|', so['x_transporteur_id'], so['x_transport_achat'], so['x_ordre_transport_id'], '|', l)
assert so['x_transporteur_id'] == 20 and so['x_transport_achat'] == 410.0 and so['x_ordre_transport_id'] == po['id']
assert pos[1]['state'] == 'cancel' and l and l[0]['prix'] == 574.0 and l[0]['seq'] == 12 and 'GENDRON' in l[0]['nom']
assert 'Transporteur retenu : GENDRON TRANSPORTS - 410.00 EUR HT' in notes(f)[-2] and 'Autres demandes annulées : TRANSPORTS P. FRECHOT' in notes(f)[-2]
assert 'ajoutée en fin de devis : prix d achat 410.00 EUR HT + 40 % = 574.00 EUR HT' in notes(f)[-1]
# 10. ligne vide existante : valorisée au lieu d'être doublée
f.d['sale.order.line'][l[0]['id']]['price_unit'] = 0.0
r = T.achat_confirme(f, po['id']); l = [l for l in lignes(f) if l['nom'].startswith('Transport')]
print('10.', r, '|', l)
assert r.endswith('ligne valorisée 574.00') and len(l) == 1 and l[0]['prix'] == 574.0
# 11. ligne déjà chiffrée : inchangée ; demande sans article transport : ignorée ; état non confirmé : ignoré
f.d['sale.order.line'][l[0]['id']]['price_unit'] = 600.0
assert T.achat_confirme(f, po['id']).endswith('ligne déjà chiffrée, inchangée') and f.d['sale.order.line'][l[0]['id']]['price_unit'] == 600.0
f.d['purchase.order.line'][po['order_line'][0]]['product_id'] = [999, 'autre']
assert T.achat_confirme(f, po['id']) == 'ignoré : pas de ligne Transport affrété'
po['state'] = 'draft'
assert T.achat_confirme(f, po['id']).startswith('ignoré : état draft')
# 12. modèle inattendu
try:
    T.transport_webhook(f, 'tarif', {'_model': 'purchase.order', '_id': 1}); raise AssertionError('WebErreur attendue')
except T.WebErreur as e:
    print('12.', e)
print()
print('TEST MOCK OK : %d notes, %d mail(s), %d création(s)' % (len(notes(f)), len([j for j in f.journal if j[0] == 'mail']), len([j for j in f.journal if j[0] == 'create'])))
