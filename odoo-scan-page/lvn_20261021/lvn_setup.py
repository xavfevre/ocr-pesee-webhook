# -*- coding: utf-8 -*-
"""N° LVN (lettre de voiture papier) lu par l'OCR sur la photo de chargement (Xavier, 21/10/2026).
Crée le champ x_lvn sur la feuille de travail transport et sur la tâche, et l'affiche dans les formulaires.
Usage : ODOO_USER=… ODOO_PWD=… python lvn_setup.py [etat|apply|retour]"""
import os, sys, xmlrpc.client, re
sys.stdout.reconfigure(encoding='utf-8')
URL = 'https://maquignon.odoo.com'; DB = 'maquignon'; U = os.environ['ODOO_USER']; P = os.environ['ODOO_PWD']
uid = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/common').authenticate(DB, U, P, {})
m = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/object', allow_none=True)
def call(model, meth, *a, **k): return m.execute_kw(DB, uid, P, model, meth, list(a), k)
CTX = {'context': {'allowed_company_ids': [1, 2, 3, 4, 13], 'active_test': False}}
mode = sys.argv[1] if len(sys.argv) > 1 else 'etat'
WS_MODEL, TASK_MODEL = 958, 932
VUE_WS = 'x_project_task_worksheet_template_1.form.lvn (Maquignon)'
VUE_TASK = 'project.task.form.lvn (Maquignon)'

def champ(model_id, model_name):
    ids = call('ir.model.fields', 'search', [['model', '=', model_name], ['name', '=', 'x_lvn']])
    return ids[0] if ids else None

def etat():
    print('champ x_lvn feuille :', champ(WS_MODEL, 'x_project_task_worksheet_template_1'), '| tâche :', champ(TASK_MODEL, 'project.task'))
    print('vues :', call('ir.ui.view', 'search_read', [['name', 'in', [VUE_WS, VUE_TASK]]], fields=['name', 'inherit_id', 'priority']))

def apply():
    for model_id, model_name in ((WS_MODEL, 'x_project_task_worksheet_template_1'), (TASK_MODEL, 'project.task')):
        if not champ(model_id, model_name):
            fid = call('ir.model.fields', 'create', {'model_id': model_id, 'name': 'x_lvn', 'field_description': 'N° LVN (lettre de voiture papier)', 'ttype': 'char', 'state': 'manual', 'copied': False})
            print('champ créé', model_name, fid)
    # feuille de travail : après « Numero Bon » (champ posé par la vue Studio 4379, priorité 99 -> la nôtre passe après)
    if not call('ir.ui.view', 'search', [['name', '=', VUE_WS]]):
        vid = call('ir.ui.view', 'create', {'name': VUE_WS, 'model': 'x_project_task_worksheet_template_1', 'type': 'form', 'inherit_id': 4258, 'mode': 'extension', 'priority': 200,
                                            'arch_db': '<data><xpath expr="//field[@name=\'x_studio_numero_bon\']" position="after"><field name="x_lvn" string="N° LVN (papier)"/></xpath></data>'})
        print('vue feuille créée', vid)
    # tâche : après « Km à vide » dans le formulaire transport
    champs_task = {f['name']: f['field_description'] for f in call('ir.model.fields', 'search_read', [['model', '=', 'project.task'], ['field_description', 'ilike', 'km']], fields=['name', 'field_description'])}
    print('champs km de la tâche :', champs_task)
    cible = next((n for n, d in champs_task.items() if 'vide' in d.lower()), None) or next((n for n, d in champs_task.items() if 'charge' in d.lower()), None)
    vues = call('ir.ui.view', 'search_read', [['model', '=', 'project.task'], ['type', '=', 'form'], ['arch_db', 'ilike', cible]], fields=['name', 'inherit_id', 'priority'], **CTX) if cible else []
    print('cible', cible, '| vues qui la posent :', [(v['id'], v['name'], v['inherit_id'], v['priority']) for v in vues])
    if cible and vues and not call('ir.ui.view', 'search', [['name', '=', VUE_TASK]]):
        base = vues[0]['id']   # on hérite de la vue qui pose le champ (8041, priorité 9995) : appliquée juste après elle
        vid = call('ir.ui.view', 'create', {'name': VUE_TASK, 'model': 'project.task', 'type': 'form', 'inherit_id': base, 'mode': 'extension', 'priority': 200,
                                            'arch_db': '<data><xpath expr="//field[@name=\'%s\']" position="after"><field name="x_lvn" string="N° LVN (papier)" readonly="1"/></xpath></data>' % cible})
        print('vue tâche créée', vid, 'sous la vue', base)

def retour():
    for v in call('ir.ui.view', 'search', [['name', 'in', [VUE_WS, VUE_TASK]]]):
        call('ir.ui.view', 'unlink', [v]); print('vue supprimée', v)
    for model_id, model_name in ((WS_MODEL, 'x_project_task_worksheet_template_1'), (TASK_MODEL, 'project.task')):
        f = champ(model_id, model_name)
        if f: call('ir.model.fields', 'unlink', [f]); print('champ supprimé', model_name)

{'etat': etat, 'apply': apply, 'retour': retour}[mode]()
if mode != 'etat': etat()
