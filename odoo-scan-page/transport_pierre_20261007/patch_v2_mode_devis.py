# -*- coding: utf-8 -*-
"""Écran Expédition : le mode de transport vient du devis (Xavier, 07/10/2026).
 - page : on scanne d'abord ; le cadre « Transport » affiche « Prévu au devis S… : … » et se préremplit (mode, transporteur,
   camion) ; les boutons ne servent qu'à corriger ; si le devis ne dit rien, l'écran le dit et demande le choix ;
 - relais : fiche palette avec `mode_devis_src` et `camion_devis` ; au départ, si le devis n'avait pas de mode, il reçoit
   celui choisi (et le transporteur) pour la suite (planning, suivi, statistiques).
Patche web_actions.py et expedition_setup.py (gabarit + JS) ; relancer ensuite expedition_setup.py apply."""
import io, os, sys, ast
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.abspath(os.path.join(HERE, '..', '..'))
lire = lambda p: io.open(p, encoding='utf-8', newline='').read().replace('\r\n', '\n')
ecrire = lambda p, s: io.open(p, 'w', encoding='utf-8', newline='').write(s)


def rep(s, old, new, n=1, nom=''):
    assert s.count(old) == n, 'ancre %s : %d (attendu %d) %r' % (nom, s.count(old), n, old[:70])
    return s.replace(old, new)


# ── relais ──
p = os.path.join(R, 'web_actions.py'); s = lire(p)
if 'mode_devis_src' not in s:
    s = rep(s, """        so = call('sale.order', 'read', [colis['x_commande_id'][0]],
                  fields=['name', 'partner_id', 'partner_shipping_id', 'x_mode_transport', 'x_transporteur_id', 'state'])[0]""",
            """        so = call('sale.order', 'read', [colis['x_commande_id'][0]],
                  fields=['name', 'partner_id', 'partner_shipping_id', 'x_mode_transport', 'x_transporteur_id', 'carrier_id', 'state'])[0]""", nom='read so')
    s = rep(s, """            'mode_devis': (so.get('x_mode_transport') or '') if so else '',""",
            """            'mode_devis': (so.get('x_mode_transport') or ('camions' if so.get('carrier_id') else '')) if so else '',
            'mode_devis_src': ('mode de transport du devis' if so.get('x_mode_transport') else ('méthode de livraison du devis' if so.get('carrier_id') else 'non renseigné sur le devis')) if so else 'palette sans commande',
            'camion_devis': so['carrier_id'][1] if so and so.get('carrier_id') else '',""", nom='mode_devis')
    s = rep(s, """        so = call('sale.order', 'read', [so_id], fields=['name'])[0]
        reste_of = call('mrp.production', 'search_count', [['origin', '=', so['name']], ['state', 'not in', ['done', 'cancel']]])""",
            """        so = call('sale.order', 'read', [so_id], fields=['name', 'x_mode_transport', 'x_transporteur_id'])[0]
        # le devis apprend le mode choisi au chargement s'il ne l'avait pas (et le transporteur)
        maj = {}
        if not so.get('x_mode_transport'):
            maj['x_mode_transport'] = mexp
        if mexp == 'exterieur' and tr_id and not so.get('x_transporteur_id'):
            maj['x_transporteur_id'] = tr_id
        if maj:
            _sur(lambda: call('sale.order', 'write', [so_id], maj))
        reste_of = call('mrp.production', 'search_count', [['origin', '=', so['name']], ['state', 'not in', ['done', 'cancel']]])""", nom='maj devis')
    ast.parse(s); ecrire(p, s); print('web_actions.py : mode_devis_src, camion_devis, devis mis à jour au départ')
else:
    print('web_actions.py : déjà patché')

# ── gabarit et JS de la page ──
p = os.path.join(HERE, 'expedition_setup.py'); s = lire(p)
if 'exp-devis' in s:
    print('expedition_setup.py : déjà patché'); sys.exit(0)
# 1. ordre des cadres : scan d'abord, transport ensuite (prérempli), départ
old_cadre1 = s[s.index('      <div class="exp-card">\n        <div class="exp-lbl">1. Qui transporte ?</div>'):s.index('      <div class="exp-card">\n        <div class="exp-lbl">2. Scannez les bons de colisage</div>')]
old_cadre2 = s[s.index('      <div class="exp-card">\n        <div class="exp-lbl">2. Scannez les bons de colisage</div>'):s.index('      <div class="exp-card">\n        <div class="exp-lbl">3. Départ</div>')]
new_cadre1 = old_cadre1.replace('<div class="exp-lbl">1. Qui transporte ?</div>',
                                '<div class="exp-lbl">2. Transport (prérempli depuis le devis)</div>\n        <div id="exp-devis" class="exp-devis">Scannez une palette : le mode prévu au devis s\'affichera ici.</div>')
