# -*- coding: utf-8 -*-
"""Procédure opérateurs : ajoute le bouton « Déclôturer » du poste de scan (règle 6, fiche 3, bureau)."""
import io, os, sys
sys.stdout.reconfigure(encoding='utf-8')
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ocr', 'docs', 'build_procedures.py')
s = io.open(p, encoding='utf-8').read()
assert 'Déclôturer' not in s, 'déjà patché'
rep = [
    # règle 6
    ("Elle est verrouillée, le bon de colisage s'imprime et <b>Céline le reçoit aussitôt par mail</b> ; plus rien ne peut y être ajouté.\"),",
     "Elle est verrouillée, le bon de colisage s'imprime et <b>Céline le reçoit aussitôt par mail</b> ; plus rien ne peut y être ajouté. Erreur après la clôture ? Le bouton <b>« 🔓 Déclôturer »</b> du poste de scan la rouvre (le bureau est prévenu) : on corrige, puis on clôture à nouveau.\"),"),
    # fiche 3, étape palette clôturée
    ("rien ne peut y être ajouté ni retiré, mais le bouton <b>« Réimprimer le bon de colisage »</b> fonctionne.\",",
     "rien ne peut y être ajouté ni retiré, mais le bouton <b>« Réimprimer le bon de colisage »</b> fonctionne. Pour la modifier, appuyer sur le bouton orange <b>« 🔓 Déclôturer »</b> (voir plus bas).\","),
    # légende de la capture
    ("\"scan_cloturee\", \"Palette déjà clôturée scannée : « 🔒 Clôturée · lecture seule », contenu affiché sans corbeille, boutons de clôture grisés, « Réimprimer le bon de colisage » disponible.\")",
     "\"scan_cloturee\", \"Palette déjà clôturée scannée : « 🔒 Clôturée · lecture seule », contenu affiché sans corbeille, boutons de clôture grisés, « Réimprimer le bon de colisage » et « 🔓 Déclôturer » disponibles.\")"),
    # nouvelle section après « Clôturer la palette »
    ("story.append(Paragraph(\"Réimprimer un bon de colisage\", st_h2))",
     "story.append(Paragraph(\"Déclôturer une palette (erreur après la clôture)\", st_h2))\n"
     "steps([\n"
     "    \"Scanner la palette clôturée (ou taper son numéro) : elle s'affiche en lecture seule avec le bouton orange <b>« 🔓 Déclôturer »</b>. Appuyer dessus et confirmer. Pas de code : tout opérateur peut le faire.\",\n"
     "    \"La palette redevient <b>modifiable</b> et redevient la palette active de son opérateur (bouton ⚡ de la tablette) : retirer ou ajouter les OF, déclarer un rebut si besoin.\",\n"
     "    \"<b>Le bureau reçoit aussitôt le mail « Palette PACK… déclôturée »</b> : l'ancien bon de colisage ne vaut plus rien, jetez-le.\",\n"
     "    \"<b>Clôturer à nouveau</b> avec l'emplacement : nouveau bon de colisage à imprimer, nouveau mail à Céline.\",\n"
     "])\n"
     "story.append(Paragraph(\"Réimprimer un bon de colisage\", st_h2))"),
    # bureau : mail de déclôture
    ("    \"<b>À chaque clôture</b> (tablette ou poste de scan), Céline reçoit aussitôt le mail « Palette clôturée : PACK… »",
     "    \"Si un opérateur <b>déclôture</b> une palette au poste de scan, le bureau reçoit le mail « Palette PACK… déclôturée » : son bon de colisage n'est plus valable, un nouveau arrive à la prochaine clôture.\",\n"
     "    \"<b>À chaque clôture</b> (tablette ou poste de scan), Céline reçoit aussitôt le mail « Palette clôturée : PACK… »"),
]
for old, new in rep:
    assert s.count(old) == 1, old[:60]
    s = s.replace(old, new, 1)
s = s.replace("Ce qui a changé le 16/09/2026 :", "Ce qui a changé les 16 et 17/09/2026 : bouton « Déclôturer » au poste de scan (17/09) ;", 1)
io.open(p, 'w', encoding='utf-8').write(s)
print('build_procedures.py patché (%d remplacements)' % (len(rep) + 1))
