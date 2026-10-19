# -*- coding: utf-8 -*-
"""Procédure « Prestations S3T sur la fiche de fin de travaux » (19/10/2026).
  python build_procedure_s3t.py  ->  Desktop/Protec assainissement/Procedure_fiche_S3T_2026-10-19.pdf
Captures facultatives : docs/captures_s3t/1_onglet_s3t.png, 2_bandeau_s3t.png, 3_devis_s3t.png, 4_chatter_creneau.png."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = r"C:\Users\xavfe\Desktop\Protec assainissement\Procedure_fiche_S3T_2026-10-19.pdf"
CAP = lambda n: os.path.join(ICI, 'captures_s3t', n)
INK = colors.HexColor('#0f172a'); GREY = colors.HexColor('#475569'); BLUE = colors.HexColor('#0b7285'); LIGHT = colors.HexColor('#e6f4f1'); LINE = colors.HexColor('#cbd5e1')
H1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=INK, spaceAfter=4)
H2 = ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=13, leading=16, textColor=BLUE, spaceBefore=12, spaceAfter=5)
P = ParagraphStyle('p', fontName='Helvetica', fontSize=10, leading=14, textColor=INK)
SMALL = ParagraphStyle('s', parent=P, fontSize=8.6, leading=11.5, textColor=GREY)
ETAPE = ParagraphStyle('e', parent=P, leftIndent=14, firstLineIndent=-14, spaceAfter=3)
NOTE = ParagraphStyle('n', parent=P, backColor=LIGHT, borderPadding=(5, 7, 5, 7), leftIndent=4, rightIndent=4, spaceBefore=4, spaceAfter=6)


def etapes(lignes):
    return [Paragraph('%d. %s' % (i + 1, l), ETAPE) for i, l in enumerate(lignes)]


def tableau(lignes, largeurs, style=P):
    t = Table([[Paragraph(c, style) for c in l] for l in lignes], colWidths=largeurs, repeatRows=1)
    t.setStyle(TableStyle([('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9.5), ('BACKGROUND', (0, 0), (-1, 0), LIGHT), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                           ('LINEBELOW', (0, 0), (-1, -1), 0.3, LINE), ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    return t


def capture(nom, legende, largeur=178):
    f = CAP(nom)
    if not os.path.exists(f):
        return []
    img = Image(f); ratio = img.imageHeight / float(img.imageWidth); img.drawWidth = largeur * mm; img.drawHeight = largeur * mm * ratio
    return [Spacer(1, 3), img, Paragraph(legende, SMALL), Spacer(1, 4)]


def deux_captures(n1, l1, n2, l2, largeur=68):
    """Deux captures téléphone côte à côte."""
    cells = []
    for n, l in ((n1, l1), (n2, l2)):
        f = CAP(n)
        if not os.path.exists(f):
            continue
        img = Image(f); ratio = img.imageHeight / float(img.imageWidth); img.drawWidth = largeur * mm; img.drawHeight = largeur * mm * ratio
        cells.append([img, Paragraph(l, SMALL)])
    if not cells:
        return []
    t = Table([[c[0] for c in cells], [c[1] for c in cells]], colWidths=[(largeur + 6) * mm] * len(cells))
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    return [Spacer(1, 3), t, Spacer(1, 4)]


doc = SimpleDocTemplate(SORTIE, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                        title="Prestations S3T sur la fiche de fin de travaux", author="PROTEC")
s = [Paragraph("Prestations S3T sur la fiche de fin de travaux", H1),
     Paragraph("Sous-traitance S3T pour PROTEC : saisie par Thomas sur le téléphone, suivi par le bureau. Version du 19/10/2026.", SMALL), Spacer(1, 6)]
s.append(Paragraph("Quand S3T intervient pour un client PROTEC (inspection télévisée, prise en charge du fourgon, location de caméra…), "
                   "Thomas remplit la fiche de fin de travaux habituelle et note les prestations S3T dans l'onglet <b>S3T</b>. "
                   "Ces prestations sont transmises au bureau PROTEC et un devis S3T → PROTEC est créé automatiquement pour la facturation de S3T.", NOTE))

s.append(Paragraph("Côté Thomas : remplir l'onglet S3T", H2))
s.extend(etapes(["Ouvrir <b>Ma tournée</b> sur le téléphone (lien habituel), puis la fiche de fin de travaux de l'intervention.",
                 "Remplir la fiche comme d'habitude : véhicule, heures d'arrivée et de départ, trajet, opérateurs.",
                 "Appuyer sur l'onglet <b>S3T</b> (dernier onglet du bloc « Nature des travaux »). La liste reprend les articles de S3T : inspections télévisées REU, REP ou EU + EP, forfaits « moins de 275 ml », branchements, prise en charge d'un fourgon, rapport d'ITV, location de caméra, découchage…",
                 "Saisir la <b>quantité réalisée</b> en face de chaque prestation faite, dans l'unité indiquée (forfait, heure, unité, nuit). Laisser vide ce qui n'a pas été fait.",
                 "Ligne <b>Précisions S3T</b> : le matériel ou une remarque utile pour la facturation (caméra utilisée, regard, longueur…).",
                 "Signature et photos comme d'habitude, puis <b>ENREGISTRER</b>. Le bandeau vert confirme et affiche le numéro du devis S3T créé (ex. S3T2026-0068).",
                 "<b>PAUSE</b> garde les saisies sans rien transmettre : rien n'est créé côté S3T tant que la fiche n'est pas enregistrée."]))
s.extend(deux_captures('1_onglet_s3t.png', "L'onglet S3T : quantités en face des prestations réalisées, puis précisions.",
                       '2_bandeau_s3t.png', "Après ENREGISTRER : le bandeau indique le devis S3T créé."))
s.append(Paragraph("Si la fiche est modifiée et enregistrée à nouveau, les prestations du devis S3T sont remplacées par les nouvelles, tant que S3T n'a pas confirmé ce devis. "
                   "Une fois le devis confirmé par S3T, il n'est plus modifié : prévenir le bureau en cas de correction.", NOTE))

s.append(Paragraph("Côté bureau PROTEC : où retrouver les prestations", H2))
s.extend(etapes(["<b>Sur le créneau du planning</b> : le chatter du créneau reçoit le résumé de la fiche avec un tableau « Prestations S3T (sous-traitant) » (prestation, quantité) et les précisions.",
                 "<b>Sur la commande PROTEC</b> (le devis ou bon de commande client lié au créneau) : une note « Prestations S3T (sous-traitant) » reprend le même tableau et le numéro du devis S3T. C'est le point de départ pour facturer le client PROTEC.",
                 "<b>Sur le rapport d'intervention client</b> : les prestations S3T figurent dans « Prestations réalisées », sans mention du sous-traitant.",
                 "<b>Côté S3T</b> (société S3T dans Odoo, menu Ventes › Devis) : un devis <b>S3T → PROTEC « Pôle Assainissement »</b> en brouillon, avec les lignes aux tarifs S3T, la référence de la commande PROTEC en référence client et, en bas, la date, le client et l'adresse de l'intervention. "
                 "Vérifier, <b>Confirmer</b>, puis facturer : la facture S3T arrive dans PROTEC par la facturation électronique comme aujourd'hui."]))
s.extend(capture('3_devis_s3t.jpg', "Le devis S3T → PROTEC créé en brouillon dans la société S3T (ici un test, supprimé ensuite)."))
s.extend(capture('4_chatter_creneau.png', "Le résumé de la fiche dans le chatter du créneau, avec le tableau des prestations S3T.", 52))

s.append(Paragraph("Points d'attention", H2))
s.append(tableau([
    ["Situation", "Explication", "Que faire"],
    ["L'onglet S3T affiche « Articles S3T inaccessibles »", "Odoo n'a pas répondu, ou le compte du relais n'a plus accès à la société S3T.", "Réessayer un peu plus tard ; si cela persiste, prévenir Xavier."],
    ["Le bandeau indique « ERREUR » après S3T", "La fiche est bien enregistrée, mais le devis S3T n'a pas pu être créé (article supprimé, droit manquant).", "Transmettre le message au bureau : le devis S3T se crée à la main depuis la note posée sur le créneau."],
    ["Plusieurs articles portent le même nom dans l'onglet (ex. « Prise en charge d'un fourgon »)", "Le catalogue S3T contient des doublons d'articles.", "Prendre le premier ; faire nettoyer le catalogue S3T (archiver les doublons) pour que la liste soit nette."],
    ["Le devis S3T ne correspond plus à la fiche", "La fiche a été ré-enregistrée après la confirmation du devis.", "Corriger le devis ou la facture S3T à la main."],
    ["Intervention sans commande PROTEC", "Le créneau n'a pas de référence de commande.", "Le devis S3T est quand même créé (origine « sans commande ») ; seule la note sur la commande PROTEC manque."],
], [52 * mm, 62 * mm, 64 * mm]))
doc.build(s)
print('PDF :', SORTIE)
