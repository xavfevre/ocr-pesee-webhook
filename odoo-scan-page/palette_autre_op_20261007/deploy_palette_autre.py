# -*- coding: utf-8 -*-
"""Écrit dans Odoo les vues patchées (7890 Poste de scan, 7907 Vue Opérateur) depuis les fichiers AFTER, après
contrôle que la vue en ligne est toujours identique au BEFORE ; relit et vérifie.   python deploy_palette_autre.py dry | apply"""
import os, ssl, sys, io, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
HERE = os.path.dirname(os.path.abspath(__file__))
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [1, 2, 3, 4, 13]}))
lire = lambda f: io.open(os.path.join(HERE, f), encoding='utf-8', newline='').read()
norm = lambda s: s.replace('\r\n', '\n')
for vid, nom in ((7890, 'vue_7890'), (7907, 'vue_7907')):
    live = x('ir.ui.view', 'read', [vid], ['name', 'arch_db', 'write_date'])[0]
    before, after = lire(nom + '.BEFORE.xml'), lire(nom + '.AFTER.xml')
    ok_before = norm(live['arch_db']) == norm(before)
    print('vue %s « %s » (modifiée %s) : en ligne = BEFORE : %s | AFTER : %d octets (%+d)' % (
        vid, live['name'], live['write_date'][:16], ok_before, len(after), len(after) - len(before)))
    if not ok_before:
        print('   -> la vue en ligne a changé depuis la sauvegarde BEFORE : on ne touche pas'); continue
    if mode != 'apply':
        continue
    x('ir.ui.view', 'write', [vid], {'arch_db': after})
    relu = x('ir.ui.view', 'read', [vid], ['arch_db', 'write_date'])[0]
    print('   écrite ; relecture identique à AFTER : %s (modifiée %s)' % (norm(relu['arch_db']) == norm(after), relu['write_date'][:16]))
if mode != 'apply':
    print('simulation : rien modifié')
