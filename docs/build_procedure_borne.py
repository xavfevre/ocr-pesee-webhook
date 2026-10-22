# -*- coding: utf-8 -*-
"""Procédure Delphine « Borne à béton Distri Béton et caméras du pont : installation et utilisation » (22/10/2026).
  python build_procedure_borne.py  ->  Desktop/Maquignon/Procedure_borne_DistriBeton_Delphine_2026-10-22.pdf
Captures : docs/captures_borne/borne_page.jpg, bascule_reglages.jpg, bascule_page.jpg (pa_test/captures_borne.py)."""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = r"C:\Users\xavfe\Desktop\Maquignon\Procedure_borne_DistriBeton_Delphine_2026-10-22.pdf"
CAP = lambda n: os.path.join(ICI, 'captures_borne', n)
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
                        title="Borne à béton Distri Béton et caméras du pont : installation et utilisation", author="Carrières Maquignon")
s = []
s.append(Paragraph("BORNE À BÉTON DISTRI BÉTON &amp; CAMÉRAS DU PONT — Installation et utilisation", H1))
s.append(Paragraph("Procédure pour Delphine, PC de caisse de Chatel'Granulats. Version du 22/10/2026.", SMALL))
s.append(Spacer(1, 6))

s.append(Paragraph("En deux mots", H2))
s.append(Paragraph("La borne Easy Béton garde ses fichiers sur son propre PC (192.168.1.200). Jusqu'ici il fallait les récupérer par FTP, les importer dans Odoo à la main, "
                   "et déposer de temps en temps la liste des clients pour que les badges fonctionnent. Désormais un petit programme, <b>l'agent</b>, installé une fois sur le PC "
                   "de caisse, fait la navette toutes les minutes :", P))
s.extend(puces([
    "<b>Clients Odoo → borne</b> : dès qu'un client Distri Béton est créé ou modifié dans Odoo, la liste complète part sur la borne. Le badge d'un nouveau client marche dans la minute. Rien à faire.",
    "<b>Prises de béton → Odoo</b> : les fichiers de prises arrivent sur une page web où l'on <b>vérifie et valide</b> avant que les commandes soient créées dans Odoo. Plus d'import manuel.",
]))
s.append(Paragraph("Les deux caméras du site (dôme du portail et borne) s'affichent en plus sur la page Pont-bascule, grâce à un second petit programme installé de la même façon.", P))

s.append(Paragraph("1. Installation sur l'ORDINATEUR DE CAISSE (une seule fois, 5 minutes)", H2))
s.append(Paragraph("<b>Uniquement sur l'ordinateur de caisse de Chatel'Granulats</b>, celui du pont-bascule et de la caisse Odoo : c'est le seul qui voit à la fois la borne (réseau local) et internet, et qui reste allumé toute la journée. "
                   "Ne pas faire ces deux installations sur un portable ni sur un autre poste : l'agent ne verrait pas la borne. "
                   "À faire dans la session Windows habituelle de ce PC (celle qui reste ouverte) ; les deux programmes redémarrent ensuite tout seuls à chaque ouverture de session.", NOTE))
