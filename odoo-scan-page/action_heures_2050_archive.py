# Verrou de paie : fige les feuilles d'heures jusqu'a une date incluse
ctx = env.context
adm = (ctx.get('hj_k') or '')
adm_ref = env['ir.config_parameter'].sudo().get_param('maquignon.rh_admin_key') or ''
if not (adm and adm == adm_ref):
    raise UserError('Clé responsables requise.')
vl = (ctx.get('vl_date') or '').strip()
if vl:
    datetime.datetime.strptime(vl, '%Y-%m-%d')
    env['ir.config_parameter'].sudo().set_param('maquignon.heures_verrou', vl)
else:
    env['ir.config_parameter'].sudo().set_param('maquignon.heures_verrou', '')
action = {'ok': 1, 'verrou': vl}
