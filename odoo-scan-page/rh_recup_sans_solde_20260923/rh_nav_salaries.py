# -*- coding: utf-8 -*-
"""Fiche salarié : barre « ◀ salarié précédent · liste déroulante · salarié suivant ▶ » (ordre société puis nom, comme
/heures-admin), en gardant la période de paie mémorisée du salarié cible (sinon la période affichée)."""
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
    # CSS
    ("""      .fs-info{background:#fff;border-radius:10px;padding:8px 12px;margin-bottom:10px;color:#475569;font-size:12.5px;font-weight:600;line-height:1.45;}""",
     """      .fs-info{background:#fff;border-radius:10px;padding:8px 12px;margin-bottom:10px;color:#475569;font-size:12.5px;font-weight:600;line-height:1.45;}
      .fs-emp{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px;background:#0f172a;border-radius:12px;padding:8px 12px;}
      .fs-emp a{border:1px solid #475569;border-radius:9px;padding:6px 12px;font-weight:800;text-decoration:none;color:#e2e8f0;background:#1e293b;}
      .fs-emp a:hover{background:#334155;}
      .fs-emp select{border:1px solid #475569;border-radius:9px;padding:6px 8px;font-weight:800;background:#fff;color:#0f172a;max-width:320px;}
      .fs-emp .l{color:#94a3b8;font-size:12px;font-weight:800;}"""),
    # données : salariés précédent / suivant, périodes mémorisées
    ("""        <t t-set="mrows" t-value="[r for r in rows if d1 &lt;= r.x_date and r.x_date &lt;= d2]"/>""",
     """        <t t-set="mrows" t-value="[r for r in rows if d1 &lt;= r.x_date and r.x_date &lt;= d2]"/>
        <!-- navigation entre salariés : même ordre que /heures-admin (société puis nom) ; la période de paie mémorisée
             du salarié cible (paramètre maquignon.heures_export_exc) est reprise par le script, sinon la période affichée -->
        <t t-set="tous" t-value="request.env['hr.employee'].sudo().search([('active','=',True)], order='company_id, name')"/>
        <t t-set="tous_ids" t-value="tous.ids"/>
        <t t-set="pos" t-value="tous_ids.index(emp.id) if emp.id in tous_ids else -1"/>
        <t t-set="e_prev" t-value="tous[pos - 1] if pos &gt; 0 else None"/>
        <t t-set="e_next" t-value="tous[pos + 1] if (pos &gt;= 0 and pos + 1 &lt; len(tous_ids)) else None"/>
        <t t-set="exc_brut" t-value="request.env['ir.config_parameter'].sudo().get_param('maquignon.heures_export_exc') or '{}'"/>"""),
    # barre de navigation salariés (sous l'en-tête)
    ("""        <div class="fs-info">
          ✏️ <b>Chaque ligne s'enregistre toute seule</b>""",
     """        <div class="fs-emp">
          <span class="l">SALARIÉ</span>
          <a t-if="e_prev" class="fs-emp-lnk" t-att-data-emp="e_prev.id" t-attf-href="/heures-salarie?emp={{e_prev.id}}&amp;{{q_per}}&amp;k={{kk}}" title="Salarié précédent (ordre de la liste Heures)">◀ <t t-esc="e_prev.name"/></a>
          <select id="fs-emp-sel" title="Aller à un autre salarié">
            <t t-foreach="tous.mapped('company_id')" t-as="co">
              <optgroup t-att-label="co.name">
                <t t-foreach="tous.filtered(lambda e0: e0.company_id.id == co.id)" t-as="e0">
                  <option t-att-value="e0.id" t-att-selected="'selected' if e0.id == emp.id else None" t-esc="e0.name"/>
                </t>
              </optgroup>
            </t>
          </select>
          <a t-if="e_next" class="fs-emp-lnk" t-att-data-emp="e_next.id" t-attf-href="/heures-salarie?emp={{e_next.id}}&amp;{{q_per}}&amp;k={{kk}}" title="Salarié suivant (ordre de la liste Heures)"><t t-esc="e_next.name"/> ▶</a>
          <span class="l" t-if="pos &gt;= 0"><t t-esc="pos + 1"/> / <t t-esc="len(tous_ids)"/></span>
        </div>
        <div class="fs-info">
          ✏️ <b>Chaque ligne s'enregistre toute seule</b>"""),
    # attributs pour le script
    ("""        <div id="fs-k" t-att-data-k="kk" t-att-data-emp="emp.id" t-att-data-m1="'%.4f' % m_1" style="display:none;"/>""",
     """        <div id="fs-k" t-att-data-k="kk" t-att-data-emp="emp.id" t-att-data-m1="'%.4f' % m_1" t-att-data-qper="q_per" t-att-data-exc="exc_brut" style="display:none;"/>"""),
    # script : liens précédent / suivant / liste avec la période mémorisée du salarié cible
    ("""  var M1 = parseFloat(document.getElementById('fs-k').getAttribute('data-m1') || 0);""",
     """  var M1 = parseFloat(document.getElementById('fs-k').getAttribute('data-m1') || 0);
  var QPER = document.getElementById('fs-k').getAttribute('data-qper') || '';
  var EXC = {};
  try { EXC = JSON.parse(document.getElementById('fs-k').getAttribute('data-exc') || '{}'); } catch(e){ EXC = {}; }
  function lienEmp(id){
    var per = EXC[String(id)];
    var q = (per && per.length === 2 && per[0] && per[1]) ? ('du=' + per[0] + '&au=' + per[1]) : QPER;
    return '/heures-salarie?emp=' + id + '&' + q + '&k=' + KK;
  }
  document.querySelectorAll('a.fs-emp-lnk').forEach(function(a){ a.setAttribute('href', lienEmp(a.getAttribute('data-emp'))); });
  var selEmp = document.getElementById('fs-emp-sel');
  if(selEmp){ selEmp.addEventListener('change', function(){ if(selEmp.value){ location.href = lienEmp(selEmp.value); } }); }"""),
])
