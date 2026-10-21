# -*- coding: utf-8 -*-
"""Procédure « Export mensuel des ventes Distri Béton vers le cabinet FITECO » (21/10/2026).
  python build_procedure_export_distribeton.py  ->  Desktop/Maquignon/Procedure_export_ventes_DistriBeton_Fiteco_2026-10-21.pdf
Captures : docs/captures_export/distri_haut.jpg (formulaire + étapes 1-2) et distri_bas.jpg (étapes 3-4)."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = r"C:\Users\xavfe\Desktop\Maquignon\Procedure_export_ventes_DistriBeton_Fiteco_2026-10-21.pdf"
CAPTURES = [os.path.join(ICI, 'captures_export', 'distri_haut.jpg'), os.path.join(ICI, 'captures_export', 'distri_bas.jpg')]
INK = colors.HexColor('#0f172a'); GREY = colors.HexColor('#475569'); BLUE = colors.HexColor('#1d4ed8'); LIGHT = colors.HexColor('#eef2ff'); LINE = colors.HexColor('#cbd5e1')
H1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=INK, spaceAfter=4)
H2 = ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=BLUE, spaceBefore=10, spaceAfter=4)
P = ParagraphStyle('p', fontName='Helvetica', fontSize=9.8, leading=13.5, textColor=INK)
SMALL = ParagraphStyle('s', parent=P, fontSize=8.6, leading=11.5, textColor=GREY)
ETAPE = ParagraphStyle('e', parent=P, leftIndent=14, firstLineIndent=-14, spaceAfter=2)
PUCE = ParagraphStyle('b', parent=P, leftIndent=10, firstLineIndent=-8, spaceAfter=1.5)
NOTE = ParagraphStyle('n', parent=P, backColor=LIGHT, borderPadding=(5, 7, 5, 7), leftIndent=4, rightIndent=4, spaceBefore=4, spaceAfter=6)


def etapes(lignes):
    return [Paragraph('%d. %s' % (i + 1, l), ETAPE) for i, l in enumerate(lignes)]


def puces(lignes):
    return [Paragraph('\u2022 ' + l, PUCE) for l in lignes]


def tableau(lignes, largeurs):
    t = Table([[Paragraph(c, P) for c in l] for l in lignes], colWidths=largeurs)
    t.setStyle(TableStyle([('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9.5), ('BACKGROUND', (0, 0), (-1, 0), LIGHT), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                           ('LINEBELOW', (0, 0), (-1, -1), 0.3, LINE), ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    return t


def capture(chemin, legende, largeur=100):
    if not os.path.exists(chemin):
        return []
    img = Image(chemin); ratio = img.imageHeight / float(img.imageWidth); img.drawWidth = largeur * mm; img.drawHeight = largeur * mm * ratio; img.hAlign = 'CENTER'
    return [img, Paragraph(legende, SMALL), Spacer(1, 4)]


doc = SimpleDocTemplate(SORTIE, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                        title="Distri Béton - Export mensuel des ventes vers le cabinet FITECO", author="Carrières Maquignon")
s = []
s.append(Paragraph("DISTRI BÉTON — Export mensuel des ventes vers le cabinet FITECO", H1))
s.append(Paragraph("Page « Export/Import Sage » d'Odoo, société SAS DISTRI BETON VIENNE. Remplace le bouton d'export de la fiche du journal, retiré le 02/09/2026. Version du 21/10/2026.", SMALL))
s.append(Spacer(1, 6))

s.append(Paragraph("En deux mots", H2))
s.append(Paragraph("Chaque mois, <b>entre le 1<super>er</super> et le 15</b>, on envoie au cabinet FITECO Châtellerault le fichier des <b>ventes du mois précédent</b> "
                   "(factures et avoirs clients, journal VE) pour qu'il fasse la TVA. Achats et banque sont tenus par le cabinet à partir des pièces ; la banque reste rapprochée dans Odoo. "
                   "Le fichier est le même qu'avant (format validé par Christine Fontenault le 24/04/2025), seule la façon de le produire change.", P))

s.extend(capture(CAPTURES[0], "La page pour Distri Béton : société, période, puis les étapes 1 (vérifier) et 2 (exporter)."))

s.append(KeepTogether([Paragraph("1. Ouvrir la page", H2)] + etapes([
    "Dans Odoo, application <b>Comptabilité</b>, menu <b>Export/Import Sage</b> (la page s'ouvre dans un nouvel onglet, le jeton d'accès est inclus).",
    "Choisir la société <b>SAS DISTRI BETON VIENNE</b> dans la liste : la page passe en mode « cabinet FITECO » et ne montre que le journal des ventes.",
    "Vérifier la période : elle est préremplie au lendemain du dernier export. Pour un mois complet, mettre <b>du 1<super>er</super> au dernier jour du mois</b> (ex. du 01/09/2026 au 30/09/2026).",
])))

s.append(KeepTogether([Paragraph("2. Vérifier (étape 1 de la page)", H2)] + puces([
    "<b>Rien à signaler</b> : on passe à l'export.",
    "<b>Garde-fou</b> « pièces déjà transférées exclues » : des factures de la période ont déjà été exportées (fichier précédent) ; elles ne ressortiront pas, c'est normal.",
    "<b>Écritures rétroactives</b> : des factures datées d'une période déjà exportée ont été saisies depuis. Bouton <b>Exporter ces écritures pour FITECO</b> : un fichier à part, à envoyer au cabinet avec le fichier du mois.",
])))

s.append(KeepTogether([Paragraph("3. Exporter (étape 2)", H2)] + etapes([
    "Bouton <b>« Télécharger le fichier des ventes (.csv) »</b>. Le fichier arrive dans Téléchargements sous le nom <b>ventes_DISTRIBETON_AAAA-MM.csv</b> (ex. ventes_DISTRIBETON_2026-09.csv).",
    "Les factures du fichier sont marquées <b>« Transféré Sage »</b> dans Odoo : cela veut dire « transmises au cabinet ». Elles ne ressortiront plus dans un export suivant.",
    "Ne pas ouvrir le fichier avec Excel puis l'enregistrer : Excel abîme les dates et les accents. Pour y jeter un œil, l'ouvrir avec le Bloc-notes.",
])))

s.extend(capture(CAPTURES[1], "Étapes 3 (envoyer au cabinet) et 4 (verrouiller).", 95))

s.append(KeepTogether([Paragraph("4. Envoyer au cabinet (étape 3)", H2)] + etapes([
    "Bouton <b>« Préparer l'e-mail au cabinet »</b> : la messagerie s'ouvre avec les destinataires (Christine Fontenault, copie Aurélia Colin), l'objet et le texte déjà remplis.",
    "<b>Joindre le fichier</b> téléchargé à l'étape 2 (et le fichier des écritures rétroactives s'il y en a un), puis envoyer. Variante : dépôt sur MyFiteco.",
    "Attention : la boîte <b>ventes+207082@fiteco.com</b> sert aux factures envoyées une par une (c'est l'adresse de la fiche « PARTICULIER BORNE ») ; le fichier mensuel, lui, va aux comptables.",
])))

s.append(KeepTogether([Paragraph("5. Verrouiller les ventes (étape 4)", H2), Paragraph("Une fois le fichier envoyé, <b>verrouiller les ventes jusqu'au dernier jour du mois exporté</b> et confirmer. Plus aucune facture de Distri Béton ne pourra être créée ou modifiée à une date antérieure : ce que le cabinet a reçu reste figé. Le verrou ne recule jamais.", P)]))

s.append(Paragraph("6. Cas particuliers", H2))
s.append(tableau([
    ['Situation', 'Que faire'],
    ["Une facture a été oubliée ou saisie après l'export", "Carte <b>Exporter une seule facture</b> : taper son numéro (ex. FAC/2026/00461), télécharger le fichier ventes_DISTRIBETON_FAC-2026-00461.csv et l'envoyer au cabinet avec un mot. Si la facture est déjà marquée transférée, la page demande confirmation."],
    ['Un avoir', "Il est dans le journal des ventes comme une facture : il part dans le fichier du mois, en sens inverse."],
    ["Le fichier du mois a été perdu ou jamais importé par le cabinet", "Cocher <b>Inclure les pièces déjà transférées</b> (bandeau rouge), retélécharger, et prévenir le cabinet qu'il s'agit d'un renvoi pour éviter un doublon."],
    ["Savoir ce qui a été envoyé", "<b>Historique des exports</b> en bas de page : date, journal, période. Le bloc « Dernier export » en haut rappelle la dernière période sortie."],
    ["La page refuse de s'ouvrir (page blanche ou « 403 »)", "Repasser par le menu Odoo <b>Comptabilité > Export/Import Sage</b> : le jeton d'accès de l'adresse doit être présent."],
], [60 * mm, 118 * mm]))

s.append(Paragraph("7. Ce que contient le fichier (pour le cabinet)", H2))
s.extend(puces([
    "Un fichier texte, une ligne par écriture, colonnes séparées par « ; » : numéro de pièce, numéro de facture, journal VE, date de facture (JJMMAA), code client, référence, nom du client, compte, libellé, échéance, débit, crédit, lien vers le PDF de la facture, plan, analytique, type.",
    "Pour chaque facture : une ligne <b>411100</b> client (débit TTC, code client <b>DISxxxxx</b> ; particuliers de la borne = <b>DIS99999</b>), une ligne <b>701100</b> ventes HT (la REP béton y est fusionnée : une seule ligne HT + taxe éco, comme demandé), une ligne <b>445711</b> TVA collectée. Les ventes de badges sont en 707100.",
    "Format identique à celui validé par Fiteco le 24/04/2025 (compte 7011 au lieu de 7071, une ligne HT + taxe éco, TVA 445711).",
]))

s.append(Paragraph("Contacts FITECO Châtellerault : Christine FONTENAULT — c.fontenault@fiteco.com · Aurélia COLIN — aurelia.colin@fiteco.com · 05 49 20 02 92. Boîte factures (envoi unitaire) : ventes+207082@fiteco.com.", NOTE))

doc.build(s)
print('écrit :', SORTIE)
