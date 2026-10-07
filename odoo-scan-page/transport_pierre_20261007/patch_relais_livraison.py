# -*- coding: utf-8 -*-
"""Phase 4 « suivi livraison » (07/10/2026) :
 - relais 2104 : modes `livrer` (palettes ou chargement -> Livrée, date, notes commande/tâche), `a_livrer` (palettes chargées
   sur nos camions, pour « Ma tournée »), `lots` enrichi (statut par palette, livré le…), `annuler` d'une livraison ;
 - « Ma tournée » (app.py) : bloc « Palettes à livrer » par mission (même camion, même client) avec bouton « 📍 Livrées »,
   route POST /tournee/livraison signée (jeton de la mission, type livr).
  python patch_relais_livraison.py"""
import io, os, sys, ast
sys.stdout.reconfigure(encoding='utf-8')
R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
lire = lambda p: io.open(p, encoding='utf-8', newline='').read()
ecrire = lambda p, s: io.open(p, 'w', encoding='utf-8', newline='').write(s)


def rep(s, old, new, n=1, nom=''):
    assert s.count(old) == n, 'ancre %s : %d (attendu %d) %r' % (nom, s.count(old), n, old[:80])
    return s.replace(old, new)


# ───────────── web_actions.py ─────────────
p = os.path.join(R, 'web_actions.py'); s = lire(p)
if '_exp_livrer(' in s:
    print('web_actions.py : déjà patché')
