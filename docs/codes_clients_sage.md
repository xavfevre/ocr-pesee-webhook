# Codes clients Sage ↔ Odoo

*Étapes 1 et 2 réalisées le 13/08/2026. Étape 3 (interface web d'export écritures + nouveaux clients) à venir.*

## Principe

Le champ **Référence** (`ref`) de la fiche client Odoo porte le **code client du
dossier Sage** de sa société. Une fiche = une société (assainissement fait :
plus aucune fiche client partagée, sauf SNT TRAVAUX PUBLICS, volontairement).
Le champ « Code client » affiché dans les vues est un miroir de `ref` ; les
colonnes « Code Client / Sage » des listes devis/factures pointent aussi vers
`partner_id.ref`. Le champ Studio `x_studio_code_client_sage` (vide, sans
usage) a été supprimé.

## Schémas de codes par société

| Société | Dossier Sage | Codes existants | Nouveaux clients |
|---|---|---|---|
| SARL MAQUIGNON | oui (9 535 clients) | codes Sage « nom » (`COLAS`…) | `MAQxxxxx` (séquence) |
| CARRIERE D'HAIMS | oui (2 299 clients) | codes Sage « nom » | `HAIxxxxx` (séquence) |
| CHATEL'GRANULATS | historique | legacy noms + numéros, puis `CGxxxxx` | `CGxxxxx` (séquence) |
| DISTRI BETON | — | `DISxxxxx` | `DISxxxxx` (séquence) |

`DIS99999` (PARTICULIER BORNE) est un code spécial hors séquence.

## Étape 1 — rapprochement avec les exports Sage (Maquignon + Haims)

- 527 fiches déjà correctes ; 37 + 13 complétées par correspondance exacte/approchante ;
- 421 fiches en séquence interne `MAQ0xxxx` : 206 + 95 recodées avec leur vrai
  code Sage ; les 120 restantes gardent leur code MAQ (clients **à créer dans
  Sage** via l'export de l'étape 3) ;
- corrections croisées : codes pris dans la mauvaise séquence recodés
  (CG00466-468, DIS00809, PASQUIERD, SIRON, GALERNE pour B.P.N.R.) ; codes CG
  retirés de 4 contacts (Association CHAM, Besnault) ;
- 72 fiches sans code codées dans les nouvelles séquences ;
- fiches « sans société » affectées (étiquettes Client X, créateur, parent) ;
  étiquettes clients complétées.

## Étape 2 — automatisation « cohérence fiche client »

**Cause racine des fiches mal casées** (comprise le 13/08) : l'ancienne règle
« Num client » (règle 2, action 1260) codait toute fiche sans référence selon
la **société active de l'utilisateur** (`env.company`) — séquence CG si
« CHATEL », **sinon DIS pour tout le monde** — contacts compris, avec des
séquences désynchronisées (CG à 465 alors que la base était à CG00486).
Delphine/Isabelle travaillant sur 4-5 sociétés, la société active ne
correspondait pas toujours à la fiche. → **Règle désactivée.**

**Remplacée par** : action serveur **2082** + règle d'automatisation **89**
(`on_create_or_write` sur `customer_rank` / `company_id`,
domaine `customer_rank > 0` et pas un contact) :

1. **Société** manquante → société active du créateur ;
2. **Code** selon la société de la **fiche** : `MAQxxxxx` / `HAIxxxxx` /
   `CGxxxxx` / `DISxxxxx` (max recalculé à chaque attribution — pas de séquence
   à maintenir). Attribué si absent, **recodé si la fiche change de société**
   et portait un code séquence d'une autre société. Les codes Sage « nom »
   ne sont jamais touchés ;
3. **Étiquette** « Client X » de la société ajoutée, celles des autres
   sociétés retirées (les règles 23-26 d'ajout d'étiquettes restent actives).

Exclus : contacts (`parent_id`), utilisateurs Odoo, étiquettes « Compte odoo »
/ « Société du Groupe ».

Testé en prod : création sans société → MAQ + Client Maquignon ; création
Châtel → CG ; bascule Châtel→Haims → recodage HAI + étiquette corrigée ;
code « nom » conservé à la bascule. Fiches test supprimées.

Mirror du code : `odoo-scan-page/action_code_client_sage_2082.py`.

## Restes à faire / points ouverts

- **Étape 3** : interface web export écritures de vente au format d'import du
  cabinet + fichier « nouveaux clients » (les codes `MAQ0xxxx` restants et
  toutes les nouvelles séquences y partiront) — en attente du format d'import.
- Codes Châtel legacy (~550 noms/numéros) : à vérifier si un export Sage
  Châtel existe.
- Doublons volontairement conservés : fiches Alliance/Joubert côté DIS
  (annulées de fait, sans factures).
