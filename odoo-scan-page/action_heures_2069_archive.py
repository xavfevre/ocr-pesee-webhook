# Congés : décision du manager via lien signé (email)
ctx = env.context
dc_id = ctx.get('dc_id')
tok = (ctx.get('dc_token') or '').strip()
decision = ctx.get('dc_decision')
if not dc_id or not tok:
    raise UserError('Lien invalide.')
dc = env['x_demande_conge'].sudo().browse(int(dc_id))
if not dc.exists() or not dc.x_token or dc.x_token != tok:
    raise UserError('Lien invalide ou expiré.')
if dc.x_statut != 'attente':
    raise UserError('Cette demande a déjà été traitée (%s).' % dict([('approuve','approuvée'),('refuse','refusée')]).get(dc.x_statut, dc.x_statut))
if decision not in ('approuve', 'refuse'):
    raise UserError('Décision invalide.')
adm = env['ir.config_parameter'].sudo().get_param('maquignon.rh_admin_key') or ''
env['ir.actions.server'].sudo().browse(2014).with_context(
    dc_id=dc.id, dc_decision=decision,
    dc_reponse=(ctx.get('dc_reponse') or '').strip() or ('Validé par le responsable (email)' if decision == 'approuve' else 'Refusé par le responsable (email)'),
    hj_k=adm).run()
action = {'ok': 1, 'statut': decision}
