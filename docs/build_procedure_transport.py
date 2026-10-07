# -*- coding: utf-8 -*-
"""Procédure « Transport des palettes de pierre : du devis à la livraison » (version du 07/10/2026).
Génère procedure_transport_palettes.pdf dans docs/ (python docs/build_procedure_transport.py depuis docs/)."""
import os, re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

TEAL = colors.HexColor("#01666B"); INK = colors.HexColor("#0F172A"); GREY = colors.HexColor("#64748B")
ORANGE = colors.HexColor("#B45309"); GREEN = colors.HexColor("#15803D"); BLUE = colors.HexColor("#0E7490")
AMBERL = colors.HexColor("#FBEBD3"); GREENL = colors.HexColor("#DCFCE7"); BLUEL = colors.HexColor("#E0F2FE")
W, H = A4; MARG = 16 * mm
try:
    pdfmetrics.registerFont(TTFont("SegoeEmoji", "C:/Windows/Fonts/seguiemj.ttf")); EMOJI = True
except Exception:  # noqa: BLE001
    EMOJI = False
RX = re.compile("([🌀-🫿☀-➿⬀-⯿🄀-🉿←-⇿]️?)")


def emo(t):
    return RX.sub(r'<font name="SegoeEmoji">\1</font>', t) if EMOJI else t


_P = Paragraph


def Paragraph(t, st, *a, **k):  # noqa: N802
    return _P(emo(t), st, *a, **k)


st_h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13.5, textColor=TEAL, leading=17, spaceBefore=9, spaceAfter=4)
st_txt = ParagraphStyle("t", fontName="Helvetica", fontSize=11, textColor=INK, leading=15, spaceAfter=5)
st_step = ParagraphStyle("s", fontName="Helvetica", fontSize=11, textColor=INK, leading=15, leftIndent=22, firstLineIndent=-22, spaceAfter=4)
st_small = ParagraphStyle("sm", fontName="Helvetica", fontSize=9.5, textColor=GREY, leading=12)
st_cap = ParagraphStyle("cap", fontName="Helvetica-Oblique", fontSize=9, textColor=GREY, leading=11.5, spaceAfter=6)
st_cell = ParagraphStyle("c", fontName="Helvetica", fontSize=9.8, textColor=INK, leading=12.5)
st_cellb = ParagraphStyle("cb", fontName="Helvetica-Bold", fontSize=9.8, textColor=INK, leading=12.5)


def header_footer(canv, doc):
    canv.saveState()
    canv.setFillColor(TEAL); canv.rect(0, H - 22 * mm, W, 22 * mm, stroke=0, fill=1)
    canv.setFillColor(colors.white); canv.setFont("Helvetica-Bold", 14)
    canv.drawString(MARG, H - 14 * mm, "SARL MAQUIGNON — Transport des palettes de pierre")
    canv.setFont("Helvetica", 9); canv.drawRightString(W - MARG, H - 8 * mm, "Du devis à la livraison · octobre 2026")
    canv.setFillColor(GREY); canv.setFont("Helvetica", 8.5)
    canv.drawString(MARG, 9 * mm, "Une palette ne part que clôturée, scannée et validée : c'est ce qui met à jour le BL, la facture et le suivi.")
    canv.drawRightString(W - MARG, 9 * mm, "Page %d" % doc.page)
    canv.restoreState()


doc = BaseDocTemplate("procedure_transport_palettes.pdf", pagesize=A4, leftMargin=MARG, rightMargin=MARG, topMargin=26 * mm, bottomMargin=14 * mm)
doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(MARG, 14 * mm, W - 2 * MARG, H - 40 * mm, id="f")], onPage=header_footer)])
story = []
CAPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captures_transport")


def sect(txt, color=TEAL):
    t = Table([[Paragraph('<font color="white"><b>%s</b></font>' % txt, ParagraphStyle("b", fontName="Helvetica-Bold", fontSize=13, textColor=colors.white, leading=16))]], colWidths=[W - 2 * MARG])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("ROUNDEDCORNERS", [6, 6, 6, 6])]))
    story.append(t); story.append(Spacer(1, 6))


