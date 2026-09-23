# -*- coding: utf-8 -*-
"""Fiche salarié : dates du/au modifiables dans le titre ; « Afficher » mémorise la période pour ce salarié
(action 2090, même mémoire que les dates de la ligne dans /heures-admin) puis recharge la fiche."""
import io, sys
sys.stdout.reconfigure(encoding='utf-8')


def patch(path, pairs):
    s = io.open(path, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, s.count(old), old[:90])
        s = s.replace(old, new)
    io.open(path, 'w', encoding='utf-8', newline='\n').write(s)
    print(path, ': OK')


patch('rh_page_fiche.py', [
    ("""      .fs-emp .l{color:#94a3b8;font-size:12px;font-weight:800;}""",
     """      .fs-emp .l{color:#94a3b8;font-size:12px;font-weight:800;}
      .fs-per{display:inline-flex;align-items:center;gap:6px;font-weight:300;font-size:22px;}
      .fs-per input[type=date]{border:1.5px solid #cbd5e1;border-radius:9px;padding:4px 8px;font-weight:800;font-size:16px;color:#0f172a;background:#fff;}
      .fs-per button{border:none;border-radius:9px;background:#0f172a;color:#fff;font-weight:800;padding:7px 12px;cursor:pointer;font-size:14px;}
      .fs-per button:disabled{opacity:.5;}"""),
    ("""          <h4 style="font-weight:300;margin:0;">📋 <b t-esc="emp.name"/> — <t t-if="libre">du <b t-esc="d1.strftime('%d/%m/%Y')"/> au <b t-esc="d2.strftime('%d/%m/%Y')"/></t><t t-else=""><t t-esc="mois_noms[d1.month - 1]"/> <t t-esc="d1.year"/></t> <span style="color:#94a3b8;font-size:13px;"> · <t t-esc="emp.company_id.name"/> · <t t-esc="cal.name if cal else 'sans horaire'"/></span></h4>""",
     """          <h4 style="font-weight:300;margin:0;display:flex;align-items:center;gap:8px;flex-wrap:wrap;">📋 <b t-esc="emp.name"/> — <t t-if="not libre"><span><t t-esc="mois_noms[d1.month - 1]"/> <t t-esc="d1.year"/> :</span></t>
            <span class="fs-per" title="Période de paie de ce salarié : modifiez les dates puis « Afficher » (mémorisées, comme sur sa ligne dans Heures salariés)">du <input type="date" id="fs-du" t-att-value="d1.strftime('%Y-%m-%d')"/> au <input type="date" id="fs-au" t-att-value="d2.strftime('%Y-%m-%d')"/> <button type="button" id="fs-per-go">Afficher</button></span>
            <span style="color:#94a3b8;font-size:13px;"> · <t t-esc="emp.company_id.name"/> · <t t-esc="cal.name if cal else 'sans horaire'"/></span></h4>"""),
    ("""  var selEmp = document.getElementById('fs-emp-sel');
  if(selEmp){ selEmp.addEventListener('change', function(){ if(selEmp.value){ location.href = lienEmp(selEmp.value); } }); }""",
     """  var selEmp = document.getElementById('fs-emp-sel');
  if(selEmp){ selEmp.addEventListener('change', function(){ if(selEmp.value){ location.href = lienEmp(selEmp.value); } }); }
  /* dates du/au du titre : mémorisées pour ce salarié (action 2090, même mémoire que la ligne de /heures-admin), puis rechargement */
  var perGo = document.getElementById('fs-per-go');
  function appliquePeriode(){
    var d = document.getElementById('fs-du').value, f = document.getElementById('fs-au').value;
    if(!d || !f || d > f){ alert('Choisissez des dates valides (du ≤ au).'); return; }
    perGo.disabled = true; perGo.textContent = '…';
    var lignes = {}; lignes[String(EMP)] = [d, f];
    fetch(RPC, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({action_id:2090, ctx:{active_model:'x_heures_jour', hj_k:KK, lignes:lignes}})})
      .then(function(r){ return r.json(); }).catch(function(){ return {}; })
      .then(function(){ location.href = '/heures-salarie?emp=' + EMP + '&du=' + d + '&au=' + f + '&k=' + KK; });
  }
  if(perGo){ perGo.addEventListener('click', appliquePeriode); }
  ['fs-du', 'fs-au'].forEach(function(id){ var i = document.getElementById(id); if(i){ i.addEventListener('keydown', function(e){ if(e.key === 'Enter'){ appliquePeriode(); } }); } });"""),
])