else:
    BLOC = r'''
def _exp_livrer(call, ctx):
    """Palettes livrées : par ids ou par n° de chargement ; statut Livrée + date ; notes commande et tâche."""
    ids = [int(i) for i in (ctx.get('palettes') or []) if int(i)]
    lot = (ctx.get('lot') or '').strip()
    if lot and not ids:
        ids = call('stock.package', 'search', [['x_exp_lot', '=', lot], ['x_exp_statut', 'in', ['chargee', 'enlevee']]])
    if not ids:
        raise WebErreur('Aucune palette à livrer.')
    qui = (ctx.get('qui') or '').strip()[:80]
    source = {'tournee': 'par le chauffeur', 'expedition': "depuis l'écran Expédition", 'bureau': 'saisi au bureau'}.get(ctx.get('source') or '', '')
    local, utc = _exp_maintenant()
    quand = utc.strftime('%Y-%m-%d %H:%M:%S')
    if ctx.get('date'):
        try:
            import datetime as _dt
            quand = _dt.datetime.strptime(str(ctx['date'])[:10], '%Y-%m-%d').strftime('%Y-%m-%d 10:00:00')
        except Exception:  # noqa: BLE001
            pass
    palettes = []
    for i in ids:
        colis = _exp_lire(call, colis_id=i)
        if not colis:
            raise WebErreur('Palette introuvable (%s).' % i)
        if (colis.get('x_exp_statut') or '') not in ('chargee', 'enlevee'):
            raise WebErreur("%s n'est pas en cours de livraison (statut : %s)." % (colis['name'], colis.get('x_exp_statut') or 'en stock'))
        palettes.append(_exp_palette(call, colis))
    call('stock.package', 'write', [p['id'] for p in palettes], {'x_exp_statut': 'livree', 'x_livraison_date': quand})
    par_cde = {}
    for p in palettes:
        par_cde.setdefault(p['commande_id'], []).append(p)
    for so_id, grp in par_cde.items():
        noms = ', '.join(p['name'] for p in grp)
        if not so_id:
            continue
        so = call('sale.order', 'read', [so_id], fields=['name'])[0]
        reste_of = call('mrp.production', 'search_count', [['origin', '=', so['name']], ['state', 'not in', ['done', 'cancel']]])
        reste_pal = call('stock.package', 'search_count', [['x_commande_id', '=', so_id], ['x_studio_cloturee', '=', True], '|', ['x_exp_statut', '=', False], ['x_exp_statut', 'not in', ['livree', 'enlevee']]])
        etat = 'commande entièrement livrée' if (reste_of == 0 and reste_pal == 0) else ('livraison partielle : %d OF en fabrication, %d palette(s) pas encore livrée(s)' % (reste_of, reste_pal))
        _note(call, 'sale.order', so_id, '📍 Livraison le %s : %s%s%s — %s.' % (local.strftime('%d/%m/%Y %H:%M') if not ctx.get('date') else str(ctx['date'])[:10], noms, (' (chargement %s)' % grp[0]['exp_lot']) if grp[0].get('exp_lot') else '', (' — %s %s' % (source, qui)).rstrip() if (source or qui) else '', etat))
        tache = next((p['tache_id'] for p in grp if p['tache_id']), 0)
        if tache:
            _note(call, 'project.task', tache, '📍 Livré : %s (%s)' % (noms, etat))
    return {'ok': 1, 'n': len(palettes), 'msg': '📍 %d palette(s) livrée(s) : %s' % (len(palettes), ', '.join(p['name'] for p in palettes))}


def _exp_a_livrer(call, ctx):
    """Palettes chargées sur nos camions (statut Chargée, mode camions) pour les camions donnés, depuis N jours :
    pour « Ma tournée » (rapprochées des missions par camion et client)."""
    import datetime as _dt
    camions = [c for c in (ctx.get('camions') or []) if c]
    jours = int(ctx.get('jours') or 7)
    depuis = (_dt.datetime.utcnow() - _dt.timedelta(days=jours)).strftime('%Y-%m-%d 00:00:00')
    if not camions:
        return {'palettes': []}
    rows = call('stock.package', 'search_read', [['x_exp_statut', '=', 'chargee'], ['x_exp_mode', '=', 'camions'], ['x_exp_camion', 'in', camions], ['x_exp_date', '>=', depuis]],
                fields=EXP_CHAMPS, order='x_exp_date, name')
    out = []
    for c in rows:
        p = _exp_palette(call, c)
        comm = 0
        if p['commande_id']:
            so = call('sale.order', 'read', [p['commande_id']], fields=['partner_id'])[0]
            if so['partner_id']:
                comm = call('res.partner', 'read', [so['partner_id'][0]], fields=['commercial_partner_id'])[0]['commercial_partner_id'][0]
        out.append({'id': p['id'], 'name': p['name'], 'client': p['client'], 'commande': p['commande'], 'adresse': p['adresse'], 'ton': p['ton'],
                    'camion': c.get('x_exp_camion') or '', 'lot': c.get('x_exp_lot') or '', 'date': (c.get('x_exp_date') or '')[:10], 'partner_commercial_id': comm})
    return {'palettes': out}

'''
    s = rep(s, "\n\ndef _expedition(call, ctx):", BLOC + "\n\ndef _expedition(call, ctx):", nom='bloc livrer')
    # dispatcher
    s = rep(s, """    if mode == 'lots':
        return _exp_lots(call, ctx.get('jours') or 3)
    if mode == 'bl_plan':""", """    if mode == 'lots':
        return _exp_lots(call, ctx.get('jours') or 3)
    if mode == 'livrer':
        return _exp_livrer(call, ctx)
    if mode == 'a_livrer':
        return _exp_a_livrer(call, ctx)
    if mode == 'bl_plan':""", nom='dispatcher')
    # lots : statut par palette, livraison
    s = rep(s, """        l['n'] += 1; l['ton'] += round(c['x_studio_tonnage'] or 0); l['palettes'].append({'id': c['id'], 'name': c['name']})""",
            """        l['n'] += 1; l['ton'] += round(c['x_studio_tonnage'] or 0)
        l['palettes'].append({'id': c['id'], 'name': c['name'], 'statut': c.get('x_exp_statut') or '', 'livraison': (c.get('x_livraison_date') or '')[:16]})
        if (c.get('x_exp_statut') or '') == 'livree':
            l['livrees'] = l.get('livrees', 0) + 1""", nom='lots statut')
    s = rep(s, """    rows = call('stock.package', 'search_read', [['x_exp_lot', '!=', False], ['x_exp_statut', 'in', list(EXP_PARTIS)], ['x_exp_date', '>=', depuis]],
                fields=EXP_CHAMPS, order='x_exp_date desc, name')""",
            """    rows = call('stock.package', 'search_read', [['x_exp_lot', '!=', False], ['x_exp_statut', 'in', list(EXP_PARTIS)], ['x_exp_date', '>=', depuis]],
                fields=EXP_CHAMPS + ['x_livraison_date'], order='x_exp_date desc, name')""", nom='lots champs')
    # annuler : une livraison redevient « chargée », un départ redevient « en stock »
    s = rep(s, """    if (colis.get('x_exp_statut') or '') not in ('chargee', 'enlevee'):
        raise WebErreur("%s n'est pas en cours d'expédition (statut : %s)." % (colis['name'], colis.get('x_exp_statut') or 'en stock'))
    lot = colis.get('x_exp_lot') or ''""",
            """    if (colis.get('x_exp_statut') or '') == 'livree':
        retour = 'enlevee' if colis.get('x_exp_mode') == 'client' else 'chargee'
        call('stock.package', 'write', [colis['id']], {'x_exp_statut': retour, 'x_livraison_date': False})
        if colis.get('x_commande_id'):
            _note(call, 'sale.order', colis['x_commande_id'][0], '↩️ Livraison annulée pour %s : la palette est de nouveau « %s ».' % (colis['name'], 'enlevée' if retour == 'enlevee' else 'chargée'))
        return {'ok': 1, 'msg': '↩️ Livraison de %s annulée (palette de nouveau %s)' % (colis['name'], 'enlevée' if retour == 'enlevee' else 'chargée')}
    if (colis.get('x_exp_statut') or '') not in ('chargee', 'enlevee'):
        raise WebErreur("%s n'est pas en cours d'expédition (statut : %s)." % (colis['name'], colis.get('x_exp_statut') or 'en stock'))
    lot = colis.get('x_exp_lot') or ''""", nom='annuler livraison')
    ast.parse(s); ecrire(p, s); print('web_actions.py : livrer / a_livrer / lots / annuler livraison')

