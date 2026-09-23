# -*- coding: utf-8 -*-
"""Page salarié /mes-heures (vue 7956) : saisie directe récup / sans solde, heures sup en récup par défaut, textes explicites.
  python rh_patch_7956.py            -> écrit vue_7956_NEW.xml seulement
  python rh_patch_7956.py test|prod  -> + écriture de l'arch dans Odoo (vue 7956)"""
import io, os, sys
sys.stdout.reconfigure(encoding='utf-8')
SRC = 'vue_7956_mes_heures.xml'
lines = io.open(SRC, encoding='utf-8').read().split('\n')


def find(sub, start=0, expect=1):
    idx = [i for i in range(start, len(lines)) if sub in lines[i]]
    assert len(idx) == expect, (sub[:80], idx)
    return idx[0]


def replace_lines(i0, i1, new):
    """remplace lines[i0..i1] inclus par la liste new"""
    global lines
    lines = lines[:i0] + new + lines[i1 + 1:]


def esc_js(js):
    return js.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# ── 1. CSS ───────────────────────────────────────────────────────────────────
i = find('      .mh-b-rec{background:#e0f2fe;color:#075985;}')
replace_lines(i, i, [lines[i],
    '      .mh-b-ss{background:#fee2e2;color:#991b1b;}',
    '      .mh-day.t-sans_solde{border-left-color:#dc2626;background:#fecaca;}',
    '      .mh-day.t-sans_solde .mh-state{color:#7f1d1d;}',
    '      .mh-day.t-sans_solde .mh-theo{color:#991b1b;}',
    '      .mh-hint{font-size:12px;color:#64748b;font-weight:600;margin:2px 0 4px;}',
    '      .mh-ctrl{margin-top:7px;border-radius:9px;padding:7px 10px;font-size:13px;font-weight:800;line-height:1.35;}',
    '      .mh-ctrl.ok{background:#dcfce7;color:#166534;}',
    '      .mh-ctrl.warn{background:#fef3c7;color:#92400e;}',
    '      .mh-ctrl.bad{background:#fee2e2;color:#991b1b;}',
    '      .mh-ctrl.info{background:#f1f5f9;color:#475569;font-weight:600;}',
    '      .mh-manque{margin-top:7px;border:1.5px dashed #f59e0b;border-radius:10px;padding:8px 10px;background:#fffbeb;}',
    '      .mh-manque .t{font-size:12.5px;font-weight:900;color:#92400e;margin-bottom:5px;}',
    '      .mh-manque .q{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px;}',
    '      .mh-q{border:none;border-radius:9px;padding:7px 10px;font-weight:800;font-size:12.5px;cursor:pointer;}',
    '      .mh-q-rec{background:#e0f2fe;color:#075985;}',
    '      .mh-q-ss{background:#fee2e2;color:#991b1b;}',
    '      .mh-manque label{display:flex;align-items:center;gap:7px;font-size:13px;font-weight:800;color:#334155;margin:4px 0;}',
    '      .mh-manque input{width:76px;margin-left:auto;border:1.5px solid #cbd5e1;border-radius:8px;padding:5px 6px;font-weight:800;text-align:center;font-size:15px;}',
    '      .mh-lock.l-sans_solde{background:#fee2e2;color:#991b1b;}'])
i = find('      .mh-cal td.c-recup .dn{color:#075985;}')
replace_lines(i, i, [lines[i],
    '      .mh-cal td.c-sans_solde{background:#fecaca;}',
    '      .mh-cal td.c-sans_solde .dn{color:#991b1b;} .mh-cal td.c-sans_solde .val{color:#7f1d1d !important;}'])

# ── 2. bandeau semaine ───────────────────────────────────────────────────────
i0 = find('<div class="mh-tot" id="mh-tot">')
i1 = find('ℹ️ Vous saisissez uniquement vos') + 1
assert lines[i1].strip() == '</div>'
replace_lines(i0, i1, [
    '          <div class="mh-tot" id="mh-tot">Travaillé <b id="mh-t-eff">–</b> · Horaire <b id="mh-t-theo">–</b> · 🔄 Récup semaine <b id="mh-t-hs">–</b></div>',
    '          <div style="background:#fff;border-radius:10px;padding:8px 12px;margin-bottom:10px;color:#475569;font-size:12.5px;font-weight:600;line-height:1.45;">',
    '            ℹ️ <b>Chaque jour, enregistrez vos heures</b> — bouton <b>« ✓ Journée normale »</b> si vous avez fait votre horaire habituel.<br/>',
    '            ➕ Heures faites <b>en plus</b> : ajoutées automatiquement à vos <b>heures à récupérer</b>.<br/>',
    '            ➖ Heures faites <b>en moins</b> : dites si c\'est de la <b>🔄 récup</b> (retirée de vos heures à récupérer) ou du <b>🚫 sans solde</b> (non payé).<br/>',
    '            🌴 Congés payés : <b>« Demander des congés »</b> en bas de page (validés par le bureau). Maladie, fériés, absences : enregistrés par le bureau.',
    '          </div>'])

