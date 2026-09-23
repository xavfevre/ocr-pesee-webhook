# -*- coding: utf-8 -*-
"""Page bureau /heures-admin (vue 7957) : sans solde, récup / sans solde en heures, HS payées, lien fiche salarié.
  python rh_patch_7957.py            -> vue_7957_NEW.xml
  python rh_patch_7957.py test|prod  -> + écriture dans Odoo (test : relais local)"""
import io, os, sys
sys.stdout.reconfigure(encoding='utf-8')
SRC = 'vue_7957_heures_admin.xml'
s = io.open(SRC, encoding='utf-8').read()
n0 = len(s)


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:100])
    s = s.replace(old, new)


def esc_js(js):
    return js.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# CSS
rep("      .c-recup{background:#e0f2fe;color:#075985;}\n",
    "      .c-recup{background:#e0f2fe;color:#075985;}\n      .c-sans_solde{background:#fee2e2;color:#991b1b;}\n"
    "      .ha-cell small{display:block;font-size:9.5px;font-weight:900;line-height:1.1;}\n"
    "      .ha-extra{display:grid;grid-template-columns:auto 1fr;gap:6px 8px;align-items:center;margin:6px 0 10px;font-size:12.5px;font-weight:800;color:#334155;}\n"
    "      .ha-extra input[type=number]{border:1.5px solid #cbd5e1;border-radius:8px;padding:5px;font-weight:700;width:90px;}\n"
    "      .ha-note{font-size:11.5px;color:#64748b;font-weight:600;margin:4px 0 8px;line-height:1.35;}\n")
# en-tête colonnes + colspan sociétés
rep('<th>Total</th><th>Théo</th><th>Écart</th><th title="Découchages">🛏</th><th/>',
    '<th>Total</th><th>Théo</th><th title="Heures comptées en récup : heures sup en plus, récups prises et heures manquantes en moins (sans solde exclu)">Récup ±</th><th title="Heures de récup prises">🔄 h</th><th title="Heures sans solde">🚫 h</th><th title="Découchages">🛏</th><th/>')
rep('<th colspan="5"/>', '<th colspan="7"/>')
rep('<td class="soc" t-att-colspan="len(dates) + 6" t-esc="e.company_id.name"/>', '<td class="soc" t-att-colspan="len(dates) + 8" t-esc="e.company_id.name"/>')
# accumulateurs de ligne
rep('          <t t-set="wtheo" t-value="0.0"/>\n', '          <t t-set="wtheo" t-value="0.0"/>\n          <t t-set="wdelta" t-value="0.0"/>\n          <t t-set="wrec" t-value="0.0"/>\n          <t t-set="wss" t-value="0.0"/>\n')
rep("""              <!-- écart : les jours posés en congé/maladie/férié/absence/récup ne comptent
                   pas dans le théorique ; jour travail = théo figé (demi-journées gérées) -->
              <t t-set="wtheo" t-value="wtheo + (s.x_theo if (s and s.x_type == 'travail') else (0.0 if s else theo))"/>
              <t t-set="wtot" t-value="wtot + (s.x_heures if (s and s.x_type == 'travail') else 0.0)"/>""",
    """              <!-- horaire : jours travaillés / récup / sans solde = théo figé (demi-journées de congé gérées),
                   jour vide = calendrier ; congés, maladie, fériés, absences ne comptent pas.
                   Récup ± = x_hs (heures sup +, récup prise et heures manquantes −, sans solde exclu) -->
              <t t-set="wtheo" t-value="wtheo + (s.x_theo if (s and s.x_type in ('travail', 'recup', 'sans_solde')) else (0.0 if s else theo))"/>
              <t t-set="wtot" t-value="wtot + (s.x_heures if (s and s.x_type == 'travail') else 0.0)"/>
              <t t-set="wdelta" t-value="wdelta + (s.x_hs if (s and s.x_type in ('travail', 'recup', 'sans_solde')) else 0.0)"/>
              <t t-set="wrec" t-value="wrec + ((s and s.x_h_recup) or 0.0)"/>
              <t t-set="wss" t-value="wss + ((s and s.x_h_sans_solde) or 0.0)"/>""")
