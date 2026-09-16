# -*- coding: utf-8 -*-
"""Render v4 (16/09/2026 après-midi) :
 - poste de scan : palette clôturée scannée = lecture seule (contenu + bon de colisage), plus de refus ;
 - seuil de poids palette (ir.config_parameter maquignon.palette_max_kg) renvoyé aux pages (jauge) ;
 - 2101 renvoie le tonnage de la palette après la pose (toast tablette) ;
 - mode responsable : transfert d'une palette à l'opérateur de la tablette, code maquignon.palette_code_chef ;
 - 2103 : alerte hebdo palettes (pierres non palettisées par opérateur, palettes dormantes) envoyée par mail."""
import io, ast, sys
sys.stdout.reconfigure(encoding='utf-8')
p = 'ocr/web_actions.py'; s = io.open(p, encoding='utf-8').read()


def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:90]); s = s.replace(old, new)


# ── paramètres (cache 10 min) ──
rep("""def _fmt3(v):
    return ('%.3f' % v).rstrip('0').rstrip('.')
""", """def _fmt3(v):
    return ('%.3f' % v).rstrip('0').rstrip('.')


_PARAMS = {}


def _param(call, cle, defaut):
    \"\"\"ir.config_parameter lu au plus toutes les 10 min (seuil de poids, code responsable, mail d'alerte).\"\"\"
    import time
    now = time.time()
    v = _PARAMS.get(cle)
    if v is None or now - v[1] > 600:
        try:
            val = call('ir.config_parameter', 'get_param', cle, defaut)
        except Exception:  # noqa: BLE001
            val = defaut
        _PARAMS[cle] = (val, now)
        v = _PARAMS[cle]
    return v[0]


def _max_kg(call):
    try:
        return float(str(_param(call, 'maquignon.palette_max_kg', '1500')).replace(',', '.')) or 1500.0
    except Exception:  # noqa: BLE001
        return 1500.0
""")

# ── 2101 : tonnage après la pose ──
rep("""    _verif_of(of, colis)
    _colis_prendre(call, colis, emp)
    msg, res = _poser(call, of, colis, int(ctx.get('qte') or 0))
    res['msg'] = msg
    return res
""", """    _verif_of(of, colis)
    _colis_prendre(call, colis, emp)
    msg, res = _poser(call, of, colis, int(ctx.get('qte') or 0))
    res['msg'] = msg
    try:
        res['colis_ton'] = round(call('stock.package', 'read', [colis['id']], fields=['x_studio_tonnage'])[0]['x_studio_tonnage'] or 0)
    except Exception:  # noqa: BLE001
        res['colis_ton'] = 0
    res['max_kg'] = _max_kg(call)
    return res


def _transferer(call, ctx):
    \"\"\"Mode responsable (tablette) : la palette passe à l'opérateur choisi sur la tablette, sur code.\"\"\"
    code = str(ctx.get('code') or '').strip()
    attendu = str(_param(call, 'maquignon.palette_code_chef', '') or '').strip()
    if not attendu or code != attendu:
        raise WebErreur('🔑 Code responsable incorrect.')
    emp = _operateur(call, ctx)
    colis = _colis_lire(call, int(ctx.get('colis_id') or 0), ctx.get('colis_name') or '')
    if not colis:
        raise WebErreur('Palette introuvable.')
    if colis['x_studio_cloturee']:
        raise WebErreur('🔒 %s est clôturée.' % colis['name'])
    avant = colis['x_operateur_id'][1] if colis['x_operateur_id'] else 'sans opérateur'
    vals = {'x_operateur_id': emp['id']}
    if emp['id'] not in (colis['x_operateur_ids'] or []):
        vals['x_operateur_ids'] = [[4, emp['id']]]
    call('stock.package', 'write', [colis['id']], vals)
    call('hr.employee', 'write', [emp['id']], {'x_palette_scan_id': colis['id']})
    _sur(lambda: call('stock.package', 'message_post', [colis['id']],
                      body='🔑 Palette transférée de %s à %s (mode responsable, tablette)' % (avant, emp['name'])))
    return {'ok': 1, 'colis': colis['name'], 'colis_id': colis['id'], 'avant': avant, 'apres': emp['name'],
            'msg': '🔑 %s transférée de %s à %s' % (colis['name'], avant, emp['name'])}
""")