s.append(KeepTogether([Paragraph("<b>A. L'agent de la borne</b>", P)] + etapes([
    "Dans Odoo, menu <b>Logistiques › Borne à béton › Page de validation</b>. La page « Borne à béton — Distri Béton » s'ouvre dans un nouvel onglet.",
    "Dans la carte de droite « Export automatique des clients vers la borne », cliquer sur <b>« Installer l'agent sur ce PC »</b>. Chrome télécharge <b>installer_agent_borne.cmd</b>.",
    "Ouvrir ce fichier depuis la barre de téléchargement (en bas ou en haut à droite de Chrome). Si Windows affiche un écran bleu « Windows a protégé votre ordinateur » : cliquer <b>Informations complémentaires</b> puis <b>Exécuter quand même</b>.",
    "Une fenêtre noire défile quelques secondes et se termine par « Terminé ». Appuyer sur une touche pour la fermer. Rien à taper : la clé et le mot de passe de la borne sont déjà dedans, le fichier s'efface tout seul ensuite.",
    "Vérifier : dans la minute, en haut de la page, la pastille devient verte avec « agent … vu il y a quelques secondes », et la carte « Export automatique » affiche un premier dépôt. Les prises en attente apparaissent dans la liste de gauche.",
])))
s.append(KeepTogether([Paragraph("<b>B. Les caméras sur la page Pont-bascule</b>", P)] + etapes([
    "Ouvrir la page Pont-bascule (menu <b>Logistiques › Pont-bascule</b>, ou l'onglet déjà ouvert sur le PC de caisse).",
    "Cliquer sur <b>Réglages</b> en haut à droite, puis, en bas de la carte des réglages, sur <b>« Installer les caméras sur ce PC »</b>. Chrome télécharge <b>installer_cameras_chatel.cmd</b>.",
    "Ouvrir le fichier téléchargé (même avertissement Windows possible : Informations complémentaires › Exécuter quand même), puis une touche pour fermer la fenêtre noire.",
    "Dix secondes plus tard, F5 sur la page : les deux vues (portail et borne) s'affichent dans la troisième colonne. Le bouton Masquer / Afficher de la carte Caméras les cache si besoin.",
])))
s.extend(capture(CAP('bascule_reglages.jpg'), "Carte Réglages de la page Pont-bascule : le bouton d'installation des caméras est en bas.", 120))
s.append(Paragraph("Si un jour un des deux programmes ne tourne plus (PC réinstallé, session changée) : refaire l'étape A ou B, c'est tout. Ils apparaissent dans le dossier Démarrage de Windows sous « Borne Distri Beton » et « Cameras pont-bascule ».", NOTE))

s.append(PageBreak())
s.append(Paragraph("2. Chaque matin : valider les prises de la veille", H2))
s.append(Paragraph("La borne écrit ses fichiers chaque soir vers <b>20 h</b> ; l'agent les transmet aussitôt. Le matin, les prises de la veille attendent sur la page.", P))
s.extend(capture(CAP('borne_page.jpg'), "La page Borne à béton : à gauche les prises à valider et l'historique des imports, à droite l'export automatique des clients et son historique.", 165))
s.extend(etapes([
    "Ouvrir <b>Logistiques › Borne à béton › Page de validation</b>. Mettre son prénom dans la case « Je suis » en haut à droite (une fois, il est gardé).",
    "Lire la liste <b>« Prises de béton à valider »</b>, regroupée par jour : heure, n° de bon, client (nom et code DIS), article (nom et code recette), m³, prix, chantier, badge.",
    "Les lignes <b>blanches</b> sont prêtes : client et article reconnus. Les cocher (ou « tout cocher »).",
    "Les lignes <b>orange</b> ont un problème, écrit en orange sous le client ou l'article. Les traiter avant de cocher (voir le tableau ci-dessous).",
    "Cliquer <b>« Créer les commandes Odoo »</b> et confirmer. Une commande Distri Béton confirmée est créée par prise, avec le badge, le nom du badge, le chantier et la date de distribution, comme avec l'import manuel d'avant. Le message vert donne les numéros S… ; ils sont aussi dans « Historique des imports », cliquables vers Odoo.",
    "Une prise qui ne doit pas devenir une commande (déjà saisie à la main, test, erreur de la borne) : la cocher et cliquer <b>Rejeter</b>, avec un motif. Elle reste dans l'historique comme rejetée.",
]))
s.append(tableau([
    ["Ce qui est écrit", "Ce que ça veut dire", "Que faire"],
    ["client DIS00xxx introuvable dans Odoo", "Le code DIS de la borne n'existe sur aucune fiche client Odoo (fiche sans code, code différent, client archivé).", "Bouton <b>Choisir</b> à côté : taper le nom ou le code, cliquer le bon client. La ligne devient blanche. Puis corriger le code DIS sur la fiche client dans Odoo pour la prochaine fois."],
    ["article BF250 / BETON FERME 250 introuvable", "Le code recette de la borne ne correspond à aucune référence interne d'article Odoo.", "Bouton <b>Choisir</b> : chercher l'article (ex. « ferme 250 »). Puis mettre le code recette en référence interne de l'article dans Odoo."],
    ["doublon probable : commande S… du même client à la même heure", "Une commande existe déjà pour ce client à cette date de distribution (import manuel fait avant).", "Vérifier la commande citée. Si c'est bien la même prise : <b>Rejeter</b> avec le motif « déjà saisie ». Sinon valider."],
    ["déjà importé : commande S… (étiquette « doublon »)", "Cette prise a déjà été importée par la page.", "Rejeter."],
    ["volume nul / date illisible", "Fichier de la borne incomplet.", "Rejeter, et signaler si ça se reproduit."],
], [48 * mm, 62 * mm, 68 * mm]))
s.append(Paragraph("<b>Prix</b> : pour les professionnels, la borne n'envoie pas de prix et Odoo applique le tarif du client, comme avant. Pour les particuliers payés par carte à la borne (client DIS99999 PARTICULIER BORNE), le prix HT de la borne est repris tel quel, la commande correspond donc au ticket.", NOTE))

