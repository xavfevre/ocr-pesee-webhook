# Éco-contribution REP Tuffeau au prorata par facture (06/08/2026)

## Symptôme signalé
« Sur la dernière facture de la commande S06604, l'éco-contribution ne
s'ajoute pas. »

## Diagnostic
L'éco-contribution est une **ligne unique** sur la commande (qté 1, prix =
volume total × 4,16 €/m³, recalculée par les automatisations 54/78
existantes). Sur une commande facturée en plusieurs fois :
- la 1re facture consomme la ligne entière → elle facture **100 % de l'éco**
  même si elle ne porte qu'une partie du volume (S06604 : facture 1 =
  4,385 m³ de pierres mais 58,01 € d'éco = les 13,944 m³ de la commande) ;
- les factures suivantes n'ont plus rien à reprendre → **aucune éco**.

Au global la commande n'est PAS sous-facturée (l'éco totale est passée sur
la 1re facture), mais la répartition par facture est fausse. Cause aggravante
découverte au passage : le produit ECO CONTRIBUTION est en politique de
facturation « à la livraison » avec livré = 0, donc l'assistant de
facturation ne l'embarque que si quelqu'un force la quantité livrée.

## Choix du client
Éco-contribution **au prorata du volume de chaque facture**.

## Correctif (prod, 06/08)
Action serveur **2067** + automatisation **base.automation 85** (à la
création de chaque facture client) : code dans
`odoo-scan-page/action_eco_prorata_2067.py`.

À la création d'une facture depuis une ou plusieurs commandes :
1. calcule le **volume porté par cette facture** (somme des `x_studio_vol`
   des lignes de commande liées, au prorata qté facturée / qté commandée) ;
2. cible éco = volume × 4,16 €/m³ ;
3. **garde-fou anti-double-facturation** : la cible est plafonnée à
   (éco totale des commandes − éco déjà facturée sur leurs autres factures,
   avoirs déduits). Indispensable pour les commandes historiques dont la 1re
   facture a déjà tout facturé (ex. S06604 : les factures suivantes n'auront
   pas d'éco, c'est normal, elle est déjà payée) ;
4. réécrit la ligne éco si l'assistant l'a mise (montant + libellé avec le
   volume de la facture), la crée si elle manque, la supprime si le volume
   de la facture est nul.

## Tests réalisés en prod (réversibles, brouillons supprimés après)
- S06604 (éco déjà toute sur la facture 1) : action sur le brouillon de la
  2e facture → **rien d'ajouté** (garde-fou) ✓
- S10329 (rien de volumique facturable) : facture assistant = forfait seul →
  **pas de ligne éco** ✓
- S06845 (commande refacturée après avoir total) : gestion du **signe des
  avoirs** vérifiée (facture 11,71 € + avoir −11,71 € → déjà facturé net = 0
  → la nouvelle facture reprend bien 11,71 €, réécriture au bon montant) ✓

Les anciennes automatisations 54/78 (calcul de la ligne éco sur la commande)
restent en place : la ligne de commande continue d'afficher l'éco totale ;
c'est la répartition par facture qui est maintenant gérée par l'action 2067.
