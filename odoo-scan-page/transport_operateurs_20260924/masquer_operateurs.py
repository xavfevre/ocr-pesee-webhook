# -*- coding: utf-8 -*-
"""Champ « Opérateurs » (x_studio_operateurs) masqué sur les tâches sans étiquette TP (id 1) : formulaire tâche
(vue Studio 4380, priorité 9990 -> notre héritage passe après) et kanban (étiquettes opérateurs, vue 7977).
  python masquer_operateurs.py test|prod"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'test').lower()
U, D = ('https://testmaq230926v2.odoo.com', 'testmaq230926v2') if mode == 'test' else ('https://maquignon.odoo.com', 'maquignon')
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [1, 2, 3, 4, 13]}))
VUES = [
    ('project.task.form - opérateurs masqués hors TP', 'form', 'project.view_task_form2', 9995,
     """<data>
  <xpath expr="//field[@name='x_studio_operateurs']" position="attributes">
    <attribute name="invisible">project_id not in [2] or 1 not in tag_ids</attribute>
  </xpath>
</data>"""),
    ('project.task.kanban - opérateurs masqués hors TP', 'kanban', 'project.view_task_kanban', 9995,
     """<data>
  <xpath expr="//field[@name='x_studio_operateurs']" position="attributes">
    <attribute name="invisible">1 not in tag_ids</attribute>
  </xpath>
</data>"""),
]
for nom, typ, base_xml, prio, arch in VUES:
    base = [v for v in x('ir.ui.view', 'search_read', [['model', '=', 'project.task'], ['type', '=', typ], ['inherit_id', '=', False]], fields=['xml_id']) if v['xml_id'] == base_xml]
    assert base, base_xml
    ex = x('ir.ui.view', 'search', [['name', '=', nom]])
    if ex:
        x('ir.ui.view', 'write', ex, {'arch_base': arch, 'active': True, 'priority': prio}); vid = ex[0]; print(nom, ': mise à jour', vid)
    else:
        vid = x('ir.ui.view', 'create', [{'name': nom, 'model': 'project.task', 'type': typ, 'inherit_id': base[0]['id'], 'mode': 'extension', 'priority': prio, 'arch_base': arch}])
        vid = vid[0] if isinstance(vid, list) else vid; print(nom, ': créée', vid, '(hérite de', base[0]['id'], ')')
for typ in ('form', 'kanban'):
    arch = x('project.task', 'get_views', [[False, typ]])['views'][typ]['arch']
    i = arch.find('name="x_studio_operateurs"')
    print(typ, 'combinée :', arch[i:i + 320].replace('\n', ' ') if i >= 0 else 'CHAMP ABSENT')
