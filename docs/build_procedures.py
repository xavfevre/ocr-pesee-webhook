# -*- coding: utf-8 -*-
"""Procédures opérateurs — atelier pierre Maquignon (tablette + poste de scan).
Version du 16/09/2026 : règle « une palette = un opérateur ».
Génère procedures_operateurs.pdf dans le dossier courant (python docs/build_procedures.py depuis docs/)."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle, PageBreak)
from reportlab.lib.styles import ParagraphStyle

TEAL = colors.HexColor("#01666B")
INK = colors.HexColor("#0F172A")
GREY = colors.HexColor("#64748B")
ORANGE = colors.HexColor("#B45309")
RED = colors.HexColor("#B4232A")
GREEN = colors.HexColor("#15803D")
LIGHT = colors.HexColor("#EAF4F4")
AMBERL = colors.HexColor("#FBEBD3")
GREENL = colors.HexColor("#DCFCE7")

st_h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=14, textColor=TEAL,
                       leading=18, spaceBefore=10, spaceAfter=4)
st_step = ParagraphStyle("s", fontName="Helvetica", fontSize=11.5, textColor=INK, leading=16,
                         leftIndent=24, firstLineIndent=-24, spaceAfter=5)
st_txt = ParagraphStyle("t", fontName="Helvetica", fontSize=11.5, textColor=INK, leading=16, spaceAfter=5)
st_rule = ParagraphStyle("r", fontName="Helvetica-Bold", fontSize=14.5, textColor=INK, leading=19,
                         leftIndent=34, firstLineIndent=-34, spaceAfter=9)
st_small = ParagraphStyle("sm", fontName="Helvetica", fontSize=9.5, textColor=GREY, leading=12)

W, H = A4
MARG = 16 * mm


def header_footer(canv, doc):
    canv.saveState()
    canv.setFillColor(TEAL)
    canv.rect(0, H - 22 * mm, W, 22 * mm, stroke=0, fill=1)
    canv.setFillColor(colors.white)
    canv.setFont("Helvetica-Bold", 15)
    canv.drawString(MARG, H - 14 * mm, "SARL MAQUIGNON — Procédures atelier pierre")
    canv.setFont("Helvetica", 9)
    canv.drawRightString(W - MARG, H - 14 * mm, "Tablette & poste de scan · septembre 2026")
    canv.setFillColor(GREY)
    canv.setFont("Helvetica", 8.5)
    canv.drawString(MARG, 9 * mm, "En cas de blocage : appeler le bureau. Ne jamais forcer une action refusée par l'écran.")
    canv.drawRightString(W - MARG, 9 * mm, "Page %d" % doc.page)
    canv.restoreState()


doc = BaseDocTemplate("procedures_operateurs.pdf", pagesize=A4,
                      leftMargin=MARG, rightMargin=MARG,
                      topMargin=26 * mm, bottomMargin=14 * mm)
frame = Frame(MARG, 14 * mm, W - 2 * MARG, H - 40 * mm, id="f")
doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=header_footer)])

story = []


def sect(txt, color=TEAL):
    t = Table([[Paragraph('<font color="white"><b>%s</b></font>' % txt,
                          ParagraphStyle("b", fontName="Helvetica-Bold", fontSize=13.5,
                                         textColor=colors.white, leading=17))]],
              colWidths=[W - 2 * MARG])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 6),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                           ("ROUNDEDCORNERS", [6, 6, 6, 6])]))
    story.append(t)
    story.append(Spacer(1, 6))


def steps(items):
    for i, it in enumerate(items, 1):
        story.append(Paragraph("<b>%d.</b>  %s" % (i, it), st_step))


def note(txt, bg=AMBERL, fg=ORANGE):
    t = Table([[Paragraph(txt, ParagraphStyle("nn", fontName="Helvetica-Bold", fontSize=10.5,
                                              textColor=fg, leading=14))]],
              colWidths=[W - 2 * MARG])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 5),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.append(Spacer(1, 2))
    story.append(t)
    story.append(Spacer(1, 6))


# ───────────────────────── PAGE 0 — LES RÈGLES PALETTES (affiche) ─────────────────────────
sect("LES 6 RÈGLES PALETTES — à afficher à l'atelier et au poste de scan", GREEN)
story.append(Spacer(1, 4))
regles = [
    ("1", "<b>Une palette = un opérateur.</b> La première pierre que vous posez (ou le premier scan d'une palette vierge) fait de vous le <b>responsable</b> de la palette. Elle apparaît ensuite dans « Mes palettes »."),
    ("2", "<b>On ne pose jamais sur la palette d'un collègue.</b> L'écran la refuse : « ⛔ PACK… est la palette de … ». Besoin d'y ajouter une pierre ? Le collègue la pose lui-même, ou le bureau change le responsable."),
    ("3", "<b>Sur la tablette, choisissez toujours votre nom</b> avant d'agir (le dernier nom choisi reste affiché : vérifiez-le). <b>Au poste de scan, pas de nom</b> : c'est l'OF scanné qui dit à qui est la pierre."),
    ("4", "<b>Votre palette active vous suit.</b> Le bouton ⚡ de la tablette montre la dernière palette sur laquelle vos pierres ont été posées, depuis la tablette ou depuis le poste de scan."),
    ("5", "<b>Palette neuve = étiquette PACK pré-imprimée.</b> Scannez-la (ou tapez son numéro, ex. 440) : elle devient la vôtre. Ne réutilisez jamais une étiquette d'une palette déjà partie."),
    ("6", "<b>Palette pleine → clôturer avec l'emplacement</b> (Stock Atelier / Stock Usine). Elle est verrouillée, le bon de colisage s'imprime, plus rien ne peut y être ajouté."),
]
for num, txt in regles:
    story.append(Paragraph('<font color="#15803D"><b>%s</b></font>   %s' % (num, txt), st_rule))
note("Message « ⛔ palette de … » ou « 🔒 clôturée » = l'écran a raison. Prenez une de vos palettes ou une palette vierge. Ne cherchez pas à contourner.", bg=GREENL, fg=GREEN)
story.append(Paragraph("Ce qui a changé le 16/09/2026 : sur la tablette chacun ne voit plus que ses palettes (plus de liste « palettes des autres ») et la dernière palette n'est plus mémorisée sur la tablette mais sur votre nom. Au poste de scan, plus de nom à choisir : la palette affichée est celle du poste, et l'OF scanné dit à qui est la pierre.", st_small))

# ───────────────────────── PAGE 1 — MA PRODUCTION ─────────────────────────
story.append(PageBreak())
sect("FICHE 1 — MA PRODUCTION (tablette) : faire les pierres")
story.append(Paragraph("Ouvrir la tablette sur <b>Ma production</b> et choisir son nom dans la liste en haut.", st_step))
story.append(Paragraph("Trouver sa pierre", st_h2))
steps([
    "Les cartes sont triées par n° d'OF (ou par date de début). Utiliser les <b>filtres</b> du haut : client, réf. commande, machine, palette — ou les cases « rentre dans (tous sens) » pour trouver les pierres qui tiennent dans un gabarit.",
    "La <b>couleur du bandeau</b> de chaque carte = le type de pierre (bleu = Tuffeau, vert = Haims, orange = Migné, magenta = Tervoux, turquoise = Richemont, jaune = Sireuil).",
    "Sur la carte : dimensions (long × larg × haut), nombre de pièces, réf. pierre (losange), client, réf. commande, n° de prépalettisation, note atelier, plans PDF.",
])
story.append(Paragraph("Faire la pierre", st_h2))
steps([
    "Appuyer sur <b>« Démarrer »</b> quand on commence la pierre (le temps est compté à partir de là).",
    "OF à plusieurs pièces : compter au fur et à mesure avec <b>« +1 pièce »</b>. Les pièces comptées peuvent partir sur palette avant la fin de l'OF (bouton « Palettiser (N faites) »).",
    "Quand la pierre est finie, appuyer sur <b>« Terminer »</b> puis confirmer. La carte devient grisée et propose la mise en palette.",
    "En cas d'erreur, <b>« Annuler Terminé »</b> remet l'OF en cours.",
])
note("IMPORTANT : toujours Démarrer / Terminer au moment réel — c'est ce qui calcule les temps par pierre et le planning de l'atelier.")

# ───────────────────────── PAGE 2 — MISE EN PALETTE ─────────────────────────
story.append(PageBreak())
sect("FICHE 2 — METTRE LES PIERRES EN PALETTE (depuis la tablette)")
story.append(Paragraph("Dès qu'une pierre est faite, la carte propose la mise en palette, sans passer par le poste de scan. Seules <b>vos</b> palettes sont proposées.", st_step))
story.append(Paragraph("Une pierre est finie quand sa <b>dernière opération</b> est terminée. S'il reste une opération (ex. taille après sciage), la carte de l'Historique affiche « ⏭ Reste à faire : … » : la mise en palette se fait après cette opération (ou, pour des pièces comptées avec « +1 pièce », par « Palettiser (N faites) » depuis Ma production).", st_step))
story.append(Paragraph("Cas 1 — même palette que la pierre précédente", st_h2))
steps([
    "Appuyer sur le bouton vert <b>⚡ PACK…</b> (votre palette active) : la pierre part directement dessus. Une seule pression, terminé.",
    "OF à plusieurs pièces : le pavé « Combien sur la palette ? » demande le nombre (ou « Tout »).",
])
story.append(Paragraph("Cas 2 — choisir ou changer de palette", st_h2))
steps([
    "Appuyer sur <b>« Mettre au colis »</b> (ou « Palettiser (N faites) ») : la liste <b>« Mes palettes »</b> s'affiche, avec pour chacune : nombre d'OF, m³, kg, client, réf. commande et prépalettisation.",
    "Toucher la palette voulue. Pour une <b>palette neuve</b> : scanner le code-barre de son étiquette (📷) ou taper son numéro dans la case, puis Entrée — elle devient la vôtre.",
    "« Palettes sans opérateur » : anciennes palettes ouvertes avant le 16/09, sans responsable. Le premier qui pose dessus en devient responsable.",
])
story.append(Paragraph("Clôturer une palette pleine (depuis la tablette)", st_h2))
steps([
    "Dans la liste « Mes palettes », appuyer sur le <b>cadenas 🔒</b> à droite de la palette.",
    "Choisir l'emplacement : <b>Stock Atelier</b> ou <b>Stock Usine</b>.",
    "Le bon de colisage s'imprime et la palette est verrouillée (plus rien ne peut y être ajouté). Votre bouton ⚡ l'oublie automatiquement.",
])
note("« ⛔ PACK… est la palette de … » : vous avez scanné ou tapé la palette d'un collègue. Prenez une de vos palettes ou une palette vierge.")

# ───────────────────────── PAGE 3 — POSTE DE SCAN ─────────────────────────
story.append(PageBreak())
sect("FICHE 3 — POSTE DE SCAN : remplir une palette à la douchette")
story.append(Paragraph("Le poste de scan sert à composer les palettes en scannant. Pas de nom à choisir : l'ordre est toujours <b>palette → pierres → emplacement</b>.", st_step))
steps([
    "<b>Scanner la palette</b> (étiquette PACK…) ou appuyer sur <b>« Palettes ouvertes… »</b> et la toucher dans la liste. L'écran affiche à qui elle est (« Palette de … ») ou « Palette vierge ». Vérifiez toujours la palette affichée avant de scanner des pierres.",
    "<b>Scanner les OF</b> un par un (code-barre de la fiche OF ou de la tablette). C'est l'OF qui dit à qui est la pierre : sur une palette vierge, la première pierre attribue la palette à son opérateur ; sur la palette d'un autre opérateur, l'écran refuse (⛔) — scannez la palette de cet opérateur ou une palette vierge.",
    "L'OF doit être terminé (dernière opération faite) ou ses pièces comptées sur la tablette.",
    "OF à plusieurs pièces : le pavé « Combien sur cette palette ? » s'affiche — taper le nombre puis Valider, « Tout », ou scanner directement la suite pour tout mettre.",
    "Erreur de scan ? <b>« Retirer dernier OF »</b>, ou la corbeille 🗑️ en face de la ligne concernée. Pierre cassée ? le bouton 💥 (Fiche 4).",
])
story.append(Paragraph("Clôturer la palette", st_h2))
steps([
    "Scanner le <b>code-barre d'emplacement</b> (Stock Atelier / Stock Usine) affiché à l'écran, ou toucher le bouton bleu correspondant, puis confirmer.",
    "La palette est verrouillée, l'emplacement enregistré, le stock déplacé, et le <b>bon de colisage s'ouvre</b> pour impression (commande, objet, prépalettisation, adresse de livraison, opérateur).",
    "Après la clôture, l'écran n'a plus de palette active : scannez la suivante.",
])
story.append(Paragraph("Réimprimer un bon de colisage", st_h2))
steps([
    "Palette encore ouverte : la rendre active puis appuyer sur <b>« Bon de colisage »</b> (bouton bleu sous la palette active).",
    "Palette déjà clôturée : demander au bureau (Inventaire → Colis → Imprimer → Bon de colisage).",
])
note("Plusieurs personnes peuvent se succéder au poste de scan : la palette active est celle affichée à l'écran. Avant de scanner des pierres, regardez de qui est la palette affichée, ou scannez la bonne.")

# ───────────────────────── PAGE 4 — REBUTS ─────────────────────────
story.append(PageBreak())
sect("FICHE 4 — DÉCLARER UN REBUT (pierre cassée)", RED)
story.append(Paragraph("Une pierre cassée doit TOUJOURS être déclarée : la déclaration relance automatiquement un OF pour la refaire, met à jour la palette et prévient le bureau.", st_step))
story.append(Paragraph("Où trouver le bouton « Rebut »", st_h2))
steps([
    "<b>Tablette — Ma production</b> : sur la carte d'un OF terminé (casse à la fabrication ou juste après).",
    "<b>Tablette — Historique</b> : sur n'importe quelle carte des jours précédents (casse découverte après coup, palette qui tombe…).",
    "<b>Poste de scan</b> : le bouton 💥 en face de chaque ligne du contenu de la palette (casse à la mise en palette).",
])
story.append(Paragraph("La déclaration, pas à pas", st_h2))
steps([
    "Appuyer sur <b>« Rebut »</b>.",
    "Indiquer le <b>nombre de pierres cassées</b> (ou « Toutes » si toute la série est perdue).",
    "Choisir le <b>motif</b> : Casse fabrication · Casse manutention · Palette tombée · Défaut pierre — ou taper un autre motif.",
    "Valider. L'écran confirme : <b>« OF relancé : WH/OF/xxxxx »</b>.",
])
story.append(Paragraph("Ce qui se passe automatiquement", st_h2))
steps([
    "Les pierres cassées sont <b>retirées de la palette</b> (le reste de l'OF y demeure) et sorties du stock.",
    "Un <b>nouvel OF identique</b> (mêmes cotes, même réf. pierre, même prépalettisation) est créé et confirmé : il apparaît dans le planning et sur la tablette pour être refait.",
    "Le bureau voit le motif, la date et le lien entre les deux OF.",
])
note("Palette tombée entière : déclarer le rebut OF par OF depuis l'Historique (filtre « colis » pour retrouver toutes les pierres de la palette).", bg=colors.HexColor("#F9E4E5"), fg=RED)

# ───────────────────────── PAGE 5 — BUREAU ─────────────────────────
story.append(PageBreak())
sect("FICHE 5 — POUR LE BUREAU : suivre et réattribuer les palettes", ORANGE)
story.append(Paragraph("Dans Odoo : <b>Inventaire → Produits → Colis</b>. La liste montre pour chaque palette l'<b>Opérateur</b> responsable, si elle est clôturée et son emplacement.", st_txt))
story.append(Paragraph("Changer le responsable d'une palette (opérateur absent, erreur de nom…)", st_h2))
steps([
    "Ouvrir la palette (PACK…) et modifier le champ <b>Opérateur (responsable de la palette)</b>. Effacer le champ = palette « sans opérateur » : le premier qui pose dessus la reprend.",
    "Le champ « Opérateurs ayant posé » garde l'historique de tous ceux qui ont posé dessus (lecture seule).",
    "La palette active d'un opérateur se règle sur sa fiche employé, champ <b>Palette active (poste de scan)</b> ; elle se remet à jour toute seule à la prochaine pose.",
])
story.append(Paragraph("Étiquettes de palettes vierges", st_h2))
steps([
    "Inventaire → Colis → <b>Générer des colis</b> (quantité) crée des numéros PACK vierges ; imprimer leurs étiquettes et les agrafer sur les palettes vides.",
    "Une palette vierge n'a pas d'opérateur : elle est prise par le premier qui la scanne. Elle n'apparaît dans aucune liste tant qu'elle est vide.",
])
story.append(Paragraph("Bon de colisage", st_h2))
steps([
    "Le bon de colisage (imprimé à la clôture, ou Imprimer → Bon de colisage) mentionne désormais l'<b>opérateur</b> responsable, en plus de la commande, du client, de la prépalettisation et de l'emplacement.",
    "À la clôture, un mail « Bon de colisage » part automatiquement au bureau.",
])
story.append(Spacer(1, 8))
story.append(Paragraph("Rappels généraux", st_h2))
steps([
    "Les compteurs de la tablette (pierres faites, m³, poids) se mettent à jour tout seuls — ne rien saisir à la main.",
    "Un doute, un message d'erreur qui insiste, une palette introuvable : appeler le bureau plutôt que de bricoler.",
])

doc.build(story)
print("procedures_operateurs.pdf généré")
