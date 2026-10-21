# -*- coding: utf-8 -*-
"""Procédure « Facturation électronique : envoyer une facture par la plateforme agréée, puis le cas des collectivités
(Chorus Pro) » pour Isabelle (15/10/2026, v2 : partie A envoi normal, partie B collectivités, demande de Xavier).
  python build_procedure_chorus.py  ->  Desktop/Maquignon/Procedure_facturation_electronique_2026-10-15.pdf
Captures facultatives (docs/captures_chorus) : 4_fiche_entreprise.png, 3_envoi.png, 1_fiche_client.png, 2_facture_chorus.png.
Annexe : docs/captures_chorus/annexe_collectivites.json (adresses vérifiées dans l'annuaire le 15/10/2026)."""
import os, sys, json
sys.stdout.reconfigure(encoding='utf-8')
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = r"C:\Users\xavfe\Desktop\Maquignon\Procedure_facturation_electronique_2026-10-15.pdf"
CAP = lambda n: os.path.join(ICI, 'captures_chorus', n)
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


doc = SimpleDocTemplate(SORTIE, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                        title="Facturation électronique dans Odoo", author="Carrières Maquignon")
s = [Paragraph("Facturation électronique dans Odoo : envoyer une facture par la plateforme agréée", H1),
     Paragraph("Partie A : l'envoi normal à un client entreprise. Partie B : ce qui change pour une collectivité (Chorus Pro). Version du 15/10/2026.", SMALL), Spacer(1, 6)]
s.append(Paragraph("Odoo est la <b>plateforme agréée</b> de SARL Maquignon et de Carrière d'Haims depuis le 15/10/2026 : leurs factures clients peuvent partir par le réseau de la facturation électronique au lieu du seul e-mail. "
                   "La condition : le client doit être inscrit dans l'<b>annuaire</b> national (il a choisi sa propre plateforme pour recevoir). Odoo le vérifie sur la fiche client. "
                   "Si le client n'y est pas encore, on continue par e-mail, rien ne change. Les particuliers et les clients étrangers ne passent jamais par le réseau. "
                   "Chatel'Granulats n'est pas inscrite comme plateforme : pour elle, tout reste comme avant.", NOTE))

# ---------------------------------------------------------------- A
s.append(Paragraph("Partie A. Envoyer une facture à un client entreprise", H2))
s.append(Paragraph("A1. Une seule fois : la fiche client", H3))
s.extend(etapes([
    "Ouvrir la fiche du client (Contacts, ou en cliquant son nom sur la facture). Type <b>Société</b>, pays <b>France</b>, <b>n° de TVA</b>.",
    "Champ <b>« ID de la société »</b> (sous le n° de TVA) = son <b>SIREN</b> (9 chiffres) ou son SIRET (14 chiffres). Odoo en déduit l'adresse électronique.",
    "Onglet <b>Comptabilité</b>, bloc « Factures clients » : la liste d'adresse est sur <b>« Adresse électronique FRCTC France »</b> et la case à côté contient le <b>SIREN</b> (9 chiffres). "
    "Si elle est vide, le taper. Un client qui a communiqué une adresse plus précise (SIREN_SIRET ou avec un code de routage) : taper cette adresse telle qu'il l'a donnée.",
    "La ligne « État de la facturation électronique » affiche <b>« Le partenaire est dans l'annuaire »</b> : le client recevra par le réseau. Le bouton <b>Vérifier</b> recontrôle à tout moment. <b>Enregistrer</b>.",
]))
s.extend(capture('4_fiche_entreprise.png', "Fiche d'un client entreprise, onglet Comptabilité : l'adresse électronique FRCTC France avec le SIREN, et l'état « Le partenaire est dans l'annuaire »."))
s.append(Paragraph("« Le partenaire n'est pas dans l'annuaire » : le client n'a pas encore de plateforme (ou le SIREN est faux). On lui envoie sa facture par e-mail comme avant, et on recliquera <b>Vérifier</b> plus tard. "
                   "Au 15/10/2026, 13 clients entreprises sont déjà trouvés dans l'annuaire.", NOTE))

s.append(Paragraph("A2. La facture", H3))
s.extend(etapes([
    "Créer la facture comme d'habitude (depuis le devis ou directement). Chaque ligne doit avoir un <b>article</b> et <b>une seule taxe</b> : c'est la seule exigence du réseau.",
    "<b>Confirmer</b> la facture.",
]))

