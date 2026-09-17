# -*- coding: utf-8 -*-
"""Bon de colisage (vue QWeb 7898 maquignon.report_bon_colisage) : dimensions des pierres à 3 décimales (0,275 et non
0,28), zéros de fin retirés comme sur le poste de scan. Contrôle des autres rapports. Usage : dry | apply"""
import os, ssl, sys, io, re, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
VID = 7898
a = x('ir.ui.view', 'read', [VID], fields=['arch_db', 'name'])[0]['arch_db']
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ocr', 'odoo-scan-page')
io.open(os.path.join(d, 'report_bon_colisage_7898.BEFORE_dims.xml'), 'w', encoding='utf-8').write(a)
pat = re.compile(r"'%\.2f' % (ofw\.x_studio_(?:long|larg|haut)_m_1|ln\.x_studio_of_id\.x_studio_(?:long|larg|haut)_m_1)")
hits = pat.findall(a)
print('vue %d : %d formats à 2 décimales sur les dimensions' % (VID, len(hits)), hits)
b = pat.sub(lambda mm: "('%%.3f' %% %s).rstrip('0').rstrip('.')" % mm.group(1), a)
print('après : %d formats 2 déc. restants sur dimensions | exemples :' % len(pat.findall(b)))
for mm in list(re.finditer(r"\('%\.3f' % [^)]+\)\.rstrip\('0'\)\.rstrip\('\.'\)", b))[:2]:
    print('   ', mm.group(0))
# autres rapports qui arrondiraient des dimensions à 2 décimales
autres = x('ir.ui.view', 'search_read', [['type', '=', 'qweb'], ['arch_db', 'ilike', "x_studio_long_m_1"]], fields=['name', 'key'])
for v in autres:
    arch = x('ir.ui.view', 'read', [v['id']], fields=['arch_db'])[0]['arch_db']
    n2 = len(re.findall(r"'%\.2f' % [^\"]*x_studio_(?:long|larg|haut)_m_1", arch))
    print('rapport %d %-40s key=%-45s dimensions en %%.2f : %d' % (v['id'], v['name'][:40], v['key'], n2))
if mode == 'apply' and hits:
    x('ir.ui.view', 'write', [VID], {'arch_db': b})
    io.open(os.path.join(d, 'report_bon_colisage_7898.AFTER_dims.xml'), 'w', encoding='utf-8').write(b)
    print('vue %d mise à jour (sauvegardes BEFORE/AFTER_dims dans odoo-scan-page/)' % VID)
    # rendu de contrôle : un colis clôturé avec dimensions à 3 décimales
    pk = x('stock.package', 'search_read', [['x_studio_cloturee', '=', True]], fields=['name'], order='write_date desc', limit=1)
    if pk:
        html = x('ir.actions.report', '_render_qweb_html', 'maquignon.report_bon_colisage', [pk[0]['id']]) if False else None
        print('contrôle à faire sur', pk[0]['name'])
