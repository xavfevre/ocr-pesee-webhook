# -*- coding: utf-8 -*-
"""Récup / sans solde « de telle heure à telle heure » sur la page salarié :
 - relais 2012 : hj_recup_de/hj_recup_a et hj_ss_de/hj_ss_a (heures décimales) -> durée au quart d'heure, contrôle de
   chevauchement avec les heures travaillées, note automatique « Récup 16:00-17:45 · Sans solde 12:00-12:30 »
 - page 7956 : champs de/à sous chaque nombre d'heures ; le créneau saisi est retiré des heures travaillées et les heures
   se calculent ; préremplissage depuis la note ; créneau affiché dans l'état du jour."""
import io, sys
sys.stdout.reconfigure(encoding='utf-8')


def patch(path, pairs):
    s = io.open(path, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, s.count(old), old[:90])
        s = s.replace(old, new)
    io.open(path, 'w', encoding='utf-8', newline='\n').write(s)
    print(path, ': OK')


# ── relais ───────────────────────────────────────────────────────────────────
patch('ocr/heures_actions.py', [
    ('''def _fr(h):
    return ("%.2f" % h).replace(".", ",")
''', '''def _fr(h):
    return ("%.2f" % h).replace(".", ",")


def _hm(h):
    return "%02d:%02d" % (int(h), round((h - int(h)) * 60))
'''),
    ('''                if h_recup < 0 or h_ss < 0 or h_recup > 12 or h_ss > 12:
                    raise HeuresErreur("Heures de récup / sans solde : entre 0 et 12 h.")
                manque = max(theo - heures, 0.0)''',
     '''                # créneaux « de telle heure à telle heure » : la durée fait foi, note automatique
                plages = []
                for cle, lbl in (("recup", "Récup"), ("ss", "Sans solde")):
                    de, a = ctx.get("hj_%s_de" % cle), ctx.get("hj_%s_a" % cle)
                    if de in (None, "") or a in (None, ""):
                        continue
                    try:
                        de, a = float(de), float(a)
                    except (TypeError, ValueError):
                        raise HeuresErreur("Créneau de %s invalide." % lbl.lower())
                    if not (0.0 <= de < a <= 24.0):
                        raise HeuresErreur("%s : indiquez une heure de début avant l'heure de fin." % lbl)
                    for (h1, h2) in ((md, mf), (ad, af)):
                        if h2 > h1 and de < h2 and a > h1:
                            raise HeuresErreur("Le créneau %s de %s à %s chevauche vos heures travaillées (%s-%s). Corrigez les horaires."
                                               % (lbl.lower(), _hm(de), _hm(a), _hm(h1), _hm(h2)))
                    if cle == "recup":
                        h_recup = _quart(a - de)
                    else:
                        h_ss = _quart(a - de)
                    plages.append("%s %s-%s" % (lbl, _hm(de), _hm(a)))
                if plages:
                    note = " · ".join(plages)
                if h_recup < 0 or h_ss < 0 or h_recup > 12 or h_ss > 12:
                    raise HeuresErreur("Heures de récup / sans solde : entre 0 et 12 h.")
                manque = max(theo - heures, 0.0)'''),
])
import py_compile
py_compile.compile('ocr/heures_actions.py', doraise=True)

