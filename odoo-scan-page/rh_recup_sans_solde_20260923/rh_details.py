import io, sys
sys.stdout.reconfigure(encoding='utf-8')
p = 'rh_patch_7956.py'; s = io.open(p, encoding='utf-8').read()
pairs = [
    ("""              <div class="mh-manque" data-role="manque" style="display:none;">
                <div class="t">Heures manquantes : de quoi s'agit-il ?</div>
                <div class="q">""",
     """              <details class="mh-manque" data-role="manque" style="display:none;">
                <summary class="t" data-role="manque-t">🔄 Récup ou 🚫 sans solde pris dans la journée ? (facultatif)</summary>
                <div class="q" data-role="manque-q">"""),
    ("""                <div class="mh-plage">ou de <input type="time" data-f="ss_de"/> à <input type="time" data-f="ss_a"/></div>
              </div>
              <button type="button" class="mh-save" data-act="save">""",
     """                <div class="mh-plage">ou de <input type="time" data-f="ss_de"/> à <input type="time" data-f="ss_a"/></div>
              </details>
              <button type="button" class="mh-save" data-act="save">"""),
    ("""    ctrl.innerHTML = txt; ctrl.className = 'mh-ctrl ' + cls;
    if(mq){ mq.style.display = show ? '' : 'none'; }
    return res;""",
     """    ctrl.innerHTML = txt; ctrl.className = 'mh-ctrl ' + cls;
    if(mq){
      mq.style.display = (theo <= 0) ? 'none' : '';
      var mt = card.querySelector('[data-role=manque-t]'), mqq = card.querySelector('[data-role=manque-q]');
      var manqueH = (cls === 'warn' || cls === 'bad');
      if(mt){ mt.textContent = manqueH ? '⚠️ Heures manquantes : de quoi s\'agit-il ?' : ((R || S) ? '🔄 Récup / 🚫 sans solde de la journée' : '🔄 Récup ou 🚫 sans solde pris dans la journée ? (facultatif)'); }
      if(mqq){ mqq.style.display = manqueH ? '' : 'none'; }
      if(show){ mq.open = true; }
    }
    return res;"""),
    ("""    '      .mh-manque .t{font-size:12.5px;font-weight:900;color:#92400e;margin-bottom:5px;}',""",
     """    '      .mh-manque .t{font-size:12.5px;font-weight:900;color:#92400e;margin-bottom:5px;cursor:pointer;}',
    '      .mh-manque[open] .t{margin-bottom:8px;}',"""),
]
for old, new in pairs:
    assert s.count(old) == 1, (s.count(old), old[:80]); s = s.replace(old, new)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s); print('bloc récup/sans solde repliable : OK')
p = 'pw_plages.py'; s = io.open(p, encoding='utf-8').read()
old = "    c.locator('input[data-f=recup_de]').fill('16:00')"
new = "    c.locator('[data-role=manque-t]').click(); pg.wait_for_timeout(300)\n    print('bloc ouvert :', c.locator('[data-role=manque]').get_attribute('open') is not None, '|', c.locator('[data-role=manque-t]').inner_text())\n    c.locator('input[data-f=recup_de]').fill('16:00')"
assert s.count(old) == 1; s = s.replace(old, new)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s); print('test : OK')
