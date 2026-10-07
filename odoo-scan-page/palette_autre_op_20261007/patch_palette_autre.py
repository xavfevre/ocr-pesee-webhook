# -*- coding: utf-8 -*-
"""Pose sur la palette d'un autre opérateur, sur confirmation explicite de l'opérateur (Xavier, 07/10/2026).
Patch local de : ocr/web_actions.py (relais Render, actions 2101 tablette et 2102 poste de scan),
vue 7890 « Poste de scan » (vue_7890.BEFORE.xml -> vue_7890.AFTER.xml, JS inline échappé + copie lisible
scan_view_7890.js) et vue 7907 « Vue Opérateur » (vue_7907.BEFORE.xml -> vue_7907.AFTER.xml).
Rien n'est envoyé à Odoo ici : voir deploy_palette_autre.py.   python patch_palette_autre.py"""
import io, os, sys, ast
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(HERE, '..', '..'))          # dossier ocr/


def lire(p):
    return io.open(p, encoding='utf-8', newline='').read()


def ecrire(p, s):
    io.open(p, 'w', encoding='utf-8', newline='').write(s)


def ecrire_comme(p, s):
    """Écrit s dans p en conservant le style de fin de ligne déjà utilisé par p (archives du dépôt en CRLF)."""
    if os.path.exists(p) and '\r\n' in lire(p):
        s = s.replace('\r\n', '\n').replace('\n', '\r\n')
    ecrire(p, s)


def remplacer(s, old, new, n=1, nom=''):
    assert s.count(old) == n, 'ancre %s trouvée %d fois (attendu %d) : %r' % (nom, s.count(old), n, old[:80])
    return s.replace(old, new)


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# ───────────────────────────── 1. relais Render : web_actions.py ─────────────────────────────
p = os.path.join(R, 'web_actions.py'); s = lire(p)
assert '\r\n' not in s
if 'confirme_autre' in s:
    print('web_actions.py : déjà patché')
