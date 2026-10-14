# -*- coding: utf-8 -*-
"""Page « Mes heures » (/mes-heures, vue website 7956) : remplace les champs <input type="time"> par un sélecteur
d'heure intégré à la page (grille heures + minutes, boutons Effacer / Annuler / OK toujours visibles).
Motif (Xavier, 14/10/2026) : sur certains téléphones Android le sélecteur natif de Chrome déborde à droite et son
bouton de validation est caché (police du téléphone agrandie) ; la page n'a aucune prise sur ce sélecteur natif.
Les champs restent des <input> à valeur « HH:MM » : le script existant (calculs, enregistrement) est inchangé.

   python patch_mes_heures_picker.py test     -> page de test locale test_picker.html (sans Odoo)
   python patch_mes_heures_picker.py dry      -> lit la vue en prod, transforme, vérifie, écrit vue_7956_new.xml (rien modifié)
   python patch_mes_heures_picker.py apply    -> idem + sauvegarde backup_7956_<horodatage>.xml + écriture dans Odoo
   python patch_mes_heures_picker.py retour   -> réécrit la dernière sauvegarde (annulation)
Identifiants attendus dans l'environnement : ODOO_USER, ODOO_PWD (dry/apply/retour)."""
import os, re, sys, glob, html, time, xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
ICI = os.path.dirname(os.path.abspath(__file__))
MODE = (sys.argv[1] if len(sys.argv) > 1 else 'dry').lower()
VUE = 7956
CSS = open(os.path.join(ICI, 'picker_css.txt'), encoding='utf-8').read()
HTML = open(os.path.join(ICI, 'picker_html.txt'), encoding='utf-8').read()
JS = open(os.path.join(ICI, 'picker_js.txt'), encoding='utf-8').read()
MARQUEUR_CSS = '      /* ===== Vue ordinateur automatique'
MARQUEUR_HTML = '        <div t-att-data-emp="emp.id"'
INPUT_NEUF = '<input type="text" class="mh-hr" readonly="readonly" inputmode="none" placeholder="--:--" '


def xml_esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def transforme(arch):
    if 'id="mh-hp"' in arch:
        raise SystemExit('la vue contient déjà le sélecteur : rien à faire')
    a, n1 = re.subn(r'\.mh-plage input\[type=time\]\{', '.mh-plage input.mh-hr{', arch)
    assert n1 == 1, 'règle CSS .mh-plage introuvable (%d)' % n1
    assert a.count(MARQUEUR_CSS) == 1, 'marqueur CSS introuvable'
    a = a.replace(MARQUEUR_CSS, CSS + MARQUEUR_CSS)
    a, n2 = re.subn(r'<input type="time" ', INPUT_NEUF, a)
    assert n2 == 10, '10 champs heure attendus, %d trouvés' % n2
    assert a.count(MARQUEUR_HTML) == 1, 'marqueur HTML introuvable'
    a = a.replace(MARQUEUR_HTML, HTML + '        <script>\n' + xml_esc(JS) + '        </script>\n' + MARQUEUR_HTML)
    ET.fromstring(a.encode('utf-8'))  # XML valide ?
    return a