def steps(items):
    for i, it in enumerate(items, 1):
        story.append(Paragraph("<b>%d.</b>  %s" % (i, it), st_step))


def note(txt, bg=AMBERL, fg=ORANGE):
    t = Table([[Paragraph(txt, ParagraphStyle("nn", fontName="Helvetica-Bold", fontSize=10.2, textColor=fg, leading=13.5))]], colWidths=[W - 2 * MARG])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.append(Spacer(1, 2)); story.append(t); story.append(Spacer(1, 6))


def capture(name, caption, max_h=120 * mm):
    path = os.path.join(CAPT, name)
    if not os.path.exists(path):
        return
    iw, ih = ImageReader(path).getSize()
    width = W - 2 * MARG - 8; h = width * ih / iw
    if h > max_h:
        width, h = max_h * iw / ih, max_h
    im = Image(path, width=width, height=h); im.hAlign = "CENTER"
    t = Table([[im], [Paragraph(caption, st_cap)]], colWidths=[W - 2 * MARG])
    t.setStyle(TableStyle([("BOX", (0, 0), (0, 0), 0.6, GREY), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    story.append(Spacer(1, 3)); story.append(t); story.append(Spacer(1, 4))


def tableau(entetes, lignes, largeurs):
    data = [[Paragraph("<b>%s</b>" % e, st_cellb) for e in entetes]] + [[Paragraph(c, st_cell) for c in l] for l in lignes]
    t = Table(data, colWidths=largeurs, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), BLUEL), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story.append(t); story.append(Spacer(1, 6))


# ───────────── PAGE 0 — LE FLUX EN UN COUP D'ŒIL ─────────────
sect("LE FLUX EN UN COUP D'ŒIL — qui fait quoi, et ce qu'Odoo fait tout seul", GREEN)
tableau(["Étape", "Qui", "Où", "Ce qui se passe"], [
    ["1. Devis", "Céline", "Odoo, devis, cadre « Transport de la commande (pierre) »", "Choix du <b>mode de transport</b> (nos camions / transporteur extérieur / enlèvement par le client). Transporteur extérieur : demande de tarif, choix, prix d'achat. La ligne « Transport de pierres » s'ajoute toute seule en fin de devis (prix d'achat + 40 %), Céline peut l'ajuster."],
    ["2. Fabrication", "Atelier", "Tablette, poste de scan", "Pierres faites, mises en palette, palettes <b>clôturées</b> avec emplacement (bon de colisage imprimé, mail à Céline)."],
    ["3. Départ", "Chargeur", "Écran <b>Expédition</b> (onglet 🚚 de la tablette et du poste de scan)", "Scan des bons de colisage, transport prérempli depuis le devis, validation du départ : liste de chargement à imprimer et signer, mail au bureau."],
    ["4. Automatique", "Odoo", "Commande, BL, tâche Commande Pierres", "<b>BL validé</b> pour les pièces parties (reliquat pour le reste), transporteur et suivi sur le BL, notes 🚚 📦 sur la commande, tâche en « Expédié » quand tout est parti."],
    ["5. Livraison", "Chauffeur ou Céline", "« Ma tournée » (nos camions), écran Expédition (affrètement)", "Palettes marquées <b>livrées</b> avec la date ; note 📍 sur la commande ; « commande entièrement livrée » quand plus rien n'est en fabrication ni en stock."],
    ["6. Facture", "Céline", "Odoo, commande", "Facturation sur les <b>quantités livrées</b>, qui suivent désormais les départs réels."],
], [26 * mm, 24 * mm, 46 * mm, W - 2 * MARG - 96 * mm])
note("Trois règles : une palette ne part que <b>clôturée</b> ; une palette partie ne se re-scanne pas (l'écran la refuse) ; en cas d'erreur, on <b>annule le départ</b> depuis « Départs des 10 derniers jours », on ne bricole pas la fiche Colis.", bg=GREENL, fg=GREEN)
story.append(Paragraph("Mis en place le 07/10/2026. Pages : /expedition (écran), /expedition/liste (liste de chargement), Suivi devis/commande (ligne « 📦 palettes »), Inventaire → Colis (cadre « Expédition »).", st_small))

# ───────────── ORGANIGRAMME DU FLUX ─────────────
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon


def organigramme():
    Wd, Hd = W - 2 * MARG, 150 * mm
    d = Drawing(Wd, Hd)
    C = {"celine": colors.HexColor("#01666B"), "atelier": colors.HexColor("#1D4ED8"), "charg": colors.HexColor("#0E7490"),
         "odoo": colors.HexColor("#B45309"), "client": colors.HexColor("#15803D"), "fin": colors.HexColor("#334155")}

    def boite(x, y, w, h, titre, lignes, coul, fs=8.2):
        d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=colors.white, strokeColor=coul, strokeWidth=1.3))
        d.add(Rect(x, y + h - 5.2 * mm, w, 5.2 * mm, rx=5, ry=5, fillColor=coul, strokeColor=coul))
        d.add(Rect(x, y + h - 5.2 * mm, w, 2.6 * mm, fillColor=coul, strokeColor=coul))
        d.add(String(x + w / 2, y + h - 3.7 * mm, titre, fontName="Helvetica-Bold", fontSize=8.6, fillColor=colors.white, textAnchor="middle"))
        yy = y + h - 9.3 * mm
        for ln in lignes:
            d.add(String(x + w / 2, yy, ln, fontName="Helvetica", fontSize=fs, fillColor=INK, textAnchor="middle")); yy -= 3.8 * mm

    def fleche(x1, y1, x2, y2):
        d.add(Line(x1, y1, x2, y2, strokeColor=GREY, strokeWidth=1.1))
        import math
        a = math.atan2(y2 - y1, x2 - x1); L = 2.6 * mm
        d.add(Polygon([x2, y2, x2 - L * math.cos(a - 0.45), y2 - L * math.sin(a - 0.45), x2 - L * math.cos(a + 0.45), y2 - L * math.sin(a + 0.45)], fillColor=GREY, strokeColor=GREY))

    g = 3 * mm; col = (Wd - 2 * g) / 3
    # ligne 1 : devis
    y1, h1 = Hd - 16 * mm, 14 * mm
    boite(0, y1, Wd, h1, "1 - DEVIS  (Céline)", ["Mode de transport choisi sur le devis : nos camions / transporteur extérieur / enlèvement par le client", "La ligne « Transport de pierres » s'ajoute toute seule en fin de devis"], C["celine"])
    # ligne 2 : trois branches
    y2, h2 = y1 - 27 * mm, 22 * mm
    boite(0, y2, col, h2, "Nos camions", ["Ligne transport créée à 0 :", "Céline la chiffre", "(variante au choix)"], C["celine"])
    boite(col + g, y2, col, h2, "Transporteur extérieur", ["Demande de tarif aux transporteurs", "(copie à Céline) → prix saisis →", "offre confirmée = ordre de transport", "ligne transport = achat + 40 %"], C["celine"], fs=7.8)
    boite(2 * (col + g), y2, col, h2, "Enlèvement par le client", ["Pas de ligne transport", "(une ligne vide est retirée)"], C["client"])
    for i in range(3):
        fleche(i * (col + g) + col / 2, y1, i * (col + g) + col / 2, y2 + h2)
    # ligne 3 : fabrication
    y3, h3 = y2 - 19 * mm, 14 * mm
    boite(0, y3, Wd, h3, "2 - COMMANDE confirmée → FABRICATION  (atelier)", ["Pierres faites, mises en palette ; palettes clôturées avec emplacement : bon de colisage imprimé, mail à Céline"], C["atelier"])
    for i in range(3):
        fleche(i * (col + g) + col / 2, y2, i * (col + g) + col / 2, y3 + h3)
    # ligne 4 : expédition
    y4, h4 = y3 - 20 * mm, 15 * mm
    boite(0, y4, Wd, h4, "3 - EXPÉDITION  (chargeur, écran Expédition)", ["Scan des bons de colisage → transport prérempli depuis le devis → « Valider le départ »", "Liste de chargement imprimée et signée ; palette « Chargée » (ou « Enlevée » pour un client)"], C["charg"])
    fleche(Wd / 2, y3, Wd / 2, y4 + h4)
    # ligne 5 : automatismes
    y5, h5 = y4 - 24 * mm, 19 * mm; col4 = (Wd - 3 * g) / 4
    boite(0, y5, col4, h5, "BL validé", ["pièces parties, en m³ ;", "reliquat automatique ;", "transporteur et suivi"], C["odoo"], fs=7.6)
    boite(col4 + g, y5, col4, h5, "Commande", ["notes : départ, BL,", "livraison ; devis", "complété si besoin"], C["odoo"], fs=7.6)
    boite(2 * (col4 + g), y5, col4, h5, "Bureau", ["mail « Départ palettes »", "+ liste de chargement", "(Céline, Loïc)"], C["odoo"], fs=7.6)
    boite(3 * (col4 + g), y5, col4, h5, "Tâche Commande Pierres", ["→ « Expédié » quand", "tout est parti"], C["odoo"], fs=7.6)
    for i in range(4):
        fleche(Wd / 2, y4, i * (col4 + g) + col4 / 2, y5 + h5)
    d.add(String(Wd, y5 + h5 + 1.2 * mm, "4 - automatique (Odoo)", fontName="Helvetica-Oblique", fontSize=7.5, fillColor=C["odoo"], textAnchor="end"))
    # ligne 6 : livraison selon le mode
    y6, h6 = y5 - 24 * mm, 19 * mm
    boite(0, y6, col, h6, "Nos camions : chauffeur", ["« Ma tournée » : cadre", "« Palettes à livrer »", "→ « Palettes livrées »"], C["charg"], fs=7.8)
    boite(col + g, y6, col, h6, "Transporteur : Céline", ["récépissé reçu →", "« Marquer livré » (écran", "Expédition) ou fiche Colis"], C["celine"], fs=7.8)
    boite(2 * (col + g), y6, col, h6, "Client", ["palette « Enlevée »", "dès le départ :", "rien à faire"], C["client"], fs=7.8)
    for i in range(3):
        fleche(Wd / 2, y5, i * (col + g) + col / 2, y6 + h6)
    d.add(String(Wd, y6 + h6 + 1.2 * mm, "5 - livraison", fontName="Helvetica-Oblique", fontSize=7.5, fillColor=C["charg"], textAnchor="end"))
    # ligne 7 : livrée -> facture
    y7, h7 = y6 - 17 * mm, 12 * mm
    boite(0, y7, Wd, h7, "Palette « Livrée » → 6 - FACTURE  (Céline)", ["Note « Livraison » sur la commande ; facturation sur les quantités réellement livrées (reliquat = reste à produire ou à charger)"], C["fin"])
    for i in range(3):
        fleche(i * (col + g) + col / 2, y6, i * (col + g) + col / 2, y7 + h7)
    return d


