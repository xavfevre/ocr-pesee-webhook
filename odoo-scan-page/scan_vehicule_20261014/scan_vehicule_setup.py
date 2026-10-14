# -*- coding: utf-8 -*-
"""Scanner -> fiche véhicule (14/10/2026) : objets Odoo de la page /scan-vehicule du relais.
  - paramètre système `maquignon.scan_key` (clé d'accès de la page et du veilleur du PC), créé s'il n'existe pas ;
  - action serveur « 📎 Scanner un document » sur fleet.vehicle (menu Action de la fiche véhicule, 1 ligne de code :
    ouvre la page du relais sur le véhicule courant dans un nouvel onglet).
   python scan_vehicule_setup.py dry     -> montre ce qui serait fait
   python scan_vehicule_setup.py apply   -> crée / met à jour
   python scan_vehicule_setup.py etat    -> état (clé, action, cibles enregistrées, documents à classer)
   python scan_vehicule_setup.py retour  -> supprime l'action (la clé et les cibles sont gardées)
Identifiants attendus dans l'environnement : ODOO_USER, ODOO_PWD."""
import os, sys, json, secrets, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
MODE = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common').authenticate(D, us, p, {})
assert uid, 'authentification refusée'
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object')


def x(mo, me, *a, **k):
    k = dict(k); ctx = {'active_test': False}; ctx.update(k.pop('context', {})); k['context'] = ctx
    try:
        return m.execute_kw(D, uid, p, mo, me, list(a), k)
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in str(e):
            return None
        raise


RELAIS = 'https://ocr-pesee-webhook.onrender.com/scan-vehicule/'
NOM_ACTION = '📎 Scanner un document'
CODE = ("action = {'type': 'ir.actions.act_url', 'target': 'new', 'url': '%s?veh=%%s&k=%%s' %% (record.id, env['ir.config_parameter'].sudo().get_param('maquignon.scan_key', ''))}" % RELAIS)
cle = x('ir.config_parameter', 'get_param', 'maquignon.scan_key', '') or ''
modele = x('ir.model', 'search', [['model', '=', 'fleet.vehicle']])[0]
actions = x('ir.actions.server', 'search_read', [['name', '=', NOM_ACTION], ['model_id', '=', modele]], fields=['id', 'code', 'binding_model_id', 'binding_view_types', 'state'])
print('clé maquignon.scan_key :', 'présente' if cle else 'ABSENTE', '| action :', [(a['id'], a['state'], a['binding_view_types']) for a in actions] or 'absente')

if MODE == 'etat':
    cibles = x('ir.config_parameter', 'search_read', [['key', 'like', 'maquignon.scan_cible_%']], fields=['key', 'value'])
    print('cibles enregistrées :', [(c['key'].split('_')[-1], c['value']) for c in cibles])
    att = x('ir.attachment', 'search_read', [['res_model', '=', 'fleet.vehicle'], ['res_id', '=', 0], ['name', 'like', 'A CLASSER - %']], fields=['name', 'create_date'])
    print('documents à classer :', [(a['name'], a['create_date']) for a in att])
    print('URL de la page (sans véhicule) :', RELAIS + '?k=' + cle)
    sys.exit()
if MODE == 'retour':
    emb = x('ir.embedded.actions', 'search', [['name', '=', NOM_ACTION]])
    if emb:
        x('ir.embedded.actions', 'unlink', emb); print('bouton Documents supprimé')
    tous = x('ir.actions.server', 'search', [['name', '=', NOM_ACTION]])
    if tous:
        x('ir.actions.server', 'unlink', tous); print('actions supprimées :', tous)
    sys.exit()
if MODE != 'apply':
    print('Simulation :', ('créer la clé' if not cle else 'clé conservée') + ', ' + ('créer' if not actions else 'mettre à jour') + " l'action « %s » (model fleet.vehicle, 1 ligne de code, menu Action du formulaire)." % NOM_ACTION)
    print('code :', CODE); sys.exit()
if not cle:
    cle = secrets.token_urlsafe(18)
    x('ir.config_parameter', 'set_param', 'maquignon.scan_key', cle); print('clé créée')
vals = {'name': NOM_ACTION, 'model_id': modele, 'state': 'code', 'code': CODE, 'binding_model_id': modele, 'binding_view_types': 'form', 'binding_type': 'action'}
if actions:
    x('ir.actions.server', 'write', [actions[0]['id']], vals); print('action %d mise à jour' % actions[0]['id'])
else:
    aid = x('ir.actions.server', 'create', [vals]); print('action créée :', aid)
# Même bouton dans la vue Documents du véhicule (dossier Fleet) : action sur documents.document (2 lignes) exposée comme
# « embedded action » du dossier Fleet, comme « Link to a vehicle » (ir.embedded.actions, parent = action Documents 303).
mdoc = x('ir.model', 'search', [['model', '=', 'documents.document']])[0]
CODE_DOC = ("r = records.filtered(lambda d: d.res_model == 'fleet.vehicle')[:1]\n"
            "action = {'type': 'ir.actions.act_url', 'target': 'new', 'url': '%s?veh=%%s&k=%%s' %% (r.res_id or env.context.get('default_res_id', 0), env['ir.config_parameter'].sudo().get_param('maquignon.scan_key', ''))}" % RELAIS)
adoc = x('ir.actions.server', 'search', [['name', '=', NOM_ACTION], ['model_id', '=', mdoc]])
vdoc = {'name': NOM_ACTION, 'model_id': mdoc, 'state': 'code', 'code': CODE_DOC, 'binding_type': 'action'}
if adoc:
    x('ir.actions.server', 'write', adoc, vdoc); print('action Documents %d mise à jour' % adoc[0])
else:
    adoc = [x('ir.actions.server', 'create', [vdoc])]; print('action Documents créée :', adoc[0])
dossier = x('res.company', 'read', [1], ['documents_fleet_folder'])[0]['documents_fleet_folder'][0]
act_docs = x('ir.actions.act_window', 'search', [['res_model', '=', 'documents.document'], ['name', '=', 'Documents']], limit=1)[0]
emb = x('ir.embedded.actions', 'search', [['name', '=', NOM_ACTION], ['parent_res_model', '=', 'documents.document'], ['parent_res_id', '=', dossier]])
vemb = {'name': NOM_ACTION, 'parent_action_id': act_docs, 'action_id': adoc[0], 'parent_res_model': 'documents.document', 'parent_res_id': dossier, 'groups_ids': [[6, 0, [1]]], 'sequence': 3}
if emb:
    x('ir.embedded.actions', 'write', emb, vemb); print('bouton Documents (embedded action) %d mis à jour' % emb[0])
else:
    print('bouton Documents (embedded action) créé :', x('ir.embedded.actions', 'create', [vemb]), 'sur le dossier', dossier)
print('URL de la page :', RELAIS + '?veh=<id>&k=' + cle)
print('clé pour le veilleur du PC (installer.ps1 -Cle ...) :', cle)