s.append(Paragraph("3. Les clients et les badges", H2))
s.extend(puces([
    "Créer le client dans Odoo normalement, société Distri Béton, avec son <b>code DIS</b> (donné automatiquement à la création). Dans la minute, la carte « Export automatique » affiche un nouveau dépôt et le client est sur la borne : son badge peut être fait.",
    "La carte indique aussi les clients modifiés qui partiront au prochain passage, et le nombre de clients envoyés. Pas besoin de cliquer.",
    "Deux garde-fous arrêtent l'envoi si quelque chose cloche : <b>deux clients avec le même code DIS</b> dans Odoo, ou une liste qui a <b>rétréci de plus de 10 %</b> (un fichier incomplet effacerait des clients sur la borne). La page l'écrit en rouge avec le motif : corriger dans Odoo (code en double), ou, si la baisse est voulue, cliquer « Forcer un dépôt au prochain passage ».",
    "Les clients sans code DIS ne partent pas sur la borne : ils ne peuvent pas avoir de badge.",
]))

s.append(Paragraph("4. L'import automatique (option, désactivée par défaut)", H2))
s.append(Paragraph("La case <b>« Import automatique dans Odoo »</b>, en haut de la liste des prises, permet de se passer de la validation du matin : les prises dont le client et l'article sont reconnus deviennent des commandes dès leur arrivée, marquées « import automatique » dans l'historique. Seules les prises à problème restent à valider. Ne l'activer que si Xavier le demande ; le réglage est gardé dans Odoo.", P))

s.append(Paragraph("5. Si quelque chose ne va pas", H2))
s.append(tableau([
    ["Symptôme", "Cause probable", "Que faire"],
    ["Pastille rouge ou orange : « agent vu il y a 2 h » ou « agent jamais vu »", "Le PC de caisse est éteint, la session est fermée, ou l'agent s'est arrêté.", "Allumer / ouvrir la session du PC de caisse. Il redémarre seul. Sinon refaire l'étape 1-A. Rien n'est perdu : les fichiers attendent sur la borne."],
    ["Aucune prise ne remonte alors que la borne a tourné", "La borne écrit ses fichiers à 20 h ; avant, il n'y a rien à lire. Ou l'agent est arrêté.", "Attendre le lendemain matin ; vérifier la pastille de l'agent."],
    ["« Dépôt bloqué : codes en double »", "Deux fiches clients Odoo ont le même code DIS.", "Corriger les fiches dans Odoo (Contacts, filtre sur le code). Le dépôt repart seul."],
    ["Les caméras n'apparaissent pas sur la page Pont-bascule", "Le programme caméras n'est pas lancé, ou la carte est masquée.", "Bouton Afficher de la carte Caméras ; sinon refaire l'étape 1-B."],
], [55 * mm, 58 * mm, 65 * mm]))
s.append(Paragraph("Dans Odoo, menu Logistiques › Borne à béton, on retrouve aussi <b>Prises de béton</b> (toutes les prises reçues, avec leur état) et <b>Exports clients</b> (chaque dépôt sur la borne). Les commandes créées portent l'origine « Borne S… ».", SMALL))

doc.build(s)
print('écrit :', SORTIE)