else:
    old = """    _verif_of(of, colis)
    _colis_prendre(call, colis, emp)
    msg, res = _poser(call, of, colis, int(ctx.get('qte') or 0))
    res['msg'] = msg
"""
    new = """    _verif_of(of, colis)
    prop = colis['x_operateur_id']
    autre = bool(prop and prop[0] != emp['id'])
    if autre and colis['x_studio_cloturee']:
        raise WebErreur('🔒 %s est clôturée : prenez une autre palette.' % colis['name'])
    if autre and not int(ctx.get('confirme_autre') or 0):
        # Palette d'un autre opérateur (Xavier, 07/10/2026) : plus de refus sec, on demande à l'opérateur de
        # confirmer sur la tablette ; rien n'est écrit tant qu'il n'a pas répondu « Oui, poser ».
        total, lignes, place, dispo = _disponible(call, of)
        q = max(1, min(int(ctx.get('qte') or 0) or dispo, dispo))
        return {'confirmer': 1, 'colis_id': colis['id'], 'colis': colis['name'], 'proprietaire': prop[1],
                'of': of['name'], 'qte': q, 'total': total,
                'msg': '⚠️ %s est la palette de %s — confirmation demandée' % (colis['name'], prop[1])}
    if autre:
        _colis_co_operateur(call, colis, emp)
    else:
        _colis_prendre(call, colis, emp)
    msg, res = _poser(call, of, colis, int(ctx.get('qte') or 0))
    if autre:
        msg += ' — palette de %s (posé par %s, confirmé)' % (prop[1], emp['name'])
        res['autre'] = 1
        res['proprietaire'] = prop[1]
        _sur(lambda: call('stock.package', 'message_post', [colis['id']],
                          body='🤝 %d pcs de %s posées par %s sur la palette de %s (confirmé sur la tablette)'
                               % (res['qte'], of['name'], emp['name'], prop[1])))
    res['msg'] = msg
"""
    s = remplacer(s, old, new, nom='_palettiser')
    old = """def _colis_active(call, emp):"""
    new = """def _colis_co_operateur(call, colis, emp):
    \"\"\"Pose confirmée sur la palette d'un autre opérateur : il devient co-opérateur de la palette
    (x_operateur_ids) ; le responsable (x_operateur_id) et la palette active de chacun ne changent pas.\"\"\"
    if emp['id'] not in (colis['x_operateur_ids'] or []):
        call('stock.package', 'write', [colis['id']], {'x_operateur_ids': [[4, emp['id']]]})
        colis['x_operateur_ids'] = (colis['x_operateur_ids'] or []) + [emp['id']]


def _colis_active(call, emp):"""
    s = remplacer(s, old, new, nom='_colis_co_operateur')
    # poste de scan
    old = """def _scan_of(call, colis_id, of, qte, force):
    colis = _colis_poste(call, colis_id)
    if not colis:
        return _scan_etat(call, 0, "⚠️ Scannez d'abord une palette (PACK…)", False)
    if colis['x_studio_cloturee']:
        return _scan_etat(call, colis['id'], '🔒 %s est clôturée : scannez une palette ouverte ou vierge pour poser %s' % (colis['name'], of['name']), False)
    ops = _of_operateurs(call, of)
    prop = colis['x_operateur_id']
    if prop and ops and prop[0] not in ops:
        noms = ', '.join(e['name'] for e in call('hr.employee', 'read', ops, fields=['name']))
        return _scan_etat(call, colis['id'], '⛔ %s est la palette de %s — cette pierre est de %s : scannez sa palette ou une palette vierge'
                          % (colis['name'], prop[1], noms), False)
    total = int(of['x_studio_nbr'] or 1)
    if not force and not qte and total > 1:
        try:
            _verif_of(of, colis)
            total, lignes, place, dispo = _disponible(call, of)
        except WebErreur as e:
            return _scan_etat(call, colis['id'], str(e), False)
        return _scan_etat(call, colis['id'], '✂️ %s : combien de pièces sur %s ?' % (of['name'], colis['name']), True,
                          {'demande_qte': {'of_id': of['id'], 'name': of['name'], 'total': total,
                                           'remaining': dispo, 'placed': place, 'note': of['x_note_atelier'] or ''}})
    try:
        msg, res = _poser(call, of, colis, qte)
    except WebErreur as e:
        return _scan_etat(call, colis['id'], str(e), False)
    if ops:
"""
    new = """def _scan_of(call, colis_id, of, qte, force, autre_ok=False):
    colis = _colis_poste(call, colis_id)
    if not colis:
        return _scan_etat(call, 0, "⚠️ Scannez d'abord une palette (PACK…)", False)
    if colis['x_studio_cloturee']:
        return _scan_etat(call, colis['id'], '🔒 %s est clôturée : scannez une palette ouverte ou vierge pour poser %s' % (colis['name'], of['name']), False)
    ops = _of_operateurs(call, of)
    prop = colis['x_operateur_id']
    autre = bool(prop and ops and prop[0] not in ops)
    noms = ''
    if autre:
        noms = ', '.join(e['name'] for e in call('hr.employee', 'read', ops, fields=['name']))
        if not autre_ok:
            # Palette d'un autre opérateur (Xavier, 07/10/2026) : la pose reste possible, mais sur confirmation
            # explicite (bouton « Poser quand même ») ; rien n'est écrit avant.
            return _scan_etat(call, colis['id'], '⛔ %s est la palette de %s — cette pierre est de %s : scannez sa palette ou une palette vierge, ou confirmez « Poser quand même »'
                              % (colis['name'], prop[1], noms), False,
                              {'demande_autre': {'of_id': of['id'], 'name': of['name'], 'qte': int(qte or 0),
                                                 'colis': colis['name'], 'proprietaire': prop[1], 'pour': noms}})
    total = int(of['x_studio_nbr'] or 1)
    if not force and not qte and total > 1:
        try:
            _verif_of(of, colis)
            total, lignes, place, dispo = _disponible(call, of)
        except WebErreur as e:
            return _scan_etat(call, colis['id'], str(e), False)
        return _scan_etat(call, colis['id'], '✂️ %s : combien de pièces sur %s ?' % (of['name'], colis['name']), True,
                          {'demande_qte': {'of_id': of['id'], 'name': of['name'], 'total': total,
                                           'remaining': dispo, 'placed': place, 'note': of['x_note_atelier'] or '',
                                           'autre_ok': 1 if autre_ok else 0}})
    try:
        msg, res = _poser(call, of, colis, qte)
    except WebErreur as e:
        return _scan_etat(call, colis['id'], str(e), False)
    if autre:
        nouveaux = [[4, e] for e in ops if e not in (colis['x_operateur_ids'] or [])]
        if nouveaux:
            call('stock.package', 'write', [colis['id']], {'x_operateur_ids': nouveaux})
        msg += ' — palette de %s, pierre de %s (confirmé)' % (prop[1], noms)
        _sur(lambda: call('stock.package', 'message_post', [colis['id']],
                          body='🤝 %d pcs de %s (pierre de %s) posées sur la palette de %s (confirmé au poste de scan)'
                               % (res['qte'], of['name'], noms, prop[1])))
    elif ops:
"""
    s = remplacer(s, old, new, nom='_scan_of')
    old = """        return _scan_of(call, colis_id, of, int(ctx.get('qte') or 0), True)
    if mode == 'retirer_dernier':
"""
    new = """        return _scan_of(call, colis_id, of, int(ctx.get('qte') or 0), True, bool(int(ctx.get('autre_ok') or 0)))
    if mode == 'placer_autre':
        # confirmation « Poser quand même » sur la palette d'un autre opérateur (quantité demandée ensuite si besoin)
        of = _of_lire(call, int(ctx.get('of_id') or 0))
        if not of:
            return _scan_etat(call, colis_id, '❌ OF introuvable', False)
        return _scan_of(call, colis_id, of, int(ctx.get('qte') or 0), False, True)
    if mode == 'retirer_dernier':
"""
    s = remplacer(s, old, new, nom='dispatcher placer')
    old = "# opération renseignée). Une palette libre devient celle de cet opérateur, la\n# palette d'un autre opérateur est refusée. La tablette (2101) garde le nom.\n"
    new = ("# opération renseignée). Une palette libre devient celle de cet opérateur ; la\n"
           "# palette d'un autre opérateur n'est posée que sur confirmation explicite\n"
           "# (« Poser quand même », depuis le 07/10/2026). La tablette (2101) garde le nom.\n")
    s = remplacer(s, old, new, nom='commentaire 2102')
    old = "#    qui y a posé la première pierre ou l'a scannée vierge) ; personne d'autre\n#    ne peut y poser, en retirer ou la clôturer depuis les pages atelier ;\n"
    new = ("#    qui y a posé la première pierre ou l'a scannée vierge) ; un autre opérateur\n"
           "#    peut y poser une pierre seulement après confirmation explicite (07/10/2026),\n"
           "#    il devient alors co-opérateur (x_operateur_ids) ; retirer et clôturer\n"
           "#    restent au responsable / au bureau ;\n")
    s = remplacer(s, old, new, nom='commentaire règle')
    ast.parse(s)
    ecrire(p, s)
    print('web_actions.py : patché (syntaxe ok)')

