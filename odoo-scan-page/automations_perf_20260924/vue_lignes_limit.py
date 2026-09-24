# -*- coding: utf-8 -*-
"""Formulaire commande : la liste des lignes (vue Studio, limit=200) passe à LIMITE lignes par page ; le pager permet
toujours d'afficher plus (cliquer sur « 1-60 / 606 » et saisir 1-606).
  python vue_lignes_limit.py [limite|off]"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
arg = sys.argv[1] if len(sys.argv) > 1 else '60'
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [1, 2, 3, 4, 13]}))
NOM = 'sale.order.form - lignes par page'
base = x('ir.ui.view', 'search_read', [['model', '=', 'sale.order'], ['type', '=', 'form'], ['inherit_id', '=', False]], fields=['xml_id', 'name'])
base = [v for v in base if v['xml_id'] == 'sale.view_order_form']
assert base, 'vue de base introuvable'
ex = x('ir.ui.view', 'search', [['name', '=', NOM]])
if arg == 'off':
    if ex:
        x('ir.ui.view', 'write', ex, {'active': False}); print('vue désactivée', ex)
    else:
        print('rien à désactiver')
else:
    lim = int(arg)
    arch = """<data>
  <xpath expr="//field[@name='order_line']/list" position="attributes">
    <attribute name="limit">%d</attribute>
  </xpath>
</data>""" % lim
    if ex:
        x('ir.ui.view', 'write', ex, {'arch_base': arch, 'active': True, 'priority': 9999}); vid = ex[0]; print(NOM, ': mise à jour', vid)
    else:
        vid = x('ir.ui.view', 'create', [{'name': NOM, 'model': 'sale.order', 'type': 'form', 'inherit_id': base[0]['id'], 'mode': 'extension', 'priority': 9999, 'arch_base': arch}])
        vid = vid[0] if isinstance(vid, list) else vid; print(NOM, ': créée', vid)
arch = x('sale.order', 'get_views', [[False, 'form']])['views']['form']['arch']
i = arch.find('<field name="order_line"')
j = arch.find('<list', i)
print('liste des lignes combinée :', arch[j:j + 120].replace('\n', ' '))
