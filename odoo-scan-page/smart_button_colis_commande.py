# -*- coding: utf-8 -*-
"""Smart button « Colis (palettes) » sur le devis / bon de commande (sale.order).

Les opérateurs scannent les palettes au poste de scan (scan_view_7890) : le lien
est porté par les OF — mrp.production.x_studio_colis (OF entier sur la palette)
et x_repartition_palette (OF réparti sur plusieurs palettes). Pas de lien fiable
par la tâche commande pierre (toutes les commandes n'en ont pas une).

PIÈGE (corrigé le 03/09/2026) : une première version passait les ids de colis
dans le contexte du bouton et filtrait l'action avec
`[('id','in', context.get('colis_ids') or [])]`. Côté client, le domaine d'une
act_window est évalué avec les CLÉS du contexte étalées comme variables —
`context` n'existe pas → l'action plantait au montage et cassait la pile des
contrôleurs (« ControllerNotFoundError: Invalid controller to restore »).
De plus le contexte de l'action ÉCRASE celui du bouton (_preprocessAction),
donc pas de valeur par défaut possible. Le pattern robuste est le
`search_default_<champ>` sur un champ stocké.

Objets en prod :

1. stock.package.x_commande_id — many2one sale.order, manuel, STOCKÉ,
   copied=False, depends 'x_studio_one2many_field_55p_1jh99tbrr.origin'
   (l'inverse de mrp.production.x_studio_colis → recalcule à chaque scan),
   compute :
       for record in self:
           names = [o for o in record['x_studio_one2many_field_55p_1jh99tbrr'].mapped('origin') if o]
           if not names:
               reps = record.env['x_repartition_palette'].search(
                   [('x_studio_colis_id', '=', record.id)], limit=1)
               names = [n for n in reps.mapped('x_studio_of_id.origin') if n]
           record['x_commande_id'] = record.env['sale.order'].search(
               [('name', '=', names[0])], limit=1).id if names else False
   NB : une palette remplie UNIQUEMENT de répartitions partielles n'est pas
   recalculée automatiquement (pas de dépendance possible sur
   x_repartition_palette) — cas inexistant à ce jour (table vide).

2. sale.order.x_nb_colis — integer, manuel, NON stocké, depends 'name',
   compute :
       for record in self:
           record['x_nb_colis'] = record.env['stock.package'].search_count(
               [('x_commande_id', '=', record.id)])

3. ir.ui.view 7978 « stock.package.search.colis.commande » (search, stock.package) :
       <search string="Colis">
           <field name="name"/>
           <field name="x_commande_id"/>
           <field name="x_studio_client"/>
           <filter name="cloturees" string="Palettes clôturées" domain="[('x_studio_cloturee','=',True)]"/>
           <filter name="ouvertes" string="Palettes ouvertes" domain="[('x_studio_cloturee','=',False)]"/>
       </search>

4. ir.actions.act_window 2089 « Colis (palettes) de la commande » —
   res_model stock.package, view_mode list,form, search_view_id 7978,
   SANS domaine (le filtrage vient du search_default du bouton).

5. ir.ui.view 7979 « sale.order.form.smart.colis » — extension de
   sale.view_order_form (2614), priority 99 :
       <data>
         <xpath expr="//div[@name='button_box']" position="inside">
           <button class="oe_stat_button" type="action" name="2089" icon="fa-cubes"
                   invisible="x_nb_colis == 0"
                   context="{'search_default_x_commande_id': id}">
             <field name="x_nb_colis" widget="statinfo" string="Colis (palettes)"/>
           </button>
         </xpath>
       </data>

Contrôles : S07305 → 5 colis (dont PACK0000050), S08042 → 5, S10563 → 4,
S07457 → 0 (bouton masqué, rien de scanné sur cette commande).
"""
