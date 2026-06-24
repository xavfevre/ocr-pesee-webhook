# Poste de scan `/scan` — répartition par palette (pop-up quantité)

Page web Odoo **`website.poste_scan`** (vue `ir.ui.view` id **7890**, URL `/scan`).
Interface tablette pour ranger des OF terminés dans des colis/palettes (douchette).

## Changement de cette livraison

**Problème :** scanner un OF le posait toujours **en entier** sur la palette.
Pour n'en mettre qu'une partie, il fallait **taper le code OF à la main** dans un
panneau séparé — inutilisable avec une douchette → en pratique la répartition ne
servait jamais.

**Correctif :** la répartition est maintenant **intégrée au scan**.
Quand on scanne un OF à plusieurs pièces (colis actif, OF terminé), une **fenêtre
(pop-up) avec pavé numérique tactile** demande *« Combien sur cette palette ? »* :

- On tape le nombre (ex. `11`) → **11 pcs sur cette palette**, le reste reste à placer.
- On **scanne la suite** sans rien taper → l'OF en cours part **au maximum** (tout).
- La saisie est **plafonnée** au nombre de pièces restant.
- **Même numéro d'OF** partout : la quantité par palette est stockée dans
  `x_repartition_palette` (pas de 2ᵉ OF créé). Un OF posé en entier passe par le
  placement réel du stock (action serveur 1585) ; un OF réparti crée des lignes
  `x_repartition_palette` (action serveur 1914).

Aucune action serveur n'a été modifiée — tout le changement est dans le HTML/JS de
la vue 7890. Le panneau manuel « Répartir » a été retiré (remplacé par le pop-up).

## Fichiers

- `scan_view_7890.BEFORE.xml` — vue avant le correctif (sauvegarde de restauration).
- `scan_view_7890.AFTER.xml`  — vue déployée (état actuel en prod).
- `deploy_scan.py` — script de déploiement XML-RPC (identifiants retirés : `<USER>` / `<MDP>`).

## Restaurer l'ancienne version

Réécrire `arch` de la vue 7890 avec le contenu de `scan_view_7890.BEFORE.xml`.

## Reste à faire (Phase 2)

Adapter l'**étiquette** et le **rapport OF** pour afficher la **quantité de la
palette** (lire `x_repartition_palette` pour les OF répartis).
