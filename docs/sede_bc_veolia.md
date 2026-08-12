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
