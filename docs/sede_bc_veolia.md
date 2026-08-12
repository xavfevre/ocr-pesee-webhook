# Bouton « ⚡ SEDE » — BC automatiques VEOLIA AGRICULTURE (12/08)

## Demande (Isabelle)
Automatiser la procédure répétitive de facturation des transports
« LA SEDE » du client VEOLIA AGRICULTURE FRANCE : ouvrir chaque tâche
grise du planning transport, ajouter l'article de la vue « Loc FM »
(1er article, par jour), créer le bon de commande, cliquer « Bon de
pesée », remettre la quantité facturée à 1 — pour tout juillet 2026, et
un bouton « SEDE » sur la vue mois pour la suite.

## Rétro-ingénierie du geste manuel
Un BC fait main (S11363) montre le résultat cible :
- BC **confirmé**, liste de prix « VEOLIA AGRICULTURE - SEDE » ;
- ligne « Location de matériel Transport (Semi Fond-mouvant - par
  jours) », **quantité 1** (location à la journée), 728 € ;
- section « Bon n°… | date | produit | camion | tonnage » au-dessus,
  reprise de la feuille de pesée (logique du bouton Studio 1615) ;
- tâche liée dans les deux sens + note au chatter + 1 bon de livraison.
L'étape « remettre la quantité à 1 » existe parce que le bouton 1615
écrase la quantité par le tonnage (28,54…) — inadapté à une location
par jour. Les anciennes lignes 0,25 × 740 € (S10087-98) sont l'ancien
schéma de facturation, abandonné par Isabelle depuis S11348.

## Réalisé
- **Action serveur 2078** (`odoo-scan-page/action_sede_bc_veolia_2078.py`) :
  pour chaque tâche VEOLIA du projet « Demande de transport » de la
  période SANS bon de commande — BC confirmé + article par jours qté 1
  (le prix vient de la liste de prix : 728 €) + section bon de pesée
  (sans écrasement de quantité) + chatter. Tâches **annulées** et BC
  **déjà existants** ignorés (relançable sans risque de doublon).
- **Bouton « ⚡ SEDE »** sur `/planning-transport-mois` (vue 7883), à côté
  d'Actualiser : confirmation, appel de 2078 sur le mois affiché
  (utilisateur connecté à Odoo requis), récapitulatif (créés / déjà
  faits / annulées / sans bon de pesée) puis rechargement.

## Juillet 2026 : fait
Test unitaire sur la tâche du 16/07 (S11365, réplique conforme de
S11363), puis génération du mois : **53 BC créés (S11366 → S11418)**,
30 déjà existants ignorés, 1 annulée ignorée, 53/53 sections bon de
pesée, tous à 728 € qté 1 confirmés. Plus aucune tâche VEOLIA de
juillet sans BC (hors annulée). Les pastilles du planning passent de
grises à orange « À facturer ».

# Extension : 7 boutons de BC automatiques (12/08)

Même mécanique que SEDE, généralisée : **action serveur 2081** (miroir
`odoo-scan-page/action_boutons_transport_2081.py`) pilotée par recette,
boutons violets sur `/planning-transport-mois` (mois affiché, tâches
annulées et BC existants ignorés, relançable sans doublon). La section
« Bon de pesée » est composée directement au bon format (plus de
retouche manuelle).

| Bouton | Client(s) | Articles | Quantité | Section |
|---|---|---|---|---|
| ⚡ Longué + Lac | CULTURES FRANCE CHAMPIGNON LONGUE, COOP DU LAC | Terre de gobetage (Tonne) + Transport gobetage (Tonne) | tonnage | sans produit |
| ⚡ Prieuré | LE PRIEURE | idem + Libellé Client « Tuffeau broyé 0/15 - 0/20 (en tonnes) » sur la ligne Terre de gobetage | tonnage | sans produit |
| ⚡ Besnault | BESNAULT FRERES | Transport Appro (Départ Eurovia - Luché) | tonnage | sans produit |
| ⚡ Machefers | VEOLIA PROPRETÉ POITOU CHARENTES | Transport de machefers | 1 (forfait 125 €) | sans produit |
| ⚡ GSM | Heidelberg Materials (GSM) | Transport de granulats (Tonne) | tonnage | standard |
| ⚡ Châtel | CHATEL'GRANULATS (Client+Fr Maquignon) | APPRO → 11 variantes selon le départ (mots-clés BARRE/BAILLY/ROY/MORIN/LUCHE/HAIMS/MAQUIGNON/USSEAU/KIDIMAT/IMERYS/SAMIN/POUZZO, insensibles aux accents) · DÉBLAIS → granulats (Tonne) · sinon → granulats (Forfait) | tonnage / tonnage / 1 | produit réduit à 4 car. / standard / nom de tâche inséré après le produit |
| ⚡ Haims | CARRIERE D'HAIMS (Client de Maquignon) | granulats (Tonne) ; tâches TRANSFERT → Transfert de matériel (Heure) | tonnage / 1 à ajuster | nom de tâche inséré avant le produit |

Garde-fous : pas de poids sur le bon → quantité 1 + signalement « à
vérifier » dans le récapitulatif ; transferts Haims listés « à vérifier »
(heures à saisir) ; feuille de pesée vide → BC sans section, signalé.

Testé en prod (un BC réel par recette, conservés) : S11463 Coop du Lac
(30,06 T ×2 lignes), S11464 Prieuré (libellé client posé), S11465
Besnault (Eurovia-Luché 21 T), S11466 Machefers (1 × 125 €), S11467 GSM
(sans poids → qté 1 signalée), S11468 Châtel APPRO Haims (« GRAV »,
29,96 T), S11469/70 Haims (« LES DUCS DE RICHELIEU » inséré, tonnage).
Nota : les BC Haims sortent à 0 € (liste Tarif Pro 2026 sans prix pour
granulats Tonne — les BC manuels étaient à 1 €/0 €) : prix intersociété
à poser au moment de la facturation, comme avant.