# ── 3. totaux du mois ────────────────────────────────────────────────────────
i0 = find('<t t-set="mm_eff" t-value=')
i1 = find('<div class="mh-tot">Effectué <b><t t-esc="\'%.2f\' % mm_eff"/>')
replace_lines(i0, i1, [
    '          <t t-set="mm_eff" t-value="sum(r.x_heures for r in mrows if r.x_type == \'travail\')"/>',
    '          <t t-set="mm_theo" t-value="sum(r.x_theo for r in mrows if r.x_type in (\'travail\', \'recup\', \'sans_solde\'))"/>',
    '          <t t-set="mm_delta" t-value="sum(r.x_hs for r in mrows if r.x_type in (\'travail\', \'recup\', \'sans_solde\'))"/>',
    '          <t t-set="mm_cp" t-value="len([r for r in mrows if r.x_type == \'cp\'])"/>',
    '          <t t-set="mm_mal" t-value="len([r for r in mrows if r.x_type == \'maladie\'])"/>',
    '          <t t-set="mm_fer" t-value="len([r for r in mrows if r.x_type == \'ferie\'])"/>',
    '          <t t-set="mm_rec" t-value="len([r for r in mrows if r.x_type == \'recup\'])"/>',
    '          <t t-set="mm_ss" t-value="len([r for r in mrows if r.x_type == \'sans_solde\'])"/>',
    '          <t t-set="mm_abs" t-value="len([r for r in mrows if r.x_type == \'absence\'])"/>',
    '          <div class="mh-tot">Travaillé <b><t t-esc="\'%.2f\' % mm_eff"/> h</b> · Horaire <b><t t-esc="\'%.2f\' % mm_theo"/> h</b> · 🔄 Récup <b><t t-esc="(\'+\' if mm_delta &gt;= 0 else \'\') + (\'%.2f\' % mm_delta)"/> h</b><t t-if="mm_cp"> · 🌴 <b><t t-esc="mm_cp"/></b></t><t t-if="mm_mal"> · 🤒 <b><t t-esc="mm_mal"/></b></t><t t-if="mm_fer"> · 🎉 <b><t t-esc="mm_fer"/></b></t><t t-if="mm_rec"> · 🔄 <b><t t-esc="mm_rec"/> j</b></t><t t-if="mm_ss"> · 🚫 <b><t t-esc="mm_ss"/> j</b></t><t t-if="mm_abs"> · ⛔ <b><t t-esc="mm_abs"/></b></t></div>'])

# ── 4. calendrier du mois ────────────────────────────────────────────────────
i = find('<t t-elif="s and s.x_type == \'travail\'"><div class="val" style="color:#15803d;"><t t-esc="\'%g\' % round(s.x_heures, 2)"/> h</div></t>')
lines[i] = '                            <t t-elif="s and s.x_type == \'travail\'"><div class="val" style="color:#15803d;"><t t-esc="\'%g\' % round(s.x_heures, 2)"/> h<t t-if="s.x_h_recup"> 🔄</t><t t-if="s.x_h_sans_solde"> 🚫</t></div></t>'
i = find('<t t-elif="s and s.x_type == \'recup\'"><div class="val" style="color:#075985;">🔄 Récup</div></t>')
replace_lines(i, i, [lines[i], '                            <t t-elif="s and s.x_type == \'sans_solde\'"><div class="val" style="color:#7f1d1d;">🚫 Ss solde</div></t>'])
i = find('<b style="color:#d97706;">!</b> = jour ouvré passé sans saisie · gris = pas d\'horaire prévu.')
lines[i] = lines[i].replace('gris = pas d\'horaire prévu.', 'gris = pas d\'horaire prévu · 🔄 / 🚫 = récup ou sans solde ce jour-là.')

