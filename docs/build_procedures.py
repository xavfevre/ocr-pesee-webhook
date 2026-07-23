# -*- coding: utf-8 -*-
"""Procédures opérateurs — atelier pierre Maquignon (tablette + poste de scan)."""
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
LIGHT = colors.HexColor("#EAF4F4")
AMBERL = colors.HexColor("#FBEBD3")

st_title = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=22, textColor=colors.white,
                          leading=26)
st_h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=14, textColor=TEAL,
                       leading=18, spaceBefore=10, spaceAfter=4)
st_step = ParagraphStyle("s", fontName="Helvetica", fontSize=11.5, textColor=INK, leading=16,
                         leftIndent=24, firstLineIndent=-24, spaceAfter=5)
st_note = ParagraphStyle("n", fontName="Helvetica-Oblique", fontSize=10.5, textColor=ORANGE,
                         leading=14)
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
    canv.drawRightString(W - MARG, H - 14 * mm, "Tablette & poste de scan · juillet 2026")
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


# ───────────────────────── PAGE 1 — MA PRODUCTION ─────────────────────────
sect("FICHE 1 — MA PRODUCTION (tablette) : faire les pierres")
story.append(Paragraph("Ouvrir la tablette sur <b>Ma production</b> et choisir son nom dans la liste en haut.", st_step))
story.append(Paragraph("Trouver sa pierre", st_h2))
steps([
    "Les cartes sont triées par n° d'OF. Utiliser les <b>filtres</b> du haut : client, réf. commande, machine, palette — ou les cases « rentre dans (tous sens) » pour trouver les pierres qui tiennent dans un gabarit.",
    "La <b>couleur du bandeau</b> de chaque carte = le type de pierre (bleu = Tuffeau, vert = Haims, orange = Migné, magenta = Tervoux, turquoise = Richemont, jaune = Sireuil).",
    "Sur la carte : dimensions (long × larg × haut), nombre de pièces, réf. pierre (losange), client, réf. commande, n° de prépalettisation.",
])
story.append(Paragraph("Faire la pierre", st_h2))
steps([
    "Appuyer sur <b>« Démarrer »</b> quand on commence la pierre (le temps est compté à partir de là).",
    "Quand la pierre est finie, appuyer sur <b>« Terminé »</b>. La carte devient grisée et de nouveaux boutons apparaissent.",
    "En cas d'erreur, <b>« Annuler Terminé »</b> remet l'OF en cours.",
])
note("IMPORTANT : toujours Démarrer / Terminer au moment réel — c'est ce qui calcule les temps par pierre et le planning de l'atelier.")

# ───────────────────────── PAGE 2 — MISE EN PALETTE ─────────────────────────
story.append(PageBreak())
sect("FICHE 2 — METTRE LES PIERRES EN PALETTE (depuis la tablette)")
story.append(Paragraph("Dès qu'un OF est terminé, la carte propose la mise en colis, sans passer par le poste de scan.", st_step))
story.append(Paragraph("Cas 1 — même palette que la pierre précédente", st_h2))
steps([
    "Appuyer sur le bouton vert <b>« éclair » (dernier colis utilisé)</b> : la pierre part directement dans la même palette. Une seule pression, terminé.",
])
story.append(Paragraph("Cas 2 — choisir ou changer de palette", st_h2))
steps([
    "Appuyer sur <b>« Mettre au colis »</b> : la liste des palettes ouvertes s'affiche, avec pour chacune : nombre d'OF, m³, kg, <b>client, réf. commande et n° de prépalettisation</b>.",
    "<b>Scanner le code-barre</b> agrafé sur la palette (même une palette vierge), ou <b>taper</b> quelques lettres du n° PACK, du client, du chantier ou de la prépalettisation pour filtrer, puis toucher la palette voulue.",
    "Palette neuve : prendre une palette pré-imprimée, scanner son code-barre — elle devient active dès la première pierre.",
])
story.append(Paragraph("Clôturer une palette pleine (depuis la tablette)", st_h2))
steps([
    "Dans la liste des colis, appuyer sur le <b>cadenas</b> à droite de la palette.",
    "Choisir l'emplacement : <b>Stock Atelier</b> ou <b>Stock Usine</b>.",
    "Le bon de colisage s'imprime automatiquement et la palette est verrouillée (plus rien ne peut y être ajouté).",
])
note("Une palette clôturée ne peut plus recevoir de pierres : le bouton « éclair » l'oublie automatiquement et l'écran refuse l'ajout.")