# cellule : attributs + contenu
rep("""t-att-data-af="s and fmt(s.x_am_fin) or ''">
                  <t t-if="s">
                    <t t-if="s.x_type == 'travail'"><t t-esc="('%.2f' % s.x_heures).replace('.', ',')"/><t t-if="s.x_decouchage">🛏</t></t>""",
    """t-att-data-af="s and fmt(s.x_am_fin) or ''" t-att-data-recup="s and ('%g' % s.x_h_recup) or ''" t-att-data-ss="s and ('%g' % s.x_h_sans_solde) or ''" t-att-data-payees="'1' if (s and s.x_hs_payees) else ''" t-att-title="(s and s.x_note) or None">
                  <t t-if="s">
                    <t t-if="s.x_type == 'travail'"><t t-esc="('%.2f' % s.x_heures).replace('.', ',')"/><t t-if="s.x_decouchage">🛏</t><small t-if="s.x_h_recup" style="color:#075985;">R <t t-esc="('%g' % s.x_h_recup).replace('.', ',')"/></small><small t-if="s.x_h_sans_solde" style="color:#991b1b;">SS <t t-esc="('%g' % s.x_h_sans_solde).replace('.', ',')"/></small><small t-if="s.x_hs_payees and s.x_heures &gt; s.x_theo" style="color:#15803d;">HS payées</small></t>""")
rep("""                    <t t-elif="s.x_type == 'recup'">REC</t>
                    <t t-else="">–</t>""", """                    <t t-elif="s.x_type == 'recup'">REC</t>
                    <t t-elif="s.x_type == 'sans_solde'">SS</t>
                    <t t-else="">–</t>""")
# totaux de ligne
rep("""            <td t-attf-style="font-weight:900;color:{{'#16a34a' if wtot - wtheo &gt;= 0 else '#dc2626'}};" t-esc="('%+.2f' % (wtot - wtheo)).replace('.', ',')"/>""",
    """            <td t-attf-style="font-weight:900;color:{{'#16a34a' if wdelta &gt;= 0 else '#dc2626'}};" t-esc="('%+.2f' % wdelta).replace('.', ',')"/>
            <td style="color:#075985;font-weight:800;" t-esc="('%g' % round(wrec, 2)).replace('.', ',') if wrec else ''"/>
            <td style="color:#991b1b;font-weight:800;" t-esc="('%g' % round(wss, 2)).replace('.', ',') if wss else ''"/>""")
# cellule salarié : lien fiche + solde recalculé
rep("""class="ha-feuille" style="text-decoration:none;font-size:13px;margin-left:2px;">📄</a>""",
    """class="ha-feuille" style="text-decoration:none;font-size:13px;margin-left:2px;">📄</a><a t-attf-href="/heures-salarie?emp={{e.id}}&amp;mois={{mois_export}}&amp;k={{kk}}" title="Fiche du salarié (format feuille Excel), modifiable directement — sur les dates de la ligne si renseignées, sinon les dates de l'en-tête, sinon le mois" class="ha-fiche" style="text-decoration:none;font-size:13px;margin-left:2px;">📋</a>""")
i0 = s.index('<t t-set="ha_prows" t-value=')
i1 = s.index('<t t-set="ha_solde" t-value="(e.x_recup_solde or 0.0) + ha_rl - ha_pris"/>') + len('<t t-set="ha_solde" t-value="(e.x_recup_solde or 0.0) + ha_rl - ha_pris"/>')
s = s[:i0] + """<t t-set="ha_prows" t-value="request.env['x_heures_jour'].sudo().search([('x_employee_id','=',e.id),('x_date','&gt;=',ha_pstart.strftime('%Y-%m-%d')),('x_date','&lt;=',today.strftime('%Y-%m-%d')),('x_type','in',['travail','recup','sans_solde'])])"/><t t-set="ha_rl" t-value="sum(request.env['x_recup_ligne'].sudo().search([('x_employee_id','=',e.id)]).filtered(lambda l: not ha_ref or l.x_date &gt; ha_ref).mapped('x_heures'))"/><t t-set="ha_delta" t-value="sum(ha_prows.filtered(lambda r: not ha_ref or r.x_date &gt; ha_ref).mapped('x_hs'))"/><t t-set="ha_solde" t-value="(e.x_recup_solde or 0.0) + ha_rl + ha_delta"/>""" + s[i1:]
rep("""<span t-if="ha_rl or e.x_recup_solde or (ha_ref and ha_pris)" """, """<span t-if="ha_rl or e.x_recup_solde or ha_delta" """)
rep("""t-attf-title="Heures à récupérer — arrêté bureau {{'%g' % (e.x_recup_solde or 0)}} h + {{'%g' % ha_rl}} h mises − {{'%g' % round(ha_pris, 2)}} h récupérées">""",
    """t-attf-title="Heures à récupérer — arrêté bureau {{'%g' % (e.x_recup_solde or 0)}} h + {{'%g' % ha_rl}} h ajoutées par le bureau {{'+' if ha_delta &gt;= 0 else '−'}} {{'%g' % abs(round(ha_delta, 2))}} h comptées depuis (heures sup +, récups prises et heures manquantes −, sans solde exclu)">""")