story.append(PageBreak())
sect("ORGANIGRAMME DU FLUX — du devis à la facture", GREEN)
story.append(organigramme())
story.append(Paragraph("Couleurs : vert-bleu = Céline, bleu = atelier et chargeur, orange = ce qu'Odoo fait tout seul, vert = client. Les pages et boutons sont détaillés dans les fiches suivantes.", st_small))

# ───────────── FICHE 1 — CÉLINE : LE DEVIS ─────────────
story.append(PageBreak())
sect("FICHE 1 — CÉLINE : décider et chiffrer le transport sur le devis")
story.append(Paragraph("Sur chaque devis pierre, sous « Demande de transport Maquignon », le cadre <b>« Transport de la commande (pierre) »</b> porte le mode de transport. C'est lui que l'écran Expédition reprend au départ.", st_txt))
story.append(Paragraph("Choisir le mode de transport", st_h2))
steps([
    "<b>Nos camions</b> : la ligne « Transport de pierres (Forfait Palettes) » s'ajoute toute seule en fin de devis quelques secondes après l'enregistrement (recharger le devis pour la voir), à 0 : la chiffrer (et changer la variante si besoin).",
    "<b>Enlèvement par le client</b> : pas de ligne transport (une ligne transport encore vide est retirée). Au départ, le chargeur saisira le nom de la personne et l'immatriculation.",
    "<b>Transporteur extérieur</b> : suivre les étapes ci-dessous pour obtenir et retenir un tarif.",
])
story.append(Paragraph("Transporteur extérieur : demander un tarif", st_h2))
steps([
    "Cocher les <b>transporteurs à consulter</b> (contacts portant l'étiquette « Transporteur » : GENDRON TRANSPORTS, TRANSPORTS P. FRECHOT…). Pour en ajouter un : fiche fournisseur avec adresse e-mail + étiquette « Transporteur ».",
    "Cliquer <b>« Demander un tarif transport »</b> : Odoo crée une <b>demande de prix</b> (Achats) par transporteur, pré-remplie avec la commande, l'enlèvement à Usseau, l'adresse de livraison, le nombre de palettes (ou une estimation sur 1 500 kg par palette), le poids et le volume des lignes, la date souhaitée. Si la fiche du transporteur a un e-mail, la demande part aussitôt par mail, <b>avec Céline en copie</b> (et le vendeur du devis) ; sinon elle est créée sans envoi (le fil du devis le dit).",
    "Quelques secondes plus tard, le fil du devis liste les demandes créées ; les ouvrir dans Achats (origine = n° du devis). Saisir sur chacune le <b>prix HT reçu</b> (ligne « Transport affrété ») et, en note, le délai.",
    "<b>Confirmer</b> la demande retenue : elle devient l'ordre de transport ; le devis reçoit <b>Transporteur retenu, Prix d'achat transport HT, Ordre de transport</b> ; les autres demandes sont annulées ; une note le dit dans le fil.",
    "La ligne <b>« Transport de pierres »</b> du devis prend automatiquement le <b>prix d'achat + 40 %</b> (marge réglable par Xavier) et le nom du transporteur ; l'ajuster si besoin.",
])
note("La facture du transporteur se rapproche ensuite de l'ordre de transport dans Achats (compte 624200). Si le poids réel à la clôture des palettes s'éloigne de l'estimation, reconfirmer le tarif avec le transporteur.")
story.append(Paragraph("Après le départ", st_h2))
steps([
    "Le fil de la commande reçoit : 🚚 <b>départ</b> (chargement, palettes, poids, transporteur ou camion, chargé par), 📦 <b>BL</b> (lignes validées, reliquat), puis 📍 <b>livraison</b>.",
    "Facturer sur les <b>quantités livrées</b> : elles correspondent aux pièces réellement parties ; le reliquat du BL couvre ce qui reste à produire ou à charger.",
    "Un devis d'avant le 07/10 n'a pas de mode : l'écran Expédition le signale au chargeur et le devis est complété au départ. Pour éviter cette question, renseigner le mode sur les commandes encore ouvertes.",
])

