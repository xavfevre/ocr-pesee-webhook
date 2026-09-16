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


import os
from reportlab.platypus import Image
from reportlab.lib.utils import ImageReader
CAPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captures")
st_cap = ParagraphStyle("cap", fontName="Helvetica-Oblique", fontSize=9, textColor=GREY, leading=11.5, spaceAfter=6)


def _img(name, width, max_h=118 * mm):
    path = os.path.join(CAPT, name + ".png")
    if not os.path.exists(path):
        return None
    iw, ih = ImageReader(path).getSize()
    h = width * ih / iw
    if h > max_h:
        width, h = max_h * iw / ih, max_h
    im = Image(path, width=width, height=h)
    im.hAlign = "CENTER"
    return im


def capture(name, caption):
    """Une capture pleine largeur, encadrée, avec sa légende."""
    im = _img(name, W - 2 * MARG - 8)
    if im is None:
        return
    t = Table([[im], [Paragraph(caption, st_cap)]], colWidths=[W - 2 * MARG])
    t.setStyle(TableStyle([("BOX", (0, 0), (0, 0), 0.6, GREY), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    story.append(Spacer(1, 3)); story.append(t); story.append(Spacer(1, 4))


def captures2(a, cap_a, b, cap_b):
    """Deux captures côte à côte."""
    wcol = (W - 2 * MARG - 8) / 2
    ia, ib = _img(a, wcol - 6, max_h=95 * mm), _img(b, wcol - 6, max_h=95 * mm)
    if ia is None and ib is None:
        return
    if ia is None or ib is None:
        capture(a if ia else b, cap_a if ia else cap_b)
        return
    t = Table([[ia, ib], [Paragraph(cap_a, st_cap), Paragraph(cap_b, st_cap)]], colWidths=[wcol, wcol])
    t.setStyle(TableStyle([("BOX", (0, 0), (0, 0), 0.6, GREY), ("BOX", (1, 0), (1, 0), 0.6, GREY),
                           ("VALIGN", (0, 0), (-1, 0), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    story.append(Spacer(1, 3)); story.append(t); story.append(Spacer(1, 4))


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
    ("6", "<b>Palette pleine → clôturer avec l'emplacement</b> (Stock Atelier / Stock Usine). Elle est verrouillée, le bon de colisage s'imprime et <b>Céline le reçoit aussitôt par mail</b> ; plus rien ne peut y être ajouté."),
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
capture("tablette_ma_production", "Tablette, onglet Ma production : nom de l'opérateur en haut, filtres, puis une carte par opération avec les boutons Démarrer / Terminer, le compteur « +1 pièce » et « Palettiser (N faites) ».")

# ───────────────────────── PAGE 2 — MISE EN PALETTE ─────────────────────────
story.append(PageBreak())
sect("FICHE 2 — METTRE LES PIERRES EN PALETTE (depuis la tablette)")
story.append(Paragraph("Dès qu'une pierre est faite, la carte propose la mise en palette, sans passer par le poste de scan. Seules <b>vos</b> palettes sont proposées.", st_step))
story.append(Paragraph("Une pierre est finie quand sa <b>dernière opération</b> est terminée. S'il reste une opération (ex. taille après sciage), la carte de l'Historique affiche « ⏭ Reste à faire : … ». Les pièces déjà comptées avec « +1 pièce » peuvent partir sur palette avant la fin : bouton <b>« Palettiser (N faites) »</b>, sur Ma production comme sur l'Historique.", st_step))
story.append(Paragraph("Chaque palette affiche une <b>jauge de poids</b> (verte, orange à partir de 80 %, rouge au-delà du seuil de 1 500 kg réglable par le bureau) et le bouton ⚡ indique le poids déjà posé. Après chaque pose, un message vert confirme en bas de l'écran ; en cas de refus, un message rouge, sans fenêtre à fermer.", st_step))
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
    "<b>Au même moment, Céline reçoit le mail « Palette clôturée : PACK… »</b> avec le bon de colisage en pièce jointe (client, emplacement, cubage, tonnage) : inutile de la prévenir.",
])
captures2("tablette_pave_quantite", "Pavé « Combien sur la palette ? » : nombre de pièces à poser (ou « Tout »), puis « Choisir la palette ».",
          "tablette_choisir_palette", "Choix de la palette : « Mes palettes » seulement avec leur jauge de poids, case pour scanner ou taper le n° d'une palette vierge, cadenas 🔒 pour clôturer, bouton 🔑 Responsable.")
note("« ⛔ PACK… est la palette de … » : vous avez scanné ou tapé la palette d'un collègue. Prenez une de vos palettes ou une palette vierge.")
capture("tablette_historique", "Onglet Historique : les opérations terminées par jour ; quand il reste une opération, la carte indique « ⏭ Reste à faire : … » à la place du bouton « Mettre au colis ».")

# ───────────────────────── PAGE 3 — POSTE DE SCAN ─────────────────────────
story.append(PageBreak())
sect("FICHE 3 — POSTE DE SCAN : remplir une palette à la douchette")
story.append(Paragraph("Le poste de scan sert à composer les palettes en scannant. Pas de nom à choisir : l'ordre est toujours <b>palette → pierres → emplacement</b>.", st_step))
captures2("scan_accueil", "Poste de scan au démarrage : aucune palette active, on scanne une palette (ou « Palettes ouvertes… »).",
          "scan_palette_active", "Palette scannée : son numéro, à qui elle est, cubage / tonnage, la jauge de poids, et son contenu OF par OF (🗑️ retirer, 💥 rebut).")
steps([
    "<b>Scanner la palette</b> (étiquette PACK…) ou appuyer sur <b>« Palettes ouvertes… »</b> et la toucher dans la liste. L'écran affiche à qui elle est (« Palette de … ») ou « Palette vierge ». Vérifiez toujours la palette affichée avant de scanner des pierres.",
    "<b>Scanner les OF</b> un par un (code-barre de la fiche OF ou de la tablette). C'est l'OF qui dit à qui est la pierre : sur une palette vierge, la première pierre attribue la palette à son opérateur ; sur la palette d'un autre opérateur, l'écran refuse (⛔) — scannez la palette de cet opérateur ou une palette vierge.",
    "L'OF doit être terminé (dernière opération faite) ou ses pièces comptées sur la tablette.",
    "OF à plusieurs pièces : le pavé « Combien sur cette palette ? » s'affiche — taper le nombre puis Valider, « Tout », ou scanner directement la suite pour tout mettre.",
    "Erreur de scan ? <b>« Retirer dernier OF »</b>, ou la corbeille 🗑️ en face de la ligne concernée. Pierre cassée ? le bouton 💥 (Fiche 4).",
    "La jauge sous le numéro de palette montre le poids posé par rapport au seuil (1 500 kg) : orange à 80 %, rouge au-delà.",
    "<b>Palette déjà clôturée ?</b> On peut la scanner quand même : l'écran affiche « 🔒 Clôturée · lecture seule » et son contenu ; rien ne peut y être ajouté ni retiré, mais le bouton <b>« Réimprimer le bon de colisage »</b> fonctionne.",
])
captures2("scan_quantite", "OF à plusieurs pièces : le pavé demande combien de pièces vont sur cette palette.",
          "scan_refus", "Refus ⛔ : la pierre scannée est d'un autre opérateur que celui de la palette active.")
captures2("scan_palettes_ouvertes", "« Palettes ouvertes… » : les palettes en cours avec leur opérateur, puis celles sans opérateur ; on touche une palette pour la rendre active.",
          "scan_cloturee", "Palette déjà clôturée scannée : « 🔒 Clôturée · lecture seule », contenu affiché sans corbeille, boutons de clôture grisés, « Réimprimer le bon de colisage » disponible.")
story.append(Paragraph("Clôturer la palette", st_h2))
steps([
    "Scanner le <b>code-barre d'emplacement</b> (Stock Atelier / Stock Usine) affiché à l'écran, ou toucher le bouton bleu correspondant, puis confirmer.",
    "La palette est verrouillée, l'emplacement enregistré, le stock déplacé, et le <b>bon de colisage s'ouvre</b> pour impression (commande, objet, prépalettisation, adresse de livraison, opérateur).",
    "<b>Céline reçoit aussitôt le mail « Palette clôturée : PACK… »</b> avec le bon de colisage en pièce jointe, que la clôture vienne du poste de scan ou de la tablette.",
    "Après la clôture, l'écran n'a plus de palette active : scannez la suivante.",
])
story.append(Paragraph("Réimprimer un bon de colisage", st_h2))
steps([
    "Palette encore ouverte : la rendre active puis appuyer sur <b>« Bon de colisage »</b> (bouton bleu sous la palette active).",
    "Palette déjà clôturée : la scanner au poste de scan (lecture seule) et appuyer sur « Réimprimer le bon de colisage » ; ou au bureau, Inventaire → Colis → Imprimer → Bon de colisage.",
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
story.append(Paragraph("Dans Odoo : <b>Inventaire → Produits → Colis</b>. La liste montre pour chaque palette l'<b>Opérateur</b> responsable, si elle est clôturée et son emplacement. La recherche propose « Opérateur », les filtres « Palettes ouvertes » / « Palettes clôturées » et un regroupement par opérateur.", st_txt))
story.append(Paragraph("Changer le responsable d'une palette (opérateur absent, erreur de nom…)", st_h2))
steps([
    "Ouvrir la palette (PACK…) et modifier le champ <b>Opérateur (responsable de la palette)</b>. Effacer le champ = palette « sans opérateur » : le premier qui pose dessus la reprend.",
    "Le champ « Opérateurs ayant posé » garde l'historique de tous ceux qui ont posé dessus (lecture seule).",
    "La palette active d'un opérateur se règle sur sa fiche employé, champ <b>Palette active (poste de scan)</b> ; elle se remet à jour toute seule à la prochaine pose.",
    "<b>Depuis la tablette, sans passer par le bureau</b> : dans « Choisir le colis », le bouton « 🔑 Responsable : prendre la palette d'un autre opérateur » demande le code responsable, liste les palettes ouvertes des autres et les transfère à l'opérateur choisi sur la tablette. Le code se règle dans Paramètres → Technique → Paramètres système, clé maquignon.palette_code_chef.",
])
story.append(Paragraph("Point hebdomadaire automatique", st_h2))
steps([
    "Chaque lundi matin, le bureau reçoit le mail « Palettes : point hebdo » : par opérateur puis par commande, les pierres terminées depuis plus de 2 jours, non facturées, qui ne sont pas (ou pas entièrement) sur palette, avec le nombre d'OF restant à faire sur la commande ; et les palettes ouvertes sans mouvement depuis 7 jours.",
    "Le même lundi, Céline reçoit « Commandes entièrement produites, non facturées » : les commandes dont tous les OF sont terminés et pas encore facturés (clé maquignon.commandes_produites_email). Une commande en sort dès qu'elle est facturée.",
    "Destinataire : clé maquignon.palettes_alerte_email (isabelle@maquignon.com par défaut). Seuil de poids des palettes : clé maquignon.palette_max_kg (1 500 kg).",
    "Rappel : tous les opérateurs n'ont pas de tablette ; ce point sert à repérer ce qui doit passer au poste de scan ou être régularisé.",
])
captures2("bureau_colis_liste", "Odoo, Inventaire → Colis : colonnes Opérateur, Palette clôturée et Zone / Emplacement.",
          "bureau_colis_fiche", "Fiche d'une palette : le champ « Opérateur (responsable de la palette) » se modifie ici ; « Opérateurs (ont posé) » garde l'historique.")
story.append(Paragraph("Étiquettes de palettes vierges", st_h2))
steps([
    "Inventaire → Colis → <b>Générer des colis</b> (quantité) crée des numéros PACK vierges ; imprimer leurs étiquettes et les agrafer sur les palettes vides.",
    "Une palette vierge n'a pas d'opérateur : elle est prise par le premier qui la scanne. Elle n'apparaît dans aucune liste tant qu'elle est vide.",
])
story.append(Paragraph("Bon de colisage", st_h2))
steps([
    "Le bon de colisage (imprimé à la clôture, ou Imprimer → Bon de colisage) mentionne désormais l'<b>opérateur</b> responsable, en plus de la commande, du client, de la prépalettisation et de l'emplacement.",
    "<b>À chaque clôture</b> (tablette ou poste de scan), Céline reçoit aussitôt le mail « Palette clôturée : PACK… » à celine@maquignon.com : client, emplacement, cubage, tonnage, et le bon de colisage PDF en pièce jointe. Une palette réouverte au bureau puis reclôturée renvoie un mail.",
])
capture("bureau_bon_colisage", "Bon de colisage imprimé à la clôture et envoyé par mail à Céline : commande, client, livraison, opérateur, emplacement, et le détail des OF.")
story.append(Spacer(1, 8))
story.append(Paragraph("Rappels généraux", st_h2))
steps([
    "Les compteurs de la tablette (pierres faites, m³, poids) se mettent à jour tout seuls — ne rien saisir à la main.",
    "Un doute, un message d'erreur qui insiste, une palette introuvable : appeler le bureau plutôt que de bricoler.",
])

doc.build(story)
print("procedures_operateurs.pdf généré")
