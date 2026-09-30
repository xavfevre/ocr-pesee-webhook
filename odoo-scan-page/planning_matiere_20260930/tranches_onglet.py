# -*- coding: utf-8 -*-
"""Onglet « 🪚 Tranches » ajouté dans la barre d'onglets des 4 pages de planning (7876, 7878, 7875, 7877), avant « Vue opérateurs ».
  python tranches_onglet.py dry|apply"""
import io, os, ssl, sys, xmlrpc.client
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
LI = '''<li class="nav-item"><a class="nav-link" t-attf-href="/planning-tranches?tp={{tp}}">🪚 Tranches</a></li>\n          '''
ANCRES = {
    7876: '''<li class="nav-item"><a class="nav-link" t-attf-href="/planning-operateurs?q={{q}}&amp;bc={{bc}}&amp;tp={{tp}}">👷 Vue opérateurs</a></li>''',
    7875: '''<li class="nav-item"><a class="nav-link" t-attf-href="/planning-operateurs?q={{q}}&amp;bc={{bc}}&amp;tp={{tp}}">👷 Vue opérateurs</a></li>''',
    7877: '''<li class="nav-item"><a class="nav-link" t-attf-href="/planning-operateurs?q={{q}}&amp;bc={{bc}}&amp;tp={{tp}}">👷 Vue opérateurs</a></li>''',
    7878: '''<li class="nav-item"><a class="nav-link active fw-bold" href="#">👷 Vue opérateurs</a></li>''',
}
for v in x('ir.ui.view', 'read', list(ANCRES), ['name', 'arch_db']):
    a = v['arch_db']
    if 'planning-tranches' in a:
        print(v['id'], v['name'], ': onglet déjà présent'); continue
    anc = ANCRES[v['id']]
    assert a.count(anc) == 1, (v['id'], a.count(anc))
    n = a.replace(anc, LI + anc)
    ET.fromstring(n.encode('utf-8'))
    print('%s %-22s : onglet inséré, XML OK' % (v['id'], v['name']))
    if mode == 'apply':
        x('ir.ui.view', 'write', [v['id']], {'arch_base': n})
        relu = x('ir.ui.view', 'read', [v['id']], ['arch_db'])[0]['arch_db']
        io.open('ocr/odoo-scan-page/planning_matiere_20260930/%d.xml' % v['id'], 'w', encoding='utf-8', newline='\n').write(relu)
        print('   écrite :', relu == n)
