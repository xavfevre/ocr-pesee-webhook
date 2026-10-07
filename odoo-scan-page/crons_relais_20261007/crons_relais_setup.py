# -*- coding: utf-8 -*-
"""Crons Odoo sans code Python (Xavier, 07/10/2026 : « économise du code sur autre chose »).
Les quatre actions planifiées maison (parc auto 2053, CACES 2094, récup 2077, fériés 2049 : 178 lignes facturées)
deviennent des actions « Créer un enregistrement » dans le modèle x_relais_tache « Relais : tâche planifiée »
(nom = clé de la tâche) ; une automatisation « à la création » lance le webhook /odoo/tache du relais, qui exécute
taches_relais.py et écrit l'état et le résultat sur l'enregistrement. Les crons gardent leur horaire et leur utilisateur.
Journal : Paramètres > Technique > Relais : tâches planifiées.
Base : ODOO_URL / ODOO_DB (défaut production) ; base de test = URL avec &host=<hôte>. WEBHOOK_TOKEN = token du relais
(variable d'environnement). Code d'origine archivé dans action_<id>_code.py (mode retour).
  python crons_relais_setup.py dry | apply | retour | etat | test <clé[:test]>"""
import io, os, sys, time, xmlrpc.client
from urllib.parse import urlparse
sys.stdout.reconfigure(encoding='utf-8')
ICI = os.path.dirname(os.path.abspath(__file__))
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = os.environ.get('ODOO_URL', 'https://maquignon.odoo.com'); D = os.environ.get('ODOO_DB', 'maquignon')
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
RELAIS = os.environ.get('RELAIS', 'https://ocr-pesee-webhook.onrender.com').rstrip('/')
TOKEN = os.environ.get('WEBHOOK_TOKEN', '')
HOTE = (urlparse(U).hostname or '').lower()
TEST = HOTE != 'maquignon.odoo.com'
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common').authenticate(D, us, p, {})
assert uid, 'authentification refusée sur ' + U
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object')


def x(mo, me, *a, **k):
    ctx = {'active_test': False}; ctx.update(k.pop('context', {})); k['context'] = ctx
    try:
        return m.execute_kw(D, uid, p, mo, me, list(a), k)
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in str(e):
            return None
        raise


one = lambda v: v[0] if isinstance(v, list) else v
MODELE = 'x_relais_tache'
NOM_MODELE = 'Relais : tâche planifiée'
NOM_AUTO = 'Relais : tâche planifiée créée -> exécution par le relais'
NOM_MENU = 'Relais : tâches planifiées'
CRONS = {   # action -> (clé de tâche, modèle d'origine de l'action)
    2053: ('parc_controles_hebdo', 'x_controle_vehicule'),
    2094: ('caces_hebdo', 'hr.employee.skill'),
    2077: ('recup_hebdo', 'x_recup_ligne'),
    2049: ('feries_feuilles_heures', 'x_heures_jour'),
}
ETATS = "[('a_faire', 'À faire'), ('en_cours', 'En cours'), ('fait', 'Fait'), ('erreur', 'Erreur')]"


def url():
    return '%s/odoo/tache?token=%s' % (RELAIS, TOKEN) + ('&host=%s' % HOTE if TEST else '')


def masque(u):
    return (u or '').replace(TOKEN, '…') if TOKEN else (u or '')


def archive(aid):
    return os.path.join(ICI, 'action_%d_code.py' % aid)


def loc(code):
    return sum(1 for l in (code or '').splitlines() if l.strip())


def modele_id():
    r = x('ir.model', 'search', [['model', '=', MODELE]])
    return r[0] if r else None


def ref(xmlid):
    mod, nom = xmlid.split('.')
    return x('ir.model.data', 'check_object_reference', mod, nom)[1]