# ───────────── app.py : Ma tournée ─────────────
p = os.path.join(R, 'app.py'); s = lire(p)
if 'tournee/livraison' in s:
    print('app.py : déjà patché')
else:
    # 1. palettes à livrer, rapprochées des missions (même camion ; même client si connu)
    s = rep(s, """        html = f'<div class="drv"><span>👤 {_esc(dname)}</span></div>'
        if not tasks:""", """        # palettes chargées sur les camions de la tournée (expédition pierre), à livrer
        palmap, pal_reste = {}, {}
        try:
            import web_actions
            def _call(model, method, *params, **kw):
                return x(models, uid, model, method, *params, **kw)
            camions = sorted({t["x_studio_transport"][1] for t in tasks if t.get("x_studio_transport")})
            pals = web_actions.executer(_call, 2104, {"mode": "a_livrer", "camions": camions, "jours": 7}).get("palettes", []) if camions else []
            if pals:
                pmap = {}
                pids = sorted({t["partner_id"][0] for t in tasks if t.get("partner_id")})
                for pr in x(models, uid, "res.partner", "read", pids, fields=["commercial_partner_id"]) if pids else []:
                    pmap[pr["id"]] = pr["commercial_partner_id"][0] if pr.get("commercial_partner_id") else pr["id"]
                pris = set()
                for t in tasks:
                    cam = t["x_studio_transport"][1] if t.get("x_studio_transport") else ""
                    comm = pmap.get(t["partner_id"][0]) if t.get("partner_id") else 0
                    for pl in pals:
                        if pl["id"] in pris or pl["camion"] != cam:
                            continue
                        if pl["partner_commercial_id"] and comm and pl["partner_commercial_id"] == comm:
                            palmap.setdefault(t["id"], []).append(pl); pris.add(pl["id"])
                for pl in pals:
                    if pl["id"] not in pris:
                        pal_reste.setdefault(pl["camion"], []).append(pl)
        except Exception as e:  # noqa: BLE001 — la tournée s'affiche même sans les palettes
            app.logger.warning(f"ma-tournee palettes: {e}")

        html = f'<div class="drv"><span>👤 {_esc(dname)}</span></div>'
        if not tasks:""", nom='palettes tournée')
    # 2. bloc par mission (avant les photos)
    s = rep(s, """            if ocr:
                html += f'<div class="ocr">{_esc(ocr)}</div>'
            lblbon = """, """            if ocr:
                html += f'<div class="ocr">{_esc(ocr)}</div>'
            pls = list(palmap.get(t["id"], []))
            cam_t = t["x_studio_transport"][1] if t.get("x_studio_transport") else ""
            if cam_t and pal_reste.get(cam_t) and cam_t not in reste_affiche:
                pls += [dict(pl, autre=1) for pl in pal_reste[cam_t]]; reste_affiche.add(cam_t)
            if pls:
                ids_js = ",".join(str(pl["id"]) for pl in pls)
                html += '<div class="pal"><b>📦 Palettes à livrer</b>'
                for pl in pls:
                    html += (f'<div class="palrow">{_esc(pl["name"])} — {_esc(pl["client"])}'
                             f'{(" · " + _esc(pl["commande"])) if pl.get("commande") else ""} · {pl["ton"]} kg'
                             f'{" <i>(autre client, même camion)</i>" if pl.get("autre") else ""}</div>')
                html += (f'<button type="button" class="palbtn" onclick="livrer({t["id"]},[{ids_js}],'
                         f'\\'{_tournee_sign(t["id"], "livr")}\\')">📍 Palettes livrées</button></div>')
            lblbon = """, nom='bloc palettes')
    s = rep(s, """        cur_day = None
        for t in tasks:
            try:
                dt = datetime.strptime(t["planned_date_begin"], "%Y-%m-%d %H:%M:%S")""", """        cur_day = None
        reste_affiche = set()
        for t in tasks:
            try:
                dt = datetime.strptime(t["planned_date_begin"], "%Y-%m-%d %H:%M:%S")""", nom='reste_affiche')
    # 3. style + JS
    s = rep(s, """.day.tod{color:#01666B;border-color:#01666B;}""", """.day.tod{color:#01666B;border-color:#01666B;}
.pal{background:#ecfeff;border:1px solid #67e8f9;border-radius:10px;padding:8px 10px;margin:8px 0;font-size:14px;}
.palrow{padding:2px 0;color:#0f172a;} .palrow i{color:#64748b;font-size:12px;}
.palbtn{margin-top:6px;width:100%;border:none;border-radius:10px;padding:12px;font-size:16px;font-weight:800;background:#0e7490;color:#fff;}""", nom='css tournée')
    s = rep(s, """function up(inp,tid,kind,tok){""", """function livrer(tid,ids,tok){
  if(!confirm('Confirmer la livraison de ces '+ids.length+' palette(s) ?')){ return; }
  fetch('/tournee/livraison',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task_id:tid,token:tok,palettes:ids})})
    .then(function(r){return r.json();}).then(function(d){ if(!d.ok){ throw new Error(d.error||'refus'); } toast('✅ '+(d.msg||'Livraison enregistrée')); setTimeout(function(){ location.reload(); }, 900); })
    .catch(function(e){ toast('⚠️ '+e.message); });
}
function up(inp,tid,kind,tok){""", nom='js livrer')
    # 4. route
    s = rep(s, """@app.route("/tournee/upload", methods=["POST"])
def tournee_upload():""", """@app.route("/tournee/livraison", methods=["POST"])
def tournee_livraison():
    \"\"\"Chauffeur : palettes livrées (jeton de la mission, type livr) -> relais 2104 mode livrer.\"\"\"
    try:
        data = request.get_json(force=True)
        task_id = int(data.get("task_id"))
        token = data.get("token")
        ids = [int(i) for i in (data.get("palettes") or [])]
        if not token or not hmac.compare_digest(token, _tournee_sign(task_id, "livr")):
            return jsonify({"ok": False, "error": "jeton invalide"}), 403
        if not ids:
            return jsonify({"ok": False, "error": "aucune palette"}), 400
        uid, models = odoo_connect()
        def _call(model, method, *params, **kw):
            return x(models, uid, model, method, *params, **kw)
        t = x(models, uid, "project.task", "read", [task_id], fields=["x_studio_chauffeur", "name"])[0]
        qui = t["x_studio_chauffeur"][1] if t.get("x_studio_chauffeur") else ""
        import web_actions
        try:
            res = web_actions.executer(_call, 2104, {"mode": "livrer", "palettes": ids, "qui": qui, "source": "tournee"})
        except web_actions.WebErreur as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify({"ok": True, "msg": res.get("msg", "")})
    except Exception as e:
        app.logger.error(f"Erreur tournee-livraison: {e}")
        return jsonify({"ok": False, "error": str(e)[:150]}), 500


@app.route("/tournee/upload", methods=["POST"])
def tournee_upload():""", nom='route livraison')
    ast.parse(s); ecrire(p, s); print('app.py : Ma tournée (palettes à livrer, bouton, route /tournee/livraison)')
