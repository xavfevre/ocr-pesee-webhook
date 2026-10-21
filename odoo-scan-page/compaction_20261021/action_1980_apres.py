# Recalcul « Fab en cours » DIFFÉRÉ en fin de transaction : une seule passe par commande, quel que soit le nombre d'OF / OT écrits.
names = set(p.origin for p in records.mapped("production_id") if p.origin)
TRC = [51, 49, 54, 57, 46, 59]   # catégories « tranches »
if names:
    _d = env.cr.precommit.data
    if 'maq_fab_recalc' not in _d:
        _d['maq_fab_recalc'] = set()
        def _maq_fab_recalc():
            noms = env.cr.precommit.data.pop('maq_fab_recalc', set())
            for so in (env['sale.order'].search([('name', 'in', sorted(noms))]) if noms else env['sale.order']):
                ofs = env['mrp.production'].search([('origin', '=', so.name), ('company_id', '=', 1)], order='name')
                open_ofs = ofs.filtered(lambda o: o.state in ('draft', 'confirmed', 'progress', 'to_close'))
                fams = {}
                for of in ofs:
                    raw = of.x_studio_catgorie.display_name if of.x_studio_catgorie else ''
                    nm = raw.split('/')[1].strip() if '/' in raw else (raw or 'Autre')
                    fams[nm] = fams.get(nm, 0) + 1
                dts = [w.date_start for of in open_ofs for w in of.workorder_ids if w.date_start]
                nums = [(o.name or '').replace('WH/OF/', '').lstrip('0') for o in open_ofs]
                so.write({'x_studio_fab_encours': bool(open_ofs),
                          'x_studio_of_non_planifies': len(open_ofs.filtered(lambda o: not any(w.employee_assigned_ids or w.date_start for w in o.workorder_ids))),
                          'x_studio_of_non_programmes': len(open_ofs.filtered(lambda o: not any(w.date_start for w in o.workorder_ids))),
                          'x_studio_of_tranches': len(open_ofs.filtered(lambda o: o.x_studio_catgorie and o.x_studio_catgorie.id in TRC)),
                          'x_studio_vol_of': sum(o.x_studio_vol_total or 0.0 for o in ofs), 'x_studio_vol_reste': sum(o.x_studio_vol_total or 0.0 for o in open_ofs),
                          'x_studio_produits_fab': ' · '.join('%s (%s)' % (k, v) for k, v in sorted(fams.items())),
                          'x_studio_of_liste': '' if not nums else ('n°' + nums[0] if len(nums) == 1 else 'n°%s → %s' % (nums[0], nums[-1])),
                          'x_studio_pierres_faites': '%s / %s' % (sum(int(o.x_studio_nbr or 0) for o in ofs.filtered(lambda o: o.state == 'done')), sum(int(o.x_studio_nbr or 0) for o in ofs)),
                          'x_studio_date_planif': min(dts).date() if dts else False})
            env.flush_all()
        env.cr.precommit.add(_maq_fab_recalc)
    _d['maq_fab_recalc'].update(names)