# ── 2102 : palette clôturée = lecture seule ──
rep("""def _colis_poste(call, colis_id):
    \"\"\"Palette active du poste : None si absente ou clôturée.\"\"\"
    if not colis_id:
        return None
    colis = _colis_lire(call, colis_id)
    if not colis or colis['x_studio_cloturee']:
        return None
    return colis
""", """def _colis_poste(call, colis_id):
    \"\"\"Palette active du poste : None si absente (une palette clôturée reste affichée en lecture seule).\"\"\"
    if not colis_id:
        return None
    return _colis_lire(call, colis_id)
""")
rep("""    etat = {'msg': msg, 'ok': 1 if ok else 0, 'colis': None, 'items': []}
    if colis:
        items = _scan_items(call, colis)
        etat['colis'] = {'id': colis['id'], 'name': colis['name'], 'zone': colis['x_studio_zone'] or '',
                         'cub': round(colis['x_studio_cubage'] or 0, 3),
                         'ton': round(colis['x_studio_tonnage'] or 0), 'n': len(items),
                         'op_nom': colis['x_operateur_id'][1] if colis['x_operateur_id'] else ''}
        etat['items'] = items
    if extra:
        etat.update(extra)
    if not msg:
        if colis:
            etat['msg'] = '📦 %s active — %s (%d OF)' % (
                colis['name'], ('palette de ' + colis['x_operateur_id'][1]) if colis['x_operateur_id']
                else 'palette vierge, elle sera au premier opérateur qui y pose', len(etat['items']))
        else:
            etat['msg'] = '👉 Scannez une palette (PACK…) pour commencer'
    return etat
""", """    etat = {'msg': msg, 'ok': 1 if ok else 0, 'colis': None, 'items': [], 'max_kg': _max_kg(call)}
    if colis:
        items = _scan_items(call, colis)
        etat['colis'] = {'id': colis['id'], 'name': colis['name'], 'zone': colis['x_studio_zone'] or '',
                         'cub': round(colis['x_studio_cubage'] or 0, 3),
                         'ton': round(colis['x_studio_tonnage'] or 0), 'n': len(items),
                         'op_nom': colis['x_operateur_id'][1] if colis['x_operateur_id'] else '',
                         'cloturee': 1 if colis['x_studio_cloturee'] else 0}
        etat['items'] = items
    if extra:
        etat.update(extra)
    if not msg:
        if colis and colis['x_studio_cloturee']:
            etat['msg'] = '🔒 %s clôturée%s · lecture seule : contenu affiché, bon de colisage réimprimable' % (
                colis['name'], (' → ' + colis['x_studio_zone']) if colis['x_studio_zone'] else '')
        elif colis:
            etat['msg'] = '📦 %s active — %s (%d OF)' % (
                colis['name'], ('palette de ' + colis['x_operateur_id'][1]) if colis['x_operateur_id']
                else 'palette vierge, elle sera au premier opérateur qui y pose', len(etat['items']))
        else:
            etat['msg'] = '👉 Scannez une palette (PACK…) pour commencer'
    return etat
""")
rep("""def _scan_palette(call, colis):
    if colis['x_studio_cloturee']:
        return _scan_etat(call, 0, '🔒 %s est clôturée : scannez une autre palette' % colis['name'], False)
    return _scan_etat(call, colis['id'])
""", """def _scan_palette(call, colis):
    return _scan_etat(call, colis['id'])   # clôturée : lecture seule (message par défaut)
""")
rep("""    colis = _colis_poste(call, colis_id)
    if not colis:
        return _scan_etat(call, 0, "⚠️ Scannez d'abord une palette (PACK…)", False)
    ops = _of_operateurs(call, of)""", """    colis = _colis_poste(call, colis_id)
    if not colis:
        return _scan_etat(call, 0, "⚠️ Scannez d'abord une palette (PACK…)", False)
    if colis['x_studio_cloturee']:
        return _scan_etat(call, colis['id'], '🔒 %s est clôturée : scannez une palette ouverte ou vierge pour poser %s' % (colis['name'], of['name']), False)
    ops = _of_operateurs(call, of)""")
