# -*- coding: utf-8 -*-
"""Contacts : recherche et regroupement par liste de prix (champ stocké `specific_property_product_pricelist`, dépendant
de la société). Vue de recherche héritée de base.view_res_partner_filter (128). Usage : dry | apply"""
import os, ssl, sys, io, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
NAME = 'res.partner.search.liste.de.prix (Maquignon)'
ARCH = """<data>
  <xpath expr="//field[@name='category_id']" position="after">
    <field name="specific_property_product_pricelist" string="Liste de prix"/>
  </xpath>
  <xpath expr="//filter[@name='group_country']" position="after">
    <filter name="group_pricelist" string="Liste de prix" context="{'group_by': 'specific_property_product_pricelist'}"/>
  </xpath>
</data>"""
ex = x('ir.ui.view', 'search_read', [['name', '=', NAME]], fields=['id'])
print('vue existante :', ex)
if mode == 'apply':
    if ex:
        x('ir.ui.view', 'write', [ex[0]['id']], {'arch_base': ARCH}); print('mise à jour', ex[0]['id'])
    else:
        vid = x('ir.ui.view', 'create', [{'name': NAME, 'type': 'search', 'model': 'res.partner', 'inherit_id': 128, 'mode': 'extension', 'priority': 99, 'arch_base': ARCH}])
        print('créée', vid)
    res = x('res.partner', 'get_views', [[128, 'search']], options={'load_filters': False}, context={'allowed_company_ids': [4], 'lang': 'fr_FR'})
    a = res['views']['search']['arch']
    print('vue combinée : champ =', 'specific_property_product_pricelist" string="Liste de prix"' in a, '| regroupement =', 'group_pricelist' in a)
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ocr', 'odoo-scan-page')
if os.path.isdir(d):
    with io.open(os.path.join(d, 'contacts_liste_de_prix.xml'), 'w', encoding='utf-8') as f:
        f.write('<!-- %s : vue de recherche res.partner héritée de base.view_res_partner_filter (128), prio 99, créée le 17/09/2026 par XML-RPC -->\n%s\n' % (NAME, ARCH))
    print('archive :', os.path.join(d, 'contacts_liste_de_prix.xml'))