s.append(Paragraph("A3. L'envoi", H3))
s.extend(etapes([
    "Bouton <b>Envoyer</b>. Dans la fenêtre, la case <b>« by the Approved Platform »</b> (la plateforme agréée) est cochée d'elle-même quand le client est dans l'annuaire ; elle n'existe pas sinon. "
    "Laisser « par e-mail » coché si le client veut aussi le PDF. Le fichier joint <i>…_ubl_21_fr.xml</i> est la facture au format <b>France E-Invoicing (UBL 2.1)</b>, ajouté automatiquement.",
    "Cliquer <b>Envoyer</b>. Sur la facture, le champ <b>« Statut de la facturation électronique »</b> passe à <b>En file d'attente</b>, puis <b>Réception en attente</b> et <b>Terminé</b> dans les heures qui suivent (Odoo transmet par lots, plusieurs fois par jour).",
    "Le client renvoie ensuite ses statuts, qui s'affichent au même endroit et dans le fil de discussion : <b>Reçu</b>, <b>Approuvé</b>, <b>Rejeté</b> ou <b>Refusée</b> (avec le motif), <b>Avec paiements</b> quand il a réglé. "
    "Un rejet se traite comme une facture renvoyée par courrier : corriger (ou faire un avoir) et renvoyer.",
]))
s.extend(capture('3_envoi.png', "La fenêtre d'envoi d'une facture à un client dans l'annuaire : « by the Approved Platform » coché et le fichier XML France E-Invoicing (UBL 2.1) joint automatiquement."))
s.append(Paragraph("Rien à faire pour les particuliers ni pour l'e-reporting : les ventes qui ne passent pas par le réseau sont déclarées automatiquement par Odoo tous les dix jours.", NOTE))

# ---------------------------------------------------------------- B
s.append(PageBreak())
s.append(Paragraph("Partie B. Les collectivités (Chorus Pro) : ce qui change", H2))
s.append(Paragraph("Les mairies, communautés de communes et le département reçoivent leurs factures dans <b>Chorus Pro</b>. L'envoi est le même qu'en partie A, avec trois différences : "
                   "l'adresse de la collectivité est <b>SIREN_SIRET</b> (le SIREN seul ne suffit pas), son <b>SIRET</b> est obligatoire sur la fiche, et la facture porte les <b>références Chorus</b> (code service, engagement).", P))

s.append(Paragraph("B1. La fiche de la collectivité", H3))
s.extend(etapes([
    "Type <b>Société</b>, pays <b>France</b>. Champ <b>« ID de la société »</b> = le <b>SIRET</b>, 14 chiffres sans espace. Il figure sur le bon de commande ; sinon annuaire-entreprises.data.gouv.fr. "
    "Prendre l'établissement qui paie (la mairie, pas l'école ni le CCAS). Le n° de TVA s'il est connu.",
    "Onglet <b>Comptabilité</b> : « Adresse électronique FRCTC France » et, dans la case à côté, l'adresse <b>SIREN_SIRET</b> : les 9 premiers chiffres du SIRET, un tiret bas, puis le SIRET complet. "
    "Exemple pour la mairie de Saires : <font face='Courier'>218602498_21860249800014</font>.",
    "L'état doit afficher <b>« Le partenaire est dans l'annuaire »</b>. <b>Enregistrer</b>. L'annexe donne l'adresse déjà vérifiée de 24 collectivités clientes.",
]))
s.extend(capture('1_fiche_client.png', "Fiche de la mairie de Saires, onglet Comptabilité : l'adresse SIREN_SIRET et l'état « Le partenaire est dans l'annuaire »."))

s.append(Paragraph("B2. Avant de facturer : les références Chorus Pro", H3))
s.append(tableau([
    ["Donnée", "Où la trouver", "Obligatoire ?"],
    ["<b>Code service</b> (« Service exécutant »)", "Sur le bon de commande de la collectivité. Sinon dans Chorus Pro : <i>Factures émises › Rechercher structure publique</i>, fiche de la structure (liste des services et mention « code service obligatoire »).", "Selon la collectivité"],
    ["<b>Numéro d'engagement</b> (« Engagement juridique »)", "Sur le bon de commande (n° d'engagement ou n° de BC). La même fiche Chorus indique « numéro d'engagement obligatoire ».", "Selon la collectivité"],
    ["Numéro de marché", "Le marché public, s'il y en a un.", "Facultatif, non transmis"],
], [52 * mm, 90 * mm, 36 * mm]))
s.append(Paragraph("Beaucoup de petites communes n'exigent ni code service ni engagement : laisser les champs vides. Un code exigé mais absent ou faux = facture rejetée par Chorus, à corriger et renvoyer.", NOTE))

