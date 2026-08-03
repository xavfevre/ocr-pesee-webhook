# Départements RH alignés sur les étiquettes salariés — 30/07/2026

## Contexte

Les 5 anciens départements (`SALARIES CHATEL'GRANULATS`, `SALARIES HAIMS`,
`SALARIES MAQUIGNON`, `SALARIES SFM`, `INTERIMAIRE`) étaient archivés et
découpaient par société, ce qui doublonnait avec le champ Société.
Ils sont laissés archivés, sans suppression.

Les nouveaux départements reprennent les étiquettes métier utilisées sur les
fiches salariés. Ils sont créés **sans société** (`company_id = False`) pour
rester utilisables par les 5 sociétés du groupe (un même métier existe chez
MAQUIGNON, SFM, HAIMS et CHATEL).

## Départements créés

| ID | Département   | Étiquette source | Effectif |
|----|---------------|------------------|----------|
| 6  | ATELIER       | ATELIER (6)      | 9        |
| 7  | Chauffeur     | Chauffeur (3)    | 6        |
| 8  | Administratif | Administratif (4)| 4        |
| 9  | CARRIER       | CARRIER (8)      | 5        |
| 10 | TP            | TP (9)           | 3        |
| 11 | Mécanicien    | Mécanicien (10)  | 1        |
| 12 | Apprenti      | Apprenti (11)    | 1        |
| 13 | employé       | employé (7)      | 1        |

Total : 30 salariés actifs affectés sur 33.

Étiquettes non reprises car sans salarié : `CP` (1), `TES` (2),
`Responsable atelier et maintenance` (5). À créer plus tard si besoin.

## Cas particuliers tranchés

- **SEGUIN Simon** portait deux étiquettes (Chauffeur + TP). Un salarié ne peut
  avoir qu'un seul département : classé en **TP**, conformément à son poste
  « Ouvrier qualifié TP ». Ses deux étiquettes sont conservées.
- **MAQUIGNON Christophe** (Responsable de carrière) et **RANGER Mickaël**
  (Agent de production), tous deux CARRIERE D'HAIMS, n'avaient aucune
  étiquette : classés en **CARRIER** d'après leur poste. Leur étiquette reste
  à ajouter côté RH si vous voulez que les deux champs restent cohérents.
- **Christophe MAQUIGNON** avait une seconde fiche salarié créée
  automatiquement sur SAS DISTRI BETON VIENNE le 09/07/2026 (aucune heure,
  aucun congé, aucun pointage dessus). Elle est **archivée** : il ne reste
  que la fiche 490 sur CARRIERE D'HAIMS, département CARRIER. DISTRI BETON
  n'a désormais aucun salarié actif.

## Fiches laissées sans département (volontairement)

Ce sont des fiches techniques, pas des salariés :

- `CHAUFFEUR Transport` (SARL MAQUIGNON) — fiche générique de transport
- `Caisse` (CHATEL'GRANULATS)

## Non fait

Aucun responsable de département (`manager_id`) n'a été renseigné : le manager
d'un département reçoit automatiquement les demandes de congés de son équipe,
ce qui modifierait le circuit de validation actuel (Charlotte via /planning-rh).
À décider avant de l'activer.

## Ordre de priorité utilisé (si plusieurs étiquettes)

`ATELIER > CARRIER > TP > Chauffeur > Mécanicien > Apprenti > Administratif > employé`
