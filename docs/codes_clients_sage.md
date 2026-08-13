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

4. **Contacts** (fiches rattachées à une mère) : héritent de la **société et
   de l'étiquette de la fiche mère**, jamais de code (le code vit sur la mère).
   Rattrapage fait sur l'existant (4 contacts corrigés sur 212).

Exclus : utilisateurs Odoo, étiquettes « Compte odoo » / « Société du Groupe ».

Testé en prod : création sans société → MAQ + Client Maquignon ; création
Châtel → CG ; bascule Châtel→Haims → recodage HAI + étiquette corrigée ;
code « nom » conservé à la bascule. Fiches test supprimées.

Mirror du code : `odoo-scan-page/action_code_client_sage_2082.py`.

## Prospects : code au premier devis / première facture

Les fiches sans activité (`customer_rank = 0`) ne sont **pas** codées en masse :
sur 631 fiches concernées, beaucoup sont des artefacts d'emails entrants
(`"Secrétariat" <secretariat@…>`) ou des doublons — les coder polluerait Sage.
À la place, deux règles (actions **2086** sale.order / **2087** account.move)
codent la **fiche mère** du client dès son **premier devis** ou sa **première
facture client** (le rang client natif ne monte qu'à la validation d'une
facture, trop tard pour l'affichage). Une fiche artefact n'a jamais de devis →
jamais codée. Fiche sans société au moment du devis → société du document.

**Exception DISTRI BETON** : le code `DISxxxxx` sert d'identifiant au
**distributeur de béton** (borne) — il est attribué **dès la création de la
fiche**, même sans devis ni facture (domaine de la règle 89 élargi à
`company_id = 2`).

## Contacts porteurs de codes (nettoyé le 13/08)

L'ancienne règle codait aussi les contacts (adresses de facturation
comprises) : 95 contacts porteurs d'un code. **78 vidés** (aucune facture
propre — le code vit sur la fiche mère, ex. adresse « 3 FAUCHER » qui portait
`DIS00740` alors que la mère a `3FAUCHER`). **17 conservés** : des contacts qui
ont leurs propres factures (JOUBERT `CG00311`, CROCODILE, BIOTHERMIE,
CHARIER…) — pattern hérité où le contact est le client facturé.

**Règle pour l'export écritures (étape 3)** : code client d'une facture =
`partner_id.ref` **si le destinataire de la facture porte un code**, sinon
`commercial_partner_id.ref` (la fiche mère). Une facture adressée à un contact
ou à une adresse de facturation remonte donc automatiquement au code de la
fiche mère, et les 17 contacts-clients hérités gardent leur propre code.

## Adresse de facturation automatique

Flux devis → facture : natif (le devis résout l'adresse de facturation dédiée
du client). Complété le 13/08 par la règle **« Facture : adresse de facturation
automatique »** (action serveur + règle 92) : une facture client créée
**directement** sur une fiche mère bascule d'elle-même sur l'adresse de
facturation dédiée si elle existe (brouillons uniquement, factures fournisseurs
non concernées). Le code Sage remonte de toute façon à la fiche mère via
`commercial_partner_id`.

## Alerte à la facturation / devis

Le **contrôle multi-sociétés natif d'Odoo** bloque désormais tout devis,
commande ou facture créé sur une société différente de celle de la fiche
client (« Oups ! Des incohérences entre sociétés ont été détectées »), y
compris via les adresses de facturation/livraison. Il était inopérant tant que
les fiches étaient « partagées » (sans société) — l'assainissement du
13/08/2026 l'a réactivé de fait. Aucune règle custom nécessaire (deux règles
d'alerte 2083/2084 créées puis retirées le même jour, redondantes).

## Restes à faire / points ouverts

- **Étape 3** : interface web export écritures de vente au format d'import du
  cabinet + fichier « nouveaux clients » (les codes `MAQ0xxxx` restants et
  toutes les nouvelles séquences y partiront) — en attente du format d'import.
- Codes Châtel legacy (~550 noms/numéros) : à vérifier si un export Sage
  Châtel existe.
- Doublons volontairement conservés : fiches Alliance/Joubert côté DIS
  (annulées de fait, sans factures).