# ───────────────────────────── 2. vue 7890 « Poste de scan » ─────────────────────────────
POP_HTML = """    <div id="autre-pop" class="qte-pop">
      <div class="qte-card" style="border-color:#f59e0b;">
        <h4>🤝 Palette d'un autre opérateur</h4>
        <div id="autre-txt" style="color:#fde68a;text-align:center;font-weight:800;font-size:17px;margin:6px 0 10px;line-height:1.35;">—</div>
        <div style="color:#94a3b8;text-align:center;font-size:13px;margin-bottom:12px;">La palette reste celle de son opérateur, la pose sera notée dessus. Scannez une autre palette pour annuler.</div>
        <div style="display:flex;gap:8px;">
          <button id="autre-ok" class="qte-ok" style="background:#d97706;">✅ Poser quand même</button>
          <button id="autre-cancel" class="qte-cancel">✖ Non</button>
        </div>
      </div>
    </div>
"""
JS_APPLY = "    if(r.demande_autre){ openAutre(r.demande_autre); }\n"
JS_PLACER_OLD = "    return act('placer', {of_id: p.of_id, qte: qty}).then(function(){ input.focus(); });\n"
JS_PLACER_NEW = "    return act('placer', {of_id: p.of_id, qte: qty, autre_ok: p.autre_ok || 0}).then(function(){ input.focus(); });\n"
JS_SCAN_OLD = "    val = (val || '').trim(); if(!val){ return; }\n"
JS_SCAN_NEW = JS_SCAN_OLD + "    if(pendingAutre){ closeAutre(); }\n"
JS_BLOCK = """  // ── pop-up « palette d'un autre opérateur » : pose seulement sur confirmation explicite (07/10/2026) ──
  var autrePop = document.getElementById('autre-pop'), autreTxt = document.getElementById('autre-txt'), pendingAutre = null;
  function openAutre(p){
    pendingAutre = p;
    autreTxt.textContent = p.colis + ' est la palette de ' + p.proprietaire + '. Poser quand même ' + p.name + (p.pour ? ' (pierre de ' + p.pour + ')' : '') + ' dessus ?';
    autrePop.style.display = 'flex'; input.focus();
  }
  function closeAutre(){ autrePop.style.display = 'none'; pendingAutre = null; }
  autrePop.addEventListener('mousedown', function(e){ if(e.target.tagName === 'BUTTON'){ e.preventDefault(); } });
  document.getElementById('autre-ok').addEventListener('click', function(){
    if(!pendingAutre){ return; }
    var p = pendingAutre; closeAutre();
    act('placer_autre', {of_id: p.of_id, qte: p.qte || 0}).then(function(){ input.focus(); });
  });
  document.getElementById('autre-cancel').addEventListener('click', function(){ closeAutre(); setRes('↩️ Pose annulée — scannez une autre palette'); input.focus(); });

"""
JS_ENTREE = "  // ── entrée principale : douchette, caméra, clavier ──\n"
for src, dst, escaped in ((os.path.join(HERE, 'vue_7890.BEFORE.xml'), os.path.join(HERE, 'vue_7890.AFTER.xml'), True),
                          (os.path.join(R, 'odoo-scan-page', 'scan_view_7890.js'), os.path.join(R, 'odoo-scan-page', 'scan_view_7890.js'), False)):
    s = lire(src)
    if 'autre-pop' in s or 'pendingAutre' in s:
        print(os.path.basename(dst), ': déjà patché'); continue
    nl = '\r\n' if '\r\n' in s else '\n'      # la copie lisible .js peut être en CRLF
    e = (lambda t: esc(t).replace('\n', nl)) if escaped else (lambda t: t.replace('\n', nl))
    if escaped:
        s = remplacer(s, '    <div id="qte-pop" class="qte-pop">\n', POP_HTML + '    <div id="qte-pop" class="qte-pop">\n', nom='html qte-pop')
    s = remplacer(s, e("    if(r.demande_qte){ openPop(r.demande_qte); }\n"), e("    if(r.demande_qte){ openPop(r.demande_qte); }\n") + e(JS_APPLY), nom='applyEtat')
    s = remplacer(s, e(JS_PLACER_OLD), e(JS_PLACER_NEW), nom='placer')
    s = remplacer(s, e(JS_SCAN_OLD), e(JS_SCAN_NEW), nom='doScan')
    s = remplacer(s, e(JS_ENTREE), e(JS_BLOCK) + e(JS_ENTREE), nom='bloc autre')
    ecrire(dst, s)
    print(os.path.basename(dst), ': patché (%d car.)' % len(s))
