# -*- coding: utf-8 -*-
"""Proposition « Apports extérieurs de déchets inertes » pour la carrière de La Martinière (Usseau) : flux + procédure (21/10/2026).
  python build_proposition_decharge_maquignon.py  ->  Desktop/Maquignon/Proposition_decharge_inertes_Maquignon_2026-10-21.pdf"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon

SORTIE = r"C:\Users\xavfe\Desktop\Maquignon\Proposition_decharge_inertes_Maquignon_2026-10-21.pdf"
INK = colors.HexColor('#0f172a'); GREY = colors.HexColor('#475569'); BLUE = colors.HexColor('#1d4ed8'); LIGHT = colors.HexColor('#eef2ff'); LINE = colors.HexColor('#cbd5e1')
GREEN = colors.HexColor('#15803d'); AMBER = colors.HexColor('#b45309')
H1 = ParagraphStyle('h1', fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=INK, spaceAfter=4)
H2 = ParagraphStyle('h2', fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=BLUE, spaceBefore=10, spaceAfter=4)
H3 = ParagraphStyle('h3', fontName='Helvetica-Bold', fontSize=10.5, leading=13, textColor=INK, spaceBefore=7, spaceAfter=2)
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


# ─── Schéma du flux : couloirs verticaux (Chauffeur / Accueil / Pont-bascule / Odoo), étapes de haut en bas ───
def schema_flux():
    W = 178 * mm; cols = ['CHAUFFEUR', 'ACCUEIL (bureau)', 'PONT-BASCULE (cabine)', 'ODOO + relais']
    nc = len(cols); cw = W / nc; rh = 11.4 * mm; nr = 9; top = 7 * mm
    H = top + nr * rh + 4 * mm
    d = Drawing(W, H)
    for i, c in enumerate(cols):
        d.add(Rect(i * cw, H - top, cw, top, fillColor=colors.HexColor('#dbe4ff') if i % 2 == 0 else colors.HexColor('#e8eeff'), strokeColor=LINE, strokeWidth=0.4))
        d.add(String(i * cw + cw / 2, H - top + 2.6 * mm, c, fontName='Helvetica-Bold', fontSize=7.6, fillColor=INK, textAnchor='middle'))
        d.add(Rect(i * cw, 0, cw, H - top, fillColor=colors.HexColor('#f8fafc') if i % 2 == 0 else colors.white, strokeColor=LINE, strokeWidth=0.4))
    boxes = {}

    def box(key, col, row, lignes, couleur=None, large=False):
        bw = cw - 6 * mm if not large else cw * 2 - 6 * mm
        x = col * cw + 3 * mm; y = H - top - (row + 1) * rh + 1.8 * mm; bh = rh - 3.6 * mm
        d.add(Rect(x, y, bw, bh, fillColor=couleur or colors.white, strokeColor=BLUE if not couleur else couleur.clone(alpha=1), strokeWidth=0.8, rx=2, ry=2))
        n = len(lignes); fs = 6.7; lead = 7.6
        y0 = y + bh / 2 + (n - 1) * lead / 2 - 2.3
        for j, l in enumerate(lignes):
            d.add(String(x + bw / 2, y0 - j * lead, l, fontName='Helvetica-Bold' if j == 0 else 'Helvetica', fontSize=fs, fillColor=INK, textAnchor='middle'))
        boxes[key] = (x, y, bw, bh)

    def fleche(a, b, texte=None):
        xa, ya, wa, ha = boxes[a]; xb, yb, wb, hb = boxes[b]
        if abs((xa + wa / 2) - (xb + wb / 2)) < 1:          # même colonne : bas -> haut
            x0, y0, x1, y1 = xa + wa / 2, ya, xb + wb / 2, yb + hb
        elif xa < xb:                                         # vers la droite
            x0, y0, x1, y1 = xa + wa, ya + ha / 2, xb, yb + hb / 2
        else:
            x0, y0, x1, y1 = xa, ya + ha / 2, xb + wb, yb + hb / 2
        d.add(Line(x0, y0, x1, y1, strokeColor=GREY, strokeWidth=0.9))
        import math
        ang = math.atan2(y1 - y0, x1 - x0); s = 2.6
        d.add(Polygon([x1, y1, x1 - s * math.cos(ang - 0.45), y1 - s * math.sin(ang - 0.45), x1 - s * math.cos(ang + 0.45), y1 - s * math.sin(ang + 0.45)], fillColor=GREY, strokeColor=GREY))
        if texte:
            d.add(String((x0 + x1) / 2, (y0 + y1) / 2 + 1.5, texte, fontName='Helvetica-Oblique', fontSize=6, fillColor=GREY, textAnchor='middle'))

    V = colors.HexColor('#dcfce7'); J = colors.HexColor('#fef3c7')
    box('dap', 1, 0, ['0. DAP élaboré et accepté', 'avant la 1re livraison', '(avec le client, ou en ligne)'], J)
    box('dapo', 3, 0, ['Fiche DAP : client, chantier,', 'nature, n°, validité 12 mois'])
    box('arr', 0, 1, ['1. Arrive, reste au camion,', 'appuie sur le portier'])
    box('rep', 1, 1, ['2. Répond (vidéo),', 'immat + n° DAP ou chantier'])
    box('ctrl', 3, 2, ['3. DAP valide ? tonnage ?', 'sinon : DAP créé pendant', "l'appel"], J)
    box('pont1', 0, 3, ['4. Avance sur le pont', 'quand on lui dit'])
    box('pass', 2, 3, ['Passerelle : poids de la', 'D400 + image caméra', 'envoyés chaque seconde'], V)
    box('p1', 1, 4, ['5. Pesée 1 (plein) :', 'poids en direct + caméra', 'contrôle visuel'])
    box('dech', 0, 5, ['6. Décharge dans la zone', 'indiquée (plateforme)'])
    box('pont2', 0, 6, ['7. Repasse sur le pont'])
    box('p2', 1, 7, ['8. Pesée 2 (vide) :', 'net = plein - vide'])
    box('odoo', 3, 7, ['Pesée enregistrée, ligne', '« Décharge (t) » sur le bon', 'de commande du client'], V)
    box('doc', 3, 8, ['9. Ticket + bordereau PDF', 'par e-mail au client,', "registre d'admission"], V)
    box('fact', 1, 8, ['10. Bureau : confirme,', 'facture, suit les DAP'])
    fleche('dap', 'dapo'); fleche('arr', 'rep'); fleche('rep', 'ctrl'); fleche('ctrl', 'pont1', 'OK')
    fleche('pass', 'p1'); fleche('pont1', 'p1'); fleche('p1', 'dech'); fleche('dech', 'pont2'); fleche('pont2', 'p2'); fleche('p2', 'odoo'); fleche('odoo', 'doc'); fleche('doc', 'fact')
    return d


doc = SimpleDocTemplate(SORTIE, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                        title="Carrière de La Martinière - Apports extérieurs de déchets inertes : proposition", author="Carrières Maquignon")
s = []
s.append(Paragraph("CARRIÈRE DE LA MARTINIÈRE (USSEAU) — Apports extérieurs de déchets inertes", H1))
s.append(Paragraph("Proposition d'organisation avec Odoo et le pont-bascule : flux, procédure, matériel. Version du 21/10/2026.", SMALL))
s.append(Spacer(1, 6))

s.append(Paragraph("1. Aujourd'hui", H2))
s.extend(puces([
    "La procédure affichée à la bascule repose sur le papier : DAP signé présenté à l'agent, contrôle visuel, pesée plein, déchargement, pesée vide, bon de bascule, puis bordereau de suivi rempli à la main (carnet numéroté).",
    "L'agent de bascule n'est <b>pas présent en permanence</b> et le bureau est loin : sans DAP, le chauffeur doit faire le trajet jusqu'au bureau avant de décharger.",
    "Les bons de bascule papier sont ressaisis au bureau pour facturer l'article « Décharge (Tonnes) » au prix propre à chaque client.",
    "Le PC de la bascule n'a pas internet. Dans Odoo existe déjà un fichier « Décharge/DAP » (n° 448 à 452 recopiés du carnet) mais sans lien avec la fiche client, sans date de validité ni état.",
]))

s.append(Paragraph("2. Ce que l'on propose", H2))
s.append(Paragraph("Tout se pilote depuis <b>l'accueil</b>, le chauffeur reste dans son camion, et chaque pesée est enregistrée dans Odoo au moment où elle se fait.", P))
s.extend(puces([
    "<b>Le DAP dans Odoo</b> : élaboré à l'accueil avec le client (ou rempli en ligne par le client puis validé), relié à sa fiche, avec chantier, transporteur, nature et code déchet, tonnage estimé, validité 12 mois, numéro d'acceptation. Un DAP accepté est visible à la bascule dans la seconde.",
    "<b>La bascule télécommandée</b> : la page « Pont-bascule » d'Odoo affiche le poids de la D400 en direct et l'image de la caméra du pont, depuis l'accueil comme depuis la cabine. La pesée crée la ligne « Décharge (Tonnes) » sur le bon de commande du client au prix négocié ; le bureau confirme et facture.",
    "<b>Le portier vidéo à la colonne</b> : le chauffeur appuie, l'accueil répond, voit le camion et le guide. Sans DAP, l'accueil le crée pendant l'appel : plus de trajet jusqu'au bureau.",
    "<b>Les documents sans papier</b> : ticket de pesée et bordereau de suivi générés en PDF et envoyés par e-mail au client dès la pesée vide. Le registre d'admission et le registre des refus se remplissent tout seuls.",
]))

s.append(KeepTogether([Paragraph("3. Le flux", H2), schema_flux(), Paragraph("Jaune : étapes liées au DAP. Vert : automatique. Quand l'agent est dans la cabine, il fait les étapes 2, 3, 5 et 8 lui-même sur la même page.", SMALL)]))

s.append(Paragraph("4. Procédures", H2))
s.append(Paragraph("4.1 Accueil : élaborer un DAP (avant la première livraison d'un chantier)", H3))
s.extend(etapes([
    "Odoo, menu <b>Décharge/DAP</b>, bouton <b>Nouveau</b>. Choisir le <b>client</b> (fiche Odoo, créée si besoin), renseigner le <b>chantier</b> (adresse, commune), le ou les <b>transporteurs</b>, la <b>nature</b> (terres inertes / gravats inertes), le <b>code déchet</b>, le <b>tonnage estimé</b> et la date prévisible de début.",
    "Bouton <b>Imprimer le DAP</b> : le formulaire officiel (cadres A à G) sort prérempli pour signature du client. Variante : bouton <b>Envoyer au client</b>, qui reçoit un lien pour remplir et signer en ligne ; l'accueil n'a plus qu'à vérifier.",
    "Après signature : bouton <b>Accepter</b>. Odoo attribue le <b>numéro d'acceptation</b> (suite du carnet, après le 452) et la date de fin de validité (12 mois). Bouton <b>Refuser</b> si le matériau n'est pas admissible (motif conservé).",
    "Le DAP est maintenant visible à la bascule. Les cumuls de tonnage par DAP se mettent à jour à chaque pesée ; Odoo alerte quand le tonnage estimé est dépassé ou que la validité expire.",
]))
s.append(Paragraph("4.2 Accueil : réceptionner un camion à distance", H3))
s.extend(etapes([
    "Le portier sonne : répondre. Demander l'<b>immatriculation</b> et le <b>numéro de DAP</b> (ou le nom du chantier).",
    "Sur la page <b>Pont-bascule</b> (Odoo, Ventes > Pont-bascule), mode <b>Apport extérieur</b> : taper l'immatriculation ou le client. La page affiche les DAP valides du client (numéro, chantier, nature, tonnage déjà apporté). Sans DAP valide : bandeau rouge, pas de pesée possible ; créer le DAP (4.1) pendant l'appel, puis rafraîchir.",
    "Dire au chauffeur d'avancer sur le pont. Vérifier sur la <b>caméra</b> que le camion est entièrement sur le pont ; le poids passe à <b>STABLE</b>. Contrôle visuel du chargement : <b>Bon / Moyen / Mauvais</b>, puis <b>Accepté</b> ou <b>Refusé</b> (motif obligatoire, le camion repart, le refus est au registre).",
    "Bouton <b>Pesée 1 : enregistrer le poids</b> (plein). Indiquer au chauffeur la <b>zone de déchargement</b>.",
    "Au retour du camion : le sélectionner dans « Camions en attente de 2<super>e</super> pesée », vérifier caméra et STABLE, bouton <b>Pesée 2 : terminer</b>. Le net s'affiche, la ligne « Décharge (Tonnes) » est créée sur le bon de commande journalier du client, le ticket et le bordereau partent par e-mail à l'adresse du DAP.",
    "Dire au chauffeur que son ticket est envoyé. S'il passe au bureau, une copie papier peut être imprimée à l'accueil.",
]))
s.append(Paragraph("4.3 Agent dans la cabine (quand il est présent)", H3))
s.append(Paragraph("Même page, même boutons, sur le PC de la cabine : l'agent voit le chauffeur en face de lui, fait le contrôle visuel sur place et les deux pesées. Tout ce qu'il fait est visible à l'accueil en même temps, et inversement.", P))
s.append(Paragraph("4.4 Plateforme : contrôle au déchargement", H3))
s.append(Paragraph("La personne de la plateforme voit le matériau au moment où il est déversé. Phase 2 : sur son téléphone, deux boutons <b>Chargement conforme</b> / <b>Non conforme</b> rattachés à la pesée en cours, pour que le registre porte aussi ce contrôle.", P))
s.append(Paragraph("4.5 Bureau : facturation et registres", H3))
s.extend(puces([
    "Chaque jour ou chaque mois : les bons de commande journaliers « BASCULE-MAQUIGNON-date » sont confirmés et facturés comme aujourd'hui, mais sans ressaisie.",
    "Menu Logistiques > Pesées : liste de toutes les pesées « apport » avec DAP, transporteur, nature, qualité, zone, net. C'est le <b>registre chronologique d'admission</b> ; un filtre donne le <b>registre des refus</b>. Export Excel en un clic.",
    "Fichier DAP : vue par client et par chantier, tonnage apporté contre tonnage estimé, DAP qui expirent dans le mois.",
    "Plus tard : export pour la déclaration RNDTS des terres excavées.",
]))

s.append(Paragraph("5. Matériel et installation", H2))
s.append(tableau([
    ['Élément', 'Rôle', 'Ordre de grandeur'],
    ['Pont Wi-Fi point à point (2 antennes extérieures 5 GHz)', "Relie la cabine au réseau du bureau : internet pour le PC, le portier et la caméra", '150 à 300 € le couple'],
    ['PC de la cabine (existant) + programme « passerelle »', "Lit la D400 par le câble série et envoie poids et image au relais chaque seconde ; doit rester allumé. Sinon convertisseur RS232/Ethernet", 'convertisseur 100 à 150 € si besoin'],
    ['Portier vidéo IP à la colonne (bouton, caméra, haut-parleur)', "Le chauffeur appelle sans descendre ; l'accueil répond sur un téléphone IP ou une application et voit le camion", '300 à 900 € + poste de réponse 80 à 150 €'],
    ['Caméra IP au-dessus du pont', "Vérifier à distance que le camion est bien sur le pont et voir le chargement", '100 à 250 €'],
    ['Panneau de consignes à la colonne', "Les 6 étapes pour le chauffeur (voir ci-dessous)", 'impression'],
    ["Imprimante Epson à l'accueil (tickets)", "Le ticket de pesée s'imprime à l'accueil depuis la page ; rien à la bascule, le chauffeur reçoit ses documents par e-mail", 'imprimante prévue'],
    ["Caisse Odoo à l'accueil (point de vente)", "Encaissement immédiat des particuliers (espèces, carte) avec ticket de caisse, sur la même imprimante ; la pesée peut créer directement le ticket à régler", 'inclus dans Odoo'],
], [58 * mm, 82 * mm, 38 * mm]))
s.append(Paragraph("Les prix sont des ordres de grandeur à confirmer sur devis. Le logiciel (DAP, page bascule, passerelle, e-mails, registres) est réalisé en interne sur Odoo et le relais existants, sans licence supplémentaire.", SMALL))

s.append(Paragraph("6. Consignes affichées à la colonne", H2))
s.append(Paragraph("1. Appuyez sur le bouton.<br/>2. Donnez votre immatriculation et votre numéro de DAP ou votre chantier.<br/>3. Avancez sur le pont quand on vous le dit.<br/>4. Déchargez dans la zone indiquée.<br/>5. Repassez sur le pont.<br/>6. Votre ticket arrive par e-mail.", NOTE))

s.append(Paragraph("7. Mise en place", H2))
s.append(tableau([
    ['Étape', 'Contenu', 'Dépend de'],
    ['1', "DAP dans Odoo (fiche enrichie, boutons Imprimer / Accepter / Refuser, formulaire officiel prérempli, reprise des DAP du carnet)", 'rien : utilisable tout de suite'],
    ['2', "Pont Wi-Fi posé, PC de la cabine sur le réseau, programme passerelle installé (poids en direct à l'accueil)", 'pont Wi-Fi'],
    ['3', "Page Pont-bascule : mode Apport extérieur (contrôle DAP, contrôle visuel, refus), ticket et bordereau PDF par e-mail, vue caméra", 'étapes 1 et 2'],
    ['4', "Portier vidéo et caméra installés, consignes affichées ; essais avec quelques chauffeurs habitués", 'étape 2'],
    ['5', "Registres et alertes DAP ; fin du carnet papier", 'étape 3'],
], [16 * mm, 118 * mm, 44 * mm]))

s.append(Paragraph("8. Ce que ça change", H2))
s.append(tableau([
    ['Pour', 'Avant', 'Après'],
    ['Le chauffeur', "DAP papier à présenter, trajet au bureau s'il manque, bordereau à remplir à la main", "Appuie sur le portier, donne son numéro de DAP, reste dans le camion, reçoit son ticket par e-mail"],
    ["L'accueil", "Ne voit pas la bascule, DAP sur papier", "Pèse à distance avec le poids et la caméra en direct, crée les DAP, voit tout dans Odoo"],
    ["L'agent de bascule", "Doit être présent pour chaque camion", "Même page quand il est là ; la bascule fonctionne sans lui le reste du temps"],
    ['Le bureau / la compta', "Ressaisie des bons papier, registres à tenir", "Lignes de commande créées à la pesée, registres automatiques, alertes DAP"],
], [34 * mm, 68 * mm, 76 * mm]))

s.append(Paragraph("9. Points à décider", H2))
s.extend(puces([
    "Dépassement du tonnage estimé d'un DAP : simple alerte (recommandé) ou blocage de la pesée.",
    "Qui répond au portier à l'accueil, et pendant quelles heures ; que fait le chauffeur en dehors (panneau : numéro de téléphone).",
    "Garder le carnet papier pendant la période de transition, ou passer directement au bordereau PDF.",
    "Signature du chauffeur : aucune (e-mail) ou signature sur l'écran de la cabine quand l'agent est présent.",
]))
s.append(Paragraph("Rappel réglementaire (arrêté du 12/12/2014, installations de stockage de déchets inertes) : document préalable d'acceptation avant admission, contrôle visuel à l'arrivée et au déchargement, registre d'admission et des refus conservé, accusé d'acceptation remis au producteur. L'organisation proposée couvre ces quatre points, et le formulaire DAP actuel (cadres A à G, validité maximale 12 mois) reste le document de référence.", SMALL))

doc.build(s)
print('écrit :', SORTIE)