def etat():
    mid = modele_id()
    print('modèle %s : %s' % (MODELE, mid or 'ABSENT'))
    if mid:
        print('   champs :', sorted(f['name'] for f in x('ir.model.fields', 'search_read', [['model_id', '=', mid]], fields=['name']) if f['name'].startswith('x_')))
        par_etat = {}
        for t in x(MODELE, 'search_read', [], fields=['x_etat']):
            par_etat[t['x_etat'] or 'vide'] = par_etat.get(t['x_etat'] or 'vide', 0) + 1
        print('   tâches :', par_etat or 'aucune')
        for b in x('base.automation', 'search_read', [['name', '=', NOM_AUTO]], fields=['active', 'trigger', 'action_server_ids']):
            for a in x('ir.actions.server', 'read', b['action_server_ids'], ['state', 'webhook_url']):
                print('   automatisation %s %s -> action %d %s %s' % (b['id'], 'active' if b['active'] else 'INACTIVE', a['id'], a['state'], masque(a['webhook_url'])))
        print('   menu :', [(mn['id'], mn['complete_name']) for mn in x('ir.ui.menu', 'search_read', [['name', '=', NOM_MENU]], fields=['complete_name'])])
    tot = 0
    for aid, (cle, _) in CRONS.items():
        a = x('ir.actions.server', 'read', [aid], ['name', 'state', 'code', 'model_id', 'value', 'crud_model_id'])[0]
        c = x('ir.cron', 'search_read', [['ir_actions_server_id', '=', aid]], fields=['active', 'interval_number', 'interval_type', 'nextcall', 'user_id'])
        c = c[0] if c else {}
        tot += loc(a['code'])
        print('%d %s : %s | %d ligne(s) | modèle %s | valeur %r | cible %s | cron %s toutes les %s %s, prochain %s (%s)' % (
            aid, a['name'][:45], a['state'], loc(a['code']), a['model_id'] and a['model_id'][1], a['value'], a['crud_model_id'] and a['crud_model_id'][1],
            'actif' if c.get('active') else 'INACTIF', c.get('interval_number'), c.get('interval_type'), c.get('nextcall'), c.get('user_id') and c['user_id'][1]))
    print('lignes de code Python restantes dans ces 4 actions : %d' % tot)
    print('base %s (%s) | relais %s' % (U, 'TEST, URL avec &host=' + HOTE if TEST else 'production', RELAIS))


def creer_modele():
    mid = modele_id()
    if not mid:
        mid = one(x('ir.model', 'create', [{'name': NOM_MODELE, 'model': MODELE, 'state': 'manual', 'order': 'id desc'}]))
        print('modèle %s créé : %s' % (MODELE, mid))
    existants = {f['name'] for f in x('ir.model.fields', 'search_read', [['model_id', '=', mid]], fields=['name'])}
    champs = [
        ('x_name', {'field_description': 'Tâche', 'ttype': 'char', 'required': True}),
        ('x_etat', {'field_description': 'État', 'ttype': 'selection', 'selection': ETATS}),
        ('x_debut', {'field_description': 'Début', 'ttype': 'datetime'}),
        ('x_fin', {'field_description': 'Fin', 'ttype': 'datetime'}),
        ('x_resultat', {'field_description': 'Résultat', 'ttype': 'text'}),
    ]
    for nom, vals in champs:
        if nom in existants:
            continue
        x('ir.model.fields', 'create', [dict(vals, name=nom, model_id=mid, state='manual')])
        print('   champ %s créé' % nom)
    if not x('ir.model.access', 'search', [['model_id', '=', mid]]):
        x('ir.model.access', 'create', [{'name': MODELE + ' utilisateurs', 'model_id': mid, 'group_id': ref('base.group_user'), 'perm_read': True, 'perm_write': False, 'perm_create': False, 'perm_unlink': False}])
        x('ir.model.access', 'create', [{'name': MODELE + ' administrateurs', 'model_id': mid, 'group_id': ref('base.group_system'), 'perm_read': True, 'perm_write': True, 'perm_create': True, 'perm_unlink': True}])
        print('   droits d accès créés (lecture utilisateurs, tout administrateurs)')
    if not x('ir.ui.menu', 'search', [['name', '=', NOM_MENU]]):
        act = one(x('ir.actions.act_window', 'create', [{'name': NOM_MENU, 'res_model': MODELE, 'view_mode': 'list,form'}]))
        parent = x('ir.ui.menu', 'search', [['complete_name', '=', 'Settings/Technical']], limit=1) or [8]
        mn = one(x('ir.ui.menu', 'create', [{'name': NOM_MENU, 'parent_id': parent[0], 'action': 'ir.actions.act_window,%d' % act}]))
        print('   menu %s créé sous Paramètres > Technique (action %s)' % (mn, act))
    return mid


