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

## Étape 2 — automatisation

- **Action serveur 2012→2082** « Code client automatique (Sage) » +
  **règle d'automatisation 89** (`base.automation`, on_create_or_write sur
  `customer_rank` / `company_id`).
- Déclenche : fiche autonome (pas contact), client (`customer_rank > 0`),
  sans code, société 1/2/3/4. Exclut utilisateurs Odoo et étiquettes
  « Compte odoo » / « Société du Groupe ».
- Code attribué : préfixe société + n° suivant sur 5 chiffres (le max est
  recalculé à chaque fois — pas de séquence à maintenir).

Mirror du code : `odoo-scan-page/action_code_client_sage_2082.py`.

## Restes à faire / points ouverts

- **Étape 3** : interface web export écritures de vente au format d'import du
  cabinet + fichier « nouveaux clients » (les codes `MAQ0xxxx` restants et
  toutes les nouvelles séquences y partiront) — en attente du format d'import.
- Codes Châtel legacy (~550 noms/numéros) : à vérifier si un export Sage
  Châtel existe.
- Doublons volontairement conservés : fiches Alliance/Joubert côté DIS
  (annulées de fait, sans factures).
