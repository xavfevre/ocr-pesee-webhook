# -*- coding: utf-8 -*-
"""Étiquettes sur les commandes clients (16/09/2026) : le champ standard « Étiquettes » (sale.order.tag_ids, crm.tag)
est remonté en haut à droite du formulaire, affiché par défaut dans les listes Devis / Commandes, ajouté à la recherche
(recherche + regroupement). Étiquettes créées : En attente accord architecte / accord client / acompte.
Usage : python tags_apply.py dry | apply"""
import os, ssl, sys, io, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
VUES = [
    ('sale.order.form.etiquettes (Maquignon)', 'form', 2614, 210, """<data>
  <xpath expr="//group[@name='order_details']/*[1]" position="before">
    <xpath expr="//field[@name='tag_ids']" position="move"/>
  </xpath>
  <xpath expr="//field[@name='tag_ids']" position="attributes">
    <attribute name="string">Étiquettes</attribute>
    <attribute name="options">{'color_field': 'color'}</attribute>
    <attribute name="placeholder">Ex. : En attente accord architecte</attribute>
  </xpath>
</data>"""),
    ('sale.order.list.etiquettes (Maquignon)', 'list', 2608, 99, """<data>
  <xpath expr="//field[@name='partner_id']" position="after">
    <xpath expr="//field[@name='tag_ids']" position="move"/>
  </xpath>
  <xpath expr="//field[@name='tag_ids']" position="attributes">
    <attribute name="optional">show</attribute>
    <attribute name="string">Étiquettes</attribute>
  </xpath>
</data>"""),
    ('sale.order.search.etiquettes (Maquignon)', 'search', 2615, 99, """<data>
  <xpath expr="//field[@name='partner_id']" position="after">
    <field name="tag_ids" string="Étiquettes"/>
  </xpath>
  <xpath expr="//filter[@name='customer']" position="after">
    <filter name="groupby_tag_ids" string="Étiquettes" context="{'group_by': 'tag_ids'}"/>
  </xpath>
</data>"""),
]
TAGS = [('En attente accord architecte', 1), ('En attente accord client', 2), ('En attente acompte', 3)]
existants = {v['name']: v['id'] for v in x('ir.ui.view', 'search_read', [['name', 'in', [v[0] for v in VUES]]], fields=['name'])}
print('vues déjà présentes :', existants)
for name, typ, parent, prio, arch in VUES:
    print('-', name, '-> hérite', parent, 'prio', prio, '(%d car.)' % len(arch))
    if mode != 'apply':
        continue
    vals = {'name': name, 'type': typ, 'model': 'sale.order', 'inherit_id': parent, 'mode': 'extension', 'priority': prio, 'arch_base': arch}
    if name in existants:
        x('ir.ui.view', 'write', [existants[name]], {'arch_base': arch, 'priority': prio}); print('   mise à jour', existants[name])
    else:
        vid = x('ir.ui.view', 'create', [vals]); print('   créée', vid)
for nom, couleur in TAGS:
    ex = x('crm.tag', 'search', [['name', '=ilike', nom]])
    print('- étiquette', nom, ': existe' if ex else ': à créer')
    if mode == 'apply' and not ex:
        print('   créée', x('crm.tag', 'create', [{'name': nom, 'color': couleur}]))
# archive des vues dans le dépôt
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ocr', 'odoo-scan-page')
if os.path.isdir(d):
    with io.open(os.path.join(d, 'etiquettes_commandes.xml'), 'w', encoding='utf-8') as f:
        f.write('<!-- Étiquettes commandes clients (Maquignon) — vues héritées créées le 16/09/2026 par XML-RPC (ir.ui.view) -->\n')
        for name, typ, parent, prio, arch in VUES:
            f.write('\n<!-- %s : type %s, inherit_id %d, priority %d -->\n%s\n' % (name, typ, parent, prio, arch))
    print('archive :', os.path.join(d, 'etiquettes_commandes.xml'))
