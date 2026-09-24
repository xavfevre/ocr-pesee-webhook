# -*- coding: utf-8 -*-
"""Tâches de transport : l'opérateur = le chauffeur, et lui seul.
Automatisation 18 / action 1523 (« Lier véhicule Fleet automatiquement », project.task on_create_or_write) :
 - avant : le chauffeur est AJOUTÉ aux opérateurs (jamais retiré) -> une duplication ou un changement de chauffeur
   laisse l'ancien chauffeur dans les opérateurs (2 222 tâches terminées dans ce cas au 23/09/2026) ;
 - après : tâche transport (sans étiquette TP) -> opérateurs = [chauffeur] exactement ;
           tâche TP (étiquette 1) -> comportement inchangé (opérateurs des machines + chauffeur).
  python transport_operateur_fix.py test        : patch sur la base de test + scénario duplication / changement de chauffeur
  python transport_operateur_fix.py prod        : patch en production + même scénario (copies supprimées)
  python transport_operateur_fix.py prod nettoyage : + remise à [chauffeur] des tâches transport terminées/annulées"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'test').lower()
nettoyage = 'nettoyage' in sys.argv[2:]
U, D = ('https://testmaq230926v2.odoo.com', 'testmaq230926v2') if mode == 'test' else ('https://maquignon.odoo.com', 'maquignon')
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)


def x(mo, me, *a, **k):
    k['context'] = dict({'allowed_company_ids': [1, 2, 3, 4, 13], 'tracking_disable': True, 'mail_notrack': True}, **k.get('context', {}))
    return m.execute_kw(D, uid, p, mo, me, list(a), k)


OLD = """for record in records:
    if record.x_studio_chauffeur and record.x_studio_chauffeur.id not in record.x_studio_operateurs.ids:
        record.write({'x_studio_operateurs': [(4, record.x_studio_chauffeur.id)]})
"""
NEW = """TAG_TP = 1
for record in records:
    ch = record.x_studio_chauffeur
    if not ch:
        continue
    if TAG_TP in record.tag_ids.ids:
        # tache TP : les operateurs des machines restent, le chauffeur s'y ajoute
        if ch.id not in record.x_studio_operateurs.ids:
            record.write({'x_studio_operateurs': [(4, ch.id)]})
    elif record.x_studio_operateurs.ids != [ch.id]:
        # tache transport : l'operateur, c'est le chauffeur et lui seul — une duplication ou un
        # changement de chauffeur ne laisse plus l'ancien chauffeur dans les operateurs
        record.write({'x_studio_operateurs': [(6, 0, [ch.id])]})
"""
act = x('base.automation', 'read', [18], fields=['action_server_ids', 'name'])[0]
code = x('ir.actions.server', 'read', act['action_server_ids'], fields=['code'])[0]['code']
if NEW in code:
    print('action 1523 : déjà patchée')
else:
    assert code.count(OLD) == 1, 'bloc « chauffeur -> opérateurs » introuvable'
    x('ir.actions.server', 'write', act['action_server_ids'], {'code': code.replace(OLD, NEW)})
    print('action 1523 patchée (%s)' % act['name'])

# ---- scénario : duplication d'une tâche transport puis changement de chauffeur ; tâche TP inchangée
emp = {e['id']: e['name'] for e in x('hr.employee', 'search_read', [['active', 'in', [True, False]]], fields=['name'])}
F = ['name', 'x_studio_chauffeur', 'x_studio_operateurs', 'tag_ids', 'state']
src = x('project.task', 'search_read', [['project_id', '=', 2], ['tag_ids', 'not in', [1]], ['x_studio_chauffeur', '!=', False], ['state', '=', '1_done']], fields=F, order='id desc', limit=1)[0]
autre = [e for e in x('hr.employee', 'search_read', [['company_id', '=', 1], ['id', '!=', src['x_studio_chauffeur'][0]]], fields=['name'], limit=1)][0]
print('transport source :', src['id'], src['name'][:40], '| chauffeur', emp.get(src['x_studio_chauffeur'][0]), '| opérateurs', [emp.get(o, o) for o in src['x_studio_operateurs']])
cp = x('project.task', 'copy', [src['id']])
cp = cp[0] if isinstance(cp, list) else cp
t = x('project.task', 'read', [cp], fields=F)[0]
print('   copie', cp, ': chauffeur', emp.get(t['x_studio_chauffeur'][0]) if t['x_studio_chauffeur'] else None, '| opérateurs', [emp.get(o, o) for o in t['x_studio_operateurs']])
x('project.task', 'write', [cp], {'x_studio_chauffeur': autre['id']})
t = x('project.task', 'read', [cp], fields=F)[0]
print('   chauffeur ->', autre['name'], '| opérateurs', [emp.get(o, o) for o in t['x_studio_operateurs']])
tpsrc = x('project.task', 'search_read', [['project_id', '=', 2], ['tag_ids', 'in', [1]], ['x_studio_chauffeur', '!=', False], ['x_studio_operateurs', '!=', False]], fields=F, order='id desc', limit=1)
cp2 = None
if tpsrc:
    tpsrc = tpsrc[0]
    print('TP source :', tpsrc['id'], tpsrc['name'][:40], '| chauffeur', emp.get(tpsrc['x_studio_chauffeur'][0]), '| opérateurs', [emp.get(o, o) for o in tpsrc['x_studio_operateurs']])
    cp2 = x('project.task', 'copy', [tpsrc['id']])
    cp2 = cp2[0] if isinstance(cp2, list) else cp2
    t2 = x('project.task', 'read', [cp2], fields=F)[0]
    print('   copie TP', cp2, ': opérateurs', [emp.get(o, o) for o in t2['x_studio_operateurs']], '(inchangés + chauffeur)')
x('project.task', 'unlink', [i for i in (cp, cp2) if i])
print('   copies supprimées')

if mode == 'prod' and nettoyage:
    rows = x('project.task', 'search_read', [['project_id', '=', 2], ['tag_ids', 'not in', [1]], ['x_studio_chauffeur', '!=', False], ['state', 'in', ['1_done', '1_canceled']]], fields=['x_studio_chauffeur', 'x_studio_operateurs'])
    todo = [r for r in rows if sorted(r['x_studio_operateurs']) != [r['x_studio_chauffeur'][0]]]
    print('nettoyage : tâches transport terminées/annulées à remettre sur [chauffeur] :', len(todo))
    n = 0
    for r in todo:
        x('project.task', 'write', [r['id']], {'x_studio_operateurs': [(6, 0, [r['x_studio_chauffeur'][0]])]}); n += 1
    print('   corrigées :', n)
