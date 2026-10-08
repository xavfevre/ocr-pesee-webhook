# -*- coding: utf-8 -*-
"""Procédure caisse « Pont-bascule » pour Chatel'Granulats (08/10/2026).
  python build_procedure_bascule_chatel.py  ->  Desktop/Maquignon/Procedure_pont-bascule_Chatel_2026-10-08.pdf"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = r"C:\Users\xavfe\Desktop\Maquignon\Procedure_pont-bascule_Chatel_2026-10-08.pdf"
CAPTURE = os.path.join(ICI, 'captures_bascule', 'page_bascule.jpg')
INK = colors.HexColor('#0f172a'); GREY = colors.HexColor('#475569'); BLUE = colors.HexColor('#1d4ed8'); LIGHT = colors.HexColor('#eef2ff'); LINE = colors.HexColor('#cbd5e1')
H1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=INK, spaceAfter=4)
H2 = ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=BLUE, spaceBefore=10, spaceAfter=4)
P = ParagraphStyle('p', fontName='Helvetica', fontSize=9.8, leading=13.5, textColor=INK)
SMALL = ParagraphStyle('s', parent=P, fontSize=8.6, leading=11.5, textColor=GREY)
ETAPE = ParagraphStyle('e', parent=P, leftIndent=14, firstLineIndent=-14, spaceAfter=2)
NOTE = ParagraphStyle('n', parent=P, backColor=LIGHT, borderPadding=(5, 7, 5, 7), leftIndent=4, rightIndent=4, spaceBefore=4, spaceAfter=6)


def etapes(lignes):
    return [Paragraph('%d. %s' % (i + 1, l), ETAPE) for i, l in enumerate(lignes)]


def tableau(lignes, largeurs):
    t = Table([[Paragraph(c, P) for c in l] for l in lignes], colWidths=largeurs)
    t.setStyle(TableStyle([('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 9.5), ('BACKGROUND', (0, 0), (-1, 0), LIGHT), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                           ('LINEBELOW', (0, 0), (-1, -1), 0.3, LINE), ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    return t


doc = SimpleDocTemplate(SORTIE, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                        title="Chatel'Granulats - Pont-bascule : procédure caisse", author="Carrières Maquignon")
s = []
s.append(Paragraph("CHATEL'GRANULATS — Pont-bascule : procédure pour la caisse", H1))
s.append(Paragraph("Page « Pont-bascule » reliée à l'indicateur Bilanciai DD700, à l'imprimante Epson et à Odoo. Version du 08/10/2026.", SMALL))
s.append(Spacer(1, 6))
if os.path.exists(CAPTURE):
    img = Image(CAPTURE); ratio = img.imageHeight / float(img.imageWidth); img.drawWidth = 178 * mm; img.drawHeight = 178 * mm * ratio
    s.append(img); s.append(Paragraph("La page au repos : à gauche le poids et la pesée en cours, à droite les camions en attente de 2<super>e</super> pesée et les pesées du jour.", SMALL))

s.append(Paragraph("1. Ouvrir la page et connecter la bascule", H2))
s.extend(etapes([
    "Dans Odoo, application <b>Ventes</b>, menu <b>Pont-bascule</b> (ou le favori « Pont-bascule » de Chrome sur le PC de caisse). Chrome ou Edge uniquement.",
    "Première utilisation sur un PC : bouton <b>Connecter la bascule</b> en haut à droite, choisir <b>Prolific USB-to-Serial Comm Port (COM4)</b>, Connexion. Ensuite la page se reconnecte toute seule à l'ouverture.",
    "Vérifier les deux pastilles vertes en haut : <b>bascule connectée</b> et <b>Odoo connecté</b>. Le poids du pont s'affiche et passe à <b>STABLE</b> quand il ne bouge plus ; les boutons ne s'activent qu'à ce moment-là.",
]))

s.append(Paragraph("2. Pesée en deux passages (le cas courant)", H2))
s.append(Paragraph("<b>Vente</b> : le camion passe vide, charge, puis repasse plein. <b>Réception</b> (livraison fournisseur) : plein puis vide. Le net est la différence dans les deux cas.", P))
s.extend(etapes([
    "Choisir <b>Vente</b> ou <b>Réception</b>.",
    "Taper l'<b>immatriculation</b>. Si le camion est déjà connu, la page le dit (tare mémorisée) et propose les raccourcis du point 3.",
    "<b>Client ou fournisseur</b> : taper deux lettres, choisir dans la liste Odoo (la ville aide pour les homonymes). Un nom tapé sans le choisir dans la liste reste un simple texte : pas de commande Odoo possible.",
    "<b>Produit</b> : choisir dans la liste (articles vendus à la tonne) ou taper un texte libre. Note facultative : chantier, bon de commande client…",
    "Camion sur le pont, poids STABLE : <b>Pesée 1 : enregistrer le poids</b>. Le camion apparaît dans « Camions en attente de 2<super>e</super> pesée ».",
    "Au retour du camion : cliquer sa ligne dans la liste d'attente (ou retaper l'immatriculation), vérifier client et produit, poids STABLE, <b>Pesée 2 : terminer et imprimer le ticket</b>. Le ticket sort sur l'Epson, la pesée passe dans « Pesées du jour » et dans Odoo.",
]))

s.append(Paragraph("3. Camion connu : une seule pesée grâce à la tare mémorisée", H2))
s.extend(etapes([
    "<b>Mémoriser une tare</b> : camion <u>vide</u> sur le pont, immatriculation tapée, choisir « Véhicule client ou transporteur » ou « Véhicule de l'entreprise », puis <b>Mémoriser ce poids comme tare du véhicule</b>. Les camions du parc Maquignon sont reconnus automatiquement par leur plaque.",
    "<b>Pesée avec la tare</b> : taper l'immatriculation, la page affiche « tare mémorisée … kg », camion <u>plein</u> sur le pont, client et produit, puis <b>Pesée avec la tare mémorisée : terminer et imprimer</b>. Net = poids - tare. Le ticket indique la date de la tare.",
    "Refaire « Mémoriser » de temps en temps (changement de benne, de carburant, de remorque) : la nouvelle tare remplace l'ancienne. Les tares se corrigent aussi dans Odoo, Logistiques, <b>Véhicules (tares)</b>.",
]))

s.append(Paragraph("4. Pesée simple et saisie manuelle", H2))
s.extend(etapes([
    "<b>Pesée simple</b> : un seul passage, le poids affiché est le net (benne seule, colis…). Bouton « Pesée simple : enregistrer et imprimer ».",
    "<b>Saisir le poids à la main</b> : cocher la case, taper le poids en kg. À utiliser si la bascule ne communique plus ou pour reprendre une pesée lue sur l'indicateur. La pesée et le ticket portent la mention « Poids saisi à la main ».",
]))

s.append(Paragraph("5. Que devient la pesée dans Odoo : le choix « Dans Odoo, à la fin de la pesée »", H2))
s.append(tableau([
    ["Choix", "Ce que fait la page", "Suite à donner"],
    ["<b>Bon de commande journalier</b>", "Ajoute une ligne au devis du jour de ce client (créé au premier passage) : article, tonnage, n° de pesée, immatriculation, heure. Prix = liste de prix du client.", "Rien à la caisse. Le bureau confirme et facture le devis, à la journée ou au mois."],
    ["<b>Ticket de caisse</b>", "Crée un devis pour cette pesée, au nom du client, ou de « Comptoir Chatel Granulats » s'il n'a pas de fiche.", "Dans la caisse Odoo : bouton <b>Commandes de vente</b>, retrouver le devis (nom du client ou n° de pesée), <b>Régler</b> : le ticket de caisse sort avec la ligne de pesée."],
    ["<b>Pesée seule</b>", "Enregistre la pesée sans commande.", "Possible plus tard : boutons <b>BC</b> et <b>€</b> dans « Pesées du jour »."],
], [38 * mm, 78 * mm, 62 * mm]))
s.append(Paragraph("Pour les deux premiers choix il faut un client <u>choisi dans la liste Odoo</u> et un article <u>de la liste</u>. Sinon la pesée est quand même enregistrée et un message rouge l'indique : compléter puis utiliser BC ou € dans la liste du jour. Le numéro de commande Odoo est imprimé sur le ticket de pesée.", NOTE))

s.append(Paragraph("6. Tickets, numéros, corrections", H2))
s.extend(etapes([
    "Chaque pesée a un numéro unique <b>CHA-2026-00001</b>, imprimé sur le ticket et visible dans Odoo.",
    "<b>Réimprimer</b> : icône imprimante dans « Pesées du jour ». Les pesées des jours précédents sont dans Odoo, Logistiques, <b>Pesées pont-bascule</b>.",
    "<b>Annuler</b> un camion en attente de 2<super>e</super> pesée : croix au bout de sa ligne. Une pesée terminée ne se supprime pas : la marquer en note et prévenir le bureau.",
    "Les poids imprimés sont ceux lus sur l'indicateur approuvé ; l'indicateur reste la référence légale.",
]))

s.append(Paragraph("7. En cas de problème", H2))
s.append(tableau([
    ["Symptôme", "Cause probable", "Que faire"],
    ["« bascule non connectée », poids « — »", "Câble USB débranché, PC redémarré, autre programme sur le port", "Vérifier le câble Prolific sur le PC, cliquer <b>Connecter la bascule</b>, choisir COM4. En attendant : saisie manuelle."],
    ["Poids jamais STABLE", "Camion en mouvement, moteur, vent", "Attendre l'arrêt complet ; le poids doit rester identique trois lectures de suite."],
    ["« Impression impossible »", "Certificat de l'imprimante non accepté dans ce navigateur, ou imprimante éteinte", "Un onglet s'ouvre sur l'imprimante : « Paramètres avancés », « Continuer vers le site », puis réimprimer. Vérifier https://192.168.1.20."],
    ["« Odoo : … » en rouge", "Internet coupé ou clé d'accès absente", "Vérifier la connexion ; ouvrir la page depuis Odoo, Ventes, Pont-bascule (la clé est dans le lien)."],
    ["Message rouge « sans commande »", "Client ou article non choisis dans les listes Odoo", "Compléter la fiche puis boutons BC ou € dans « Pesées du jour »."],
    ["Camion connu non reconnu", "Immatriculation tapée différemment", "Les espaces et tirets ne comptent pas, mais toutes les lettres et chiffres oui : vérifier la plaque."],
], [46 * mm, 56 * mm, 76 * mm]))
s.append(Spacer(1, 8))
s.append(Paragraph("Réglages du poste (bouton Réglages) : nom du poste, adresse IP de l'imprimante (192.168.1.20 à Chatel), clé d'accès. Contact : Xavier Fèvre.", SMALL))
doc.build(s)
print('PDF :', SORTIE)