# ───────────── FICHE 2 — CHARGEUR : L'ÉCRAN EXPÉDITION ─────────────
story.append(PageBreak())
sect("FICHE 2 — CHARGEUR : enregistrer le départ des palettes")
story.append(Paragraph("Écran <b>Expédition</b> : onglet 🚚 en haut de la tablette et du poste de scan, ou menu Logistiques → Expédition palettes. Douchette ou caméra de la tablette.", st_txt))
story.append(Paragraph("1. Scanner les bons de colisage", st_h2))
steps([
    "Scanner le code-barre du <b>bon de colisage</b> de chaque palette chargée (ou taper son numéro, ex. 102, puis Entrée). La palette s'affiche : client, commande, adresse de livraison, nombre d'OF, poids, volume.",
    "L'écran <b>refuse</b> une palette non clôturée (« clôturez-la d'abord »), vide, ou déjà partie (il indique quand, avec qui, et le n° de chargement).",
    "Si le chargement mélange plusieurs clients, un avertissement orange s'affiche : vérifier avant de valider. La corbeille 🗑️ retire une palette scannée par erreur.",
])
capture("expedition_scan.jpg", "Écran Expédition après le scan de PACK0000102 : la palette est affichée avec sa commande et son adresse ; le devis de cette commande ne portait pas de mode de transport, l'écran le signale.", max_h=150 * mm)
story.append(Paragraph("2. Transport : prérempli depuis le devis", st_h2))
steps([
    "Dès la première palette, le cadre affiche <b>« ✅ Prévu au devis S… : … »</b> et sélectionne le mode, le transporteur ou le camion. Ne rien changer si c'est juste.",
    "<b>Nos camions</b> : choisir le camion dans la liste, chauffeur facultatif. <b>Transporteur extérieur</b> : transporteur, immatriculation, n° de lettre de voiture si on l'a. <b>Enlèvement par le client</b> : nom de la personne qui enlève et immatriculation.",
    "Si l'on choisit autre chose que le devis, le cadre passe en orange avec l'écart : c'est permis, mais à faire sciemment. Si le devis ne dit rien, l'écran le dit et le devis sera complété au départ.",
    "<b>Chargé par</b> : son nom (gardé d'un chargement à l'autre).",
])
capture("expedition_transporteur.jpg", "« Transporteur extérieur » choisi : transporteur, immatriculation, chauffeur, chargé par, lettre de voiture. Le bouton « Valider le départ » devient actif dès qu'une palette est scannée.", max_h=112 * mm)
story.append(Paragraph("3. Valider le départ", st_h2))
steps([
    "Appuyer sur <b>« 🚚 Valider le départ »</b> et confirmer. Les palettes passent « Chargée » (ou « Enlevée » pour un client), avec un n° de chargement CHG-AAAAMMJJ-HHMM.",
    "Cliquer <b>« 🖨 Liste de chargement »</b> : l'imprimer en deux exemplaires, la faire signer par le chauffeur ou le client (cases Chargeur / Chauffeur ou Client / Réserves), en garder une. La liste reprend commande, client, adresse, palettes, poids, volume, transporteur, camion, lettre de voiture.",
    "Le bureau reçoit aussitôt le mail « Départ palettes … » avec le lien de la liste. Puis <b>« 🆕 Nouveau chargement »</b> pour le suivant.",
])
story.append(Paragraph("Départs des 10 derniers jours", st_h2))
steps([
    "Réimprimer une liste de chargement ; <b>↩️ annuler le départ</b> d'une palette (elle redevient « en stock », le bureau est informé par une note) ; <b>📍 Marquer livré</b> quand le transporteur a livré (voir fiche 4).",
])
note("Une palette non clôturée ne peut pas partir : la clôturer d'abord (tablette ou poste de scan, avec l'emplacement). Une palette partie par erreur : annuler le départ ici, puis la remettre si besoin.")

