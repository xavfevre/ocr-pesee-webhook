# Recalcul « Fab en cours » DIFFÉRÉ en fin de transaction : une seule passe par commande, quel que soit
# le nombre d'OF / OT écrits dans la transaction (avant : recalcul complet à chaque écriture de chaque OF,
# soit un coût quadratique à la confirmation d'une commande de plusieurs centaines de lignes).
names = set(p.origin for p in records.mapped('production_id') if p.origin)
if names:
    _d = env.cr.precommit.data
    if 'maq_fab_recalc' not in _d:
        _d['maq_fab_recalc'] = set()
        def _maq_fab_recalc():
            noms = env.cr.precommit.data.pop('maq_fab_recalc', set())
            orders = env['sale.order'].search([('name', 'in', sorted(noms))]) if noms else env['sale.order']
            TRC = [51, 49, 54, 57, 46, 59]
            for so in orders:
                ofs = env['mrp.production'].search([('origin', '=', so.name), ('company_id', '=', 1)], order='name')
                open_ofs = ofs.filtered(lambda o: o.state in ('draft', 'confirmed', 'progress', 'to_close'))
                nonplan = 0
                nonprog = 0
                ntr = 0
                for of in open_ofs:
                    wos = of.workorder_ids
                    assigned = False
                    dated = False
                    for w in wos:
                        if w.employee_assigned_ids or w.date_start:
                            assigned = True
                        if w.date_start:
                            dated = True
                    if not assigned:
                        nonplan += 1
                    if not dated:
                        nonprog += 1
                    if of.x_studio_catgorie and of.x_studio_catgorie.id in TRC:
                        ntr += 1
                fams = {}
                for of in ofs:
                    raw = of.x_studio_catgorie.display_name if of.x_studio_catgorie else ''
                    parts = raw.split('/')
                    nm = parts[1].strip() if len(parts) > 1 else (raw or 'Autre')
                    fams[nm] = fams.get(nm, 0) + 1
                dts = [w.date_start for of in open_ofs for w in of.workorder_ids if w.date_start]
                planif = min(dts).date() if dts else False
                nums = [(o.name or '').replace('WH/OF/', '').lstrip('0') for o in open_ofs]
                if not nums:
                    of_liste = ''
                elif len(nums) == 1:
                    of_liste = 'n°' + nums[0]
                else:
                    of_liste = 'n°%s → %s' % (nums[0], nums[-1])
                done_p = sum(int(o.x_studio_nbr or 0) for o in ofs.filtered(lambda o: o.state == 'done'))
                tot_p = sum(int(o.x_studio_nbr or 0) for o in ofs)
                so.write({
                    'x_studio_fab_encours': bool(open_ofs),
                    'x_studio_of_non_planifies': nonplan,
                    'x_studio_of_non_programmes': nonprog,
                    'x_studio_of_tranches': ntr,
                    'x_studio_vol_of': sum(o.x_studio_vol_total or 0.0 for o in ofs),
                    'x_studio_vol_reste': sum(o.x_studio_vol_total or 0.0 for o in open_ofs),
                    'x_studio_produits_fab': ' · '.join('%s (%s)' % (k, v) for k, v in sorted(fams.items())),
                    'x_studio_of_liste': of_liste,
                    'x_studio_pierres_faites': '%s / %s' % (done_p, tot_p),
                    'x_studio_date_planif': planif,
                })
            env.flush_all()
        env.cr.precommit.add(_maq_fab_recalc)
    _d['maq_fab_recalc'].update(names)