# ── page salarié ─────────────────────────────────────────────────────────────
patch('rh_patch_7956.py', [
    # CSS
    ("""    '      .mh-manque input{width:76px;margin-left:auto;border:1.5px solid #cbd5e1;border-radius:8px;padding:5px 6px;font-weight:800;text-align:center;font-size:15px;}',""",
     """    '      .mh-manque input[type=number]{width:76px;margin-left:auto;border:1.5px solid #cbd5e1;border-radius:8px;padding:5px 6px;font-weight:800;text-align:center;font-size:15px;}',
    '      .mh-plage{display:flex;align-items:center;gap:6px;font-size:12px;font-weight:700;color:#64748b;margin:0 0 6px 24px;flex-wrap:wrap;}',
    '      .mh-plage input[type=time]{border:1.5px solid #cbd5e1;border-radius:8px;padding:4px 5px;font-weight:700;font-size:13px;width:96px;}',"""),
    # carte : note en attribut + créneau dans l'état
    ("""t-att-data-heures="s and ('%.4f' % s.x_heures) or ''" t-att-data-hs="s and ('%.4f' % s.x_hs) or ''">""",
     """t-att-data-heures="s and ('%.4f' % s.x_heures) or ''" t-att-data-hs="s and ('%.4f' % s.x_hs) or ''" t-att-data-note="(s and s.x_note) or ''">"""),
    ("""<t t-if="s.x_h_sans_solde"> + 🚫 <t t-esc="('%.2f' % s.x_h_sans_solde).replace('.', ',')"/> h sans solde</t><t t-if="s.x_decouchage"> · 🛏</t></t>""",
     """<t t-if="s.x_h_sans_solde"> + 🚫 <t t-esc="('%.2f' % s.x_h_sans_solde).replace('.', ',')"/> h sans solde</t><t t-if="s.x_note and (s.x_note.startswith('Récup ') or s.x_note.startswith('Sans solde '))"> (<t t-esc="s.x_note"/>)</t><t t-if="s.x_decouchage"> · 🛏</t></t>"""),
    # bloc heures manquantes : créneaux de/à
    ("""                <label>🔄 Heures prises en récup
                  <input type="number" data-f="h_recup" step="0.25" min="0" max="12" placeholder="0" t-att-value="('%g' % s.x_h_recup) if (s and s.x_type == 'travail' and s.x_h_recup) else ''"/> h
                </label>
                <label>🚫 Heures sans solde (non payées)
                  <input type="number" data-f="h_ss" step="0.25" min="0" max="12" placeholder="0" t-att-value="('%g' % s.x_h_sans_solde) if (s and s.x_type == 'travail' and s.x_h_sans_solde) else ''"/> h
                </label>""",
     """                <label>🔄 Heures prises en récup
                  <input type="number" data-f="h_recup" step="0.25" min="0" max="12" placeholder="0" t-att-value="('%g' % s.x_h_recup) if (s and s.x_type == 'travail' and s.x_h_recup) else ''"/> h
                </label>
                <div class="mh-plage">ou de <input type="time" data-f="recup_de"/> à <input type="time" data-f="recup_a"/> <span>(le créneau est retiré de vos heures, les heures se calculent)</span></div>
                <label>🚫 Heures sans solde (non payées)
                  <input type="number" data-f="h_ss" step="0.25" min="0" max="12" placeholder="0" t-att-value="('%g' % s.x_h_sans_solde) if (s and s.x_type == 'travail' and s.x_h_sans_solde) else ''"/> h
                </label>
                <div class="mh-plage">ou de <input type="time" data-f="ss_de"/> à <input type="time" data-f="ss_a"/></div>"""),
    # JS : préremplissage, retrait du créneau, envoi
    ("""  document.querySelectorAll('.mh-day').forEach(function(c){ calc(c); });
  document.addEventListener('input', function(e){ var card = e.target.closest('.mh-day'); if(card && e.target.matches('input[data-f]')){ calc(card); } });""",
     """  /* créneau « de … à … » : retiré des heures travaillées (comme le bureau), durée reportée dans le nombre d'heures */
  function retire(card, de, a){
    var inp = inputs(card);
    [[inp.m_deb, inp.m_fin], [inp.am_deb, inp.am_fin]].forEach(function(sg){
      var s0 = toDec(sg[0].value), s1 = toDec(sg[1].value);
      if(!(s1 > s0) || a <= s0 || de >= s1){ return; }
      if(de <= s0 && a >= s1){ sg[0].value = ''; sg[1].value = ''; return; }
      if(de <= s0){ sg[0].value = fromDec(a); return; }
      if(a >= s1){ sg[1].value = fromDec(de); return; }
      if((de - s0) >= (s1 - a)){ sg[1].value = fromDec(de); } else { sg[0].value = fromDec(a); }
    });
  }
  function plage(card, cle){
    var inp = inputs(card); var i1 = inp[cle + '_de'], i2 = inp[cle + '_a'], n = inp['h_' + cle];
    if(!i1 || !i2 || !n){ return null; }
    if(!i1.value || !i2.value){ return null; }
    var de = toDec(i1.value), a = toDec(i2.value);
    if(!(de < a)){ n.value = ''; return null; }
    return {de:de, a:a, h:q4(a - de)};
  }
  function appliquePlage(card, cle){
    var p = plage(card, cle); if(!p){ return; }
    retire(card, p.de, p.a);
    inputs(card)['h_' + cle].value = String(p.h);
    var autre = (cle === 'recup') ? 'ss' : 'recup';
    var q = plage(card, autre); if(q){ inputs(card)['h_' + autre].value = String(q.h); }
    calc(card);
  }
  function videPlages(card, cle){
    var inp = inputs(card);
    (cle ? [cle] : ['recup', 'ss']).forEach(function(k){ if(inp[k + '_de']){ inp[k + '_de'].value = ''; } if(inp[k + '_a']){ inp[k + '_a'].value = ''; } });
  }
  function prefill(card){
    var note = card.getAttribute('data-note') || ''; var inp = inputs(card);
    [['Récup', 'recup'], ['Sans solde', 'ss']].forEach(function(p){
      var m = note.match(new RegExp(p[0] + ' (\\\\d\\\\d:\\\\d\\\\d)-(\\\\d\\\\d:\\\\d\\\\d)'));
      if(m && inp[p[1] + '_de'] && inp[p[1] + '_a']){ inp[p[1] + '_de'].value = m[1]; inp[p[1] + '_a'].value = m[2]; }
    });
  }
  document.querySelectorAll('.mh-day').forEach(function(c){ prefill(c); calc(c); });
  document.addEventListener('input', function(e){
    var card = e.target.closest('.mh-day'); if(!card || !e.target.matches('input[data-f]')){ return; }
    var f = e.target.getAttribute('data-f');
    if(f === 'h_recup' || f === 'h_ss'){ videPlages(card, f === 'h_recup' ? 'recup' : 'ss'); }
    calc(card);
  });
  document.addEventListener('change', function(e){
    var card = e.target.closest('.mh-day'); if(!card || !e.target.matches('input[data-f]')){ return; }
    var f = e.target.getAttribute('data-f');
    if(f === 'recup_de' || f === 'recup_a'){ appliquePlage(card, 'recup'); }
    if(f === 'ss_de' || f === 'ss_a'){ appliquePlage(card, 'ss'); }
  });"""),
    ("""               hj_h_recup:(typ === 'travail' ? (R || 0) : 0), hj_h_ss:(typ === 'travail' ? (S || 0) : 0)};
    var dec = card.querySelector('input[data-f=decouchage]');""",
     """               hj_h_recup:(typ === 'travail' ? (R || 0) : 0), hj_h_ss:(typ === 'travail' ? (S || 0) : 0)};
    if(typ === 'travail'){
      var pr = plage(card, 'recup'), ps = plage(card, 'ss');
      if(pr){ ctx.hj_recup_de = pr.de; ctx.hj_recup_a = pr.a; ctx.hj_h_recup = pr.h; }
      if(ps){ ctx.hj_ss_de = ps.de; ctx.hj_ss_a = ps.a; ctx.hj_h_ss = ps.h; }
    }
    var dec = card.querySelector('input[data-f=decouchage]');"""),
    ("""      if(ty === 'travail'){
        st.textContent = '✓ ' + fr(res.heures||0) + ' h' + (res.h_recup ? ' + 🔄 ' + fr(res.h_recup) + ' h récup' : '') + (res.h_ss ? ' + 🚫 ' + fr(res.h_ss) + ' h sans solde' : '');""",
     """      if(ty === 'travail'){
        var pr2 = plage(card, 'recup'), ps2 = plage(card, 'ss');
        var det = [];
        if(pr2 && res.h_recup){ det.push('Récup ' + fromDec(pr2.de) + '-' + fromDec(pr2.a)); }
        if(ps2 && res.h_ss){ det.push('Sans solde ' + fromDec(ps2.de) + '-' + fromDec(ps2.a)); }
        if(!res.h_recup){ videPlages(card, 'recup'); }
        if(!res.h_ss){ videPlages(card, 'ss'); }
        st.textContent = '✓ ' + fr(res.heures||0) + ' h' + (res.h_recup ? ' + 🔄 ' + fr(res.h_recup) + ' h récup' : '') + (res.h_ss ? ' + 🚫 ' + fr(res.h_ss) + ' h sans solde' : '') + (det.length ? ' (' + det.join(' · ') + ')' : '');"""),
    ("""        st.textContent = LBL[ty] || ty;
        card.querySelectorAll('.mh-times input').forEach(function(i){ i.value=''; });""",
     """        st.textContent = LBL[ty] || ty;
        videPlages(card);
        card.querySelectorAll('.mh-times input').forEach(function(i){ i.value=''; });"""),
    ("""      if(inp.h_recup){ inp.h_recup.value = ''; }
      if(inp.h_ss){ inp.h_ss.value = ''; }
      save(card, 'travail', toDec(inp.m_deb.value), toDec(inp.m_fin.value), toDec(inp.am_deb.value), toDec(inp.am_fin.value), 0, 0);
      return;""",
     """      if(inp.h_recup){ inp.h_recup.value = ''; }
      if(inp.h_ss){ inp.h_ss.value = ''; }
      videPlages(card);
      save(card, 'travail', toDec(inp.m_deb.value), toDec(inp.m_fin.value), toDec(inp.am_deb.value), toDec(inp.am_fin.value), 0, 0);
      return;"""),
    ("""      var reste = q4(Math.max(r0.theo - r0.H, 0));
      if(inp.h_recup){ inp.h_recup.value = (act === 'q-recup' && reste) ? String(reste) : ''; }""",
     """      var reste = q4(Math.max(r0.theo - r0.H, 0));
      videPlages(card);
      if(inp.h_recup){ inp.h_recup.value = (act === 'q-recup' && reste) ? String(reste) : ''; }"""),
])