rep("""    colis = _colis_poste(call, colis_id)
    if not colis:
        return _scan_etat(call, 0, '⚠️ Aucune palette active', False)
    items = _scan_items(call, colis)""", """    colis = _colis_poste(call, colis_id)
    if not colis:
        return _scan_etat(call, 0, '⚠️ Aucune palette active', False)
    if colis['x_studio_cloturee']:
        return _scan_etat(call, colis['id'], '🔒 %s est clôturée : rien ne peut être retiré (demandez au bureau)' % colis['name'], False)
    items = _scan_items(call, colis)""")
rep("""    colis = _colis_poste(call, colis_id)
    if not colis:
        return _scan_etat(call, 0, '⚠️ Aucune palette active à clôturer', False)
    if not zone:""", """    colis = _colis_poste(call, colis_id)
    if not colis:
        return _scan_etat(call, 0, '⚠️ Aucune palette active à clôturer', False)
    if colis['x_studio_cloturee']:
        return _scan_etat(call, colis['id'], '🔒 %s est déjà clôturée' % colis['name'], False)
    if not zone:""")
rep("""    return _scan_etat(call, 0, '✅ %s clôturée → %s · verrouillée · bon de colisage à imprimer' % (colis['name'], zone),
                      True, {'print_id': colis['id'], 'print_name': colis['name']})""",
    """    return _scan_etat(call, colis['id'], '✅ %s clôturée → %s · verrouillée · bon de colisage à imprimer' % (colis['name'], zone),
                      True, {'print_id': colis['id'], 'print_name': colis['name']})""")

