# -*- coding: utf-8 -*-
"""Suivi des EPI (équipements de protection individuelle) — configuration Odoo, idempotente :
 1. catégorie d'articles « EPI » ; les 2 articles existants (chaussures Defender, bottes fourrées) y passent,
    suivis en stock, achat seulement ; attribut « Pointure » 38→47 en variantes sur les deux
 2. emplacements : « Maq/Stock EPI » (interne, accueil) et « EPI remis aux salariés » (virtuel, consommation)
 3. types d'opération « Réception EPI » (fournisseur -> Stock EPI) et « Dotation EPI » (Stock EPI -> remis)
 4. champs : stock.picking.x_employee_id, stock.move.x_employee_id (Salarié), hr.employee.x_epi_move_ids
    + onglet « EPI » sur la fiche salarié, champ Salarié sur le transfert (types EPI)
 5. paramètres maquignon.epi_* (ids) et clé de la page maquignon.epi_key
  python epi_setup.py prod"""
import os, ssl, sys, secrets, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else '').lower()
assert mode == 'prod', 'usage : python epi_setup.py prod'
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)


def x(mo, me, *a, **k):
    k['context'] = dict({'allowed_company_ids': [1, 2, 3, 4, 13]}, **k.get('context', {}))
    return m.execute_kw(D, uid, p, mo, me, list(a), k)


def creer(model, vals):
    r = x(model, 'create', [vals])
    return r[0] if isinstance(r, list) else r


def un(model, dom, vals, lab):
    ids = x(model, 'search', dom, context={'active_test': False})
    if ids:
        print('%-42s existe (%s)' % (lab, ids[0])); return ids[0]
    i = creer(model, vals); print('%-42s créé (%s)' % (lab, i)); return i


# 1. catégorie + articles
cat = un('product.category', [['name', '=', 'EPI']], {'name': 'EPI', 'parent_id': 1}, 'catégorie EPI')
attr = un('product.attribute', [['name', '=', 'Pointure']], {'name': 'Pointure', 'create_variant': 'always', 'display_type': 'radio'}, 'attribut Pointure')
vals_ids = []
for pt in range(38, 48):
    vals_ids.append(un('product.attribute.value', [['attribute_id', '=', attr], ['name', '=', str(pt)]], {'attribute_id': attr, 'name': str(pt), 'sequence': pt}, 'pointure %d' % pt))
for tid in (2989, 2990):
    t = x('product.template', 'read', [tid], fields=['name', 'categ_id', 'is_storable', 'attribute_line_ids', 'purchase_ok', 'sale_ok'])[0]
    vals = {}
    if t['categ_id'][0] != cat: vals['categ_id'] = cat
    if not t['is_storable']: vals['is_storable'] = True
    if not t['purchase_ok']: vals['purchase_ok'] = True
    if t['sale_ok']: vals['sale_ok'] = False
    if not t['attribute_line_ids']:
        vals['attribute_line_ids'] = [[0, 0, {'attribute_id': attr, 'value_ids': [[6, 0, vals_ids]]}]]
    if vals:
        x('product.template', 'write', [tid], vals)
    nv = len(x('product.template', 'read', [tid], fields=['product_variant_ids'])[0]['product_variant_ids'])
    print('%-42s -> EPI, stock suivi, %d variante(s)' % (t['name'][:40], nv))

# 2. emplacements
loc_stock = un('stock.location', [['complete_name', '=', 'Maq/Stock EPI']], {'name': 'Stock EPI', 'location_id': 7, 'usage': 'internal', 'company_id': 1}, 'emplacement Maq/Stock EPI')
parent_virtuel = x('stock.location', 'read', [14], fields=['location_id'])[0]['location_id'][0]
loc_conso = un('stock.location', [['name', '=', 'EPI remis aux salariés']], {'name': 'EPI remis aux salariés', 'location_id': parent_virtuel, 'usage': 'inventory', 'company_id': 1}, 'emplacement EPI remis aux salariés')

# 3. types d'opération
pt_rec = un('stock.picking.type', [['sequence_code', '=', 'EPIIN'], ['company_id', '=', 1]],
            {'name': 'Réception EPI', 'code': 'incoming', 'sequence_code': 'EPIIN', 'warehouse_id': 1, 'company_id': 1,
             'default_location_src_id': 4, 'default_location_dest_id': loc_stock, 'show_operations': True}, 'type Réception EPI')
