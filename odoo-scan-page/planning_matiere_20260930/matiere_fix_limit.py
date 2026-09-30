# -*- coding: utf-8 -*-
"""Board machines (vue 7876) : avec un filtre Matière, les OF brouillons « À planifier » restent limités à 30 comme sans filtre,
mais la matière est appliquée dans la requête (catégorie d'article) et non après coup — sinon la page chargeait tous les brouillons."""
import io, os, ssl, sys, xmlrpc.client
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
a = x('ir.ui.view', 'read', [7876], ['arch_db'])[0]['arch_db']
old1 = "limit=(None if (q or bc or tp) else 30)"
old2 = """(bc and [('production_id.origin','=',bc)] or [])"/>"""
new2 = """(bc and [('production_id.origin','=',bc)] or []) + ((tp and tp != 'AUTRE') and [('production_id.x_studio_catgorie.complete_name','ilike','/ ' + tp)] or [])"/>"""
assert a.count(old1) == 1 and a.count(old2) == 1, (a.count(old1), a.count(old2))
n = a.replace(old1, "limit=(None if (q or bc) else 30)").replace(old2, new2)
ET.fromstring(n.encode('utf-8'))
x('ir.ui.view', 'write', [7876], {'arch_base': n})
relu = x('ir.ui.view', 'read', [7876], ['arch_db'])[0]['arch_db']
print('7876 écrite :', relu == n)
io.open('ocr/odoo-scan-page/planning_matiere_20260930/7876.xml', 'w', encoding='utf-8', newline='\n').write(relu)
i = relu.find('draft_dom'); print(relu[i - 20:i + 330])