# ── 2103 : alerte hebdo palettes ──
rep("""def _scan(call, ctx):
    colis_id = int(ctx.get('colis_id') or 0)""", """# ─── 2103 · Alerte hebdo palettes (bureau) ───────────────────────────────────

def _alerte_palettes(call, ctx):
    \"\"\"Pierres terminées non palettisées (par opérateur, > 2 jours, 30 derniers jours) et palettes
    ouvertes sans mouvement depuis 7 jours. ctx.envoyer=1 : mail à maquignon.palettes_alerte_email.\"\"\"
    import datetime as _dt
    import html as _html
    now = _dt.datetime.utcnow()
    d30 = (now - _dt.timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
    d2 = (now - _dt.timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
    ofs = call('mrp.production', 'search_read',
               [['state', '=', 'done'], ['company_id', '=', 1], ['x_studio_colis', '=', False],
                ['date_finished', '>=', d30], ['date_finished', '<=', d2]],
               fields=['name', 'x_studio_nbr', 'date_finished', 'x_studio_nom_du_client', 'workorder_ids'], limit=4000)
    reps = {}
    for r in call('x_repartition_palette', 'search_read', [['x_studio_of_id', 'in', [o['id'] for o in ofs]]],
                  fields=['x_studio_of_id', 'x_studio_qte'], limit=5000):
        reps[r['x_studio_of_id'][0]] = reps.get(r['x_studio_of_id'][0], 0) + int(r['x_studio_qte'] or 0)
    wo_ids = [w for o in ofs for w in o['workorder_ids']]
    wos = {w['id']: w for w in call('mrp.workorder', 'read', wo_ids, fields=['sequence', 'employee_assigned_ids'])} if wo_ids else {}
    par_op = {}
    for o in ofs:
        if reps.get(o['id'], 0) >= int(o['x_studio_nbr'] or 1):
            continue
        ops = []
        for wid in sorted(o['workorder_ids'], key=lambda i: ((wos.get(i) or {}).get('sequence') or 0, i), reverse=True):
            if wos.get(wid, {}).get('employee_assigned_ids'):
                ops = wos[wid]['employee_assigned_ids']
                break
        cle = ops[0] if ops else 0
        par_op.setdefault(cle, []).append(o)
    noms = {e['id']: e['name'] for e in call('hr.employee', 'read', [k for k in par_op if k], fields=['name'])} if any(par_op) else {}
    noms[0] = 'Sans opérateur'
    # palettes dormantes
    pk = call('stock.package', 'search_read', [['x_studio_cloturee', '!=', True]],
              fields=['name', 'x_operateur_id', 'x_studio_tonnage'], limit=1000)
    ids = [q['id'] for q in pk]
    last, cnt = {}, {}
    for o in call('mrp.production', 'search_read', [['x_studio_colis', 'in', ids]], fields=['x_studio_colis', 'write_date'], limit=5000):
        cid = o['x_studio_colis'][0]; cnt[cid] = cnt.get(cid, 0) + 1; last[cid] = max(last.get(cid, ''), o['write_date'])
    for r in call('x_repartition_palette', 'search_read', [['x_studio_colis_id', 'in', ids]], fields=['x_studio_colis_id', 'write_date'], limit=5000):
        cid = r['x_studio_colis_id'][0]; cnt[cid] = cnt.get(cid, 0) + 1; last[cid] = max(last.get(cid, ''), r['write_date'])
    d7 = (now - _dt.timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    dorm = sorted([q for q in pk if cnt.get(q['id']) and last.get(q['id'], '') < d7], key=lambda q: last[q['id']])
    # HTML
    h = ['<p>Bonjour,</p><p>Point hebdomadaire palettes (généré automatiquement le %s).</p>' % now.strftime('%d/%m/%Y')]
    h.append('<h3>Pierres terminées depuis plus de 2 jours, pas (ou pas entièrement) sur palette — 30 derniers jours</h3>')
    if not par_op:
        h.append('<p>Aucune.</p>')
    for cle, lst in sorted(par_op.items(), key=lambda kv: -len(kv[1])):
        lst.sort(key=lambda o: o['date_finished'], reverse=True)
        pcs = sum(int(o['x_studio_nbr'] or 1) - reps.get(o['id'], 0) for o in lst)
        h.append('<p><b>%s</b> : %d OF (%d pierres)<br/><span style="color:#555">%s%s</span></p>' % (
            _html.escape(noms.get(cle, '?')), len(lst), pcs,
            ', '.join('%s (%s, %s)' % (o['name'], _html.escape(o['x_studio_nom_du_client'] or '-'), o['date_finished'][:10]) for o in lst[:8]),
            ' …' if len(lst) > 8 else ''))
    h.append('<h3>Palettes ouvertes sans mouvement depuis 7 jours</h3>')
    if not dorm:
        h.append('<p>Aucune.</p>')
    else:
        h.append('<ul>' + ''.join('<li><b>%s</b> — %s — %d OF, %.0f kg — dernier mouvement %s</li>' % (
            q['name'], _html.escape(q['x_operateur_id'][1] if q['x_operateur_id'] else 'sans opérateur'), cnt[q['id']],
            q['x_studio_tonnage'] or 0, last[q['id']][:10]) for q in dorm) + '</ul>')
    h.append('<p style="color:#777;font-size:12px">Rappel : tous les opérateurs n\\'ont pas de tablette ; ce point sert à repérer ce qui doit être palettisé au poste de scan ou régularisé au bureau.</p>')
    corps = ''.join(h)
    res = {'ok': 1, 'n_ops': len(par_op), 'n_of': sum(len(v) for v in par_op.values()), 'n_dormantes': len(dorm), 'html': corps}
    if ctx.get('envoyer'):
        dest = str(_param(call, 'maquignon.palettes_alerte_email', 'isabelle@maquignon.com') or '').strip()
        mid = _creer(call, 'mail.mail', {'subject': 'Palettes : point hebdo du %s' % now.strftime('%d/%m/%Y'),
                                        'email_to': dest, 'body_html': corps, 'auto_delete': False})
        _sur(lambda: call('mail.mail', 'send', [mid]))
        res['envoye_a'] = dest
    return res


def _scan(call, ctx):
    colis_id = int(ctx.get('colis_id') or 0)""")