# ── 5. carte du jour (vue semaine) ───────────────────────────────────────────
i0 = find('        <t t-foreach="range(7)" t-as="i">')
i1 = find('<button type="button" class="mh-save" data-act="save">💾 Enregistrer ces heures</button>') + 3
assert lines[i1].strip() == '</t>' and lines[i1 - 1].strip() == '</div>' and lines[i1 - 2].strip() == '</t>', lines[i1 - 2:i1 + 1]
CARD = r'''        <t t-foreach="range(7)" t-as="i">
          <t t-set="d" t-value="monday + datetime.timedelta(days=i)"/>
          <t t-set="dstr" t-value="d.strftime('%Y-%m-%d')"/>
          <t t-set="morn" t-value="[a for a in cal.attendance_ids if a.dayofweek == str(i) and not a.display_type and a.day_period == 'morning' and (not cal.two_weeks_calendar or not a.week_type or a.week_type == wt)]"/>
          <t t-set="aft" t-value="[a for a in cal.attendance_ids if a.dayofweek == str(i) and not a.display_type and a.day_period in ('afternoon',) and (not cal.two_weeks_calendar or not a.week_type or a.week_type == wt)]"/>
          <t t-set="tmd" t-value="min([a.hour_from for a in morn]) if morn else 0"/>
          <t t-set="tmf" t-value="max([a.hour_to for a in morn]) if morn else 0"/>
          <t t-set="tad" t-value="min([a.hour_from for a in aft]) if aft else 0"/>
          <t t-set="taf" t-value="max([a.hour_to for a in aft]) if aft else 0"/>
          <t t-set="theo" t-value="(tmf - tmd) + (taf - tad)"/>
          <t t-set="s" t-value="saisies.get(dstr)"/>
          <t t-set="fmt" t-value="lambda h: '%02d:%02d' % (int(h), round((h - int(h)) * 60)) if h else ''"/>
          <!-- congé, maladie, férié, absence, repos : posés par le bureau, non modifiables ici.
               Travail, récup, sans solde : le salarié saisit lui-même (heures sup en récup par défaut). -->
          <t t-set="lock" t-value="s and s.x_type in ('cp', 'maladie', 'ferie', 'absence', 'repos')"/>
          <t t-set="stype" t-value="(s and s.x_type) or ''"/>
          <t t-set="s_theo" t-value="s.x_theo if (s and s.x_type in ('travail', 'recup', 'sans_solde')) else theo"/>
          <div t-attf-class="mh-day t-{{stype or 'vide'}}" t-att-data-date="dstr" t-att-data-type="stype" t-att-data-theo="'%.4f' % s_theo" t-att-data-tmd="fmt(tmd)" t-att-data-tmf="fmt(tmf)" t-att-data-tad="fmt(tad)" t-att-data-taf="fmt(taf)" t-att-data-heures="s and ('%.4f' % s.x_heures) or ''" t-att-data-hs="s and ('%.4f' % s.x_hs) or ''">
            <div class="mh-dh">
              <span class="mh-dname"><t t-esc="jours[i]"/> <t t-esc="d.strftime('%d/%m')"/></span>
              <span class="mh-state" t-att-data-role="'state'">
                <t t-if="s">
                  <t t-if="s.x_type == 'travail'">✓ <t t-esc="('%.2f' % s.x_heures).replace('.', ',')"/> h<t t-if="s.x_h_recup"> + 🔄 <t t-esc="('%.2f' % s.x_h_recup).replace('.', ',')"/> h récup</t><t t-if="s.x_h_sans_solde"> + 🚫 <t t-esc="('%.2f' % s.x_h_sans_solde).replace('.', ',')"/> h sans solde</t><t t-if="s.x_decouchage"> · 🛏</t></t>
                  <t t-elif="s.x_type == 'cp'">🌴 Congés</t>
                  <t t-elif="s.x_type == 'maladie'">🤒 Maladie</t>
                  <t t-elif="s.x_type == 'ferie'">🎉 Férié</t>
                  <t t-elif="s.x_type == 'absence'">⛔ Absence</t>
                  <t t-elif="s.x_type == 'recup'">🔄 Récup (journée)</t>
                  <t t-elif="s.x_type == 'sans_solde'">🚫 Sans solde (journée)</t>
                  <t t-else="">💤 Repos</t>
                </t>
                <t t-else="">—</t>
              </span>
            </div>
            <div class="mh-theo" t-if="theo &gt; 0">Horaire habituel : <t t-esc="fmt(tmd)"/>-<t t-esc="fmt(tmf)"/><t t-if="taf"> / <t t-esc="fmt(tad)"/>-<t t-esc="fmt(taf)"/></t> (<t t-esc="('%.2f' % theo).replace('.', ',')"/> h)</div>
            <div class="mh-theo" t-else="">Pas d'horaire prévu ce jour</div>
            <t t-set="jdemi" t-value="bool(s and s.x_type == 'travail' and s.x_note and '— ' in s.x_note and ('(demande' in s.x_note or '(bureau)' in s.x_note or 'congé partiel' in s.x_note))"/>
            <t t-if="jdemi">
              <t t-set="jdlbl" t-value="(s.x_note or '').split(' — ')[0]"/>
              <div t-attf-class="mh-lock {{'l-recup' if jdlbl == 'Récupération' else ('l-cp' if jdlbl == 'Congés payés' else ('l-maladie' if jdlbl == 'Maladie' else ('l-ferie' if jdlbl == 'Férié' else 'l-absence')))}}">
                <span style="font-size:20px;">
                  <t t-if="jdlbl == 'Récupération'">🔄</t>
                  <t t-elif="jdlbl == 'Congés payés'">🌴</t>
                  <t t-elif="jdlbl == 'Maladie'">🤒</t>
                  <t t-elif="jdlbl == 'Férié'">🎉</t>
                  <t t-else="">⛔</t>
                </span>
                <span><t t-esc="s.x_note.split(' (')[0]"/><small>Le reste de la journée est en travail — saisissez vos heures ci-dessous.</small></span>
              </div>
            </t>
            <t t-if="lock">
              <div t-attf-class="mh-lock l-{{s.x_type}}">
                <span style="font-size:20px;">
                  <t t-if="s.x_type == 'cp'">🌴</t>
                  <t t-elif="s.x_type == 'maladie'">🤒</t>
                  <t t-elif="s.x_type == 'ferie'">🎉</t>
                  <t t-elif="s.x_type == 'absence'">⛔</t>
                  <t t-else="">💤</t>
                </span>
                <span>
                  <t t-if="s.x_type == 'cp'">Congés payés</t>
                  <t t-elif="s.x_type == 'maladie'">Arrêt maladie</t>
                  <t t-elif="s.x_type == 'ferie'">Jour férié</t>
                  <t t-elif="s.x_type == 'absence'">Absence</t>
                  <t t-else="">Repos</t>
                  <small>Enregistré par le bureau — pas d'heures à renseigner. En cas d'erreur, prévenez le bureau.</small>
                </span>
              </div>
            </t>
            <t t-elif="verrou and dstr &lt;= verrou">
              <div class="mh-lock l-repos">
                <span style="font-size:20px;">🔒</span>
                <span>Journée verrouillée
                  <small>La paie de cette période est établie : plus de modification possible ici. Contactez le bureau pour toute correction.</small>
                </span>
              </div>
            </t>
            <t t-else="">
              <t t-if="s and s.x_type in ('recup', 'sans_solde')">
                <div t-attf-class="mh-lock l-{{s.x_type}}">
                  <span style="font-size:20px;"><t t-if="s.x_type == 'recup'">🔄</t><t t-else="">🚫</t></span>
                  <span><t t-if="s.x_type == 'recup'">Journée entière de récupération (<t t-esc="('%.2f' % s.x_theo).replace('.', ',')"/> h retirées de vos heures à récupérer)</t><t t-else="">Journée entière sans solde (<t t-esc="('%.2f' % s.x_theo).replace('.', ',')"/> h non payées)</t>
                    <small>Erreur ? Cliquez « ✓ Journée normale » ou saisissez vos heures : la journée sera remplacée.</small></span>
                </div>
              </t>
              <div class="mh-btns" t-if="theo &gt; 0">
                <button type="button" class="mh-b mh-b-ok" data-act="normal">✓ Journée normale</button>
                <button type="button" class="mh-b mh-b-rec" data-act="recup">🔄 Toute la journée en récup</button>
                <button type="button" class="mh-b mh-b-ss" data-act="ss">🚫 Toute la journée sans solde</button>
              </div>
              <div class="mh-hint" t-if="theo &gt; 0">« Journée normale » = horaire habituel enregistré d'un clic. Sinon, saisissez vos heures :</div>
              <div class="mh-times">
                <label>Matin</label>
                <input type="time" data-f="m_deb" t-att-value="s and s.x_type == 'travail' and fmt(s.x_m_deb) or ''"/>
                <input type="time" data-f="m_fin" t-att-value="s and s.x_type == 'travail' and fmt(s.x_m_fin) or ''"/>
                <label>Ap.-midi</label>
                <input type="time" data-f="am_deb" t-att-value="s and s.x_type == 'travail' and fmt(s.x_am_deb) or ''"/>
                <input type="time" data-f="am_fin" t-att-value="s and s.x_type == 'travail' and fmt(s.x_am_fin) or ''"/>
              </div>
              <label style="display:flex;align-items:center;gap:7px;font-size:13px;font-weight:700;color:#334155;margin:6px 0 2px;cursor:pointer;">
                <input type="checkbox" data-f="decouchage" t-att-checked="'checked' if (s and s.x_decouchage) else None" style="width:17px;height:17px;"/>
                🛏 Découchage (nuit en déplacement)
              </label>
              <div class="mh-ctrl info" data-role="ctrl"></div>
              <div class="mh-manque" data-role="manque" style="display:none;">
                <div class="t">Heures manquantes : de quoi s'agit-il ?</div>
                <div class="q">
                  <button type="button" class="mh-q mh-q-rec" data-act="q-recup">🔄 Tout en récup</button>
                  <button type="button" class="mh-q mh-q-ss" data-act="q-ss">🚫 Tout sans solde</button>
                </div>
                <label>🔄 Heures prises en récup
                  <input type="number" data-f="h_recup" step="0.25" min="0" max="12" placeholder="0" t-att-value="('%g' % s.x_h_recup) if (s and s.x_type == 'travail' and s.x_h_recup) else ''"/> h
                </label>
                <label>🚫 Heures sans solde (non payées)
                  <input type="number" data-f="h_ss" step="0.25" min="0" max="12" placeholder="0" t-att-value="('%g' % s.x_h_sans_solde) if (s and s.x_type == 'travail' and s.x_h_sans_solde) else ''"/> h
                </label>
              </div>
              <button type="button" class="mh-save" data-act="save">💾 Enregistrer cette journée</button>
            </t>
          </div>
        </t>'''