def page_test():
    src = open(os.path.join(ICI, 'vue_7956.xml'), encoding='utf-8').read()
    css = html.unescape(re.search(r'<style>(.*?)</style>', src, re.S).group(1))
    css = css.replace('.mh-plage input[type=time]{', '.mh-plage input.mh-hr{') + CSS
    champ = lambda f, v='': '<input type="text" class="mh-hr" readonly="readonly" inputmode="none" placeholder="--:--" data-f="%s" value="%s"/>' % (f, v)
    carte = lambda nom, v: ('<div class="mh-day t-%s" data-date="2026-10-14"><div class="mh-dh"><span class="mh-dname">%s</span><span class="mh-state">%s</span></div>'
                            '<div class="mh-times"><label>Matin</label>%s%s<label>Ap.-midi</label>%s%s</div>'
                            '<details class="mh-manque" open=""><summary class="t">🔄 Récup ou 🚫 sans solde pris dans la journée ? (facultatif)</summary>'
                            '<div class="mh-plage">ou de %s à %s <span>(le créneau est retiré de vos heures)</span></div></details>'
                            '<button type="button" class="mh-save">💾 Enregistrer cette journée</button></div>'
                            % ('travail' if v else 'vide', nom, '✓ 7,50 h' if v else '—', champ('m_deb', v and '07:30'), champ('m_fin', v and '12:00'),
                               champ('am_deb', v and '13:30'), champ('am_fin', v and '17:00'), champ('recup_de'), champ('recup_a')))
    doc = ('<!doctype html><html lang="fr"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>'
           '<title>Test sélecteur heures</title><style>body{margin:0;font-family:system-ui,Segoe UI,Roboto,sans-serif;}*{box-sizing:border-box;}' + css + '</style></head><body>'
           '<div class="mh-wrap"><div class="mh-head"><span class="mh-emp">Test sélecteur</span></div>' + carte('mercredi 14/10', '') + carte('mardi 13/10', '1')
           + '<div style="display:flex;gap:8px;align-items:center;background:#fff;padding:10px;border-radius:10px;"><span>de</span>'
           '<input type="text" class="mh-hr" readonly="readonly" inputmode="none" placeholder="--:--" id="mh-dc-hde" style="border:1.5px solid #cbd5e1;border-radius:8px;padding:6px;font-weight:700;flex:1;"/><span>à</span>'
           '<input type="text" class="mh-hr" readonly="readonly" inputmode="none" placeholder="--:--" id="mh-dc-ha" style="border:1.5px solid #cbd5e1;border-radius:8px;padding:6px;font-weight:700;flex:1;"/></div>'
           '<pre id="log" style="background:#fff;padding:8px;border-radius:8px;font-size:12px;min-height:60px;">événements :\n</pre>' + HTML
           + '</div><script>' + JS + '</script><script>'
           'document.addEventListener("input",function(e){document.getElementById("log").textContent+="input "+(e.target.getAttribute("data-f")||e.target.id)+" = "+JSON.stringify(e.target.value)+"\\n";});'
           'document.addEventListener("change",function(e){document.getElementById("log").textContent+="change "+(e.target.getAttribute("data-f")||e.target.id)+" = "+JSON.stringify(e.target.value)+"\\n";});'
           '</script></body></html>')
    fn = os.path.join(ICI, 'test_picker.html'); open(fn, 'w', encoding='utf-8').write(doc); print('page de test :', fn)


if MODE == 'test':
    page_test(); sys.exit()
import xmlrpc.client
U = 'https://maquignon.odoo.com'; D = 'maquignon'; us = os.environ['ODOO_USER']; p = os.environ['ODOO_PWD']
uid = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/common').authenticate(D, us, p, {})
assert uid, 'authentification refusée'
m = xmlrpc.client.ServerProxy(U + '/xmlrpc/2/object')
x = lambda mo, me, *a, **k: m.execute_kw(D, uid, p, mo, me, list(a), k)
if MODE == 'retour':
    sauv = sorted(glob.glob(os.path.join(ICI, 'backup_%d_*.xml' % VUE)))
    assert sauv, 'aucune sauvegarde'
    arch = open(sauv[-1], encoding='utf-8').read()
    x('ir.ui.view', 'write', [VUE], {'arch': arch})
    relu = x('ir.ui.view', 'read', [VUE], ['arch_db'])[0]['arch_db']
    print('vue %d restaurée depuis %s : %d caractères, sélecteur présent : %s' % (VUE, os.path.basename(sauv[-1]), len(relu), 'id="mh-hp"' in relu)); sys.exit()
v = x('ir.ui.view', 'read', [VUE], ['name', 'key', 'arch_db', 'write_date'])[0]
print('vue %d %s (%s), modifiée le %s, %d caractères' % (VUE, v['name'], v['key'], v['write_date'], len(v['arch_db'])))
neuf = transforme(v['arch_db'])
open(os.path.join(ICI, 'vue_%d_new.xml' % VUE), 'w', encoding='utf-8').write(neuf)
print('transformation OK : %d caractères, champs convertis : %d, XML valide' % (len(neuf), neuf.count('class="mh-hr"')))
if MODE != 'apply':
    print('Simulation : rien modifié dans Odoo (vue_%d_new.xml écrite). Relancer avec « apply ».' % VUE); sys.exit()
sauv = os.path.join(ICI, 'backup_%d_%s.xml' % (VUE, time.strftime('%Y%m%d_%H%M%S')))
open(sauv, 'w', encoding='utf-8').write(v['arch_db']); print('sauvegarde :', sauv)
x('ir.ui.view', 'write', [VUE], {'arch': neuf})
relu = x('ir.ui.view', 'read', [VUE], ['arch_db', 'write_date'])[0]
print('écrit : %d caractères, modifiée le %s, sélecteur présent : %s, champs time restants : %d'
      % (len(relu['arch_db']), relu['write_date'], 'id="mh-hp"' in relu['arch_db'], relu['arch_db'].count('type="time"')))