def creer_automatisation(mid):
    assert TOKEN, 'WEBHOOK_TOKEN manquant'
    f_name = x('ir.model.fields', 'search', [['model_id', '=', mid], ['name', '=', 'x_name']])
    b = x('base.automation', 'search', [['name', '=', NOM_AUTO]])
    if b:
        acts = x('base.automation', 'read', b, ['action_server_ids'])[0]['action_server_ids']
        x('ir.actions.server', 'write', acts, {'state': 'webhook', 'webhook_url': url(), 'webhook_field_ids': [[6, 0, f_name]], 'code': False})
        print('automatisation %s : webhook mis à jour' % b[0])
        return b[0]
    bid = one(x('base.automation', 'create', [{'name': NOM_AUTO, 'model_id': mid, 'trigger': 'on_create', 'active': True,
                                               'action_server_ids': [[0, 0, {'name': 'Relais : exécuter la tâche planifiée (webhook)', 'model_id': mid, 'state': 'webhook',
                                                                             'webhook_url': url(), 'webhook_field_ids': [[6, 0, f_name]], 'usage': 'base_automation'}]]}]))
    print('automatisation créée :', bid)
    return bid


def appliquer():
    mid = creer_modele()
    creer_automatisation(mid)
    for aid, (cle, _) in CRONS.items():
        a = x('ir.actions.server', 'read', [aid], ['name', 'state', 'code'])[0]
        if a['state'] == 'code' and a['code'] and not os.path.exists(archive(aid)):
            io.open(archive(aid), 'w', encoding='utf-8', newline='').write(a['code'])
            print('action %d : code archivé' % aid)
        x('ir.actions.server', 'write', [aid], {'state': 'object_create', 'model_id': mid, 'link_field_id': False, 'value': cle, 'code': False})
        print('action %d (%s) -> « Créer un enregistrement » %s = %s' % (aid, a['name'][:40], MODELE, cle))


def retour():
    for aid, (cle, modele_origine) in CRONS.items():
        assert os.path.exists(archive(aid)), 'archive absente pour %d' % aid
        code = io.open(archive(aid), encoding='utf-8', newline='').read()
        mo = x('ir.model', 'search', [['model', '=', modele_origine]])[0]
        x('ir.actions.server', 'write', [aid], {'state': 'code', 'code': code, 'model_id': mo, 'value': False})
        print('action %d : code Python remis (%d lignes), modèle %s' % (aid, loc(code), modele_origine))
    b = x('base.automation', 'search', [['name', '=', NOM_AUTO]])
    if b:
        acts = x('base.automation', 'read', b, ['action_server_ids'])[0]['action_server_ids']
        x('base.automation', 'unlink', b)
        if acts:
            x('ir.actions.server', 'unlink', [i for i in acts if x('ir.actions.server', 'search', [['id', '=', i]])])
        print('automatisation supprimée :', b)
    print('le modèle %s, son menu et les tâches journalisées sont conservés (supprimer à la main si besoin)' % MODELE)


def tester(cle):
    tid = one(x(MODELE, 'create', [{'x_name': cle, 'x_etat': 'a_faire'}]))
    print('tâche %s créée (%s) : attente du relais…' % (tid, cle))
    t0 = time.time()
    while time.time() - t0 < 90:
        t = x(MODELE, 'read', [tid], ['x_etat', 'x_resultat', 'x_debut', 'x_fin'])[0]
        if t['x_etat'] in ('fait', 'erreur'):
            print('   %s en %.0f s : %s' % (t['x_etat'], time.time() - t0, (t['x_resultat'] or '')[:1500]))
            return t
        time.sleep(3)
    print('   rien après 90 s (relais déployé ? automatisation ? URL ?)')


if mode == 'etat':
    etat()
elif mode == 'apply':
    appliquer(); print(); etat()
elif mode == 'retour':
    retour(); print(); etat()
elif mode == 'test':
    tester(sys.argv[2])
else:
    print('SIMULATION (rien modifié). Plan : modèle %s + automatisation webhook %s ; actions %s -> « Créer un enregistrement »' % (MODELE, masque(url()), sorted(CRONS)))
    print()
    etat()
