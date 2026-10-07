# -*- coding: utf-8 -*-
"""Actions « transport des commandes pierre » sans code Python dans Odoo (Xavier, 07/10/2026 : « tu as ajouté du code
payant » = module « Maintenance par 100 lignes » de l'abonnement).
  - 2118 « Devis : demander un tarif transport » (bouton du devis) et 2122 « Devis : ligne Transport de pierres
    automatique » (automatisation 103) deviennent « Exécuter plusieurs actions » : une note instantanée dans le fil
    (action « Envoyer un e-mail » en mode Note, modèle de mail statique : l'utilisateur voit tout de suite que quelque chose
    se passe) puis un « Webhook » vers le relais Render /odoo/transport/<quoi> qui fait le travail (transport_webhooks.py) ;
  - 2119 « Achat transport confirmé -> transporteur retenu sur le devis » (automatisation 102) devient un simple Webhook ;
  - filtres des automatisations resserrés (102 : commandes d'achat avec l'article Transport affrété ; 103 : devis de
    SARL MAQUIGNON avec un mode de transport) pour que la note instantanée ne sorte pas sur n'importe quel enregistrement.
Le code Python d'origine est archivé dans action_<id>_code.py (mode retour = remise en place à l'identique).
Base : ODOO_URL / ODOO_DB (défaut production) ; sur une base de test (hôte différent de maquignon.odoo.com) l'URL reçoit
&host=<hôte> pour que le relais agisse sur cette base. WEBHOOK_TOKEN = token du relais (variable d'environnement, jamais
dans un fichier). RELAIS = URL du relais (défaut Render).
  python transport_webhooks_setup.py dry | apply | retour | etat"""
import io, os, sys, xmlrpc.client
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
    ctx = {'allowed_company_ids': [1]}; ctx.update(k.pop('context', {})); k['context'] = ctx
    try:
        return m.execute_kw(D, uid, p, mo, me, list(a), k)
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in str(e):
            return None
        raise


one = lambda v: v[0] if isinstance(v, list) else v
PRODUIT_ACHAT = 8586
ACTIONS = {
    2118: dict(quoi='tarif', model='sale.order', note=True,
               champs=['name', 'x_mode_transport', 'x_transporteurs_ids', 'user_id', 'write_date'],
               texte="⏳ Demande de tarif transport lancée : les demandes de prix (et les mails aux transporteurs) sont créées dans "
                     "quelques secondes ; le compte rendu arrive dans ce fil."),
    2119: dict(quoi='achat-confirme', model='purchase.order', note=False,
               champs=['name', 'state', 'origin', 'partner_id', 'amount_untaxed', 'write_date'], texte=''),
    2122: dict(quoi='mode-devis', model='sale.order', note=True,
               champs=['name', 'state', 'x_mode_transport', 'x_transport_achat', 'write_date'],
               texte="⏳ Mode de transport modifié : la ligne « Transport de pierres » en fin de devis est ajustée dans quelques "
                     "secondes (recharger le devis pour la voir)."),
}
DOMAINES = {102: "[('state', '=', 'purchase'), ('order_line.product_id', '=', %d)]" % PRODUIT_ACHAT,
            103: "[('x_mode_transport', '!=', False), ('company_id', '=', 1)]"}
DOMAINES_ORIGINE = {102: "[('state', '=', 'purchase')]", 103: False}
MODELES = {n: x('ir.model', 'search', [['model', '=', n]])[0] for n in ('sale.order', 'purchase.order')}


def url(quoi):
    return '%s/odoo/transport/%s?token=%s' % (RELAIS, quoi, TOKEN) + ('&host=%s' % HOTE if TEST else '')


def masque(u):
    return (u or '').replace(TOKEN, '…') if TOKEN else (u or '')


def archive(aid):
    return os.path.join(ICI, 'action_%d_code.py' % aid)


def loc(code):
    return sum(1 for l in (code or '').splitlines() if l.strip())


def etat():
    tot = 0
    for aid, d in ACTIONS.items():
        a = x('ir.actions.server', 'read', [aid], ['name', 'state', 'code', 'child_ids', 'webhook_url', 'webhook_field_ids'])[0]
        tot += loc(a['code'])
        print('%s (%d) : type %s | %d ligne(s) de code | webhook %s' % (a['name'], aid, a['state'], loc(a['code']), masque(a['webhook_url'])))
        for c in (x('ir.actions.server', 'read', a['child_ids'], ['name', 'state', 'sequence', 'webhook_url', 'template_id', 'mail_post_method']) if a['child_ids'] else []):
            print('     enfant %d (%s) : %s | %s%s' % (c['id'], c['sequence'], c['state'], masque(c['webhook_url']) or '', (c['template_id'] and ('modèle %s, %s' % (c['template_id'][1], c['mail_post_method']))) or ''))
    for b in x('base.automation', 'read', [102, 103], ['name', 'active', 'filter_domain', 'trigger_field_ids']):
        print('automatisation %d : %s | filtre %s' % (b['id'], 'active' if b['active'] else 'INACTIVE', b['filter_domain']))
    print('lignes de code Python restantes dans ces 3 actions : %d' % tot)
    print('base %s (%s) | relais %s' % (U, 'TEST, URL avec &host=' + HOTE if TEST else 'production', RELAIS))


