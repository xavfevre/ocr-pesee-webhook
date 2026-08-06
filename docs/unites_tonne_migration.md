# Unités de mesure : les deux « Tonne » et la migration (06/08/2026)

## Le problème
Deux unités s'affichaient « Tonne » dans Odoo :
- **id 1** — en réalité l'unité générique de base d'Odoo (« Unité(s) »),
  **renommée « Tonne »** depuis le compte Isabelle le 05/08 à 9h17 ;
  facteur 1, sans lien avec le kg. Unité principale de ~344 produits,
  presque tous vendus **à l'unité** (balustres, big bags, badges, remises…).
- **id 14** — la vraie tonne (= 1000 kg), utilisée par ~209 produits.

Conséquences : les articles à l'unité imprimaient « 1,000 Tonne » sur les
factures, et toute ligne mélangeant les deux unités (produit dans l'une,
ligne dans l'autre) subissait une conversion ÷1000 : « 8,56 → 0,009 Tonne »
(symptôme signalé par le client sur S11135/S11263).

## Corrections de données ponctuelles
- Lignes corrigées (unité 1 → 14, quantités/compteurs recalculés, montants
  intacts) : S11135 et S11262 (Autres Graviers 0/20 Bleu, 8,56 T),
  S09679 (Bleu diorite 0,54 T).
- ⚠️ Signalé au client sans correction : le ticket de caisse ChatelGranulats
  000332 (02/07) a vendu 0,54 T de Bleu diorite pour 0,02 € au lieu de
  ~13,40 € à cause de cette conversion (ticket historique clôturé).
- Ligne d'avril (location matériel, qté 1) : même mélange, zéro impact
  chiffré, laissée en l'état.

## Corrections structurelles
1. **Unité id 1 renommée « Unité »** (fr + en), prod et base de test —
   les ~300 produits à l'unité réimpriment correctement.
2. **Règle d'accès 686** (ir.rule, prod) : création/modification/suppression
   d'unités de mesure **réservée au compte Isabelle** — les autres
   utilisateurs sont bloqués (lecture/utilisation intactes). Demande
   explicite du client.
3. **Migration de 20 vrais produits tonnage** de l'unité 1 vers la vraie
   Tonne (id 14). Sélection **décidée sur les factures** : produits à ≥50 %
   de quantités décimales (signature des pesées en pont-bascule) et prix/T
   cohérent, plus les granulats jamais facturés au nom sans ambiguïté.
   Ids : 756, 759, 760, 762, 2395, 2871, 2872, 2873, 2874, 2877, 2878,
   2886, 2891, 2895, 2898, 2909, 3114, 3141, 3209, 3230
   (graviers, concassés, enrochements, béton recyclé, transports « en
   tonnes », 0/20…).

## Méthode de migration (validée sur base de test avant prod)
Odoo interdit le changement d'unité d'un produit déjà facturé (« archiver et
recréer »). Contournement légitime ici car **1 Tonne(id 1) = 1 Tonne(id 14)
numériquement** : bascule de l'identifiant d'unité par SQL direct (action
serveur, `env.cr.execute`), sans toucher aux quantités ni aux montants, sur
toutes les tables porteuses : `product_template.uom_id`,
`sale_order_line.product_uom_id`, `stock_move.product_uom`,
`stock_move_line.product_uom_id`, `account_move_line.product_uom_id`,
`purchase_order_line.product_uom_id`, puis `env.registry.clear_cache()`.

Volumes prod : 20 modèles, 716 lignes de vente, 718 mouvements de stock,
573 lignes de mouvement, 531 lignes de facture, 0 ligne d'achat.
Vérifié après coup : produits tous sur Tonne(14), lignes de factures
comptabilisées inchangées en montants, compteurs commandé/facturé/livré
cohérents.

## Reste à trancher (produits ambigus laissés sur « Unité »)
- « TP » (id 2869) : usage mixte sur les factures (27 % décimales, prix
  moyen 715 €) — à clarifier avec le bureau.
- « Béton Recyclé » migré (100 % décimales sur ses 20 factures = tonnage
  confirmé par les données).
- Gabions pré-remplis, « Tuffeau/Haims/Richemont - A l'unité », dallages :
  restent à l'unité (confirmé par les factures : quantités entières).

## Annexe — Tuffeau d'Usseau (06/08)
À la demande du client, sur les commandes S08675, S09148, S08047, S10296,
S09388, S10995, S11020, S08126 : les produits tuffeau génériques remplacés
par les produits **« (U) » (Usseau)** à variante identique (18 lignes de
commande + 16 lignes de factures comptabilisées, via SQL — montants,
libellés imprimés et totaux inchangés : 8 152,68 € vérifiés). Mapping :
552→6053, 554→6055, 556→6057, 557→6058, 558→6059, 745→6061, 744→6070.
L'historique de stock/fabrication n'a volontairement pas été modifié.