rep("""    if mode == 'cloturer':
        return _scan_cloturer(call, colis_id, (ctx.get('zone') or '').strip())
    raise WebErreur('Mode inconnu : %s' % mode)""", """    if mode == 'cloturer':
        return _scan_cloturer(call, colis_id, (ctx.get('zone') or '').strip())
    if mode == 'transferer':
        return _transferer(call, ctx)
    raise WebErreur('Mode inconnu : %s' % mode)""")
rep("""            2101: _palettiser, 2102: _scan}[action_id](call, ctx)""",
    """            2101: _palettiser, 2102: _scan, 2103: _alerte_palettes}[action_id](call, ctx)""")
rep("""  2102  Poste de scan : palette active du poste, opérateur déduit de l'OF (scan, quantité, retrait, clôture)""",
    """  2102  Poste de scan : palette active du poste, opérateur déduit de l'OF (scan, quantité, retrait, clôture,
        palette clôturée en lecture seule, transfert par le responsable)
  2103  Alerte hebdo palettes : pierres non palettisées par opérateur, palettes dormantes (mail au bureau)""")
ast.parse(s); io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

# app.py : action 2103 autorisée + tâche hebdo (lundi 06:30 UTC)
a = 'ocr/app.py'; t = io.open(a, encoding='utf-8').read()
old = "    2102,  # poste de scan : palette active par opérateur (scan / quantité / retrait / clôture)\n}"
assert t.count(old) == 1
t = t.replace(old, "    2102,  # poste de scan : palette active du poste (scan / quantité / retrait / clôture / transfert)\n    2103,  # alerte hebdo palettes (bureau) — envoi manuel possible\n}")
old2 = "if ODOO_URL and ODOO_PASSWORD:\n    threading.Thread(target=_fab_dash_nightly, daemon=True).start()"
assert t.count(old2) == 1
t = t.replace(old2, """def _palettes_hebdo():
    \"\"\"Lundi 06:30 UTC : mail « Palettes : point hebdo » (web_actions 2103) au bureau.\"\"\"
    from datetime import timedelta
    while True:
        now = datetime.utcnow()
        nxt = now.replace(hour=6, minute=30, second=0, microsecond=0)
        while nxt <= now or nxt.weekday() != 0:
            nxt = nxt + timedelta(days=1)
        _time.sleep(max((nxt - now).total_seconds(), 60))
        try:
            import web_actions
            uid, models = odoo_connect()

            def call(model, method, *params, **kw):
                return x(models, uid, model, method, *params, **kw)
            res = web_actions.executer(call, 2103, {'envoyer': 1})
            app.logger.info(f"palettes hebdo: {res.get('n_of')} OF, {res.get('n_dormantes')} palettes dormantes -> {res.get('envoye_a')}")
        except Exception as e:
            app.logger.warning(f"palettes hebdo échoué: {e}")


if ODOO_URL and ODOO_PASSWORD:
    threading.Thread(target=_fab_dash_nightly, daemon=True).start()
    threading.Thread(target=_palettes_hebdo, daemon=True).start()""")
ast.parse(t); io.open(a, 'w', encoding='utf-8', newline='\n').write(t)
print('web_actions.py + app.py patchés')