replace_lines(i0, i1, CARD.split('\n'))

# ── 6. compteurs « Mes congés » ──────────────────────────────────────────────
i0 = find('<!-- ===== Mes congés (compteurs période 01/06')
i1 = find('<t t-set="rec_h_periode" t-value=')
TILES = r'''        <!-- ===== Mes congés (compteurs période 01/06 → 31/05) ===== -->
        <t t-set="per_start" t-value="datetime.date(today.year if today.month &gt;= 6 else today.year - 1, 6, 1)"/>
        <t t-set="per_rows" t-value="request.env['x_heures_jour'].sudo().search([('x_employee_id','=',emp.id),('x_date','&gt;=',per_start.strftime('%Y-%m-%d')),('x_date','&lt;=',today.strftime('%Y-%m-%d'))])"/>
        <t t-set="n_cp" t-value="len(per_rows.filtered(lambda r: r.x_type == 'cp'))"/>
        <t t-set="cp_ref" t-value="emp.x_cp_ref_date"/>
        <t t-set="n_cp_deduit" t-value="len(per_rows.filtered(lambda r: r.x_type == 'cp' and (not cp_ref or r.x_date &gt; cp_ref)))"/>
        <t t-set="n_rec" t-value="len(per_rows.filtered(lambda r: r.x_type == 'recup'))"/>
        <t t-set="n_ss" t-value="len(per_rows.filtered(lambda r: r.x_type == 'sans_solde'))"/>
        <t t-set="n_mal" t-value="len(per_rows.filtered(lambda r: r.x_type == 'maladie'))"/>
        <t t-set="n_abs" t-value="len(per_rows.filtered(lambda r: r.x_type == 'absence'))"/>
        <!-- Heures à récupérer = arrêté bureau (à la date de référence) + heures comptées chaque jour depuis (x_hs :
             heures faites en plus +, récup prise ou heures manquantes −, sans solde neutre) + heures ajoutées par le bureau -->
        <t t-set="rl_all" t-value="request.env['x_recup_ligne'].sudo().search([('x_employee_id','=',emp.id)], order='x_date desc, id desc')"/>
        <t t-set="rl_add" t-value="sum(rl_all.filtered(lambda l: not cp_ref or l.x_date &gt; cp_ref).mapped('x_heures'))"/>
        <t t-set="rec_delta" t-value="sum(per_rows.filtered(lambda r: r.x_type in ('travail', 'recup', 'sans_solde') and (not cp_ref or r.x_date &gt; cp_ref)).mapped('x_hs'))"/>
        <t t-set="rec_solde" t-value="(emp.x_recup_solde or 0.0) + rl_add + rec_delta"/>
        <t t-set="rec_h_periode" t-value="sum(per_rows.mapped('x_h_recup'))"/>
        <t t-set="ss_h_periode" t-value="sum(per_rows.mapped('x_h_sans_solde'))"/>
        <t t-set="plus_periode" t-value="sum([max(r.x_heures - r.x_theo, 0.0) for r in per_rows if r.x_type == 'travail' and not r.x_hs_payees])"/>'''
