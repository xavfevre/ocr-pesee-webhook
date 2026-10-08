# -*- coding: utf-8 -*-
"""Pont-bascule -> Odoo (Xavier, 08/10/2026) : modèle manuel x_pesee « Pesée pont-bascule » (zéro ligne de code),
menu Logistiques > Pesées pont-bascule, séquences de numérotation par site, clé d'accès de la page /bascule du relais.
Base : ODOO_URL / ODOO_DB (défaut production).   python bascule_setup.py dry | apply | etat"""
import os, secrets, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = os.environ.get('ODOO_URL', 'https://maquignon.odoo.com'); D = os.environ.get('ODOO_DB', 'maquignon')
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
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
MODELE = 'x_pesee'
NOM_MODELE = 'Pesée pont-bascule'
NOM_MENU = 'Pesées pont-bascule'
SITES = {'chatel': ('CHA', "Chatel'Granulats")}   # code site -> (préfixe des n° de ticket, libellé)
CHAMPS = [
    ('x_name', {'field_description': 'N° de ticket', 'ttype': 'char', 'required': True}),
    ('x_site', {'field_description': 'Site', 'ttype': 'char'}),
    ('x_company_id', {'field_description': 'Société', 'ttype': 'many2one', 'relation': 'res.company'}),
    ('x_etat', {'field_description': 'État', 'ttype': 'selection', 'selection': "[('ouverte', 'Pesée 1 faite'), ('terminee', 'Terminée'), ('annulee', 'Annulée')]"}),
    ('x_sens', {'field_description': 'Sens', 'ttype': 'selection', 'selection': "[('vente', 'Vente : vide puis plein'), ('reception', 'Réception : plein puis vide'), ('simple', 'Pesée simple')]"}),
    ('x_immat', {'field_description': 'Immatriculation', 'ttype': 'char'}),
    ('x_client', {'field_description': 'Client / fournisseur', 'ttype': 'char'}),
    ('x_partner_id', {'field_description': 'Contact Odoo', 'ttype': 'many2one', 'relation': 'res.partner'}),
    ('x_produit', {'field_description': 'Produit', 'ttype': 'char'}),
    ('x_product_id', {'field_description': 'Article Odoo', 'ttype': 'many2one', 'relation': 'product.product'}),
    ('x_p1', {'field_description': 'Pesée 1 (kg)', 'ttype': 'float'}),
    ('x_p1_date', {'field_description': 'Date pesée 1', 'ttype': 'datetime'}),
    ('x_p2', {'field_description': 'Pesée 2 (kg)', 'ttype': 'float'}),
    ('x_p2_date', {'field_description': 'Date pesée 2', 'ttype': 'datetime'}),
    ('x_net', {'field_description': 'Net (kg)', 'ttype': 'float'}),
    ('x_net_t', {'field_description': 'Net (t)', 'ttype': 'float'}),
    ('x_poste', {'field_description': 'Poste', 'ttype': 'char'}),
    ('x_imprime', {'field_description': 'Ticket imprimé', 'ttype': 'boolean'}),
    ('x_note', {'field_description': 'Note', 'ttype': 'text'}),
    ('x_manuel', {'field_description': 'Poids saisi à la main', 'ttype': 'boolean'}),
    ('x_tare_memo', {'field_description': 'Tare mémorisée du véhicule', 'ttype': 'boolean'}),
    ('x_vehicule_id', {'field_description': 'Véhicule', 'ttype': 'many2one', 'relation': 'x_vehicule'}),
    ('x_vehicule_type', {'field_description': 'Type de véhicule', 'ttype': 'selection', 'selection': "[('client', 'Véhicule client / transporteur'), ('entreprise', 'Véhicule de l entreprise')]"}),
]
MODELE_V = 'x_vehicule'
NOM_MODELE_V = 'Véhicule pont-bascule'
NOM_MENU_V = 'Véhicules (tares)'
CHAMPS_V = [
    ('x_name', {'field_description': 'Immatriculation', 'ttype': 'char', 'required': True}),
    ('x_type', {'field_description': 'Type', 'ttype': 'selection', 'selection': "[('client', 'Véhicule client / transporteur'), ('entreprise', 'Véhicule de l entreprise')]"}),
    ('x_fleet_id', {'field_description': 'Véhicule du parc', 'ttype': 'many2one', 'relation': 'fleet.vehicle'}),
    ('x_tare', {'field_description': 'Tare (kg)', 'ttype': 'float'}),
    ('x_tare_date', {'field_description': 'Tare pesée le', 'ttype': 'datetime'}),
    ('x_client', {'field_description': 'Client / transporteur', 'ttype': 'char'}),
    ('x_partner_id', {'field_description': 'Contact Odoo', 'ttype': 'many2one', 'relation': 'res.partner'}),
    ('x_produit', {'field_description': 'Produit habituel', 'ttype': 'char'}),
    ('x_product_id', {'field_description': 'Article Odoo habituel', 'ttype': 'many2one', 'relation': 'product.product'}),
    ('x_site', {'field_description': 'Site de la dernière tare', 'ttype': 'char'}),
    ('x_note', {'field_description': 'Note', 'ttype': 'text'}),
]


