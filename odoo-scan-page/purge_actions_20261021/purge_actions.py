# -*- coding: utf-8 -*-
"""Suppression des actions serveur périmées (demande Xavier 21/10/2026, réduction des lignes de code facturées).
Vérifié avant : aucune de ces actions n'est appelée par un menu, un bouton, une vue (JS compris), une automatisation
active, un cron utile ou le relais. Sauvegarde complète (JSON) de chaque enregistrement avant suppression.
Usage : python purge_actions.py [apply]"""
import os, sys, io, json, xmlrpc.client, datetime as dt
sys.stdout.reconfigure(encoding='utf-8')
APPLY = len(sys.argv) > 1 and sys.argv[1] == 'apply'
URL = 'https://maquignon.odoo.com'; DB = 'maquignon'
U = os.environ['ODOO_USER']; P = os.environ['ODOO_PWD']
uid = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/common').authenticate(DB, U, P, {})
m = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/object', allow_none=True)
def call(model, meth, *a, **k):
    return m.execute_kw(DB, uid, P, model, meth, list(a), k)
CTX = {'context': {'allowed_company_ids': [1, 2, 3, 4, 13], 'active_test': False}}
ICI = os.path.dirname(os.path.abspath(__file__))

ACTIONS = {   # id : motif
    2060: "DIAG recompute2 temp : diagnostic ponctuel du 06/08 sur la ligne 353543",
    2058: "DIAG clear cache temp : diagnostic ponctuel du 06/08",
    1466: "Filtre Devis commande : squelette jamais terminé (env.ref('module.action_id')), menu Action sur les devis",
    1646: "recuperation des ref client dans les of : reprise ponctuelle d'avril 2026, l'automatisation 1477 remplit le champ à la création",
    1954: "Supprimer l'OF + stock (déploiement) : outil de mise en route (SQL direct), dangereux, plus utilisé",
    2147: "Scanner un document (Document) : doublon non branché de l'action 2146 (Véhicule) qui, elle, est au menu Action",
    2117: "CA camion : recalcul par période (outil) : enveloppe de l'action 2114, jamais branchée ni appelée",
    1932: "Deblocage OT prets - correctif etat v19 : cron toutes les 15 min, aucune action depuis le 01/07/2026 (0 entrée de journal en 30 j)",
    1933: "Deblocage OT (auto confirmation OF) - correctif etat v19 : même correctif, automatisation à la confirmation",
    1260: "Num client : automatisation 2 INACTIVE, remplacée par « Code client automatique (Sage) » (2082)",
}
ids = list(ACTIONS)
champs = ['name', 'model_id', 'state', 'code', 'binding_model_id', 'binding_type', 'binding_view_types', 'usage', 'sequence', 'create_date', 'write_date', 'group_ids' if 'group_ids' in call('ir.actions.server', 'fields_get', attributes=['type'], **CTX) else 'name']
acts = {a['id']: a for a in call('ir.actions.server', 'read', ids, fields=champs, **CTX)}
autos = call('base.automation', 'search_read', [['action_server_ids', 'in', ids]], fields=['name', 'active', 'action_server_ids', 'trigger', 'model_id', 'filter_domain', 'trigger_field_ids'], **CTX)
crons = call('ir.cron', 'search_read', [['ir_actions_server_id', 'in', ids]], fields=['name', 'active', 'ir_actions_server_id', 'interval_number', 'interval_type', 'nextcall', 'lastcall'], **CTX)
sauv = {'date': dt.datetime.now().isoformat(timespec='seconds'), 'motifs': {str(k): v for k, v in ACTIONS.items()}, 'actions': acts, 'automatisations': autos, 'crons': crons}
f = os.path.join(ICI, 'purge_actions_sauvegarde_%s.json' % dt.datetime.now().strftime('%Y%m%d_%H%M'))
io.open(f, 'w', encoding='utf-8').write(json.dumps(sauv, ensure_ascii=False, indent=1, default=str))
print('sauvegarde :', f)
total = 0
for i in ids:
    a = acts.get(i)
    if not a:
        print('  %d : déjà supprimée' % i); continue
    n = sum(1 for l in (a['code'] or '').splitlines() if l.strip() and not l.strip().startswith('#'))
    total += n
    print('  %4d | %3d l. | %-55s | %s' % (i, n, a['name'][:55], ACTIONS[i][:70]))
print('automatisations à supprimer :', [(x['id'], x['name'], 'active' if x['active'] else 'inactive') for x in autos])
print('crons à supprimer :', [(x['id'], x['name']) for x in crons])
print('lignes de code retirées :', total)
if not APPLY:
    print('\nsimulation : rien supprimé'); sys.exit()
if crons:
    call('ir.cron', 'unlink', [x['id'] for x in crons], **CTX); print('crons supprimés')
if autos:
    call('base.automation', 'unlink', [x['id'] for x in autos], **CTX); print('automatisations supprimées')
restants = call('ir.actions.server', 'search', [['id', 'in', ids]], **CTX)
if restants:
    call('ir.actions.server', 'unlink', restants, **CTX)
print('actions supprimées :', len(restants) + (len(ids) - len(restants)), '| vérification :', call('ir.actions.server', 'search_count', [['id', 'in', ids]], **CTX), 'restante(s)')