replace_lines(i0, i1, TILES.split('\n'))

i0 = find('<!-- la récup se prend en jours, demi-journées ou heures : la tuile affiche les deux unités -->') - 1
assert 'background:#E0F2FE' in lines[i0]
i1 = find('<div t-elif="not n_rec and rec_part_rows"') + 1
assert lines[i1].strip() == '</div>'
replace_lines(i0, i1, r'''            <div style="background:#E0F2FE;border-radius:10px;padding:8px 10px;text-align:center;">
              <div style="font-size:22px;font-weight:900;color:#075985;"><t t-esc="'%g' % round(rec_h_periode, 2)"/> h</div>
              <div style="font-size:11px;font-weight:800;color:#075985;">🔄 Récups prises</div>
              <div t-if="n_rec" style="font-size:10px;color:#0369a1;">dont <t t-esc="n_rec"/> journée(s) entière(s)</div>
            </div>
            <div t-if="ss_h_periode" style="background:#FEE2E2;border-radius:10px;padding:8px 10px;text-align:center;">
              <div style="font-size:22px;font-weight:900;color:#991b1b;"><t t-esc="'%g' % round(ss_h_periode, 2)"/> h</div>
              <div style="font-size:11px;font-weight:800;color:#991b1b;">🚫 Sans solde</div>
              <div t-if="n_ss" style="font-size:10px;color:#b91c1c;">dont <t t-esc="n_ss"/> journée(s) entière(s)</div>
            </div>'''.split('\n'))

i0 = find('🔄 Heures à récupérer : détail du solde')
i1 = i0 + 2
assert lines[i1].strip() == '</div>', lines[i1]
replace_lines(i0, i1, r'''          <div style="margin-top:5px;font-size:11px;font-weight:700;color:#64748b;">🔄 Heures à récupérer : comment c'est calculé
            <div style="font-size:10.5px;color:#94a3b8;font-weight:700;">= arrêté bureau <t t-esc="('+' if (emp.x_recup_solde or 0) &gt; 0 else '') + ('%g' % (emp.x_recup_solde or 0))"/> h<t t-if="cp_ref"> au <t t-esc="cp_ref.strftime('%d/%m')"/></t><t t-if="rl_add"> + <t t-esc="'%g' % rl_add"/> h ajoutées par le bureau</t> <t t-esc="('+' if rec_delta &gt;= 0 else '−')"/> <t t-esc="'%g' % abs(round(rec_delta, 2))"/> h comptées depuis (heures faites en plus − récups prises − heures manquantes ; le sans solde ne compte pas)</div>
          </div>'''.split('\n'))

# ── 7. « Mon mois » ──────────────────────────────────────────────────────────
i = find('<t t-set="m_theo" t-value="sum(m_rows.filtered(lambda r: r.x_type == \'travail\').mapped(\'x_theo\'))"/>')
replace_lines(i, i, [
    '        <t t-set="m_theo" t-value="sum(m_rows.filtered(lambda r: r.x_type in (\'travail\', \'recup\', \'sans_solde\')).mapped(\'x_theo\'))"/>',
    '        <t t-set="m_delta" t-value="sum(m_rows.filtered(lambda r: r.x_type in (\'travail\', \'recup\', \'sans_solde\')).mapped(\'x_hs\'))"/>'])