s.append(Paragraph("B3. La facture : le bloc Chorus Pro", H3))
s.extend(etapes([
    "Créer la facture comme d'habitude (article et une seule taxe par ligne).",
    "Onglet <b>Autres informations</b>, bloc <b>« Chorus Pro »</b> juste sous le bloc « Comptabilité » : <b>Service exécutant</b> = le code service ; <b>Engagement juridique</b> = le numéro d'engagement ; "
    "<b>Numéro de marché</b> seulement s'il existe.",
    "<b>Confirmer</b>, puis <b>Envoyer</b> exactement comme en A3 : case « by the Approved Platform » cochée, Envoyer.",
    "Chorus Pro renvoie ses propres statuts (déposée, mise à disposition, mandatée, etc.) dans le fil de discussion de la facture. En cas de rejet, le motif y est écrit : corriger (code service, engagement, SIRET) et renvoyer.",
]))
s.extend(capture('2_facture_chorus.png', "Facture, onglet Autres informations : le bloc Chorus Pro avec le service exécutant et l'engagement juridique (valeurs d'exemple)."))

# ---------------------------------------------------------------- C
s.append(Paragraph("Partie C. Problèmes courants", H2))
s.append(tableau([
    ["Situation", "Cause", "Que faire"],
    ["La case « by the Approved Platform » n'apparaît pas dans la fenêtre d'envoi", "Client pas dans l'annuaire, ou adresse fausse sur sa fiche.", "Reprendre A1 (ou B1 pour une collectivité). En attendant, envoyer par e-mail."],
    ["« Le partenaire n'est pas dans l'annuaire »", "Entreprise sans plateforme pour l'instant ; collectivité avec le SIREN seul ou un SIRET d'un autre établissement.", "Entreprise : e-mail, revérifier plus tard. Collectivité : SIRET du bon établissement, forme SIREN_SIRET."],
    ["Statut « Erreur » après l'envoi", "Ligne sans article ou sans taxe, SIRET de la collectivité absent, fichier refusé par le réseau.", "Lire le motif dans le fil de la facture, corriger, renvoyer."],
    ["Statut « Rejeté » ou « Refusée »", "Le client ou Chorus refuse la facture (références manquantes, montant, doublon).", "Motif dans le fil ; corriger ou faire un avoir, puis renvoyer."],
    ["Le client dit ne rien recevoir", "Facture encore « En file d'attente », ou sa plateforme n'a pas encore distribué.", "Attendre « Terminé » ; vérifier avec lui l'adresse ou le code service."],
    ["Facture de Chatel'Granulats", "Société non inscrite comme plateforme.", "E-mail, et dépôt manuel sur Chorus Pro pour les collectivités, comme avant."],
], [52 * mm, 62 * mm, 64 * mm]))

# ---------------------------------------------------------------- annexe
annexe = CAP('annexe_collectivites.json')
if os.path.exists(annexe):
    data = json.load(open(annexe, encoding='utf-8'))
    s.append(PageBreak())
    s.append(Paragraph("Annexe : adresses des collectivités clientes, vérifiées dans l'annuaire le 15/10/2026", H2))
    s.append(Paragraph("Pour chacune : « ID de la société » = le SIRET, adresse = « Adresse électronique FRCTC France » + la valeur ci-dessous. Toutes ont été trouvées dans l'annuaire.", P))
    lignes = [["Collectivité (fiche Odoo)", "SIRET", "Adresse à saisir"]] + [[d['nom'], d['siret'], "<font face='Courier'>%s</font>" % d['adresse']] for d in data]
    s.append(tableau(lignes, [78 * mm, 36 * mm, 64 * mm], CELL))
    s.append(Spacer(1, 6))
    s.append(Paragraph("Fiches sans SIRET à compléter avant le premier envoi (SIRET à demander ou à chercher sur annuaire-entreprises.data.gouv.fr) : "
                       "Communauté de communes du Haut-Poitou (SIREN 200069763), Département de la Vienne (SIREN 228600011), communes de La Puye, Liglet, Coussay-les-Bois, Saint-Genest-d'Ambière, "
                       "Usseau, Mairé, Mondion, Saint-Savin, Colombiers, Vaux, Yversay, Jouhet, Saint-Germain, Paizay-le-Sec, Villentrois, Bain-de-Bretagne, Monuments et musées départementaux (SIRET à 13 chiffres à corriger). "
                       "Plusieurs collectivités ont deux ou trois fiches (Antran, Colombiers, Saint-Genest, Coussay, Mairé, Usseau, Vienne et Gartempe, Châtellerault, Saint-Léomer, Béthines, Dangé) : régler celle qui sert à facturer, ou les fusionner.", SMALL))
doc.build(s)
print('PDF :', SORTIE)
