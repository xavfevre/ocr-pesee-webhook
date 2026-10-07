# -*- coding: utf-8 -*-
"""Transport des commandes pierre, phase 1 (Xavier, 07/10/2026) : référentiel transporteurs + devis.
  - étiquette de contact « Transporteur » posée sur GENDRON TRANSPORTS et TRANSPORTS P. FRECHOT ;
  - article d'achat « Transport affrété (achat transporteur) » (service, compte 624200) ;
  - champs sur le devis : Mode de transport, Transporteurs à consulter, Transporteur retenu, Prix d'achat transport, Ordre de transport ;
  - bouton « Demander un tarif transport » (action serveur) : une demande de prix par transporteur, envoyée par mail,
    pré-remplie avec palettes, poids, volume, adresses et date ; ouvre la liste des demandes ;
  - automatisation : quand une demande de prix transport est confirmée, le devis reçoit le transporteur, le prix d'achat
    et l'ordre de transport ; les autres demandes de la commande sont annulées.
  python transport_devis_setup.py dry | apply | test <S…> | cleanup <S…>"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U, D = 'https://maquignon.odoo.com', 'maquignon'
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
CTX = {'allowed_company_ids': [1], 'active_test': False}


def x(mo, me, *a, **k):
    ctx = dict(CTX); ctx.update(k.pop('context', {})); k['context'] = ctx
    try:
        return m.execute_kw(D, uid, p, mo, me, list(a), k)
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in str(e):
            return None
        raise


def one(v):
    return v[0] if isinstance(v, list) else v


NOM_CAT = 'Transporteur'
NOM_PRODUIT = 'Transport affrété (achat transporteur)'
NOM_ACTION = 'Devis : demander un tarif transport'
NOM_AUTO = 'Achat transport confirmé -> transporteur retenu sur le devis'
NOM_VUE = 'sale.order.form.transport.pierre'
TRANSPORTEURS = ['GENDRON TRANSPORTS', 'TRANSPORTS P. FRECHOT']
MODEL_SO = x('ir.model', 'search', [['model', '=', 'sale.order']])[0]
MODEL_PO = x('ir.model', 'search', [['model', '=', 'purchase.order']])[0]
F_STATE_PO = x('ir.model.fields', 'search', [['model', '=', 'purchase.order'], ['name', '=', 'state']])[0]
TPL = x('ir.model.data', 'search_read', [['module', '=', 'purchase'], ['name', '=', 'email_template_edi_purchase']], fields=['res_id'])[0]['res_id']
CPT_624200 = x('account.account', 'search', [['code', '=', '624200'], ['company_ids', 'in', [1]]])
VUE_BASE = x('ir.ui.view', 'search', [['model', '=', 'sale.order'], ['type', '=', 'form'], ['name', '=', 'sale.order.form'], ['inherit_id', '=', False]])[0]
print('modèles sale.order %s, purchase.order %s | modèle mail demande de prix %s | compte 624200 %s | vue de base %s' % (MODEL_SO, MODEL_PO, TPL, CPT_624200, VUE_BASE))

CHAMPS = [
    ('x_mode_transport', {'field_description': 'Mode de transport', 'ttype': 'selection', 'copied': True,
                          'selection': "[('camions', 'Nos camions'), ('exterieur', 'Transporteur extérieur'), ('client', 'Enlèvement par le client')]"}),
    ('x_transporteurs_ids', {'field_description': 'Transporteurs à consulter', 'ttype': 'many2many', 'relation': 'res.partner', 'copied': True}),
    ('x_transporteur_id', {'field_description': 'Transporteur retenu', 'ttype': 'many2one', 'relation': 'res.partner', 'copied': False}),
    ('x_transport_achat', {'field_description': "Prix d'achat transport (HT)", 'ttype': 'float', 'copied': False}),
    ('x_ordre_transport_id', {'field_description': 'Ordre de transport (achat)', 'ttype': 'many2one', 'relation': 'purchase.order', 'copied': False}),
]

CODE_ACTION = r'''# Devis pierre : une demande de prix par transporteur à consulter, envoyée par mail, puis liste des demandes.
PRODUIT = %(produit)d
TPL = %(tpl)d
for so in records:
    if so.x_mode_transport != 'exterieur':
        raise UserError("Mettez d'abord « Mode de transport » sur « Transporteur extérieur ».")
    if not so.x_transporteurs_ids:
        raise UserError("Cochez au moins un transporteur à consulter.")
    lignes = so.order_line.filtered(lambda l: not l.display_type and l.product_id and l.product_id.type != 'service')
    poids = sum((l.x_studio_poids or 0.0) for l in lignes)
    vol = sum((l.x_studio_vol or 0.0) for l in lignes)
    palettes = sorted({(l.x_studio_palettes or '').strip() for l in lignes if (l.x_studio_palettes or '').strip()})
    adr = so.partner_shipping_id or so.partner_id
    adresse = ', '.join([t for t in [adr.name, adr.street, adr.street2, ' '.join([t2 for t2 in [adr.zip, adr.city] if t2])] if t])
    date = so.x_studio_date_de_livraison_souhait or so.commitment_date
    desc = ("Transport de pierres - commande %%s (%%s)\n"
            "Enlèvement : Carrières Maquignon, 51 rue du Prieuré, 86230 Usseau\n"
            "Livraison : %%s\n"
            "Palettes : %%s\n"
            "Poids total estimé : %%.0f kg - volume : %%.2f m³\n"
            "Date de livraison souhaitée : %%s\n"
            "Merci de nous indiquer votre tarif HT et votre délai.") %% (
            so.name, so.partner_id.name, adresse,
            ('%%d (%%s)' %% (len(palettes), ', '.join(palettes))) if palettes else ('environ %%d (sur la base de 1 500 kg par palette)' %% max(1, -(-int(poids) // 1500))),
            poids, vol, date.strftime('%%d/%%m/%%Y') if date else 'à convenir')
    PO = env['purchase.order'].sudo()
    envoyes, crees = [], PO
    for t in so.x_transporteurs_ids:
        deja = PO.search([('origin', '=', so.name), ('partner_id', '=', t.id), ('state', 'in', ['draft', 'sent'])], limit=1)
        if deja:
            continue
        po = PO.create({'partner_id': t.id, 'origin': so.name, 'company_id': so.company_id.id,
                        'order_line': [(0, 0, {'product_id': PRODUIT, 'name': desc, 'product_qty': 1.0, 'price_unit': 0.0})]})
        crees |= po
        if t.email:
            env['mail.template'].sudo().browse(TPL).send_mail(po.id, force_send=True)
            po.write({'state': 'sent'})
            envoyes.append(t.name)
    if crees:
        so.message_post(body="Demandes de tarif transport créées : %%s%%s" %% (
            ', '.join(crees.mapped('partner_id.name')),
            (' (envoyées par mail à : %%s)' %% ', '.join(envoyes)) if envoyes else " (aucun mail : pas d'adresse e-mail sur la fiche transporteur)"))
    action = {'type': 'ir.actions.act_window', 'res_model': 'purchase.order', 'name': 'Tarifs transport %%s' %% so.name,
              'view_mode': 'list,form', 'domain': [('origin', '=', so.name)], 'context': {'create': False}}
'''

CODE_AUTO = r'''# Demande de prix transport confirmée : transporteur retenu, prix d'achat et ordre de transport sur le devis ;
# les autres demandes de la même commande sont annulées.
PRODUIT = %(produit)d
for po in records:
    if po.state != 'purchase' or PRODUIT not in po.order_line.product_id.ids or not po.origin:
        continue
    so = env['sale.order'].sudo().search([('name', '=', po.origin)], limit=1)
    if not so:
        continue
    so.write({'x_transporteur_id': po.partner_id.id, 'x_transport_achat': po.amount_untaxed, 'x_ordre_transport_id': po.id})
    autres = env['purchase.order'].sudo().search([('origin', '=', so.name), ('id', '!=', po.id), ('state', 'in', ['draft', 'sent']),
                                                  ('order_line.product_id', '=', PRODUIT)])
    if autres:
        autres.button_cancel()
    so.message_post(body="Transporteur retenu : %%s - %%.2f EUR HT (ordre de transport %%s).%%s" %% (
        po.partner_id.name, po.amount_untaxed, po.name,
        (' Autres demandes annulées : %%s.' %% ', '.join(autres.mapped('partner_id.name'))) if autres else ''))
'''

VUE = '''<data>
  <xpath expr="//group[@name='studio_group_5s9_1iulplco5']" position="after">
    <group name="maq_transport_pierre" string="Transport de la commande (pierre)" invisible="company_id not in [1]">
      <group name="maq_transport_pierre_g">
        <field name="x_mode_transport" widget="radio" options="{'horizontal': true}"/>
        <field name="x_transporteurs_ids" widget="many2many_tags" domain="[('category_id', 'in', [%(cat)d])]" context="{'default_category_id': [%(cat)d], 'default_supplier_rank': 1, 'default_is_company': True}" invisible="x_mode_transport != 'exterieur'"/>
        <button string="Demander un tarif transport" name="%(action)d" type="action" class="btn-primary" invisible="x_mode_transport != 'exterieur' or state == 'cancel'"/>
      </group>
      <group name="maq_transport_pierre_d">
        <field name="x_transporteur_id" domain="[('category_id', 'in', [%(cat)d])]" invisible="x_mode_transport != 'exterieur'"/>
        <field name="x_transport_achat" invisible="x_mode_transport != 'exterieur'"/>
        <field name="x_ordre_transport_id" readonly="1" invisible="x_mode_transport != 'exterieur'"/>
      </group>
    </group>
  </xpath>
</data>'''


def etat():
    cat = x('res.partner.category', 'search', [['name', '=', NOM_CAT]])
    prod = x('product.product', 'search', [['name', '=', NOM_PRODUIT]])
    champs = {f['name']: f['id'] for f in x('ir.model.fields', 'search_read', [['model', '=', 'sale.order'], ['name', 'in', [n for n, _ in CHAMPS]]], fields=['name'])}
    act = x('ir.actions.server', 'search', [['name', '=', NOM_ACTION]])
    auto = x('base.automation', 'search', [['name', '=', NOM_AUTO]])
    vue = x('ir.ui.view', 'search', [['name', '=', NOM_VUE]])
    return cat, prod, champs, act, auto, vue


cat, prod, champs, act, auto, vue = etat()
print('état : étiquette %s | article %s | champs %s | action %s | automatisation %s | vue %s' % (cat, prod, sorted(champs), act, auto, vue))

if mode == 'dry':
    print('transporteurs à étiqueter :', x('res.partner', 'search_read', [['name', 'in', TRANSPORTEURS]], fields=['name', 'email', 'category_id']))
    print('simulation : rien modifié'); sys.exit(0)

if mode == 'apply':
    cat_id = cat[0] if cat else one(x('res.partner.category', 'create', [{'name': NOM_CAT, 'color': 4}]))
    for t in x('res.partner', 'search_read', [['name', 'in', TRANSPORTEURS]], fields=['name', 'category_id']):
        if cat_id not in t['category_id']:
            x('res.partner', 'write', [t['id']], {'category_id': [[4, cat_id]]})
    print('étiquette « Transporteur » :', cat_id, '-> posée sur', TRANSPORTEURS)
    if prod:
        prod_id = prod[0]
    else:
        tmpl = one(x('product.template', 'create', [{'name': NOM_PRODUIT, 'type': 'service', 'purchase_ok': True, 'sale_ok': False, 'list_price': 0.0, 'standard_price': 0.0,
                                                    'taxes_id': [[6, 0, []]], 'description_purchase': 'Transport affrété de pierres (voir le détail sur la ligne de la demande de prix).'}]))
        if CPT_624200:
            x('product.template', 'write', [tmpl], {'property_account_expense_id': CPT_624200[0]})
        prod_id = x('product.product', 'search', [['product_tmpl_id', '=', tmpl]])[0]
    print('article d achat :', prod_id)
    for name, vals in CHAMPS:
        if name in champs:
            continue
        v = dict(vals); v.update({'name': name, 'model_id': MODEL_SO, 'state': 'manual', 'store': True})
        champs[name] = one(x('ir.model.fields', 'create', [v]))
    print('champs devis :', champs)
    if act:
        act_id = act[0]
        x('ir.actions.server', 'write', [act_id], {'code': CODE_ACTION % {'produit': prod_id, 'tpl': TPL}})
    else:
        act_id = one(x('ir.actions.server', 'create', [{'name': NOM_ACTION, 'model_id': MODEL_SO, 'state': 'code', 'code': CODE_ACTION % {'produit': prod_id, 'tpl': TPL}}]))
    print('action serveur bouton :', act_id)
    code_auto = CODE_AUTO % {'produit': prod_id}
    if auto:
        auto_id = auto[0]
        a = x('base.automation', 'read', [auto_id], ['action_server_ids'])[0]
        x('ir.actions.server', 'write', a['action_server_ids'], {'code': code_auto})
    else:
        auto_id = one(x('base.automation', 'create', [{'name': NOM_AUTO, 'model_id': MODEL_PO, 'trigger': 'on_create_or_write', 'trigger_field_ids': [[6, 0, [F_STATE_PO]]],
                                                        'filter_domain': "[('state', '=', 'purchase')]", 'active': True,
                                                        'action_server_ids': [[0, 0, {'name': NOM_AUTO, 'model_id': MODEL_PO, 'state': 'code', 'code': code_auto, 'usage': 'base_automation'}]]}]))
    print('automatisation :', auto_id)
    arch = VUE % {'cat': cat_id, 'action': act_id}
    if vue:
        vue_id = vue[0]; x('ir.ui.view', 'write', [vue_id], {'arch_db': arch})
    else:
        # priorité > 160 (vue Studio 4889) pour que le groupe cible existe déjà au moment de l'application
        vue_id = one(x('ir.ui.view', 'create', [{'name': NOM_VUE, 'model': 'sale.order', 'type': 'form', 'inherit_id': VUE_BASE, 'mode': 'extension', 'priority': 200, 'arch_db': arch}]))
    print('vue formulaire devis :', vue_id)
    sys.exit(0)

so_name = sys.argv[2] if len(sys.argv) > 2 else None
assert so_name, 'indiquer le numéro du devis (S…)'
so = x('sale.order', 'search_read', [['name', '=', so_name]], fields=['id', 'state', 'partner_id', 'x_mode_transport', 'x_transporteurs_ids', 'x_transporteur_id', 'x_transport_achat', 'x_ordre_transport_id'])[0]
TESTP = 'TEST TRANSPORTEUR (à supprimer)'
if mode == 'test':
    # transporteur de test sans e-mail (aucun envoi), devis mis en « Transporteur extérieur », action lancée, puis contrôle
    tp = x('res.partner', 'search', [['name', '=', TESTP]]) or [one(x('res.partner', 'create', [{'name': TESTP, 'is_company': True, 'supplier_rank': 1, 'category_id': [[4, cat[0]]], 'company_id': 1}]))]
    x('sale.order', 'write', [so['id']], {'x_mode_transport': 'exterieur', 'x_transporteurs_ids': [[6, 0, tp]]})
    res = x('ir.actions.server', 'run', act, context={'active_model': 'sale.order', 'active_ids': [so['id']], 'active_id': so['id']})
    print('action lancée ->', (res or {}).get('name') if isinstance(res, dict) else res)
    pos = x('purchase.order', 'search_read', [['origin', '=', so_name]], fields=['name', 'partner_id', 'state', 'amount_untaxed', 'order_line'])
    for po in pos:
        l = x('purchase.order.line', 'read', po['order_line'], ['name', 'product_id', 'price_unit'])[0]
        print('   demande %s | %s | %s | ligne : %s | %s' % (po['name'], po['partner_id'][1], po['state'], l['product_id'][1], l['name'].replace('\n', ' / ')[:300]))
    # simulation du choix : prix saisi puis confirmation -> automatisation
    po = [q for q in pos if q['partner_id'][0] == tp[0]][0]
    x('purchase.order.line', 'write', po['order_line'], {'price_unit': 123.45})
    x('purchase.order', 'button_confirm', [po['id']])
    so2 = x('sale.order', 'read', [so['id']], ['x_transporteur_id', 'x_transport_achat', 'x_ordre_transport_id'])[0]
    print('après confirmation :', so2, '| état achat :', x('purchase.order', 'read', [po['id']], ['state'])[0]['state'])
    print('derniers messages du devis :', [q['body'][:160] for q in x('mail.message', 'search_read', [['model', '=', 'sale.order'], ['res_id', '=', so['id']]], fields=['body'], order='id desc', limit=2)])
    sys.exit(0)

if mode == 'cleanup':
    pos = x('purchase.order', 'search_read', [['origin', '=', so_name]], fields=['name', 'state'])
    for po in pos:
        if po['state'] not in ('cancel',):
            x('purchase.order', 'button_cancel', [po['id']])
        x('purchase.order', 'unlink', [po['id']])      # Odoo n'accepte la suppression qu'à l'état annulé
    x('sale.order', 'write', [so['id']], {'x_mode_transport': False, 'x_transporteurs_ids': [[6, 0, []]], 'x_transporteur_id': False, 'x_transport_achat': 0.0, 'x_ordre_transport_id': False})
    msgs = x('mail.message', 'search', [['model', '=', 'sale.order'], ['res_id', '=', so['id']], ['body', 'ilike', 'tarif transport']]) + x('mail.message', 'search', [['model', '=', 'sale.order'], ['res_id', '=', so['id']], ['body', 'ilike', 'Transporteur retenu']])
    if msgs:
        x('mail.message', 'unlink', msgs)
    tp = x('res.partner', 'search', [['name', '=', TESTP]])
    if tp:
        x('res.partner', 'unlink', tp)
    print('nettoyage : %d demande(s) supprimée(s), devis remis à blanc, %d note(s) retirée(s), partenaire de test supprimé' % (len(pos), len(msgs)))