# archive « dernière version » à la racine d'odoo-scan-page
ecrire_comme(os.path.join(R, 'odoo-scan-page', 'scan_view_7890.AFTER.xml'), lire(os.path.join(HERE, 'vue_7890.AFTER.xml')))

# ───────────────────────────── 3. vue 7907 « Vue Opérateur » (tablette) ─────────────────────────────
src, dst = os.path.join(HERE, 'vue_7907.BEFORE.xml'), os.path.join(HERE, 'vue_7907.AFTER.xml')
s = lire(src)
if 'voConfirmAutre' in s:
    print('vue_7907.AFTER.xml : déjà patché')
else:
    CONFIRM = r"""          // pose sur la palette d'un autre opérateur : confirmation explicite de l'opérateur (Xavier, 07/10/2026)
          window.voConfirmAutre = function(r, onYes){
            function h(t){ var d=document.createElement('div'); d.textContent=(t==null?'':String(t)); return d.innerHTML; }
            var old=document.getElementById('vo-autre-pop'); if(old){ old.remove(); }
            var ov=document.createElement('div'); ov.id='vo-autre-pop';
            ov.style.cssText='position:fixed;inset:0;background:rgba(2,6,23,.82);z-index:100000;display:flex;align-items:center;justify-content:center;padding:16px;';
            ov.innerHTML='<div style="background:#fff;border:3px solid #f59e0b;border-radius:18px;padding:20px;width:460px;max-width:96vw;box-shadow:0 20px 60px rgba(0,0,0,.5);">'
              +'<div style="font-size:22px;font-weight:900;color:#b45309;text-align:center;margin-bottom:10px;">🤝 Palette d\'un autre opérateur</div>'
              +'<div style="font-size:18px;font-weight:800;color:#0f172a;text-align:center;line-height:1.4;">'+h(r.colis)+' est la palette de <span style="color:#b45309;">'+h(r.proprietaire)+'</span>.<br/>Poser quand même <b>'+h(r.qte||'')+' pièce'+((r.qte||0)>1?'s':'')+'</b> de '+h(r.of)+' dessus ?</div>'
              +'<div style="font-size:13px;color:#64748b;text-align:center;margin:10px 0 14px;">La palette reste celle de '+h(r.proprietaire)+'. Votre pose sera notée sur la palette.</div>'
              +'<div style="display:flex;gap:10px;"><button type="button" id="vo-autre-oui" style="flex:2;background:#d97706;color:#fff;border:none;border-radius:12px;padding:16px;font-size:18px;font-weight:900;">✅ Oui, poser</button>'
              +'<button type="button" id="vo-autre-non" style="flex:1;background:#e2e8f0;color:#0f172a;border:none;border-radius:12px;padding:16px;font-size:18px;font-weight:800;">✖ Non</button></div></div>';
            document.body.appendChild(ov);
            ov.querySelector('#vo-autre-non').onclick=function(){ ov.remove(); };
            ov.querySelector('#vo-autre-oui').onclick=function(){ ov.remove(); onYes(); };
          };
"""
    s = remplacer(s, "          function saveLast(cid,cname,ton){ lastColis={id:cid,name:cname,ton:ton||0}; }\n",
                  esc(CONFIRM) + "          function saveLast(cid,cname,ton){ lastColis={id:cid,name:cname,ton:ton||0}; }\n", nom='saveLast')
    # assign (Ma production) : paramètre okAutre, confirmation, palette rapide inchangée
    s = remplacer(s, "          function assign(ofid, cid, cname, btn, after){\n            var ctx={of_id:ofid, qte:(voQteH||0), op:(parseInt(op)||0)}; if(cid){ ctx.colis_id=cid; } else { ctx.colis_name=cname; }\n",
                  "          function assign(ofid, cid, cname, btn, after, okAutre){\n            var ctx={of_id:ofid, qte:(voQteH||0), op:(parseInt(op)||0)}; if(cid){ ctx.colis_id=cid; } else { ctx.colis_name=cname; } if(okAutre){ ctx.confirme_autre=1; }\n", nom='assign')
    s = remplacer(s, "\n              var r=d.result||{};\n",
                  "\n              var r=d.result||{};\n              if(r.confirmer){ voConfirmAutre(r, function(){ assign(ofid, cid, cname, btn, after, 1); }); return; }\n", nom='assign result')
    s = remplacer(s, "              saveLast(r.colis_id||cid, r.colis||cname, r.colis_ton);\n",
                  "              if(!r.autre){ saveLast(r.colis_id||cid, r.colis||cname, r.colis_ton); }\n", nom='assign saveLast')
    # assignC (choix de palette) : idem
    s = remplacer(s, "        function assignC(ofid, cid, cname, card, after){\n          var ctx={of_id:ofid, qte:(voQte||0), op:(parseInt(op)||0)}; if(cid){ ctx.colis_id=cid; } else { ctx.colis_name=cname; }\n",
                  "        function assignC(ofid, cid, cname, card, after, okAutre){\n          var ctx={of_id:ofid, qte:(voQte||0), op:(parseInt(op)||0)}; if(cid){ ctx.colis_id=cid; } else { ctx.colis_name=cname; } if(okAutre){ ctx.confirme_autre=1; }\n", nom='assignC')
    s = remplacer(s, "\n            var r=d.result||{};\n",
                  "\n            var r=d.result||{};\n            if(r.confirmer){ voConfirmAutre(r, function(){ assignC(ofid, cid, cname, card, after, 1); }); return; }\n", nom='assignC result')
    s = remplacer(s, "            if(r.colis_id){ saveLastC(r.colis_id, r.colis||cname, r.colis_ton); }\n",
                  "            if(r.colis_id &amp;&amp; !r.autre){ saveLastC(r.colis_id, r.colis||cname, r.colis_ton); }\n", nom='assignC saveLast')
    ecrire(dst, s)
    ecrire_comme(os.path.join(R, 'odoo-scan-page', 'vue_operateur.xml'), s)
    print('vue_7907.AFTER.xml : patché (%d car.)' % len(s))
print('patch terminé')