i = find('<div style="font-size:11px;font-weight:800;color:#64748b;">théorique saisi</div>')
lines[i] = lines[i].replace('théorique saisi', 'horaire prévu')
i = find('{{\'#ECFDF5\' if m_eff &gt;= m_theo else \'#FEF3C7\'}}')
lines[i] = lines[i].replace('{{\'#ECFDF5\' if m_eff &gt;= m_theo else \'#FEF3C7\'}}', '{{\'#ECFDF5\' if m_delta &gt;= 0 else \'#FEF3C7\'}}')
i = find('{{\'#047857\' if m_eff &gt;= m_theo else \'#92400e\'}};"><t t-esc="(\'+\' if m_eff &gt;= m_theo else \'\') + (\'%.1f\' % (m_eff - m_theo))"/> h')
lines[i] = lines[i].replace('{{\'#047857\' if m_eff &gt;= m_theo else \'#92400e\'}};"><t t-esc="(\'+\' if m_eff &gt;= m_theo else \'\') + (\'%.1f\' % (m_eff - m_theo))"/> h',
                            '{{\'#047857\' if m_delta &gt;= 0 else \'#92400e\'}};"><t t-esc="(\'+\' if m_delta &gt;= 0 else \'\') + (\'%.1f\' % m_delta)"/> h')
i = find('<div style="font-size:11px;font-weight:800;color:#64748b;">écart</div>')
lines[i] = lines[i].replace('>écart<', '>🔄 compté en récup<')

# ── 8. demandes de congés : CP et congés spéciaux uniquement ─────────────────
i = find('🌴 Demander des congés / 🔄 une récup')
lines[i] = lines[i].replace('🌴 Demander des congés / 🔄 une récup', '🌴 Demander des congés')
i = find('Congés payés, récupération (journée, demi-journée ou horaires précis), sans solde')
lines[i] = '          <div style="color:#94a3b8;font-size:11.5px;font-weight:700;margin-bottom:10px;">Congés payés et congés spéciaux (maternité, paternité, événement familial, enfant malade) : la demande part au bureau pour validation. <b style="color:#64748b;">La récup et le sans solde ne se demandent plus</b> : enregistrez-les directement sur la journée concernée (boutons 🔄 / 🚫 ci-dessus).</div>'
i = find('<option value="recup">Récupération (poser des heures à récupérer)</option>')
assert '<option value="sans_solde">Sans solde</option>' in lines[i + 1]
replace_lines(i, i + 1, [])

