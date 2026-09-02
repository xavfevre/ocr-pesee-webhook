# Tablette : créer une demande de congés (lien signé salarié)
ctx = env.context
emp_id = ctx.get('dc_emp')
if emp_id:
    emp = env['hr.employee'].sudo().browse(int(emp_id))
    tok = (ctx.get('dc_token') or '')
    if not (tok and tok == (emp.x_heures_token or '')):
        raise UserError('Lien invalide.')
    du = ctx.get('dc_du'); au = ctx.get('dc_au')
    if not du or not au or du > au:
        raise UserError('Dates invalides.')
    periode = ctx.get('dc_periode') or 'journee'
    if periode not in ('journee', 'matin', 'apresmidi', 'horaires'):
        periode = 'journee'
    h_de = 0.0
    h_a = 0.0
    if periode == 'horaires':
        try:
            h_de = float(ctx.get('dc_h_de') or 0.0)
            h_a = float(ctx.get('dc_h_a') or 0.0)
        except Exception:
            h_de = 0.0
            h_a = 0.0
        if not (0.0 <= h_de < h_a <= 24.0):
            raise UserError('Horaires invalides.')
    rec = env['x_demande_conge'].sudo().create({
        'x_employee_id': emp.id, 'x_du': du, 'x_au': au,
        'x_type': ctx.get('dc_type') or 'cp',
        'x_periode': periode, 'x_h_de': h_de, 'x_h_a': h_a,
        'x_motif': (ctx.get('dc_motif') or '').strip() or False,
        'x_statut': 'attente'})
    action = {'dc_ok': 1, 'id': rec.id}