def enfant(parent, nom, model_id, vals):
    ex = x('ir.actions.server', 'search', [['name', '=', nom], ['parent_id', '=', parent]])
    base = {'name': nom, 'model_id': model_id, 'parent_id': parent, 'usage': 'ir_actions_server'}
    base.update(vals)
    if ex:
        x('ir.actions.server', 'write', ex, vals)
        return ex[0]
    return one(x('ir.actions.server', 'create', [base]))


def appliquer():
    assert TOKEN, 'WEBHOOK_TOKEN manquant (token du relais, en variable d environnement)'
    for aid, d in ACTIONS.items():
        a = x('ir.actions.server', 'read', [aid], ['name', 'state', 'code', 'model_id'])[0]
        model_id = MODELES[d['model']]
        assert a['model_id'][0] == model_id, 'action %d : modèle inattendu %s' % (aid, a['model_id'])
        if a['state'] == 'code' and a['code'] and not os.path.exists(archive(aid)):
            io.open(archive(aid), 'w', encoding='utf-8', newline='').write(a['code'])
            print('action %d : code archivé dans %s' % (aid, os.path.basename(archive(aid))))
        champs = x('ir.model.fields', 'search', [['model', '=', d['model']], ['name', 'in', d['champs']]])
        if d['note']:
            nom_tpl = 'Transport pierre : note automatique (%s)' % d['quoi']
            tpl = x('mail.template', 'search', [['name', '=', nom_tpl]])
            corps = '<p>%s</p>' % d['texte']
            if tpl:
                x('mail.template', 'write', tpl, {'body_html': corps, 'model_id': model_id})
            else:
                tpl = [one(x('mail.template', 'create', [{'name': nom_tpl, 'model_id': model_id, 'subject': 'Transport (suivi automatique)', 'body_html': corps}]))]
            note_id = enfant(aid, a['name'] + ' : note', model_id,
                             {'state': 'mail_post', 'template_id': tpl[0], 'mail_post_method': 'note', 'mail_post_autofollow': False, 'sequence': 1})
            hook_id = enfant(aid, a['name'] + ' : webhook', model_id,
                             {'state': 'webhook', 'webhook_url': url(d['quoi']), 'webhook_field_ids': [[6, 0, champs]], 'sequence': 2})
            x('ir.actions.server', 'write', [aid], {'state': 'multi', 'code': False})
            print('action %d -> plusieurs actions : note %d (modèle %s) + webhook %d' % (aid, note_id, tpl[0], hook_id))
        else:
            x('ir.actions.server', 'write', [aid], {'state': 'webhook', 'code': False, 'webhook_url': url(d['quoi']), 'webhook_field_ids': [[6, 0, champs]]})
            print('action %d -> webhook' % aid)
    for auto_id, dom in DOMAINES.items():
        x('base.automation', 'write', [auto_id], {'filter_domain': dom})
    print('filtres des automatisations 102 / 103 resserrés')


def retour():
    for aid, d in ACTIONS.items():
        assert os.path.exists(archive(aid)), 'archive absente pour %d' % aid
        code = io.open(archive(aid), encoding='utf-8', newline='').read()
        a = x('ir.actions.server', 'read', [aid], ['child_ids'])[0]
        x('ir.actions.server', 'write', [aid], {'state': 'code', 'code': code, 'webhook_url': False, 'webhook_field_ids': [[5]]})
        if a['child_ids']:
            x('ir.actions.server', 'unlink', a['child_ids'])
        print('action %d : code Python remis en place (%d lignes), enfants supprimés' % (aid, loc(code)))
    for auto_id, dom in DOMAINES_ORIGINE.items():
        x('base.automation', 'write', [auto_id], {'filter_domain': dom})
    print('filtres des automatisations 102 / 103 remis à l origine')


if mode == 'etat':
    etat()
elif mode == 'apply':
    appliquer(); print(); etat()
elif mode == 'retour':
    retour(); print(); etat()
else:
    print('SIMULATION (rien modifié). Plan :')
    for aid, d in ACTIONS.items():
        print('  action %d -> %s | URL %s | champs %s' % (aid, 'note + webhook' if d['note'] else 'webhook', masque(url(d['quoi'])), d['champs']))
    for auto_id, dom in DOMAINES.items():
        print('  automatisation %d : filtre %s' % (auto_id, dom))
    print()
    etat()