pt_dot = un('stock.picking.type', [['sequence_code', '=', 'EPI'], ['company_id', '=', 1]],
            {'name': 'Dotation EPI', 'code': 'internal', 'sequence_code': 'EPI', 'warehouse_id': 1, 'company_id': 1,
             'default_location_src_id': loc_stock, 'default_location_dest_id': loc_conso, 'show_operations': True}, 'type Dotation EPI')

# 4. champs
def champ(model, name, vals, lab):
    mid = x('ir.model', 'search', [['model', '=', model]])[0]
    ex = x('ir.model.fields', 'search', [['model_id', '=', mid], ['name', '=', name]])
    if ex:
        print('%-42s existe (%s)' % (lab, ex[0])); return ex[0]
    i = creer('ir.model.fields', dict(vals, model_id=mid, name=name, state='manual')); print('%-42s créé (%s)' % (lab, i)); return i

champ('stock.picking', 'x_employee_id', {'ttype': 'many2one', 'relation': 'hr.employee', 'field_description': 'Salarié', 'copied': True}, 'stock.picking.x_employee_id')
champ('stock.move', 'x_employee_id', {'ttype': 'many2one', 'relation': 'hr.employee', 'field_description': 'Salarié', 'copied': True}, 'stock.move.x_employee_id')
champ('hr.employee', 'x_epi_move_ids', {'ttype': 'one2many', 'relation': 'stock.move', 'relation_field': 'x_employee_id', 'field_description': 'EPI remis'}, 'hr.employee.x_epi_move_ids')

VUES = [
    ('stock.picking.form - Salarié (EPI)', 'stock.picking', 'form', 'stock.view_picking_form', 99,
     """<data>
  <xpath expr="//field[@name='partner_id']" position="after">
    <field name="x_employee_id" invisible="picking_type_id not in [%d, %d]"/>
  </xpath>
</data>""" % (pt_dot, pt_rec)),
    ('hr.employee.form - onglet EPI', 'hr.employee', 'form', 'hr.view_employee_form', 99,
     """<data>
  <xpath expr="//notebook" position="inside">
    <page string="EPI" name="epi">
      <field name="x_epi_move_ids" readonly="1">
        <list default_order="date desc">
          <field name="date" widget="date"/>
          <field name="product_id"/>
          <field name="quantity" string="Quantité"/>
          <field name="location_dest_id" string="Vers"/>
          <field name="reference"/>
          <field name="state" widget="badge"/>
        </list>
      </field>
    </page>
  </xpath>
</data>"""),
]
for nom, model, typ, base_xml, prio, arch in VUES:
    base = [v for v in x('ir.ui.view', 'search_read', [['model', '=', model], ['type', '=', typ], ['inherit_id', '=', False]], fields=['xml_id']) if v['xml_id'] == base_xml]
    assert base, base_xml
    ex = x('ir.ui.view', 'search', [['name', '=', nom]])
    if ex:
        x('ir.ui.view', 'write', ex, {'arch_base': arch, 'active': True}); print('%-42s mise à jour (%s)' % (nom, ex[0]))
    else:
        i = creer('ir.ui.view', {'name': nom, 'model': model, 'type': typ, 'inherit_id': base[0]['id'], 'mode': 'extension', 'priority': prio, 'arch_base': arch}); print('%-42s créée (%s)' % (nom, i))

# 5. paramètres
for cle, val in (('maquignon.epi_categ', cat), ('maquignon.epi_loc_stock', loc_stock), ('maquignon.epi_loc_conso', loc_conso), ('maquignon.epi_pt_dot', pt_dot), ('maquignon.epi_pt_rec', pt_rec)):
    x('ir.config_parameter', 'set_param', cle, str(val))
if not x('ir.config_parameter', 'get_param', 'maquignon.epi_key'):
    x('ir.config_parameter', 'set_param', 'maquignon.epi_key', secrets.token_urlsafe(18))
    print('clé de la page EPI créée')
else:
    print('clé de la page EPI déjà en place')
print('paramètres :', {k: x('ir.config_parameter', 'get_param', k) for k in ('maquignon.epi_categ', 'maquignon.epi_loc_stock', 'maquignon.epi_loc_conso', 'maquignon.epi_pt_dot', 'maquignon.epi_pt_rec')})
