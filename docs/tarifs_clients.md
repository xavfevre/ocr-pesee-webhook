# Tarifs clients MAQUIGNON (12/08)

## Demande
« Dans la discussion Odoo V19 Protec XML-RPC nous avons mis en place un
système pour les tarifs des clients, je voudrais faire la même chose pour
Maquignon. »

## Réalisé — module `maquignon_tarifs/` (monté sous `/tarifs-client`)
Réplique du système Protec (`protec_planning`, page /protec/tarifs),
adaptée au groupe : page bureau par client avec
- catalogue complet de la société (prix **standard** = liste de référence)
  vs **prix client** (sa liste), écart %, plages de validité ;
- **ajout / modification / suppression** de tarifs spécifiques à prix fixe
  avec dates de validité (modale) ;
- **historique facturé** par produit (clic sur la ligne) + compteurs
  (produits / spécifiques / déjà facturés) + filtres catégorie/recherche ;
- onglet **📈 Évolution** : prix par année (tarif spécifique en vigueur,
  sinon moyenne facturée) avec % d'évolution ;
- **export Excel** (2 onglets : tarifs actuels + évolution).

## Adaptations Maquignon (vs Protec)
- **Multi-sociétés** : sélecteur en tête (5 sociétés), société par défaut =
  celle de la dernière facture du client. Listes de référence par société
  (param `maquignon.tarifs_defaut_pl`, JSON — défauts : SARL 299 Tarif Pro
  2026, Chatel 284, Distri 293, Haims 281, SFM 1690).
- **Listes partagées protégées** : beaucoup de clients sont sur des listes
  communes (« Tarif Pro 2026 »…). La page n'y écrit JAMAIS : à la première
  saisie, création d'une liste **dédiée au client** (à son nom) avec un
  item de repli « formule = 100 % de l'ancienne liste » (tous les autres
  prix inchangés), puis affectation au client. Une liste est reconnue
  dédiée si son nom recouvre celui du client ou si elle est listée dans
  `maquignon.tarifs_pl_dediees` (initialisé : 288 VEOLIA-SEDE, 1678
  BESNAULT, 1681 TERROBA, 294 COLAS, 1679 Transvrac). Garde-fou serveur :
  modification/suppression refusées sur un item de liste partagée.
- **Jeton** dans Odoo (`maquignon.tarifs_key`), vérifié à chaque requête —
  pas de variable d'environnement à ajouter sur Render.
- Pas d'import Excel (spécifique au classeur Protec).

## Accès depuis Odoo (déjà en place)
- **Smart boutons « Tarifs client »** dans l'en-tête des fiches **Contact**
  (vue 7975) et **Devis** (vue 7976, société du devis présélectionnée) ;
- aussi dans le menu ⚙️ Actions des deux formulaires (actions serveur
  2079 contact / 2080 devis, act_url avec le jeton).

## Tests (locaux, contre la prod, avant merge)
403 sans jeton ; VEOLIA/SARL : 340 produits, 1 tarif spécifique (Loc FM
728 €), 9 produits facturés, export Excel OK ; cycle ajout (999,50 € sur
validité 2020, sans effet réel) → modification (888) → suppression OK ;
suppression d'un item de liste partagée refusée ; formulaires contact et
devis chargés avec les boutons. **La page n'est active qu'après le merge**
(Render déploie depuis main).

## Unités de mesure (12/08)
L'unité de vente du produit est affichée partout : colonnes Prix standard
et Prix client (« 728,00 € / Forfait », « 12,50 € / Tonne »…), libellé du
prix dans les modales d'ajout/modification, onglet Évolution (sous le nom
du produit) et colonne « Unité » de l'export Excel.