assert 'ha_pris' not in s
# légende
rep("""Cliquez sur une case pour saisir/corriger · <b>⚡</b> remplit""",
    """Cliquez sur une case pour saisir/corriger (<b>R</b> = heures de récup prises, <b>SS</b> = heures sans solde, <b>REC</b> / <b>SS</b> = journée entière) · <b>📋</b> fiche mensuelle du salarié, modifiable ligne par ligne · <b>⚡</b> remplit""")
# popup
rep("""          <button type="button" class="ha-bt c-recup" data-t="recup">Récup</button>
          <button type="button" class="ha-bt c-repos" data-t="repos">Repos</button>
        </div>
        <div class="ha-times">
          <label>Matin</label><input type="time" id="ha-md"/><input type="time" id="ha-mf"/>
          <label>Ap.-midi</label><input type="time" id="ha-ad"/><input type="time" id="ha-af"/>
        </div>""",
    """          <button type="button" class="ha-bt c-recup" data-t="recup">Récup (journée)</button>
          <button type="button" class="ha-bt c-sans_solde" data-t="sans_solde">Sans solde (journée)</button>
          <button type="button" class="ha-bt c-repos" data-t="repos">Repos</button>
        </div>
        <div class="ha-note">Heures en plus → ajoutées au solde à récupérer (sauf « HS payées »). Heures en moins → indiquez récup ou sans solde ; sinon elles sont retirées du solde.</div>
        <div class="ha-times">
          <label>Matin</label><input type="time" id="ha-md"/><input type="time" id="ha-mf"/>
          <label>Ap.-midi</label><input type="time" id="ha-ad"/><input type="time" id="ha-af"/>
        </div>
        <div class="ha-extra">
          <label for="ha-hr">🔄 Récup prise (h)</label><input type="number" id="ha-hr" step="any" min="0" max="12" placeholder="0"/>
          <label for="ha-hs">🚫 Sans solde (h)</label><input type="number" id="ha-hs" step="any" min="0" max="12" placeholder="0"/>
          <label style="grid-column:1/-1;display:flex;align-items:center;gap:7px;cursor:pointer;"><input type="checkbox" id="ha-pay"/> Heures sup payées (pas mises en récup)</label>
        </div>""")
# 📋 : même période que 📄
rep("          if(d &amp;&amp; f &amp;&amp; d &lt;= f){\n            ev.preventDefault();\n            var h = a.getAttribute('href').replace(/&amp;?mois=[0-9-]*/, '');\n            window.open(h + '&amp;du=' + d + '&amp;au=' + f, '_blank');\n          }\n        });\n      });\n    })();", "          if(d &amp;&amp; f &amp;&amp; d &lt;= f){\n            ev.preventDefault();\n            var h = a.getAttribute('href').replace(/&amp;?mois=[0-9-]*/, '');\n            window.open(h + '&amp;du=' + d + '&amp;au=' + f, '_blank');\n          }\n        });\n      });\n      /* 📋 fiche : même période que 📄 (dates de la ligne, sinon en-tête), dans le même onglet */\n      document.querySelectorAll('a.ha-fiche').forEach(function(a){\n        a.addEventListener('click', function(ev){\n          var tr = a.closest('tr');\n          var rdu = tr ? tr.querySelector('.ha-fx-du') : null;\n          var rau = tr ? tr.querySelector('.ha-fx-au') : null;\n          var d = (rdu &amp;&amp; rdu.value) ? rdu.value : du.value;\n          var f = (rau &amp;&amp; rau.value) ? rau.value : au.value;\n          if(d &amp;&amp; f &amp;&amp; d &lt;= f){\n            ev.preventDefault();\n            location.href = a.getAttribute('href').replace(/&amp;?mois=[0-9-]*/, '') + '&amp;du=' + d + '&amp;au=' + f;\n          }\n        });\n      });\n    })();")
# script
rep(esc_js("""  function rpcSave(emp, date, typ, md, mf, ad, af, done){
    rpcAction(2012, {active_model:'x_heures_jour',hj_emp:emp,hj_k:KK,hj_date:date,hj_type:typ,hj_m_deb:md,hj_m_fin:mf,hj_am_deb:ad,hj_am_fin:af}).then(function(r){return r.json();}).then(function(d){"""),
    esc_js("""  function rpcSave(emp, date, typ, md, mf, ad, af, done, extra){
    var ctx = {active_model:'x_heures_jour',hj_emp:emp,hj_k:KK,hj_date:date,hj_type:typ,hj_m_deb:md,hj_m_fin:mf,hj_am_deb:ad,hj_am_fin:af};
    if(extra){ for(var k in extra){ ctx[k] = extra[k]; } }
    rpcAction(2012, ctx).then(function(r){return r.json();}).then(function(d){"""))
