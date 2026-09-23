# -*- coding: utf-8 -*-
"""Fiche salarié : période du/au (dates de paie de la ligne dans /heures-admin) ; bouton 📋 sur ces dates."""
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
    ("""        <t t-set="mp" t-value="request.params.get('mois')"/>
        <t t-set="d1" t-value="datetime.datetime.strptime(mp + '-01', '%Y-%m-%d').date() if mp else today.replace(day=1)"/>
        <t t-set="d2" t-value="(d1.replace(year=d1.year + 1, month=1, day=1) if d1.month == 12 else d1.replace(month=d1.month + 1, day=1)) - datetime.timedelta(days=1)"/>
        <t t-set="m_prev" t-value="(d1 - datetime.timedelta(days=1)).replace(day=1).strftime('%Y-%m')"/>
        <t t-set="m_next" t-value="(d2 + datetime.timedelta(days=1)).strftime('%Y-%m')"/>""",
     """        <!-- période : du/au (dates de paie saisies sur la ligne du salarié dans /heures-admin) ou mois entier -->
        <t t-set="dup" t-value="(request.params.get('du') or '').strip()"/>
        <t t-set="aup" t-value="(request.params.get('au') or '').strip()"/>
        <t t-set="libre" t-value="bool(len(dup) == 10 and len(aup) == 10 and dup &lt;= aup)"/>
        <t t-set="mp" t-value="request.params.get('mois')"/>
        <t t-set="d1" t-value="datetime.datetime.strptime(dup, '%Y-%m-%d').date() if libre else (datetime.datetime.strptime(mp + '-01', '%Y-%m-%d').date() if mp else today.replace(day=1))"/>
        <t t-set="d2" t-value="datetime.datetime.strptime(aup, '%Y-%m-%d').date() if libre else ((d1.replace(year=d1.year + 1, month=1, day=1) if d1.month == 12 else d1.replace(month=d1.month + 1, day=1)) - datetime.timedelta(days=1))"/>
        <t t-set="nper" t-value="(d2 - d1).days + 1"/>
        <t t-set="m_prev" t-value="(d1 - datetime.timedelta(days=1)).replace(day=1).strftime('%Y-%m')"/>
        <t t-set="m_next" t-value="(d2 + datetime.timedelta(days=1)).strftime('%Y-%m')"/>
        <t t-set="q_per" t-value="('du=%s&amp;au=%s' % (d1.strftime('%Y-%m-%d'), d2.strftime('%Y-%m-%d'))) if libre else ('mois=' + d1.strftime('%Y-%m'))"/>
        <t t-set="q_prev" t-value="('du=%s&amp;au=%s' % ((d1 - datetime.timedelta(days=nper)).strftime('%Y-%m-%d'), (d1 - datetime.timedelta(days=1)).strftime('%Y-%m-%d'))) if libre else ('mois=' + m_prev)"/>
        <t t-set="q_next" t-value="('du=%s&amp;au=%s' % ((d2 + datetime.timedelta(days=1)).strftime('%Y-%m-%d'), (d2 + datetime.timedelta(days=nper)).strftime('%Y-%m-%d'))) if libre else ('mois=' + m_next)"/>"""),
    ("""          <h4 style="font-weight:300;margin:0;">📋 <b t-esc="emp.name"/> — <t t-esc="mois_noms[d1.month - 1]"/> <t t-esc="d1.year"/> <span style="color:#94a3b8;font-size:13px;"> · <t t-esc="emp.company_id.name"/> · <t t-esc="cal.name if cal else 'sans horaire'"/></span></h4>
          <div class="fs-nav">
            <a t-attf-href="/heures-salarie?emp={{emp.id}}&amp;mois={{m_prev}}&amp;k={{kk}}">◀ <t t-esc="mois_noms[int(m_prev[5:7]) - 1]"/></a>
            <a t-attf-href="/heures-salarie?emp={{emp.id}}&amp;k={{kk}}">Ce mois</a>
            <a t-attf-href="/heures-salarie?emp={{emp.id}}&amp;mois={{m_next}}&amp;k={{kk}}"><t t-esc="mois_noms[int(m_next[5:7]) - 1]"/> ▶</a>
            <a t-attf-href="https://ocr-pesee-webhook.onrender.com/export-heures?mois={{d1.strftime('%Y-%m')}}&amp;format=feuille&amp;emp={{emp.id}}&amp;k={{xk}}" target="_blank" style="background:#1d4ed8;color:#fff;border-color:#1d4ed8;">📄 Feuille Excel</a>""",
     """          <h4 style="font-weight:300;margin:0;">📋 <b t-esc="emp.name"/> — <t t-if="libre">du <b t-esc="d1.strftime('%d/%m/%Y')"/> au <b t-esc="d2.strftime('%d/%m/%Y')"/></t><t t-else=""><t t-esc="mois_noms[d1.month - 1]"/> <t t-esc="d1.year"/></t> <span style="color:#94a3b8;font-size:13px;"> · <t t-esc="emp.company_id.name"/> · <t t-esc="cal.name if cal else 'sans horaire'"/></span></h4>
          <div class="fs-nav">
            <a t-attf-href="/heures-salarie?emp={{emp.id}}&amp;{{q_prev}}&amp;k={{kk}}">◀ <t t-if="libre">période précédente</t><t t-else=""><t t-esc="mois_noms[int(m_prev[5:7]) - 1]"/></t></a>
            <a t-attf-href="/heures-salarie?emp={{emp.id}}&amp;k={{kk}}">Ce mois</a>
            <a t-if="libre" t-attf-href="/heures-salarie?emp={{emp.id}}&amp;mois={{d1.strftime('%Y-%m')}}&amp;k={{kk}}" title="Afficher le mois entier">📆 <t t-esc="mois_noms[d1.month - 1]"/> entier</a>
            <a t-attf-href="/heures-salarie?emp={{emp.id}}&amp;{{q_next}}&amp;k={{kk}}"><t t-if="libre">période suivante</t><t t-else=""><t t-esc="mois_noms[int(m_next[5:7]) - 1]"/></t> ▶</a>
            <a t-attf-href="https://ocr-pesee-webhook.onrender.com/export-heures?{{q_per}}&amp;format=feuille&amp;emp={{emp.id}}&amp;k={{xk}}" target="_blank" style="background:#1d4ed8;color:#fff;border-color:#1d4ed8;">📄 Feuille Excel</a>"""),
    ("""          <div>Nombre total d'heures (mois)<b id="fs-m-h">–</b></div>
          <div>Récup ± du mois<b id="fs-m-hs">–</b></div>""",
     """          <div>Nombre total d'heures (<t t-if="libre">période</t><t t-else="">mois</t>)<b id="fs-m-h">–</b></div>
          <div>Récup ± <t t-if="libre">de la période</t><t t-else="">du mois</t><b id="fs-m-hs">–</b></div>"""),
    ("""Heures M-1<b><t t-esc="('%+.2f' % m_1).replace('.', ',')"/> h</b></div>""",
     """<t t-if="libre">Solde au <t t-esc="m0.strftime('%d/%m')"/></t><t t-else="">Heures M-1</t><b><t t-esc="('%+.2f' % m_1).replace('.', ',')"/> h</b></div>"""),
    ("""Heures M-1 = arrêté bureau (page ⏰ Horaires par défaut) + heures comptées en récup depuis, jusqu'à la veille du mois. Reste heures = Heures M-1 + Récup ± du mois. Les jours grisés appartiennent au mois voisin (comptés dans la semaine, pas dans le mois).""",
     """Heures M-1 (ou Solde au …) = arrêté bureau (page ⏰ Horaires par défaut) + heures comptées en récup depuis, jusqu'à la veille de la période. Reste heures = ce solde + Récup ± de la période. Les jours grisés sont hors période (comptés dans la semaine, pas dans les totaux). Depuis 🗓 Heures, le bouton 📋 ouvre la fiche sur les dates saisies sur la ligne du salarié (sinon les dates de l'en-tête, sinon le mois)."""),
])

