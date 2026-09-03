# Action serveur Odoo 1987 — ARCHIVE avant suppression (03/09/2026) — portée vers Render (web_actions.py)
# Compteur de lignes de l'abonnement Odoo (« Maintenance par 100 lignes »).


of = env['mrp.production'].browse(env.context.get('active_id')).sudo()
n = int(env.context.get('rebut_n') or 0)
motif = (env.context.get('rebut_motif') or '').strip()
if not of.exists() or n <= 0:
    raise UserError('Rebut : nombre de pierres invalide')
tot = int(of.x_studio_nbr or 0) or 1
if n > tot:
    raise UserError('Rebut : maximum %s pierre(s) sur cet OF' % tot)
deja = int(of.x_studio_rebut_nb or 0)
if deja + n > tot:
    raise UserError('Rebut deja declare sur cet OF (%s pierre(s), OF de relance %s). Rien a refaire : l OF de relance est dans la liste.' % (deja, of.x_studio_relance_of or '-'))
vol_unit = (of.x_studio_vol_total or 0.0) / tot
vol_reb = vol_unit * n

# 1) retirer les pierres cassees du colis (entier ou repartition)
colis_note = ''
colis = of.x_studio_colis
if colis:
    of.write({'x_studio_colis': False})
    if n < tot:
        env['x_repartition_palette'].sudo().create({'x_studio_of_id': of.id, 'x_studio_colis_id': colis.id, 'x_studio_qte': tot - n})
    colis_note = ' · retire du colis %s' % colis.name
else:
    reps = env['x_repartition_palette'].sudo().search([('x_studio_of_id', '=', of.id)])
    rem = n
    for rp in reps:
        if rem <= 0:
            break
        q = int(rp.x_studio_qte or 0)
        cn = rp.x_studio_colis_id.name
        if q <= rem:
            rem -= q
            rp.unlink()
        else:
            rp.write({'x_studio_qte': q - rem})
            rem = 0
        colis_note = ' · repartition reduite (%s)' % cn

# 2) sortie de stock si la production etait terminee
scrap_note = ''
if of.state == 'done' and vol_reb > 0:
    try:
        sc = env['stock.scrap'].sudo().create({'product_id': of.product_id.id, 'scrap_qty': vol_reb,
            'product_uom_id': of.product_uom_id.id, 'production_id': of.id, 'company_id': of.company_id.id})
        sc.action_validate()
        if sc.state != 'done':
            env['stock.warn.insufficient.qty.scrap'].sudo().create({
                'product_id': sc.product_id.id, 'location_id': sc.location_id.id,
                'scrap_id': sc.id, 'quantity': sc.scrap_qty,
                'product_uom_name': sc.product_uom_id.name}).action_done()
        scrap_note = ' · %.3f m3 sortis du stock (rebut)' % vol_reb
    except Exception:
        scrap_note = ' · (sortie de stock impossible, a regulariser)'

# 3) OF de relance
new = of.copy({'product_qty': vol_reb or of.product_qty, 'origin': of.origin,
               'product_id': of.product_id.id, 'bom_id': of.bom_id.id if of.bom_id else False})
data = of.read(['date_deadline', 'x_studio_date_de_commande', 'x_studio_haut_m', 'x_studio_larg_m', 'x_studio_long_m', 'x_studio_n_de_bc'])[0]
vals = {'x_studio_nbr': n, 'x_studio_origine_rebut': of.name, 'priority': '1'}
if of.x_studio_catgorie:
    vals['x_studio_catgorie'] = of.x_studio_catgorie.id
if of.x_studio_palette:
    vals['x_studio_palette'] = of.x_studio_palette
for f in ('date_deadline', 'x_studio_date_de_commande', 'x_studio_haut_m', 'x_studio_larg_m', 'x_studio_long_m', 'x_studio_n_de_bc'):
    if data.get(f):
        vals[f] = data[f]
new.write(vals)
new.action_confirm()
# assigner les operateurs de l OF d origine pour que la relance apparaisse
# dans « Ma production » (sinon l operateur croit que rien ne s est passe)
for wo_new in new.workorder_ids:
    src = of.workorder_ids.filtered(lambda w: w.name == wo_new.name) or of.workorder_ids[:1]
    if src and src[0].employee_assigned_ids:
        wo_new.write({'employee_assigned_ids': [(6, 0, src[0].employee_assigned_ids.ids)]})

# 4) tracabilite
of.write({'x_studio_rebut_nb': int(of.x_studio_rebut_nb or 0) + n,
          'x_studio_rebut_motif': motif or 'Rebut',
          'x_studio_relance_of': new.name})
of.message_post(body='💥 Rebut : %s pierre(s)%s%s · motif : %s · OF de relance : %s' % (n, colis_note, scrap_note, motif or '-', new.name))
action = {'rebut_ok': True, 'new_of': new.name}
