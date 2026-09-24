# -*- coding: utf-8 -*-
"""Fiche procédure EPI — accueil (remise, entrée en stock, stock, annulation) et bureau (nouvel article avec code-barres).
Même mise en page que docs/build_procedures.py (procédures atelier). Captures : captures_epi/.
  python build_procedure_epi.py [lien]   -> procedure_epi.pdf (le lien de la page est passé en argument)"""
import os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph as _Paragraph,
                                Spacer, Table, TableStyle, PageBreak, Image, KeepTogether)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

LIEN = sys.argv[1] if len(sys.argv) > 1 else 'https://maquignon.odoo.com/epi?k=…'
TEAL = colors.HexColor("#01666B"); INK = colors.HexColor("#0F172A"); GREY = colors.HexColor("#64748B")
ORANGE = colors.HexColor("#B45309"); RED = colors.HexColor("#B4232A"); GREEN = colors.HexColor("#15803D")
LIGHT = colors.HexColor("#EAF4F4"); AMBERL = colors.HexColor("#FBEBD3"); GREENL = colors.HexColor("#DCFCE7"); REDL = colors.HexColor("#FEE2E2")
BLUE = colors.HexColor("#1D4ED8")

try:
    pdfmetrics.registerFont(TTFont("SegoeEmoji", "C:/Windows/Fonts/seguiemj.ttf")); EMOJI = True
    pdfmetrics.registerFontFamily("SegoeEmoji", normal="SegoeEmoji", bold="SegoeEmoji", italic="SegoeEmoji", boldItalic="SegoeEmoji")
except Exception:  # noqa: BLE001
    EMOJI = False
RX_EMOJI = re.compile("([🌀-🫿☀-➿⬀-⯿↩-↪]️?)")


def emo(t):
    return RX_EMOJI.sub(r'<font name="SegoeEmoji">\1</font>', t) if (EMOJI and isinstance(t, str)) else t


def Paragraph(t, st, *a, **k):  # noqa: N802
    return _Paragraph(emo(t), st, *a, **k)


st_step = ParagraphStyle("s", fontName="Helvetica", fontSize=11.5, textColor=INK, leading=16, leftIndent=24, firstLineIndent=-24, spaceAfter=5)
st_txt = ParagraphStyle("t", fontName="Helvetica", fontSize=11.5, textColor=INK, leading=16, spaceAfter=5)
st_rule = ParagraphStyle("r", fontName="Helvetica-Bold", fontSize=13.5, textColor=INK, leading=18, leftIndent=34, firstLineIndent=-34, spaceAfter=8)
st_cap = ParagraphStyle("cap", fontName="Helvetica-Oblique", fontSize=9, textColor=GREY, leading=11.5, spaceAfter=6)
st_lien = ParagraphStyle("l", fontName="Helvetica-Bold", fontSize=11, textColor=BLUE, leading=15, spaceAfter=3)
W, H = A4
MARG = 16 * mm
CAPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captures_epi")


def header_footer(canv, doc):
    canv.saveState()
    canv.setFillColor(TEAL); canv.rect(0, H - 22 * mm, W, 22 * mm, stroke=0, fill=1)
    canv.setFillColor(colors.white); canv.setFont("Helvetica-Bold", 15)
    canv.drawString(MARG, H - 14 * mm, "SARL MAQUIGNON — Procédure EPI")
    canv.setFont("Helvetica", 9); canv.drawRightString(W - MARG, H - 14 * mm, "Accueil · septembre 2026")
    canv.setFillColor(GREY); canv.setFont("Helvetica", 8.5)
    canv.drawString(MARG, 9 * mm, "En cas de blocage : appeler le bureau. Ne jamais forcer une action refusée par l'écran.")
    canv.drawRightString(W - MARG, 9 * mm, "Page %d" % doc.page)
    canv.restoreState()


doc = BaseDocTemplate("procedure_epi.pdf", pagesize=A4, leftMargin=MARG, rightMargin=MARG, topMargin=26 * mm, bottomMargin=14 * mm,
                      title="Fiche procédure EPI — SARL MAQUIGNON", author="SARL MAQUIGNON")
frame = Frame(MARG, 14 * mm, W - 2 * MARG, H - 40 * mm, id="f")
doc.addPageTemplates([PageTemplate(id="p", frames=[frame], onPage=header_footer)])
story = []


def sect(txt, color=TEAL):
    t = Table([[Paragraph('<font color="white"><b>%s</b></font>' % txt, ParagraphStyle("b", fontName="Helvetica-Bold", fontSize=13.5, textColor=colors.white, leading=17))]], colWidths=[W - 2 * MARG])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("ROUNDEDCORNERS", [6, 6, 6, 6])]))
    story.append(t); story.append(Spacer(1, 6))


