# -*- coding: utf-8 -*-
"""Smart button « Colis (palettes) » sur le devis / bon de commande (sale.order).

Les opérateurs scannent les palettes au poste de scan (scan_view_7890) : le lien
est porté par les OF — mrp.production.x_studio_colis (OF entier sur la palette)
et x_repartition_palette (OF réparti sur plusieurs palettes). Pas de lien fiable
par la tâche commande pierre (toutes les commandes n'en ont pas une).

Objets créés en prod (03/09/2026) :

1. sale.order.x_colis_ids — many2many stock.package, manuel, NON stocké,
   depends 'name', compute :
       for record in self:
           ofs = record.env['mrp.production'].search(
               [('origin', '=', record['name']), ('x_studio_colis', '!=', False)])
           ids = set(ofs.mapped('x_studio_colis').ids)
           reps = record.env['x_repartition_palette'].search(
               [('x_studio_of_id.origin', '=', record['name']), ('x_studio_colis_id', '!=', False)])
           ids |= set(reps.mapped('x_studio_colis_id').ids)
           record['x_colis_ids'] = [(6, 0, sorted(ids))]

2. sale.order.x_nb_colis — integer, manuel, NON stocké, depends 'name',
   compute :
       for record in self:
           record['x_nb_colis'] = len(record['x_colis_ids'])

3. ir.ui.view 7978 « stock.package.search.colis.commande » (search, stock.package) :
       <search string="Colis">
           <field name="name"/>
           <field name="x_studio_tche_commande_pierre"/>
           <field name="x_studio_client"/>
           <filter name="cloturees" string="Palettes clôturées" domain="[('x_studio_cloturee','=',True)]"/>
           <filter name="ouvertes" string="Palettes ouvertes" domain="[('x_studio_cloturee','=',False)]"/>
       </search>

4. ir.actions.act_window 2089 « Colis (palettes) de la commande » —
   res_model stock.package, view_mode list,form, search_view_id 7978,
   domain "[('id','in', context.get('colis_ids') or [])]"
   (les ids sont passés par le contexte du bouton — pas de champ commande
   nécessaire sur stock.package).

5. ir.ui.view 7979 « sale.order.form.smart.colis » — extension de
   sale.view_order_form (2614), priority 99 :
       <data>
         <xpath expr="//div[@name='button_box']" position="inside">
           <field name="x_colis_ids" invisible="1"/>
           <button class="oe_stat_button" type="action" name="2089" icon="fa-cubes"
                   invisible="x_nb_colis == 0"
                   context="{'colis_ids': x_colis_ids}">
             <field name="x_nb_colis" widget="statinfo" string="Colis (palettes)"/>
           </button>
         </xpath>
       </data>

Contrôles : S07305 → 5 colis (PACK0000046…50), S08042 → 5, S10563 → 4,
S07457 → 0 (bouton masqué, rien de scanné sur cette commande).
"""