# ── 9. script ────────────────────────────────────────────────────────────────
i0 = find("  var LBL = {travail:'✓', cp:'🌴 Congés'")
i1 = find("    save(card, 'travail', toDec(inp.m_deb.value), toDec(inp.m_fin.value), toDec(inp.am_deb.value), toDec(inp.am_fin.value));") + 1
assert lines[i1].strip() == '});', lines[i1]
JS = r'''  var LBL = {travail:'✓', cp:'🌴 Congés', maladie:'🤒 Maladie', ferie:'🎉 Férié', absence:'⛔ Absence', recup:'🔄 Récup (journée)', sans_solde:'🚫 Sans solde (journée)', repos:'💤 Repos'};
  /* jours dont l'horaire et l'écart entrent dans le solde « à récupérer » (les congés, maladie, fériés, absences non) */
  var SOLDE = {'':1, travail:1, recup:1, sans_solde:1};
  function fr(h){ return (Math.round(h*100)/100).toFixed(2).replace('.', ','); }
  function totals(){
    if(!document.getElementById('mh-t-eff')){ return; }
    var eff=0, theo=0, delta=0;
    document.querySelectorAll('.mh-day').forEach(function(c){
      var ty = c.getAttribute('data-type') || '';
      if(SOLDE[ty]){ theo += parseFloat(c.getAttribute('data-theo')||0); delta += parseFloat(c.getAttribute('data-hs')||0); }
      if(ty === 'travail'){ eff += parseFloat(c.getAttribute('data-heures')||0); }
    });
    document.getElementById('mh-t-eff').textContent = fr(eff)+' h';
    document.getElementById('mh-t-theo').textContent = fr(theo)+' h';
    document.getElementById('mh-t-hs').textContent = (delta>=0?'+':'')+fr(delta)+' h';
  }
  function inputs(card){ var o = {}; card.querySelectorAll('input[data-f]').forEach(function(i){ o[i.getAttribute('data-f')] = i; }); return o; }
  function num(i){ if(!i || i.value === ''){ return 0; } var v = parseFloat(String(i.value).replace(',', '.')); return isNaN(v) ? 0 : v; }
  function q4(v){ return Math.round(v*4)/4; }
  /* ligne de contrôle : ce que donne la journée, en clair, avant d'enregistrer */
  function calc(card){
    var inp = inputs(card); var ctrl = card.querySelector('[data-role=ctrl]'); var mq = card.querySelector('[data-role=manque]');
    if(!inp.m_deb || !ctrl){ return null; }
    var theo = parseFloat(card.getAttribute('data-theo')||0);
    var H = Math.max(toDec(inp.m_fin.value)-toDec(inp.m_deb.value),0) + Math.max(toDec(inp.am_fin.value)-toDec(inp.am_deb.value),0);
    var R = num(inp.h_recup), S = num(inp.h_ss);
    var manque = Math.max(theo - H, 0);
    var res = {H:H, R:R, S:S, theo:theo, ok:true};
    var txt = '', cls = 'info', show = false;
    if(theo <= 0){
      if(H > 0){ txt = '✅ ' + fr(H) + ' h travaillées un jour sans horaire prévu : <b>+' + fr(H) + ' h</b> ajoutées à vos heures à récupérer.'; cls = 'ok'; }
      else { txt = 'Pas d\'horaire prévu ce jour : saisissez vos heures seulement si vous avez travaillé.'; }
    } else if(R + S > manque + 0.01){
      txt = '❌ Vous indiquez ' + fr(R) + ' h de récup et ' + fr(S) + ' h sans solde, mais il ne manque que ' + fr(manque) + ' h par rapport à l\'horaire (' + fr(theo) + ' h prévues, ' + fr(H) + ' h travaillées). Réduisez ces heures.';
      cls = 'bad'; res.ok = false; show = true;
    } else if(H <= 0.01 && R <= 0 && S <= 0){
      txt = '👉 Saisissez vos heures d\'arrivée et de départ, ou utilisez un bouton ci-dessus.';
    } else if(H > theo + 0.01){
      txt = '✅ ' + fr(H) + ' h travaillées pour ' + fr(theo) + ' h prévues : <b>+' + fr(H - theo) + ' h</b> ajoutées à vos heures à récupérer.';
      cls = 'ok';
    } else if(manque - R - S <= 0.01){
      txt = '✅ ' + fr(H) + ' h travaillées' + (R ? ' + ' + fr(R) + ' h de récup' : '') + (S ? ' + ' + fr(S) + ' h sans solde' : '') + ' = ' + fr(theo) + ' h : journée complète.';
      cls = 'ok'; show = !!(R || S);
    } else {
      var reste = manque - R - S;
      txt = '⚠️ Il manque <b>' + fr(reste) + ' h</b> sur les ' + fr(theo) + ' h prévues (' + fr(H) + ' h travaillées' + (R ? ', ' + fr(R) + ' h de récup' : '') + (S ? ', ' + fr(S) + ' h sans solde' : '') + '). Précisez ci-dessous : récup ou sans solde ? Sinon ces heures seront retirées de vos heures à récupérer.';
      cls = 'warn'; show = true;
    }
    ctrl.innerHTML = txt; ctrl.className = 'mh-ctrl ' + cls;
    if(mq){ mq.style.display = show ? '' : 'none'; }
    return res;
  }
  document.querySelectorAll('.mh-day').forEach(function(c){ calc(c); });
  document.addEventListener('input', function(e){ var card = e.target.closest('.mh-day'); if(card && e.target.matches('input[data-f]')){ calc(card); } });
  totals();
  /* Enregistrement via le relais Render, PAS /web/dataset/call_kw : cette page
     est consultée sans compte Odoo (lien signé), et call_kw est réservé aux
     utilisateurs connectés au backend — chaque sauvegarde échouait en
     « Session expired » sur les téléphones des salariés. */
  var RPC = 'https://ocr-pesee-webhook.onrender.com/heures/rpc';
  function rpcAction(actionId, ctx){
    return fetch(RPC,{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({action_id:actionId, ctx:ctx})});
  }
  function handleErr(d){
    var m = (d.error && ((d.error.data && d.error.data.message) || d.error.message)) || '';
    if(/jeton|token/i.test(m)){
      alert("Votre lien personnel n'est plus valide (il a peut-être été régénéré). Demandez un nouveau lien à votre responsable.");
      return;
    }
    alert('Échec : ' + m);
  }
  function save(card, typ, md, mf, ad, af, R, S){
    var ctx = {active_model:'x_heures_jour', hj_emp:EMP, hj_token:TOK, hj_date:card.getAttribute('data-date'), hj_type:typ,
               hj_m_deb:md, hj_m_fin:mf, hj_am_deb:ad, hj_am_fin:af,
               hj_h_recup:(typ === 'travail' ? (R || 0) : 0), hj_h_ss:(typ === 'travail' ? (S || 0) : 0)};
    var dec = card.querySelector('input[data-f=decouchage]');
    ctx.hj_decouchage = (dec && dec.checked) ? 1 : 0;
    card.style.opacity = .5;
    rpcAction(2012, ctx).then(function(r){return r.json();}).then(function(d){
      card.style.opacity = 1;
      if(d.error){ handleErr(d); return; }
      var res = d.result || {}; var ty = res.type || typ;
      card.setAttribute('data-type', ty);
      card.setAttribute('data-heures', res.heures || 0);
      card.setAttribute('data-hs', res.hs || 0);
      if(res.theo !== undefined){ card.setAttribute('data-theo', res.theo); }
      card.className = 'mh-day t-'+ty;
      var st = card.querySelector('[data-role="state"]');
      var inp = inputs(card);
      if(ty === 'travail'){
        st.textContent = '✓ ' + fr(res.heures||0) + ' h' + (res.h_recup ? ' + 🔄 ' + fr(res.h_recup) + ' h récup' : '') + (res.h_ss ? ' + 🚫 ' + fr(res.h_ss) + ' h sans solde' : '');
        if(inp.h_recup){ inp.h_recup.value = res.h_recup ? String(res.h_recup) : ''; }
        if(inp.h_ss){ inp.h_ss.value = res.h_ss ? String(res.h_ss) : ''; }
      } else {
        st.textContent = LBL[ty] || ty;
        card.querySelectorAll('.mh-times input').forEach(function(i){ i.value=''; });
        if(inp.h_recup){ inp.h_recup.value = ''; }
        if(inp.h_ss){ inp.h_ss.value = ''; }
      }
      calc(card); totals();
      var ok = card.querySelector('.mh-save');
      if(ok){ ok.textContent = '✓ Journée enregistrée'; ok.style.background = '#15803d'; setTimeout(function(){ ok.textContent = '💾 Enregistrer cette journée'; ok.style.background = ''; }, 2000); }
      if(ty !== 'travail'){ setTimeout(function(){ location.reload(); }, 900); }
      if(navigator.vibrate){ try{ navigator.vibrate(60); }catch(e){} }
    }).catch(function(e){ card.style.opacity = 1; alert('Échec réseau'); });
  }
  document.addEventListener('click', function(e){
    var b = e.target.closest('.mh-b, .mh-save, .mh-q'); if(!b){ return; }
    var card = b.closest('.mh-day'); var act = b.getAttribute('data-act');
    var inp = inputs(card);
    if(!inp.m_deb){ return; }
    var dn = card.querySelector('.mh-dname') ? card.querySelector('.mh-dname').textContent : card.getAttribute('data-date');
    var theo = parseFloat(card.getAttribute('data-theo')||0);
    if(act === 'normal'){
      inp.m_deb.value = card.getAttribute('data-tmd'); inp.m_fin.value = card.getAttribute('data-tmf');
      inp.am_deb.value = card.getAttribute('data-tad'); inp.am_fin.value = card.getAttribute('data-taf');
      if(inp.h_recup){ inp.h_recup.value = ''; }
      if(inp.h_ss){ inp.h_ss.value = ''; }
      save(card, 'travail', toDec(inp.m_deb.value), toDec(inp.m_fin.value), toDec(inp.am_deb.value), toDec(inp.am_fin.value), 0, 0);
      return;
    }
    if(act === 'recup'){
      if(!confirm('Enregistrer le ' + dn + ' comme journée ENTIÈRE de récupération ?\n' + fr(theo) + ' h seront retirées de vos heures à récupérer.')){ return; }
      save(card, 'recup', 0, 0, 0, 0, 0, 0); return;
    }
    if(act === 'ss'){
      if(!confirm('Enregistrer le ' + dn + ' comme journée ENTIÈRE sans solde ?\n' + fr(theo) + ' h ne seront pas payées.')){ return; }
      save(card, 'sans_solde', 0, 0, 0, 0, 0, 0); return;
    }
    if(act === 'q-recup' || act === 'q-ss'){
      var r0 = calc(card); if(!r0){ return; }
      var reste = q4(Math.max(r0.theo - r0.H, 0));
      if(inp.h_recup){ inp.h_recup.value = (act === 'q-recup' && reste) ? String(reste) : ''; }
      if(inp.h_ss){ inp.h_ss.value = (act === 'q-ss' && reste) ? String(reste) : ''; }
      calc(card); return;
    }
    if(act !== 'save'){ return; }
    var r1 = calc(card); if(!r1){ return; }
    if(!r1.ok){ alert('Corrigez les heures de récup / sans solde : elles dépassent les heures manquantes de la journée.'); return; }
    if(r1.R < 0 || r1.S < 0 || r1.R > 12 || r1.S > 12){ alert('Heures de récup / sans solde : entre 0 et 12 h.'); return; }
    save(card, 'travail', toDec(inp.m_deb.value), toDec(inp.m_fin.value), toDec(inp.am_deb.value), toDec(inp.am_fin.value), q4(r1.R), q4(r1.S));
  });'''