# ───────────── FICHE 3 — CHAUFFEUR ─────────────
story.append(PageBreak())
sect("FICHE 3 — CHAUFFEUR (nos camions) : confirmer la livraison dans « Ma tournée »")
steps([
    "Ouvrir <b>Ma tournée</b> (lien personnel). Sur la mission du client, un cadre bleu <b>« 📦 Palettes à livrer »</b> liste les palettes chargées sur ce camion pour ce client, avec le poids.",
    "Une fois déchargé chez le client : appuyer sur <b>« 📍 Palettes livrées »</b> et confirmer. Les palettes passent « Livrée » avec la date et l'heure, et la commande reçoit la note 📍 avec votre nom.",
    "Prendre aussi la <b>photo de livraison</b> comme d'habitude (📸 Photo livr.).",
    "Si des palettes d'un autre client sont sur le même camion sans mission à ce nom, elles apparaissent avec la mention « autre client, même camion » : les confirmer au moment où elles sont livrées.",
])
note("Le cadre n'apparaît que si le départ a été enregistré sur l'écran Expédition avec « Nos camions » et le bon camion. Pas de cadre = pas de départ enregistré : prévenir le bureau.", bg=BLUEL, fg=BLUE)

# ───────────── FICHE 4 — BUREAU ─────────────
sect("FICHE 4 — BUREAU : suivre, livrer, corriger", ORANGE)
story.append(Paragraph("Où voir l'état des palettes", st_h2))
steps([
    "<b>Suivi devis/commande</b> : chaque carte de commande affiche « 📦 N palettes : x en stock · y parties · z livrées · dernier départ … (transporteur ou camion) ».",
    "<b>Inventaire → Colis</b> : cadre « Expédition » sur la fiche (statut, mode, transporteur, camion, chauffeur, date de départ, chargé par, n° de chargement, lettre de voiture, date de livraison) ; colonnes Statut et Date de départ dans la liste (filtres possibles).",
    "<b>Fil de la commande</b> : notes 🚚 départ, 📦 BL, 📍 livraison. <b>Tâche Commande Pierres</b> : passe en « Expédié » quand toutes les palettes sont parties et plus rien n'est en fabrication.",
])
story.append(Paragraph("Transporteur extérieur : marquer la livraison", st_h2))
steps([
    "Quand le transporteur confirme (récépissé, mail, suivi) : écran Expédition → « Départs des 10 derniers jours » → <b>« 📍 Marquer livré »</b> sur le chargement ; ou sur la fiche Colis, statut « Livrée » et date.",
    "Joindre le récépissé signé au fil de la commande (glisser-déposer) : c'est la preuve de livraison.",
])
story.append(Paragraph("Ce que fait le BL automatiquement, et quoi faire si ça bloque", st_h2))
steps([
    "Au départ, le bon de livraison en attente de la commande est <b>validé pour les pièces parties</b> : un OF entier = toute sa ligne (m³) ; des pièces réparties = au prorata ; Odoo crée le <b>reliquat</b> pour le reste. Transporteur (camion) et référence de suivi (chargement, qui, palettes, lettre de voiture) sont écrits sur le BL.",
    "Si le fil de la commande dit « <b>BL non validé automatiquement</b> : … » : le départ est bien enregistré, seul le BL est à valider à la main (ou à signaler à Xavier). Les quantités livrées ne bougent qu'une fois le BL validé.",
    "Pour suspendre la validation automatique des BL : paramètre système maquignon.expedition_bl = 0 (Xavier).",
])
story.append(Paragraph("Annuler, corriger", st_h2))
steps([
    "<b>Départ enregistré par erreur</b> : écran Expédition → Départs des 10 derniers jours → ↩️ annuler le départ de la palette (retour « en stock », note sur la commande). Le BL déjà validé ne se dévalide pas tout seul : corriger le BL avec Xavier si des quantités livrées sont fausses.",
    "<b>Livraison marquée par erreur</b> : ↩️ annuler la livraison (la palette redevient « chargée »).",
    "<b>Mauvais transporteur ou camion</b> : annuler le départ puis refaire le chargement avec le bon choix ; la fiche Colis permet aussi de corriger un champ isolé.",
])
note("Les anciennes commandes en 3 étapes (transfert interne → colis → livraison) sont traitées en chaîne par le départ ; les commandes récentes n'ont qu'un bon de livraison.")
story.append(Spacer(1, 6))
story.append(Paragraph("Récapitulatif des statuts d'une palette : En stock (clôturée, pas partie) → Chargée (départ enregistré, nos camions ou transporteur) ou Enlevée par le client → Livrée.", st_small))

doc.build(story)
print("procedure_transport_palettes.pdf généré")
