# Page liens : régénérer le token heures d'un salarié (clé responsables requise)
ctx = env.context
adm = (ctx.get('hj_k') or '')
adm_ref = env['ir.config_parameter'].sudo().get_param('maquignon.rh_admin_key') or ''
emp_id = ctx.get('emp_id')
newtok = (ctx.get('new_token') or '').strip()
if emp_id and adm and adm == adm_ref:
    if len(newtok) < 12 or len(newtok) > 64:
        raise UserError('Token invalide.')
    env['hr.employee'].sudo().browse(int(emp_id)).write({'x_heures_token': newtok})
    action = {'ok': 1}
