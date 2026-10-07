# -*- coding: utf-8 -*-
"""Procédure opérateurs : palette d'un collègue = pose et clôture possibles sur confirmation (07/10/2026).
Patche docs/build_procedures.py (règles 2 et 6, note, fiche 2 tablette, fiche 3 poste de scan, fiche 5 bureau)."""
import io, os, sys
sys.stdout.reconfigure(encoding='utf-8')
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'docs', 'build_procedures.py')
s = io.open(p, encoding='utf-8').read()
assert 'Poser quand même' not in s, 'déjà patché'
rep = [
    ("Version du 16/09/2026 : règle « une palette = un opérateur ».",
     "Version du 07/10/2026 : règle « une palette = un opérateur », pose et clôture sur la palette d'un collègue sur confirmation."),
    ('"Tablette & poste de scan · septembre 2026"', '"Tablette & poste de scan · octobre 2026"'),
    # règle 2
    ("<b>On ne pose jamais sur la palette d'un collègue.</b> L'écran la refuse : « ⛔ PACK… est la palette de … ». Besoin d'y ajouter une pierre ? Le collègue la pose lui-même, ou le bureau change le responsable.",
     "<b>La palette d'un collègue : seulement sur confirmation.</b> L'écran prévient « PACK… est la palette de … » et demande <b>« Oui, poser »</b> ou <b>« Non »</b>. Si vous confirmez, la palette reste celle du collègue et votre pose est notée. Répondez Non si ce n'est pas voulu."),
    # règle 6
    ("Erreur après la clôture ? Le bouton <b>« 🔓 Déclôturer »</b> du poste de scan la rouvre (le bureau est prévenu) : on corrige, puis on clôture à nouveau.\"),",
     "Erreur après la clôture ? Le bouton <b>« 🔓 Déclôturer »</b> du poste de scan la rouvre (le bureau est prévenu) : on corrige, puis on clôture à nouveau. La palette d'un collègue se clôture aussi, après la confirmation <b>« Oui, clôturer »</b>.\"),"),
    # note verte
    ("Message « ⛔ palette de … » ou « 🔒 clôturée » = l'écran a raison. Prenez une de vos palettes ou une palette vierge. Ne cherchez pas à contourner.",
     "« 🔒 clôturée » = l'écran a raison, prenez une autre palette. « Palette de … » = l'écran demande une confirmation : Oui seulement si c'est voulu (compléter ou fermer la palette d'un collègue absent), sinon Non."),
    # ce qui a changé
    ("Ce qui a changé les 16 et 17/09/2026 : bouton « Déclôturer »",
     "Ce qui a changé le 07/10/2026 : poser une pierre sur la palette d'un collègue, ou la clôturer, redevient possible après une confirmation à l'écran (tablette et poste de scan) ; la palette reste celle du collègue. Les 16 et 17/09/2026 : bouton « Déclôturer »"),
    # fiche 2 : intro
    ("sans passer par le poste de scan. Seules <b>vos</b> palettes sont proposées.",
     "sans passer par le poste de scan. <b>Vos</b> palettes sont proposées en premier ; celles des collègues sont dans la section « Palettes des autres opérateurs » (pose et clôture sur confirmation)."),
    ("Après chaque pose, un message vert confirme en bas de l'écran ; en cas de refus, un message rouge, sans fenêtre à fermer.",
     "Après chaque pose, un message vert confirme en bas de l'écran ; en cas de refus, un message rouge, sans fenêtre à fermer. Seule la palette d'un collègue ouvre une fenêtre de confirmation."),
    # fiche 2 : cas 2
    ("    \"« Palettes sans opérateur » : anciennes palettes ouvertes avant le 16/09, sans responsable. Le premier qui pose dessus en devient responsable.\",\n",
     "    \"« Palettes sans opérateur » : anciennes palettes ouvertes avant le 16/09, sans responsable. Le premier qui pose dessus en devient responsable.\",\n"
     "    \"« Palettes des autres opérateurs » : les palettes ouvertes des collègues, avec leur nom. On peut aussi scanner ou taper le numéro d'une de ces palettes. Dans les deux cas, la pose demande confirmation (voir ci-dessous).\",\n"),
    # fiche 2 : clôture depuis la tablette
    ("    \"Dans la liste « Mes palettes », appuyer sur le <b>cadenas 🔒</b> à droite de la palette.\",\n",
     "    \"Dans la liste « Mes palettes », appuyer sur le <b>cadenas 🔒</b> à droite de la palette. Palette d'un collègue (section « Palettes des autres opérateurs ») : la fenêtre « … est la palette de … Clôturer quand même ? » s'affiche d'abord ; appuyer sur <b>« Oui, clôturer »</b> seulement si c'est voulu.\",\n"),
    # fiche 2 : note ⛔ -> section pose sur confirmation
    ("note(\"« ⛔ PACK… est la palette de … » : vous avez scanné ou tapé la palette d'un collègue. Prenez une de vos palettes ou une palette vierge.\")",
     "story.append(Paragraph(\"Poser sur la palette d'un collègue (sur confirmation)\", st_h2))\n"
     "steps([\n"
     "    \"Choisir la palette du collègue (section « Palettes des autres opérateurs », ou scanner / taper son numéro).\",\n"
     "    \"La fenêtre <b>« 🤝 Palette d'un autre opérateur »</b> s'affiche : « PACK… est la palette de X. Poser quand même N pièce(s) de WH/OF/… dessus ? ». Appuyer sur <b>« ✅ Oui, poser »</b>, ou sur <b>« ✖ Non »</b> pour revenir à la liste. Rien n'est enregistré avant la réponse.\",\n"
     "    \"Après Oui : la pierre est posée, <b>la palette reste celle du collègue</b>, vous êtes ajouté dans « Opérateurs ayant posé », et la pose est notée sur l'OF de la pierre. Votre bouton ⚡ ne change pas.\",\n"
     "    \"Retirer une pierre de la palette d'un collègue ne se fait pas depuis la tablette : au poste de scan (corbeille 🗑️) ou par le bureau.\",\n"
     "])\n"
     "note(\"Cette confirmation sert à éviter les erreurs de palette : si vous n'aviez pas l'intention de poser sur la palette d'un collègue, répondez Non et prenez une de vos palettes ou une palette vierge.\")"),
    # fiche 3 : scan des OF
    ("sur la palette d'un autre opérateur, l'écran refuse (⛔) — scannez la palette de cet opérateur ou une palette vierge.",
     "sur la palette d'un autre opérateur, l'écran prévient (⛔ « … est la palette de … — cette pierre est de … ») et propose <b>« ✅ Poser quand même »</b> : appuyer dessus pour confirmer (la palette reste à son opérateur, la pose est notée sur l'OF), ou scanner une autre palette pour annuler."),
    ("\"scan_refus\", \"Refus ⛔ : la pierre scannée est d'un autre opérateur que celui de la palette active.\")",
     "\"scan_refus\", \"Avertissement ⛔ : la pierre scannée est d'un autre opérateur que celui de la palette active. Depuis le 07/10, une fenêtre propose « ✅ Poser quand même » ou « ✖ Non ».\")"),
    # fiche 5 : bureau
    ("    \"Le champ « Opérateurs ayant posé » garde l'historique de tous ceux qui ont posé dessus (lecture seule).\",\n",
     "    \"Le champ « Opérateurs ayant posé » garde l'historique de tous ceux qui ont posé dessus (lecture seule), y compris un collègue qui a posé sur confirmation ; dans ce cas une note « 🤝 … confirmé » est aussi dans le fil de l'OF de la pierre.\",\n"),
]
for old, new in rep:
    assert s.count(old) == 1, 'ancre introuvable ou multiple : ' + old[:70]
    s = s.replace(old, new, 1)
io.open(p, 'w', encoding='utf-8').write(s)
print('build_procedures.py patché (%d remplacements)' % len(rep))