# ───────────────────────── PAGE 3 — POSTE DE SCAN ─────────────────────────
story.append(PageBreak())
sect("FICHE 3 — POSTE DE SCAN : remplir un colis")
story.append(Paragraph("Le poste de scan sert à composer les palettes en scannant. L'ordre est toujours : palette d'abord, pierres ensuite.", st_step))
steps([
    "<b>Scanner la palette</b> (étiquette PACK…) : elle devient « COLIS ACTIF » en haut de l'écran, avec son contenu, ses m³ et son poids.",
    "Ou appuyer sur <b>« Colis ouverts… »</b> pour choisir une palette dans la liste (les plus récentes en premier, avec client / réf / prépalettisation) — un appui suffit pour la rendre active, sans scanner.",
    "<b>Scanner les OF</b> un par un (code-barre de la fiche OF) : chaque pierre s'ajoute au colis actif.",
    "Si l'OF compte plusieurs pièces et qu'on n'en met qu'une partie : le pavé « Combien sur cette palette ? » s'affiche — taper le nombre, ou « Tout ».",
    "Erreur de scan ? <b>« Retirer dernier OF »</b>, ou la corbeille en face de la ligne concernée.",
])
story.append(Paragraph("Clôturer la palette", st_h2))
steps([
    "Scanner le <b>code-barre d'emplacement</b> (Stock Atelier / Stock Usine) affiché à l'écran, ou toucher le bouton bleu correspondant.",
    "La palette est verrouillée, l'emplacement enregistré, et le <b>bon de colisage s'imprime</b> (avec commande, objet, prépalettisation, adresse de livraison).",
])
story.append(Paragraph("Réimprimer un bon de colisage", st_h2))
steps([
    "Palette encore ouverte : la rendre active puis appuyer sur <b>« Bon de colisage »</b> (bouton bleu sous le colis actif).",
    "Palette déjà clôturée : demander au bureau (Inventaire → Colis → Imprimer → Bon de colisage).",
])
note("Si l'écran affiche « Session expirée » : se reconnecter dans la petite fenêtre — l'action en cours est rejouée automatiquement, rien n'est perdu.")

# ───────────────────────── PAGE 4 — REBUTS ─────────────────────────
story.append(PageBreak())
sect("FICHE 4 — DÉCLARER UN REBUT (pierre cassée)", RED)
story.append(Paragraph("Une pierre cassée doit TOUJOURS être déclarée : la déclaration relance automatiquement un OF pour la refaire, met à jour la palette et prévient le bureau.", st_step))
story.append(Paragraph("Où trouver le bouton « Rebut »", st_h2))
steps([
    "<b>Tablette — Ma production</b> : sur la carte d'un OF terminé (casse à la fabrication ou juste après).",
    "<b>Tablette — Historique</b> : sur n'importe quelle carte des jours précédents (casse découverte après coup, palette qui tombe…).",
    "<b>Poste de scan</b> : le petit bouton « éclat » en face de chaque ligne du contenu du colis (casse à la mise en palette).",
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
story.append(Spacer(1, 8))
story.append(Paragraph("Rappels généraux", st_h2))
steps([
    "Les compteurs de la tablette (pierres faites, m³, poids) se mettent à jour tout seuls — ne rien saisir à la main.",
    "Un doute, un message d'erreur qui insiste, une palette introuvable : appeler le bureau plutôt que de bricoler.",
])

doc.build(story)
print("procedures_operateurs.pdf généré")
