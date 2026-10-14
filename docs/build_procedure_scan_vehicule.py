# -*- coding: utf-8 -*-
"""Procédure « Scanner un document dans la fiche véhicule » pour Isabelle (14/10/2026).
  python build_procedure_scan_vehicule.py  ->  Desktop/Maquignon/Procedure_scanner_vehicule_2026-10-14.pdf
Capture facultative : docs/captures_scan/page_scan.jpg (insérée si présente)."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = r"C:\Users\xavfe\Desktop\Maquignon\Procedure_scanner_vehicule_2026-10-14.pdf"
CAPTURE = os.path.join(ICI, 'captures_scan', 'page_scan.jpg')
INK = colors.HexColor('#0f172a'); GREY = colors.HexColor('#475569'); BLUE = colors.HexColor('#1d4ed8'); LIGHT = colors.HexColor('#eef2ff'); LINE = colors.HexColor('#cbd5e1')
H1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=INK, spaceAfter=4)
H2 = ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=BLUE, spaceBefore=10, spaceAfter=4)
P = ParagraphStyle('p', fontName='Helvetica', fontSize=10, leading=14, textColor=INK)
SMALL = ParagraphStyle('s', parent=P, fontSize=8.6, leading=11.5, textColor=GREY)
ETAPE = ParagraphStyle('e', parent=P, leftIndent=14, firstLineIndent=-14, spaceAfter=3)
NOTE = ParagraphStyle('n', parent=P, backColor=LIGHT, borderPadding=(5, 7, 5, 7), leftIndent=4, rightIndent=4, spaceBefore=4, spaceAfter=6)


def etapes(lignes):
    return [Paragraph('%d. %s' % (i + 1, l), ETAPE) for i, l in enumerate(lignes)]


def tableau(lignes, largeurs):
    t = Table([[Paragraph(c, P) for c in l] for l in lignes], colWidths=largeurs)
    t.setStyle(TableStyle([('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9.5), ('BACKGROUND', (0, 0), (-1, 0), LIGHT), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                           ('LINEBELOW', (0, 0), (-1, -1), 0.3, LINE), ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    return t


doc = SimpleDocTemplate(SORTIE, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                        title="Scanner un document dans la fiche véhicule", author="Carrières Maquignon")
s = [Paragraph("Scanner un document dans la fiche véhicule (Odoo, Parc automobile)", H1),
     Paragraph("Scanner Brother DS-740D sur le PC de Franck + page « Scanner dans Odoo ». Version du 14/10/2026.", SMALL), Spacer(1, 6)]
if os.path.exists(CAPTURE):
    img = Image(CAPTURE); ratio = img.imageHeight / float(img.imageWidth); img.drawWidth = 178 * mm; img.drawHeight = 178 * mm * ratio
    s += [img, Paragraph("La page « Scanner dans Odoo » : le véhicule en cours, le type de document, puis la liste de ses documents.", SMALL)]

s.append(Paragraph("1. Au quotidien : scanner un document pour un véhicule", H2))
s.extend(etapes([
    "Dans Odoo, <b>Parc automobile</b>, ouvrir la fiche du véhicule, menu <b>⚙ Action</b> (en haut) → <b>📎 Scanner un document</b>. La page « Scanner dans Odoo » s'ouvre dans un nouvel onglet, avec l'immatriculation en gros.",
    "Sur la page, cliquer le <b>type</b> du document : Carte grise, Assurance, Contrôle technique, Facture, Entretien ou Document (le choix est gardé pour les suivants).",
    "Mettre le document dans le scanner et lancer la numérisation comme d'habitude (bouton du scanner ou « Numériser » dans iPrint&amp;Scan). Garder la page ouverte.",
    "Quelques secondes après, la page affiche <b>« … attaché au véhicule »</b> et une bulle Windows le confirme. Le document est dans la fiche du véhicule (Documents › Parc automobile et fil de discussion), nommé automatiquement « Type_immatriculation_date.pdf ».",
    "Document suivant du même véhicule : changer le type si besoin et scanner. Autre véhicule : taper son immatriculation ou son nom dans « Changer de véhicule » sur la page, ou repartir de sa fiche Odoo.",
]))
s.append(Paragraph("Il n'y a plus rien à nommer ni à glisser : le PDF scanné part seul dans le véhicule affiché. La copie reste sur le PC dans Documents › Scan Odoo › Envoyés.", NOTE))

s.append(Paragraph("2. Cas particuliers", H2))
s.append(tableau([
    ["Situation", "Ce qui se passe", "Que faire"],
    ["Scan lancé sans page « Scanner dans Odoo » ouverte", "Le document est gardé « à classer » (bulle Windows « à classer »).", "Ouvrir la page sur le bon véhicule : le document apparaît dans « en attente de classement », bouton <b>Classer dans …</b>."],
    ["Document attaché au mauvais véhicule", "Il est dans la liste du véhicule, marqué en vert.", "Bouton <b>Retirer</b> sur la page (il quitte Odoo), puis ouvrir le bon véhicule et le classer depuis « à classer »… ou rescanner."],
    ["Plusieurs onglets « Scanner » ouverts", "Le dernier onglet regardé décide du véhicule.", "Vérifier l'immatriculation affichée avant de scanner ; fermer les onglets inutiles."],
    ["Bulle « erreur » ou rien n'arrive", "Veilleur arrêté, internet coupé, ou dossier de scan changé dans iPrint&amp;Scan.", "Vérifier que le PDF est bien dans Documents › Scan Odoo ; redémarrer le PC (le veilleur repart seul) ; prévenir Xavier."],
], [50 * mm, 62 * mm, 66 * mm]))

s.append(Paragraph("3. Réglage une seule fois (PC de Franck, dans la session de Franck)", H2))
s.extend(etapes([
    "Installer le veilleur, connecté dans la session Windows qui scanne : dossier « poste » fourni par Xavier, dans PowerShell : <font face='Courier'>powershell -ExecutionPolicy Bypass -File installer.ps1 -Cle &lt;clé&gt; -Poste franck</font>. Il crée le dossier <b>Documents › Scan Odoo</b> de cette session, démarre le veilleur et le relance à chaque ouverture de session (icône « Scan Odoo » près de l'horloge).",
    "Dans <b>Brother iPrint&amp;Scan</b> : « Paramètres de Numérisation Appareil » (bouton du scanner) et/ou le bouton « Numériser » → fonction <b>Fichier</b>, type <b>PDF</b>, recto-verso si disponible, couleur automatique, 200 ou 300 ppp, <b>dossier de destination = Documents › Scan Odoo</b>. Le nom de fichier n'a pas d'importance (il est renommé dans Odoo).",
    "Sur la page « Scanner dans Odoo », en haut à droite, le nom du poste doit être le même que celui donné à l'installation (<b>franck</b>).",
    "Essai : ouvrir un véhicule, Action → Scanner un document, scanner une feuille : elle doit apparaître dans la liste en vert. La retirer avec <b>Retirer</b>.",
]))
s.append(Paragraph("Un autre poste (deuxième scanner) : refaire l'installation avec un autre nom de poste ; chaque poste a sa propre page et son propre dossier.", SMALL))
doc.build(s)
print('PDF :', SORTIE)