def ref(xmlid):
    mod, nom = xmlid.split('.')
    return x('ir.model.data', 'check_object_reference', mod, nom)[1]


def modele_id():
    r = x('ir.model', 'search', [['model', '=', MODELE]])
    return r[0] if r else None


def etat():
    mid = modele_id()
    print('modèle %s : %s' % (MODELE, mid or 'ABSENT'))
    if mid:
        print('   champs :', sorted(f['name'] for f in x('ir.model.fields', 'search_read', [['model_id', '=', mid]], fields=['name']) if f['name'].startswith('x_')))
        print('   pesées :', x(MODELE, 'search_count', []), '| menu :', x('ir.ui.menu', 'search_read', [['name', '=', NOM_MENU]], fields=['id', 'parent_id']))
    print('   séquences :', [(s['code'], s['prefix'], s['number_next_actual']) for s in x('ir.sequence', 'search_read', [['code', 'like', 'x_pesee.']], fields=['code', 'prefix', 'number_next_actual'])])
    cle = x('ir.config_parameter', 'get_param', 'maquignon.bascule_key', '')
    print('   clé de la page /bascule :', (cle[:4] + '…' + cle[-4:]) if cle else 'ABSENTE')
    print('base', U)


def appliquer():
    mid = modele_id()
    if not mid:
        mid = one(x('ir.model', 'create', [{'name': NOM_MODELE, 'model': MODELE, 'state': 'manual', 'order': 'id desc'}]))
        print('modèle créé :', mid)
    existants = {f['name'] for f in x('ir.model.fields', 'search_read', [['model_id', '=', mid]], fields=['name'])}
    for nom, vals in CHAMPS:
        if nom in existants:
            continue
        x('ir.model.fields', 'create', [dict(vals, name=nom, model_id=mid, state='manual')])
        print('   champ %s créé' % nom)
    if not x('ir.model.access', 'search', [['model_id', '=', mid]]):
        x('ir.model.access', 'create', [{'name': MODELE + ' utilisateurs', 'model_id': mid, 'group_id': ref('base.group_user'), 'perm_read': True, 'perm_write': True, 'perm_create': True, 'perm_unlink': False}])
        x('ir.model.access', 'create', [{'name': MODELE + ' administrateurs', 'model_id': mid, 'group_id': ref('base.group_system'), 'perm_read': True, 'perm_write': True, 'perm_create': True, 'perm_unlink': True}])
        print('   droits créés')
    # vue liste lisible (sinon Odoo n'affiche que le nom)
    if not x('ir.ui.view', 'search', [['model', '=', MODELE], ['type', '=', 'list']]):
        arch = ('<list string="Pesées" default_order="id desc">'
                '<field name="x_name"/><field name="x_site"/><field name="x_company_id"/><field name="x_etat" widget="badge"/><field name="x_sens"/>'
                '<field name="x_immat"/><field name="x_client"/><field name="x_produit"/><field name="x_p1_date"/><field name="x_p1" sum="P1"/>'
                '<field name="x_p2_date"/><field name="x_p2"/><field name="x_net" sum="Net kg"/><field name="x_net_t" sum="Net t"/><field name="x_imprime"/></list>')
        x('ir.ui.view', 'create', [{'name': 'x_pesee.list', 'model': MODELE, 'type': 'list', 'arch_db': arch}])
        print('   vue liste créée')
    if not x('ir.ui.view', 'search', [['model', '=', MODELE], ['type', '=', 'form']]):
        arch = ('<form string="Pesée"><sheet><group><group><field name="x_name"/><field name="x_site"/><field name="x_company_id"/><field name="x_etat"/><field name="x_sens"/><field name="x_poste"/></group>'
                '<group><field name="x_immat"/><field name="x_client"/><field name="x_partner_id"/><field name="x_produit"/><field name="x_product_id"/></group></group>'
                '<group><group string="Pesées"><field name="x_p1_date"/><field name="x_p1"/><field name="x_p2_date"/><field name="x_p2"/></group>'
                '<group string="Résultat"><field name="x_net"/><field name="x_net_t"/><field name="x_imprime"/></group></group><field name="x_note" placeholder="Note"/></sheet></form>')
        x('ir.ui.view', 'create', [{'name': 'x_pesee.form', 'model': MODELE, 'type': 'form', 'arch_db': arch}])
        print('   vue formulaire créée')
    if not x('ir.ui.menu', 'search', [['name', '=', NOM_MENU]]):
        act = one(x('ir.actions.act_window', 'create', [{'name': NOM_MENU, 'res_model': MODELE, 'view_mode': 'list,form'}]))
        parent = x('ir.ui.menu', 'read', [1066], ['parent_id'])[0]['parent_id']   # même parent que « Expédition palettes » (Logistiques)
        mn = one(x('ir.ui.menu', 'create', [{'name': NOM_MENU, 'parent_id': parent and parent[0], 'action': 'ir.actions.act_window,%d' % act, 'sequence': 60}]))
        print('   menu créé :', mn, 'sous', parent and parent[1])
    # véhicules : tare mémorisée par immatriculation (une seule pesée ensuite)
    r = x('ir.model', 'search', [['model', '=', MODELE_V]])
    mv = r[0] if r else one(x('ir.model', 'create', [{'name': NOM_MODELE_V, 'model': MODELE_V, 'state': 'manual', 'order': 'x_name'}]))
    if not r:
        print('modèle véhicules créé :', mv)
    existants = {f['name'] for f in x('ir.model.fields', 'search_read', [['model_id', '=', mv]], fields=['name'])}
    for nom, vals in CHAMPS_V:
        if nom not in existants:
            x('ir.model.fields', 'create', [dict(vals, name=nom, model_id=mv, state='manual')])
            print('   champ véhicule %s créé' % nom)
    if not x('ir.model.access', 'search', [['model_id', '=', mv]]):
        x('ir.model.access', 'create', [{'name': MODELE_V + ' utilisateurs', 'model_id': mv, 'group_id': ref('base.group_user'), 'perm_read': True, 'perm_write': True, 'perm_create': True, 'perm_unlink': False}])
        x('ir.model.access', 'create', [{'name': MODELE_V + ' administrateurs', 'model_id': mv, 'group_id': ref('base.group_system'), 'perm_read': True, 'perm_write': True, 'perm_create': True, 'perm_unlink': True}])
        print('   droits véhicules créés')
    arch_v = '<list string="Véhicules" editable="bottom"><field name="x_name"/><field name="x_type" widget="badge"/><field name="x_fleet_id"/><field name="x_tare"/><field name="x_tare_date"/><field name="x_client"/><field name="x_partner_id"/><field name="x_produit"/><field name="x_product_id"/><field name="x_site"/><field name="x_note"/></list>'
    vue_v = x('ir.ui.view', 'search', [['model', '=', MODELE_V], ['type', '=', 'list']])
    if vue_v:
        x('ir.ui.view', 'write', vue_v, {'arch_db': arch_v}); print('   vue liste véhicules mise à jour')
    else:
        x('ir.ui.view', 'create', [{'name': 'x_vehicule.list', 'model': MODELE_V, 'type': 'list', 'arch_db': arch_v}]); print('   vue liste véhicules créée')
    if not x('ir.ui.menu', 'search', [['name', '=', NOM_MENU_V]]):
        act = one(x('ir.actions.act_window', 'create', [{'name': NOM_MENU_V, 'res_model': MODELE_V, 'view_mode': 'list,form'}]))
        parent = x('ir.ui.menu', 'read', [1066], ['parent_id'])[0]['parent_id']
        mn = one(x('ir.ui.menu', 'create', [{'name': NOM_MENU_V, 'parent_id': parent and parent[0], 'action': 'ir.actions.act_window,%d' % act, 'sequence': 61}]))
        print('   menu véhicules créé :', mn)
    for code, (prefixe, libelle) in SITES.items():
        if not x('ir.sequence', 'search', [['code', '=', 'x_pesee.' + code]]):
            x('ir.sequence', 'create', [{'name': 'Pesées ' + libelle, 'code': 'x_pesee.' + code, 'prefix': prefixe + '-%(year)s-', 'padding': 5, 'company_id': False}])
            print('   séquence x_pesee.%s créée (%s-AAAA-00001)' % (code, prefixe))
    if not x('ir.config_parameter', 'get_param', 'maquignon.bascule_key', ''):
        x('ir.config_parameter', 'set_param', 'maquignon.bascule_key', secrets.token_urlsafe(18))
        print('   clé de la page /bascule créée')


if mode == 'apply':
    appliquer(); print(); etat()
elif mode == 'etat':
    etat()
else:
    print('SIMULATION : modèle %s avec %d champs, menu « %s », séquences %s, clé maquignon.bascule_key' % (MODELE, len(CHAMPS), NOM_MENU, list(SITES)))
    etat()