def steps(items):
    for i, it in enumerate(items, 1):
        story.append(Paragraph("<b>%d.</b>  %s" % (i, it), st_step))


def _img(name, width, max_h=118 * mm):
    path = os.path.join(CAPT, name + ".png")
    if not os.path.exists(path):
        return None
    iw, ih = ImageReader(path).getSize()
    h = width * ih / iw
    if h > max_h:
        width, h = max_h * iw / ih, max_h
    im = Image(path, width=width, height=h); im.hAlign = "CENTER"
    return im


def capture(name, caption, max_h=118 * mm):
    im = _img(name, W - 2 * MARG - 8, max_h=max_h)
    if im is None:
        return
    t = Table([[im], [Paragraph(caption, st_cap)]], colWidths=[W - 2 * MARG])
    t.setStyle(TableStyle([("BOX", (0, 0), (0, 0), 0.6, GREY), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    story.append(KeepTogether([Spacer(1, 3), t, Spacer(1, 4)]))


def captures2(a, cap_a, b, cap_b, max_h=95 * mm):
    wcol = (W - 2 * MARG - 8) / 2
    ia, ib = _img(a, wcol - 6, max_h=max_h), _img(b, wcol - 6, max_h=max_h)
    if ia is None or ib is None:
        capture(a if ia else b, cap_a if ia else cap_b); return
    t = Table([[ia, ib], [Paragraph(cap_a, st_cap), Paragraph(cap_b, st_cap)]], colWidths=[wcol, wcol])
    t.setStyle(TableStyle([("BOX", (0, 0), (0, 0), 0.6, GREY), ("BOX", (1, 0), (1, 0), 0.6, GREY), ("VALIGN", (0, 0), (-1, 0), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    story.append(KeepTogether([Spacer(1, 3), t, Spacer(1, 4)]))


def note(txt, bg=AMBERL, fg=ORANGE):
    t = Table([[Paragraph(txt, ParagraphStyle("nn", fontName="Helvetica-Bold", fontSize=10.5, textColor=fg, leading=14))]], colWidths=[W - 2 * MARG])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.append(Spacer(1, 2)); story.append(t); story.append(Spacer(1, 6))


# ───────────── PAGE 1 — L'ESSENTIEL ─────────────
sect("LES 4 RÈGLES EPI — accueil", GREEN)
regles = [
    ("1", "<b>Chaque EPI remis à un salarié se saisit sur la page EPI</b>, au moment de la remise : salarié, EPI (taille), quantité. C'est ce qui sort l'EPI du stock et l'inscrit sur la fiche du salarié."),
    ("2", "<b>Chaque arrivée d'EPI s'enregistre en « Entrée en stock »</b> dès la réception, sinon le stock affiché est faux et les remises sont refusées (« stock insuffisant »)."),
    ("3", "<b>Une erreur se corrige par « ↩ annuler »</b> dans la liste des dernières remises : l'EPI revient en stock. On ne bricole pas les quantités."),
    ("4", "<b>Un nouvel EPI est d'abord créé dans Odoo</b> (bureau), dans la catégorie EPI avec son code-barres : il apparaît ensuite sur la page. Pas d'article = pas de remise possible."),
]
for num, txt in regles:
    story.append(Paragraph('<font color="#15803D"><b>%s</b></font>   %s' % (num, txt), st_rule))
note("La page fonctionne sur l'ordinateur de l'accueil comme sur un téléphone, sans compte Odoo. Pas de signature du salarié : la saisie fait foi.", bg=GREENL, fg=GREEN)

sect("1 · OUVRIR LA PAGE EPI")
steps([
    "<b>À l'accueil</b> (sans compte Odoo) : le lien ci-dessous, à mettre en favori sur l'ordinateur et sur le téléphone.",
    "<b>Depuis Odoo</b> (bureau, comptes connectés) : menu <b>Inventaire → EPI</b>. La page s'ouvre dans un nouvel onglet, c'est la même.",
])
story.append(Paragraph(LIEN, st_lien))
capture("menu_inventaire", "Dans Odoo, le menu EPI de l'application Inventaire ouvre la page.", max_h=22 * mm)
note("Ce lien contient la clé d'accès de l'accueil : ne pas le transmettre en dehors du bureau et de l'accueil. En cas de doute, le bureau peut changer la clé.", bg=REDL, fg=RED)

sect("2 · REMETTRE UN EPI À UN SALARIÉ")
steps([
    "Bloc <b>« ✅ Remettre un EPI à un salarié »</b> : choisir le <b>salarié</b> (liste par société).",
    "Choisir l'<b>EPI</b> : soit en <b>tapant son code-barres</b> dans la case « Code-barres » puis <b>Entrée</b> (l'EPI se met tout seul dans la liste), soit directement dans la liste « EPI ». La taille fait partie du nom, ex. « Chaussure … (42) ». Le stock s'affiche sous la liste.",
    "Vérifier la <b>quantité</b> (1 par défaut) et la <b>date</b> (aujourd'hui par défaut ; on peut antidater une remise oubliée).",
    "<b>Note</b> facultative : remplacement, usure, chantier…",
    "Cliquer <b>« ✅ Remettre »</b>. Un bandeau vert confirme : EPI, salarié, référence du transfert et stock restant.",
])
capture("remise", "Le bloc de remise : code-barres tapé (ou EPI choisi dans la liste), quantité, date, note, puis « Remettre ».", max_h=92 * mm)
note("« Code-barres inconnu » : vérifier la frappe ; si le code n'est pas encore enregistré sur l'article dans Odoo, choisir l'EPI dans la liste et signaler le code au bureau.", bg=AMBERL, fg=ORANGE)

sect("3 · STOCK INSUFFISANT, ERREUR, ANNULATION")
steps([
    "<b>« Stock insuffisant »</b> à la remise : la réception n'a pas été enregistrée. Faire d'abord l'<b>entrée en stock</b> (bloc 📦), puis recommencer la remise. Si l'EPI est bien là physiquement et qu'il faut avancer, « Remettre quand même » est possible : le stock passe en négatif et le bureau régularise.",
    "<b>Erreur de salarié, de taille ou de quantité</b> : dans <b>« 🕒 Dernières remises »</b>, cliquer <b>« ↩ annuler »</b> sur la ligne. L'EPI revient en stock (la ligne reste visible, barrée). Refaire ensuite la bonne remise.",
    "Une remise annulée ne peut pas l'être deux fois : le bouton disparaît.",
])

sect("4 · EPI REÇUS : ENTRÉE EN STOCK")
steps([
    "Bloc <b>« 📦 Entrée en stock (EPI reçus) »</b> : taper le <b>code-barres</b> puis Entrée, ou choisir l'EPI (taille) dans la liste.",
    "Saisir la <b>quantité reçue</b> et la <b>date</b> de réception ; en note, le fournisseur ou le numéro du bon de livraison.",
    "Cliquer <b>« 📦 Entrer en stock »</b>. Le stock de l'EPI est mis à jour aussitôt.",
    "Une livraison de plusieurs tailles = une entrée par taille.",
])
capture("entree", "Le bloc d'entrée en stock : une ligne par EPI et par taille reçus.", max_h=78 * mm)

sect("5 · SUIVRE LE STOCK ET LA CONSOMMATION")
steps([
    "<b>« 📊 Stock EPI »</b> : une ligne par EPI et par taille, avec le stock mini et maxi. <b>Rouge</b> = rupture ou sous le mini, <b>orange</b> = au mini : prévenir le bureau, qui lance les demandes de prix (bouton 🛒). La valeur du stock est indiquée dessous.",
    "<b>« 👤 Consommation par salarié »</b> : pour l'année affichée, ce que chaque salarié a reçu (détail par EPI, total, coût), avec un filtre par nom et les flèches pour changer d'année.",
    "Le bureau retrouve les mêmes informations dans Odoo : fiche du salarié → onglet <b>EPI</b> ; Inventaire → Analyse des mouvements, grouper par <b>Salarié</b>.",
])
capture("stock", "Le stock par taille : rouge sous le mini, orange au mini.", max_h=60 * mm)

# ───────────── PAGE 2 — BUREAU : NOUVEL ARTICLE ─────────────
story.append(PageBreak())
sect("6 · BUREAU — AJOUTER UN NOUVEL EPI DANS ODOO (avec son code-barres)", ORANGE)
story.append(Paragraph("À faire une seule fois par modèle d'EPI (gants, casque, lunettes, pantalon…). L'article apparaît sur la page EPI dès qu'il est enregistré.", st_txt))
steps([
    "Odoo → <b>Inventaire → Produits → Produits → Nouveau</b>. Nom clair, ex. « Gants manutention Tegera 660 ».",
    "Cocher <b>« Suivre l'inventaire »</b> (par quantité) et <b>« Achats »</b> ; décocher « Ventes ».",
    "<b>Catégorie : « All / EPI »</b>. C'est ce qui fait apparaître l'article sur la page EPI.",
    "<b>Code-barres</b> : dans l'onglet <b>Informations générales</b>, champ <b>« Code-barres »</b>, <b>taper le code imprimé sur l'emballage</b> (les 13 chiffres, sans espace). C'est ce code que l'accueil tape sur la page pour choisir l'EPI.",
    "<b>Coût</b> : renseigner le prix d'achat (utilisé pour la valeur du stock et le coût par salarié).",
    "Enregistrer. Puis saisir le stock de départ sur la page EPI (« Entrée en stock »).",
])
capture("produit_haut", "Fiche article : « Suivre l'inventaire » coché, catégorie All / EPI, Achats coché. Sans tailles, le champ Code-barres est ici, dans Informations générales.", max_h=80 * mm)
note("EPI avec tailles ou pointures (chaussures, gants, vêtements) : chaque taille est une <b>variante</b> avec son propre stock et son propre code-barres. Voir ci-dessous.", bg=AMBERL, fg=ORANGE)
sect("7 · BUREAU — TAILLES EN VARIANTES ET CODE-BARRES PAR TAILLE", ORANGE)
steps([
    "Sur la fiche article, onglet <b>« Attributs &amp; Variantes »</b> : ajouter l'attribut <b>« Pointure »</b> (38 à 47, déjà créé) ou <b>« Taille »</b> (S, M, L, XL… à créer une fois) et cocher les valeurs utiles. Odoo crée une variante par taille.",
    "Bouton <b>« Variantes »</b> en haut de la fiche : ouvrir chaque taille et <b>taper son code-barres</b> dans le champ « Code-barres » de la variante (le code diffère par taille sur l'emballage).",
    "Sur la page EPI, chaque taille apparaît comme un EPI à part : « Chaussure … (42) ».",
])
captures2("variantes_haut", "Onglet Attributs & Variantes : l'attribut Pointure et ses valeurs.",
          "variante", "Fiche d'une variante (pointure 42) : le champ Code-barres, propre à cette taille.", max_h=80 * mm)

sect("8 · BUREAU — FOURNISSEURS, STOCK MINI ET DEMANDES DE PRIX", ORANGE)
steps([
    "<b>Référencer les fournisseurs</b> sur la fiche article, onglet <b>Achats</b>, tableau « Fournisseurs » : une ligne par fournisseur (prix, quantité mini, délai). Un fournisseur qui n'existe pas encore se crée depuis la ligne (ou Achats → Commandes → Fournisseurs → Nouveau). Plusieurs fournisseurs sur un même EPI = une demande de prix à chacun, pour comparer.",
    "<b>Stock mini / maxi</b> : sur la page EPI, tableau « Stock EPI », colonnes <b>Mini</b> et <b>Maxi</b>, par taille. Enregistré aussitôt (c'est une règle de réapprovisionnement Odoo sur Maq/Stock EPI). Sous le mini, la ligne passe en rouge ; au mini, en orange.",
    "<b>Demandes de prix</b> : bouton <b>« 🛒 Demandes de prix aux fournisseurs »</b> sous le tableau. La page annonce les EPI sous le mini et les fournisseurs concernés, puis crée dans Odoo <b>une demande de prix (brouillon) par fournisseur</b>, quantité = de quoi remonter au maxi, prix et référence du fournisseur repris de la fiche. Relancer le bouton met à jour la demande existante, sans doublon.",
    "Un EPI sous le mini <b>sans fournisseur référencé</b> est signalé : compléter l'onglet Achats de l'article, puis relancer.",
    "Dans Odoo, <b>Achats → Demandes de prix</b> : vérifier, <b>Envoyer par e-mail</b> au fournisseur, puis <b>Confirmer</b> la commande retenue. À la livraison, <b>valider la réception</b> dans Odoo (elle est de type « Réception EPI » : le stock EPI est mis à jour tout seul, sans passer par « Entrée en stock » sur la page).",
])
capture("stock_bas", "Sous le tableau Stock EPI : le bouton de demandes de prix ; la liste des demandes en cours (numéro, fournisseur, état, montant) s'affiche dessous, avec un lien vers Odoo.", max_h=60 * mm)

sect("9 · OÙ RETROUVER LES INFORMATIONS DANS ODOO", TEAL)
steps([
    "<b>Fiche salarié → onglet EPI</b> : tout ce qu'il a reçu (date, EPI, quantité, référence du transfert).",
    "<b>Inventaire → Opérations</b> : transferts <b>« Dotation EPI »</b> (remises, référence WH/EPI/…) et <b>« Réception EPI »</b> (entrées, WH/EPIIN/…), avec le champ Salarié.",
    "<b>Inventaire → Analyse → Analyse des mouvements</b> : grouper par Salarié, par Produit, par mois.",
])
capture("salarie_epi", "Fiche salarié dans Odoo : l'onglet EPI liste les remises.", max_h=60 * mm)
note("Question, blocage, EPI manquant dans la liste : appeler le bureau. Ne pas créer d'article en double : un modèle = une fiche, les tailles en variantes.", bg=GREENL, fg=GREEN)

doc.build(story)
print("procedure_epi.pdf :", os.path.getsize("procedure_epi.pdf"), "octets")
