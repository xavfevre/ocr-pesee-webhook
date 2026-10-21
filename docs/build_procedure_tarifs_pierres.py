# -*- coding: utf-8 -*-
"""Procédure « Tarifs pierres : importer les tarifs, gérer les prix négociés, préparer le mailing » (15/10/2026).
  python build_procedure_tarifs_pierres.py  ->  Desktop/Maquignon/Procedure_tarifs_pierres_2026-10-15.pdf
Captures facultatives : docs/captures_tarifs/1_page_haut.png, 2_apercu.png, 3_clients_mailing.png, 4_menu_ventes.png, 5_brouillon_mailing.png."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = r"C:\Users\xavfe\Desktop\Maquignon\Procedure_tarifs_pierres_2026-10-15.pdf"
CAP = lambda n: os.path.join(ICI, 'captures_tarifs', n)
INK = colors.HexColor('#0f172a'); GREY = colors.HexColor('#475569'); BLUE = colors.HexColor('#1d4ed8'); LIGHT = colors.HexColor('#eef2ff'); LINE = colors.HexColor('#cbd5e1')
H1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=INK, spaceAfter=4)
H2 = ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=13, leading=16, textColor=BLUE, spaceBefore=12, spaceAfter=5)
H3 = ParagraphStyle('h3', fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=INK, spaceBefore=8, spaceAfter=3)
P = ParagraphStyle('p', fontName='Helvetica', fontSize=10, leading=14, textColor=INK)
SMALL = ParagraphStyle('s', parent=P, fontSize=8.6, leading=11.5, textColor=GREY)
ETAPE = ParagraphStyle('e', parent=P, leftIndent=14, firstLineIndent=-14, spaceAfter=3)
NOTE = ParagraphStyle('n', parent=P, backColor=LIGHT, borderPadding=(5, 7, 5, 7), leftIndent=4, rightIndent=4, spaceBefore=4, spaceAfter=6)
CELL = ParagraphStyle('c', parent=P, fontSize=8.8, leading=11)


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


doc = SimpleDocTemplate(SORTIE, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm, title="Tarifs pierres : import, prix négociés, mailing", author="Carrières Maquignon")
s = [Paragraph("Tarifs pierres : importer les tarifs, gérer les prix négociés, préparer le mailing", H1),
     Paragraph("Page « Tarifs pierres » du menu Ventes d'Odoo (SARL Maquignon). Version du 15/10/2026.", SMALL), Spacer(1, 6)]
s.append(Paragraph("La page Tarifs pierres sert à charger une nouvelle grille de prix pierres dans les listes de prix d'Odoo, en deux phases datées, "
                   "à ajouter ou revoir les prix négociés des clients, et à préparer le mailing « nouveaux tarifs » dans E-mail Marketing, avec la grille propre à chaque client. "
                   "Les prix se saisissent toujours dans l'unité du devis : <b>m²</b> pour les pierres d'épaisseur « (N cm) », <b>m³</b> pour les massifs, tranches et blocs, tonne pour l'enrochement. "
                   "La page fait elle-même la conversion en €/m³ attendue par Odoo.", NOTE))
s.append(Paragraph("Accès", H2))
s.extend(etapes(["Dans Odoo, application <b>Ventes</b> : l'entrée <b>Tarifs pierres</b> est tout à droite de la barre de menus, après « Pont-bascule ». Elle ouvre la page dans un nouvel onglet.",
                 "Pour retoucher un seul prix d'un client : fiche du contact ou devis, bouton <b>Tarifs client</b> (page existante)."]))
s.extend(capture('4_menu_ventes.png', "La barre de menus de Ventes avec l'entrée Tarifs pierres."))

s.append(Paragraph("1. Les listes de prix cibles", H2))
s.extend(etapes(["En haut de la page, le bloc « Listes de prix cibles » indique les listes PRO et PARTICULIER dans lesquelles les prix seront chargés, et combien de clients sont dessus.",
                 "Si elles n'existent pas encore (nouvelle année) : bouton <b>Créer les listes 2027</b>. La liste pro renvoie à la liste pro précédente pour tout ce qui n'est pas repris, la liste particulier au prix fiche : rien ne change tant que la grille n'est pas chargée.",
                 "Le bouton <b>Basculer les clients</b> déplace tous les clients des listes de l'année précédente vers les nouvelles, fait de la liste particulier la liste par défaut des nouveaux clients, et rebase les listes dédiées (Lefèvre, Crocodile…) sur la nouvelle liste pro pour les pierres hors prix négociés. À faire une fois, après le premier chargement."]))
s.extend(capture('1_page_haut.png', "Le haut de la page : listes cibles, dates des deux phases, modèle à télécharger, fichier à importer."))

s.append(Paragraph("2. Charger une grille", H2))
s.extend(etapes(["Régler les dates : <b>Phase 1 à partir du</b> (ex. 01/11/2026) et <b>Phase 2 à partir du</b> (ex. 01/01/2027).",
                 "<b>Télécharger le modèle</b> : un fichier Excel avec toutes les pierres vendables, leur unité, les prix PRO et PARTICULIER actuels, les colonnes jaunes à remplir et une colonne mauve par client à prix négociés.",
                 "Remplir dans Excel : colonnes jaunes <b>PRO phase 1, PRO phase 2, PARTICULIER phase 1, PARTICULIER phase 2</b>. Une case vide = pas de changement. "
                 "Colonnes mauves : le prix négocié du client, sans date, maintenu sur les deux phases. Pour un nouveau client : ajouter une colonne avec son <b>nom exact Odoo</b> avant « Remarque ».",
                 "Choisir le fichier, cliquer <b>Aperçu</b> : la page montre tout ce qui sera écrit, avec les prix actuels à côté. Les pastilles en tête disent pour chaque colonne client s'il a été reconnu (liste dédiée existante ou à créer) ou non. Les pierres non reconnues sont listées et ignorées.",
                 "Cliquer <b>Charger dans Odoo</b>. Relancer le même fichier ne crée pas de doublon : une règle existante aux mêmes dates est mise à jour."]))
s.extend(capture('2_apercu.png', "L'aperçu : pastilles des colonnes clients, puis le tableau des prix à écrire (jaune), en unité du devis avec l'équivalent €/m³ en petit."))
s.append(Paragraph("Le tableau de validation des tarifs 2027 (fichier « Tarifs_pierres_2027_validation ») est accepté tel quel : la page repère les colonnes par leur titre.", NOTE))

s.append(Paragraph("3. Les clients à prix négociés", H2))
s.append(Paragraph("Règle de la maison : un prix négocié est toujours un <b>prix fixe</b> sur la liste dédiée du client, jamais une remise en pourcentage. "
                   "Odoo n'applique pas les remises en pourcentage sur les devis : elles laissent le client au prix fiche. Pour tout ce qui n'est pas négocié, la liste dédiée se <b>replie</b> sur le tarif pro en vigueur.", NOTE))
s.extend(etapes(["Le bloc « Clients à prix négociés » liste les clients qui ont une liste dédiée avec au moins une règle sur une pierre : liste, liste de repli (« autres pierres et articles : prix de »), nombre de règles et leur détail, prix fixe ou remise.",
                 "<b>Remises négociées à convertir en prix fixes…</b> : affiche les remises encore présentes avec, pour chacune, le prix fiche, le prix que donnerait la remise et le dernier prix facturé au client. Le prix fixe à inscrire est prérempli avec le dernier prix facturé, sinon le prix remisé : corriger si besoin, cocher, puis <b>Inscrire les prix fixes cochés et supprimer les remises</b>.",
                 "<b>Mettre le repli de toutes les listes dédiées sur le nouveau tarif pro</b> : à faire après la création des listes 2027 (la bascule le fait aussi). Les prix négociés ne changent pas.",
                 "<b>Tarifs client</b> ouvre la page existante du client pour ajouter, modifier ou supprimer un prix fixe avec ses dates. Attention, cette page travaille dans l'unité Odoo, le m³ : pour une pierre d'épaisseur, saisir le prix au m² divisé par l'épaisseur (ex. 124,58 €/m² en 8 cm = 1 557,25 €/m³). Pour éviter ce calcul, passer par une colonne mauve du fichier d'import.",
                 "<b>Grille PDF</b> : la grille personnalisée du client aux dates des deux phases, lignes négociées sur fond orangé."]))

s.append(Paragraph("4. Le mailing « nouveaux tarifs pierres »", H2))
s.extend(etapes(["Bloc « Mailing » : la cible est affichée (clients pro ayant acheté de la pierre sur les deux dernières années, avec e-mail).",
                 "Cliquer <b>Préparer le brouillon dans Odoo</b>. La page calcule la grille de chaque client depuis ses listes de prix, la range dans sa fiche, et crée (ou met à jour) le brouillon « Carrières Maquignon : vos tarifs pierres 2027 » dans E-mail Marketing, sur la mise en page du brouillon « Nouveaux tarifs 2026 ». Rien n'est envoyé.",
                 "Dans <b>E-mail Marketing</b> : ouvrir le brouillon, relire le texte. La grille du client et le bouton « Télécharger votre grille en PDF » sont des champs dynamiques remplis à l'envoi pour chaque destinataire.",
                 "<b>Tester</b> vers votre propre adresse pour voir un e-mail complet, puis <b>Envoyer</b>.",
                 "Si des prix changent après la préparation : recharger la grille, puis cliquer à nouveau sur « Préparer » avant d'envoyer, pour recalculer les grilles."]))
s.extend(capture('3_clients_mailing.png', "Les blocs clients négociés et mailing de la page."))
s.extend(capture('5_brouillon_mailing.png', "Le brouillon créé dans E-mail Marketing (ici sur la base de test)."))

s.append(Paragraph("5. Problèmes courants", H2))
s.append(tableau([
    ["Situation", "Cause", "Que faire"],
    ["Le bouton « Charger » reste grisé", "Listes cibles non créées, ou fichier sans aucun prix.", "Créer les listes 2027 ; vérifier les colonnes jaunes."],
    ["Pastille rouge « introuvable » sur une colonne client", "Le titre de la colonne n'est pas le nom exact du client dans Odoo.", "Copier le nom depuis la fiche Odoo ; en cas d'homonymes, la page prend celui qui a une liste dédiée, sinon le plus facturé."],
    ["Pierre non reconnue", "Code ou nom différent de la fiche article, ou article archivé.", "Partir du modèle téléchargé, qui contient les codes."],
    ["Un prix chargé semble divisé par 20", "Prix saisi au m³ pour une pierre d'épaisseur, ou l'inverse.", "Saisir dans l'unité de la colonne « Unité » du fichier ; recharger, les règles sont mises à jour."],
    ["Un client à prix négocié paie le prix fiche sur un devis", "Son prix négocié est une remise en pourcentage : Odoo ne l'applique pas.", "Bloc 3, « Remises négociées à convertir en prix fixes… », inscrire le prix fixe."],
    ["Un client à prix négocié paie le prix particulier sur les autres pierres", "Sa liste dédiée se replie sur l'ancienne liste archivée, ou n'a pas de repli.", "Bloc 3, « Mettre le repli… sur le nouveau tarif pro »."],
    ["Le mailing n'a aucun destinataire", "Le brouillon a déjà été envoyé ou testé en masse : Odoo exclut les destinataires déjà traités.", "Dupliquer le brouillon, ou refaire « Préparer » qui en met un à jour."],
    ["Lien PDF de l'e-mail en erreur", "Mailing préparé avant le dernier chargement, ou relais indisponible.", "Refaire « Préparer », puis tester."],
], [50 * mm, 62 * mm, 66 * mm]))
doc.build(s)
print('PDF :', SORTIE)