ESC = lambda js: js.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
FEUILLE_FIN = ESC("""          if(d && f && d <= f){
            ev.preventDefault();
            var h = a.getAttribute('href').replace(/&?mois=[0-9-]*/, '');
            window.open(h + '&du=' + d + '&au=' + f, '_blank');
          }
        });
      });
    })();""")
FICHE_JS = ESC("""          if(d && f && d <= f){
            ev.preventDefault();
            var h = a.getAttribute('href').replace(/&?mois=[0-9-]*/, '');
            window.open(h + '&du=' + d + '&au=' + f, '_blank');
          }
        });
      });
      /* 📋 fiche : même période que 📄 (dates de la ligne, sinon en-tête), dans le même onglet */
      document.querySelectorAll('a.ha-fiche').forEach(function(a){
        a.addEventListener('click', function(ev){
          var tr = a.closest('tr');
          var rdu = tr ? tr.querySelector('.ha-fx-du') : null;
          var rau = tr ? tr.querySelector('.ha-fx-au') : null;
          var d = (rdu && rdu.value) ? rdu.value : du.value;
          var f = (rau && rau.value) ? rau.value : au.value;
          if(d && f && d <= f){
            ev.preventDefault();
            location.href = a.getAttribute('href').replace(/&?mois=[0-9-]*/, '') + '&du=' + d + '&au=' + f;
          }
        });
      });
    })();""")
patch('rh_patch_7957.py', [
    ("""class="ha-feuille" style="text-decoration:none;font-size:13px;margin-left:2px;">📄</a><a t-attf-href="/heures-salarie?emp={{e.id}}&amp;mois={{mois_export}}&amp;k={{kk}}" title="Fiche mensuelle du salarié (format feuille Excel), modifiable directement" style="text-decoration:none;font-size:13px;margin-left:2px;">📋</a>""",
     """class="ha-feuille" style="text-decoration:none;font-size:13px;margin-left:2px;">📄</a><a t-attf-href="/heures-salarie?emp={{e.id}}&amp;mois={{mois_export}}&amp;k={{kk}}" title="Fiche du salarié (format feuille Excel), modifiable directement — sur les dates de la ligne si renseignées, sinon les dates de l'en-tête, sinon le mois" class="ha-fiche" style="text-decoration:none;font-size:13px;margin-left:2px;">📋</a>"""),
    ("# script\n", "# 📋 : même période que 📄\nrep(%r, %r)\n# script\n" % (FEUILLE_FIN, FICHE_JS)),
])