new_cadre2 = old_cadre2.replace('<div class="exp-lbl">2. Scannez les bons de colisage</div>', '<div class="exp-lbl">1. Scannez les bons de colisage</div>')
s = s.replace(old_cadre1 + old_cadre2, new_cadre2 + new_cadre1)
# 2. style du bandeau devis
s = rep(s, "      .exp-alert{background:#92400e;color:#fef3c7;border-radius:10px;padding:8px 12px;font-weight:800;margin-top:8px;}\n",
        "      .exp-alert{background:#92400e;color:#fef3c7;border-radius:10px;padding:8px 12px;font-weight:800;margin-top:8px;}\n"
        "      .exp-devis{background:#0f172a;border:1px dashed #475569;border-radius:10px;padding:10px 12px;color:#94a3b8;font-weight:700;margin-bottom:10px;}\n"
        "      .exp-devis.ok{border-style:solid;border-color:#38bdf8;color:#e0f2fe;} .exp-devis.warn{border-color:#f59e0b;color:#fde68a;}\n", nom='css')
# 3. JS : bandeau devis, préremplissage, alerte en cas de désaccord
s = rep(s, "  function show(id, on){ var e = document.getElementById(id); if(e){ e.style.display = on ? '' : 'none'; } }\n",
        "  function show(id, on){ var e = document.getElementById(id); if(e){ e.style.display = on ? '' : 'none'; } }\n"
        "  function devisBandeau(){\n"
        "    var b = document.getElementById('exp-devis'); if(!b){ return; }\n"
        "    var p = st.palettes[0];\n"
        "    if(!p){ b.className = 'exp-devis'; b.textContent = 'Scannez une palette : le mode prévu au devis s\\'affichera ici.'; return; }\n"
        "    if(p.mode_devis){\n"
        "      var qui = p.mode_devis === 'exterieur' ? (p.transporteur_devis || 'transporteur à choisir') : (p.mode_devis === 'camions' ? (p.camion_devis || 'camion à choisir') : '');\n"
        "      var diff = st.mode && st.mode !== p.mode_devis;\n"
        "      b.className = 'exp-devis ' + (diff ? 'warn' : 'ok');\n"
        "      b.textContent = (diff ? '⚠️ Vous avez choisi « ' + (MODES[st.mode] || st.mode) + ' » mais le ' : '✅ Prévu au ') + 'devis ' + (p.commande || '') + ' : ' + (MODES[p.mode_devis] || p.mode_devis) + (qui ? ' — ' + qui : '') + ' (' + (p.mode_devis_src || '') + ')';\n"
        "    } else {\n"
        "      b.className = 'exp-devis warn'; b.textContent = '⚠️ Mode de transport non renseigné sur le devis ' + (p.commande || '') + ' : choisissez ci-dessous (le devis sera complété au départ).';\n"
        "    }\n"
        "  }\n", nom='js bandeau')
s = rep(s, "    val('exp-transporteur', st.transporteur_id || 0); val('exp-chauffeur', st.chauffeur); val('exp-par', st.charge_par || 0); val('exp-lettre', st.lettre);\n  }\n",
        "    val('exp-transporteur', st.transporteur_id || 0); val('exp-chauffeur', st.chauffeur); val('exp-par', st.charge_par || 0); val('exp-lettre', st.lettre);\n    devisBandeau();\n  }\n", nom='js renderMode')
s = rep(s, "      if(!st.mode && p.mode_devis){ st.mode = p.mode_devis; if(p.transporteur_devis_id){ st.transporteur_id = p.transporteur_devis_id; } renderMode(); setRes('✅ ' + p.name + ' ajoutée — mode prévu au devis : ' + (MODES[p.mode_devis] || p.mode_devis) + (p.transporteur_devis ? ' (' + p.transporteur_devis + ')' : ''), 'ok'); }\n"
           "      else { setRes('✅ ' + p.name + ' ajoutée (' + (p.client || '?') + ', ' + p.ton + ' kg)', 'ok'); }\n",
        "      if(!st.mode && p.mode_devis){ st.mode = p.mode_devis; if(p.transporteur_devis_id){ st.transporteur_id = p.transporteur_devis_id; } if(p.mode_devis === 'camions' && p.camion_devis){ st.camion = p.camion_devis; } renderMode(); setRes('✅ ' + p.name + ' ajoutée — transport prévu au devis : ' + (MODES[p.mode_devis] || p.mode_devis) + (p.transporteur_devis ? ' (' + p.transporteur_devis + ')' : (p.camion_devis ? ' (' + p.camion_devis + ')' : '')), 'ok'); }\n"
           "      else if(st.mode && p.mode_devis && p.mode_devis !== st.mode){ renderMode(); setRes('⚠️ ' + p.name + ' ajoutée, mais son devis prévoit « ' + (MODES[p.mode_devis] || p.mode_devis) + ' » : vérifiez le mode choisi', 'warn'); }\n"
           "      else { renderMode(); setRes('✅ ' + p.name + ' ajoutée (' + (p.client || '?') + ', ' + p.ton + ' kg)' + (p.mode_devis ? '' : ' — mode non renseigné sur le devis'), p.mode_devis ? 'ok' : 'warn'); }\n", nom='js scan')
s = rep(s, "    box.querySelectorAll('.exp-del').forEach(function(b){ b.onclick = function(){ st.palettes.splice(parseInt(b.getAttribute('data-i')), 1); save(); renderList(); }; });\n",
        "    box.querySelectorAll('.exp-del').forEach(function(b){ b.onclick = function(){ st.palettes.splice(parseInt(b.getAttribute('data-i')), 1); save(); renderList(); devisBandeau(); }; });\n", nom='js del')
ecrire(p, s); print('expedition_setup.py : cadres réordonnés, bandeau devis, préremplissage')
