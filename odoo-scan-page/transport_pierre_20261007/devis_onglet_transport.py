# -*- coding: utf-8 -*-
"""Devis : gain de place (Xavier, 07/10/2026).
 1. Onglet « 🚚 Transport & fabrication » après « Lignes de commande » : y sont déplacés les cadres Studio « Demande de
    transport Maquignon » et « Fabrication », et le cadre « Transport de la commande (pierre) » y est placé.
 2. Résumé d'une ligne dans l'en-tête, sous « Modèle de devis » : champ calculé x_transport_resume
    (« Transporteur extérieur — GENDRON TRANSPORTS — achat 300,00 € HT — ordre P00132 », « Nos camions », …).
Réécrit la vue 8042 (sale.order.form.transport.pierre). Base : ODOO_URL / ODOO_DB (défaut production).
  python devis_onglet_transport.py dry | apply | compact | retour   (apply = onglet ; compact = sans onglet, cadres par société + résumé ; retour = origine)"""
import os, ssl, sys, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
mode = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
U = os.environ.get('ODOO_URL', 'https://maquignon.odoo.com'); D = os.environ.get('ODOO_DB', 'maquignon')
us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
c = ssl.create_default_context()
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
assert uid, 'authentification refusée sur ' + U
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), dict(k, context={'allowed_company_ids': [1]}))
one = lambda v: v[0] if isinstance(v, list) else v
MODEL_SO = x('ir.model', 'search', [['model', '=', 'sale.order']])[0]
CAT = x('res.partner.category', 'search', [['name', '=', 'Transporteur']])[0]
ACT = x('ir.actions.server', 'search', [['name', '=', 'Devis : demander un tarif transport']])[0]
VUE = x('ir.ui.view', 'search', [['name', '=', 'sale.order.form.transport.pierre']])[0]
print('base %s | vue 8042 = %s | action tarif %s | étiquette %s' % (U, VUE, ACT, CAT))

COMPUTE = '''for r in self:
    mode = r.x_mode_transport
    if not mode:
        r['x_transport_resume'] = 'non renseigné sur le devis'
    elif mode == 'camions':
        r['x_transport_resume'] = 'Nos camions'
    elif mode == 'client':
        r['x_transport_resume'] = 'Enlèvement par le client'
    else:
        t = []
        if r.x_transporteur_id:
            t.append(r.x_transporteur_id.name)
        if r.x_transport_achat:
            t.append('achat %.2f € HT' % r.x_transport_achat)
        if r.x_ordre_transport_id:
            t.append('ordre ' + r.x_ordre_transport_id.name)
        r['x_transport_resume'] = 'Transporteur extérieur' + ((' — ' + ' — '.join(t)) if t else ' (tarif à demander)')'''

GROUPE = '''<group name="maq_transport_pierre" string="Transport de la commande (pierre)" invisible="company_id not in [1]">
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
        </group>'''

ARCH_ONGLET = '''<data>
  <xpath expr="//notebook/page[@name='order_lines']" position="after">
    <page string="🚚 Transport &amp; fabrication" name="maq_transport_fab">
      <xpath expr="//group[@name='studio_group_5s9_1iulplco5']" position="move"/>
      %(groupe)s
      <xpath expr="//group[@name='studio_group_6ei_1jae6rn5m']" position="move"/>
    </page>
  </xpath>
  <xpath expr="//field[@name='sale_order_template_id']" position="after">
    <field name="x_transport_resume" string="Transport" readonly="1" invisible="company_id not in [1]"/>
  </xpath>
</data>'''

ARCH_ORIGINE = '''<data>
  <xpath expr="//group[@name='studio_group_5s9_1iulplco5']" position="after">
    %(groupe)s
  </xpath>
</data>'''

# sans onglet (choix Xavier) : le cadre pierre reste sous l'en-tête ; « Demande de transport Maquignon » visible pour
# Haims (4) et Chatel'Granulats (3) seulement, « Transport de la commande (pierre) » et « Fabrication » pour Maquignon (1) ;
# résumé Transport dans l'en-tête.
ARCH_COMPACT = '''<data>
  <xpath expr="//group[@name='studio_group_5s9_1iulplco5']" position="attributes">
    <attribute name="invisible">company_id not in [3, 4]</attribute>
  </xpath>
  <xpath expr="//group[@name='studio_group_5s9_1iulplco5']" position="after">
    %(groupe)s
  </xpath>
</data>'''

params = {'cat': CAT, 'action': ACT}
champ = x('ir.model.fields', 'search', [['model', '=', 'sale.order'], ['name', '=', 'x_transport_resume']])
print('champ résumé :', champ or 'absent')
if mode == 'dry':
    print('simulation : rien modifié'); sys.exit(0)
if mode == 'retour':
    x('ir.ui.view', 'write', [VUE], {'arch_db': ARCH_ORIGINE % {'groupe': GROUPE % params}})
    print('vue 8042 remise à l origine (cadre sous l en-tête, pas d onglet)'); sys.exit(0)
if mode == 'compact':
    # version retenue par Xavier (07/10/2026) : pas d'onglet, pas de ligne résumé ; le champ résumé est retiré s'il existe
    x('ir.ui.view', 'write', [VUE], {'arch_db': ARCH_COMPACT % {'groupe': GROUPE % params}})
    if champ:
        x('ir.model.fields', 'unlink', champ); print('champ résumé supprimé :', champ)
    arch = x('sale.order', 'get_view', view_id=2614, view_type='form')['arch']
    i = arch.find('name="studio_group_5s9_1iulplco5"'); j = arch.find('name="maq_transport_pierre"')
    print('vue 8042 compacte : pas d onglet : %s | cadre Demande de transport Maquignon invisible=%r | cadre pierre présent %s | résumé en-tête retiré %s' % (
        'maq_transport_fab' not in arch, __import__('re').search(r'invisible="([^"]*)"', arch[i:i + 400]) and __import__('re').search(r'invisible="([^"]*)"', arch[i:i + 400]).group(1), j > 0, 'x_transport_resume' not in arch))
    sys.exit(0)
if not champ:
    champ = [one(x('ir.model.fields', 'create', [{'name': 'x_transport_resume', 'model_id': MODEL_SO, 'field_description': 'Transport (résumé)', 'ttype': 'char', 'state': 'manual',
                                                  'store': False, 'readonly': True, 'compute': COMPUTE,
                                                  'depends': 'x_mode_transport,x_transporteur_id,x_transport_achat,x_ordre_transport_id'}]))]
    print('champ résumé créé :', champ)
x('ir.ui.view', 'write', [VUE], {'arch_db': ARCH_ONGLET % {'groupe': GROUPE % params}})
arch = x('sale.order', 'get_view', view_id=2614, view_type='form')['arch']
i = arch.find('name="maq_transport_fab"'); page = arch[i:]
fin = page.find('</page>')
print('vue 8042 écrite ; onglet présent : %s | cadres dans l onglet : %s | résumé dans l en-tête : %s' % (
    i > 0, [g for g in ('studio_group_5s9_1iulplco5', 'maq_transport_pierre', 'studio_group_6ei_1jae6rn5m') if g in page[:fin]], 'x_transport_resume' in arch))
so = x('sale.order', 'search_read', [['name', '=', 'S12412']], fields=['x_transport_resume'])
print('résumé S12412 :', so and so[0]['x_transport_resume'])