rep(esc_js("""      document.getElementById('ha-af').value = cell.getAttribute('data-af') || cell.getAttribute('data-taf');
      pop.style.display='flex';"""),
    esc_js("""      document.getElementById('ha-af').value = cell.getAttribute('data-af') || cell.getAttribute('data-taf');
      document.getElementById('ha-hr').value = cell.getAttribute('data-recup') || '';
      document.getElementById('ha-hs').value = cell.getAttribute('data-ss') || '';
      document.getElementById('ha-pay').checked = !!cell.getAttribute('data-payees');
      pop.style.display='flex';"""))
rep(esc_js("""      if(t === 'normal'){
        rpcSave(curEmp, curCell.getAttribute('data-date'), 'travail', toDec(curCell.getAttribute('data-tmd')), toDec(curCell.getAttribute('data-tmf')), toDec(curCell.getAttribute('data-tad')), toDec(curCell.getAttribute('data-taf')), function(){ location.reload(); });"""),
    esc_js("""      if(t === 'normal'){
        rpcSave(curEmp, curCell.getAttribute('data-date'), 'travail', toDec(curCell.getAttribute('data-tmd')), toDec(curCell.getAttribute('data-tmf')), toDec(curCell.getAttribute('data-tad')), toDec(curCell.getAttribute('data-taf')), function(){ location.reload(); }, {hj_h_recup:0, hj_h_ss:0});"""))
rep(esc_js("""  document.getElementById('ha-save').addEventListener('click', function(){
    rpcSave(curEmp, curCell.getAttribute('data-date'), 'travail',
      toDec(document.getElementById('ha-md').value), toDec(document.getElementById('ha-mf').value),
      toDec(document.getElementById('ha-ad').value), toDec(document.getElementById('ha-af').value),
      function(){ location.reload(); });
  });"""),
    esc_js("""  function numv(id){ var v = parseFloat(String(document.getElementById(id).value || '0').replace(',', '.')); return isNaN(v) ? 0 : v; }
  document.getElementById('ha-save').addEventListener('click', function(){
    rpcSave(curEmp, curCell.getAttribute('data-date'), 'travail',
      toDec(document.getElementById('ha-md').value), toDec(document.getElementById('ha-mf').value),
      toDec(document.getElementById('ha-ad').value), toDec(document.getElementById('ha-af').value),
      function(){ location.reload(); },
      {hj_h_recup:numv('ha-hr'), hj_h_ss:numv('ha-hs'), hj_hs_payees:(document.getElementById('ha-pay').checked ? 1 : 0)});
  });"""))
import xml.dom.minidom
xml.dom.minidom.parseString(s.encode('utf-8'))
io.open('vue_7957_NEW.xml', 'w', encoding='utf-8', newline='\n').write(s)
print('vue_7957_NEW.xml :', n0, '->', len(s), 'chars, XML OK')
mode = (sys.argv[1] if len(sys.argv) > 1 else '').lower()
if mode in ('test', 'prod'):
    import ssl, xmlrpc.client
    U, D = ('https://testmaq230926v2.odoo.com', 'testmaq230926v2') if mode == 'test' else ('https://maquignon.odoo.com', 'maquignon')
    arch = s.replace('https://ocr-pesee-webhook.onrender.com/heures/rpc', 'http://127.0.0.1:5055/heures/rpc') if mode == 'test' else s
    us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
    c = ssl.create_default_context()
    uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
    m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
    m.execute_kw(D, uid, p, 'ir.ui.view', 'write', [[7957], {'arch_db': arch}])
    print(mode, ': vue 7957 écrite,', len(m.execute_kw(D, uid, p, 'ir.ui.view', 'read', [[7957], ['arch_db']])[0]['arch_db']), 'chars')