replace_lines(i0, i1, esc_js(JS).split('\n'))

# l'ancien bloc totals()/RPC/handleErr/save avait été remplacé : vérifier qu'il n'en reste pas une 2e copie
out = '\n'.join(lines)
for sub in ('function totals()', 'function save(', "var RPC = ", 'function handleErr(', 'data-act="normal"', 'data-f="h_recup"', 'data-f="h_ss"'):
    assert out.count(sub) == 1, (sub, out.count(sub))
assert 'input[data-f=recup]' not in out and 'hj_recup' not in out
import xml.dom.minidom
xml.dom.minidom.parseString(out.encode('utf-8'))   # XML bien formé
io.open('vue_7956_NEW.xml', 'w', encoding='utf-8', newline='\n').write(out)
print('vue_7956_NEW.xml :', len(out), 'chars, XML OK')

mode = (sys.argv[1] if len(sys.argv) > 1 else '').lower()
if mode in ('test', 'prod'):
    import ssl, xmlrpc.client
    U, D = ('https://testmaq230926v2.odoo.com', 'testmaq230926v2') if mode == 'test' else ('https://maquignon.odoo.com', 'maquignon')
    us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
    c = ssl.create_default_context()
    uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common', context=c).authenticate(D, us, p, {})
    m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object', context=c)
    arch = out.replace('https://ocr-pesee-webhook.onrender.com/heures/rpc', 'http://127.0.0.1:5055/heures/rpc') if mode == 'test' else out
    m.execute_kw(D, uid, p, 'ir.ui.view', 'write', [[7956], {'arch_db': arch}])
    chk = m.execute_kw(D, uid, p, 'ir.ui.view', 'read', [[7956], ['arch_db']])[0]['arch_db']
    print(mode, ': vue 7956 écrite,', len(chk), 'chars')
