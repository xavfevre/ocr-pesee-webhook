# Récapitulatif des personnalisations — Maquignon / Odoo 19 SaaS
*(à jour au 29/07/2026 — sociétés : SARL MAQUIGNON, CHATEL'GRANULATS, DISTRI BETON, CARRIÈRE D'HAIMS)*

## 1. Applis tablettes & terrain (pages web Odoo)

**Ma production / Historique** (`/vue-operateur?op=…`) — la tablette des opérateurs :
- cartes d'opérations colorées par pierre (couleurs officielles du planning), plans PDF, dimensions, quantités, pointage Démarrer/Pause/Terminer, pièce par pièce (+1) ;
- filtres en étiquettes mémorisés par tablette : Site (Atelier/Usine), Machines, Clients, Réf. commande, Palette, gabarit dimensionnel « rentre dans » ;
- mise au colis (choix du colis enrichi client/réf/prépal, raccourci ⚡ dernier colis, clôture + emplacement + impression) ;
- **scan caméra** de la palette (lecteur code-barres du navigateur) ;
- déclaration de **rebut** avec motif → OF relancé automatiquement (tag « Relance suite rebut de », opérateurs de l'OF d'origine réassignés pour qu'il apparaisse dans « Ma production », garde-fou anti-double déclaration, sortie de stock forcée si stock insuffisant — corrigé 26/08) ;
- **scan du bloc** au sciage primaire (lien bloc ↔ OF) ;
- champ **Note** en saisie directe sur chaque tuile, visible ensuite à la mise en palette.

**Poste de scan colis/OF** (`/scan`, `/scan?poste=2` pour l'Usine) :
- création/reprise de colis (douchette ou caméra), ajout d'OF entiers ou répartis (popup quantité), retrait, rebut par ligne ;
- clôture par scan de l'emplacement → impression du bon de colisage + verrouillage + déplacement de stock ;
- navigateur de colis ouverts enrichi (client, réf, prépalettisation, cubage/tonnage), reconnexion de session sans perte d'action.

**Planning Machines** (`/planning-machines`) : boards Complet / **Atelier** / **Usine** / Sciage primaire / Sciage secondaire, glisser-déposer des OT, brouillons, filtres.

**Plannings complémentaires** : planning opérateurs, planning transport hebdo + mensuel, suivi de commandes.

**Appli chauffeur « Ma tournée »** (Flask sur Render) : feuilles de travail, photos de bons compressées avec renvoi automatique et accusé visuel fiable, OCR des bons de pesée (webhook), pré-remplissage camion.

## 2. Bi-site Atelier / Usine
- Champ **Site** sur chaque machine ; machines Usine : TSH2300, TC625, **TC1350 Usine**, GMM — nouvelle **TC1350 Atelier** distincte ; postes alternatifs croisés pour la planification inter-sites.
- Filtres Site sur toutes les vues web, deux postes de scan, deux dashboards Fabrication, deux boards de planning.

## 3. Traçabilité des blocs
- Modèle **Bloc** (BLC-xxxxx) : n° carrière, pierre, fournisseur, dimensions capables (= facturées), prix/m³, coût, tonnage, statut (stock → sciage → débité / rebut), emplacement.
- **Réceptions de blocs (BL)** : saisie manuscrite par la secrétaire, en-tête propagé aux lignes ; fiches bloc code-barre à l'unité ou en lot.
- Scan du bloc sur la tablette TSH2300 → lien à l'OF, calcul du **rendement** (volume tranches / volume bloc) et passage de statut automatiques.

## 4. Dashboards (feuilles de calcul dynamiques)
- **33 Fabrication — Atelier** & **36 Fabrication — Usine** : production, familles de pierre, temps moyen par pierre, heures assainies, bilan par pierre (cartes couleurs), machines, opérateurs.
- **34 Commandes en cours** : compteurs auto-dimensionnés, « Reste à produire » et « À programmer » par pierre, date planifiée, zébrage — **reconstruit chaque nuit** (3 h 40) depuis Render.
- **35 Taxe ROC (CTMNC)** multi-sociétés + détail MAQUIGNON par analytique (Blocs/Tranches/Pré-sciées).
- **32 Rentabilité camions** (avec kilomètres intercalés), comparatif annuel, CA/cubage par pierre, dashboards finance/SAGE, Haims.

## 5. Rapports PDF
Devis (cadre totaux à droite), factures/commandes (description à la ligne), **bon de colisage enrichi** (commande, objet/BC, prépalettisation, adresse livraison, lignes compactes), bon de livraison, fiche bloc + fiches BL en lot, étiquettes palette/code-barres, ordre de fabrication.

## 6. Transport & camions
Tâches transport avec liaison automatique du véhicule Fleet (immatriculation), feuille de travail TP synchronisée (camion, km requis), garde-fou odomètre (relevés cohérents, dédupliqués), n° de lettre de voiture auto, rapport VEOLIA auto-envoyé, OCR photo des bons (n° bon, client, transporteur, produit, chantier, véhicule, pesées/poids net, date, et depuis 08/2026 **Contrat SAP** + **code destinataire marchandise** — remplis quand présents sur le bon, ex. Heidelberg/GSM). Duplication des tâches réparée pour tous les profils (droits Parc automobile en lecture).

## 7. Fabrication — règles & correctifs
Temps de gamme Tuffeau réalistes (~9,7 min/pierre mesurés sur pointages réels), 480 pointages aberrants corrigés, garde-fou « OF terminé » (annulation ≠ terminé), rebuts bout-en-bout, colis pré-imprimés agrafés = fonctionnement normal.

## 8. Comptabilité & gestion
- **Éco-contribution REP** : recalcul automatique par ligne, ligne 0 € masquée.
- **Taxe ROC** : étiquette produit + comptes/analytiques vérifiés.
- **Banques CHATEL (29/07)** : soldes rétablis au centime (Banque Pop 46 824,52 / BNP 31 140,97 / Caisse 119,86), doublons de reconnexion purgés, double comptabilisation des remises CB éliminée (cron redondant désactivé), remises CB pointées avec éclatement brut/commission, compte CB à l'encaissement rendu lettrable + lettrage FIFO, frais bancaires/dépôts GAB/virements internes lettrés, écart de coupure identifié sur relevés papier (dépôt GAB 700 € réintégré + 690 € pré-30/04 à détailler via relevé n°3).
- Modèle de lettrage « REMISE CB → CB à l'encaissement ».

## 9. Procédures & documentation
PDF **Procédures opérateurs** (Ma production, poste de scan, rebuts, colisage), documentation du circuit blocs, et dossier `odoo-scan-page/` du repo GitHub = miroir de toutes les vues/actions déployées (chaque changement est committé).

## 10. Infrastructure
- **Render** : webhook OCR pesée + appli chauffeur + reconstruction nocturne du dashboard 34 (déploiement au merge sur `main`).
- **Abonnement Odoo optimisé** : module de personnalisations ramené de ~36 à ~14 unités de 100 lignes (sous les 18 incluses) — ménage des rapports dupliqués Studio à refaire périodiquement.
