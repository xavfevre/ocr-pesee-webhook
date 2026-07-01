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

## Étiquette palette — pièces par palette

`label_palette_pieces.xml` (vue héritée `maquignon.label_palette_pieces`, parent
`stock.report_package_barcode` 1827, action 372 *Package Barcode with Contents*).
Affiche les OF de la palette avec le **nombre de pièces** (`4 pcs` ou `3 / 4 pcs`
si réparti) + désignation + dimensions, et l'**emplacement** (`x_studio_zone`).

## Clôture de palette + emplacement (page /scan)

Ajouts dans `scan_view_7890.AFTER.xml` :
- Scan d'un code **`CLOTURE`** (ou bouton « Clôturer & imprimer ») → ouvre le PDF
  du colisage (`/report/pdf/stock.report_package_barcode/<id>`) et libère la palette.
- Scan d'un code **`ZONE-x`** → enregistre l'emplacement dans `stock.package.x_studio_zone`
  (champ manuel créé pour ça).
- `codes_palette.xml` (page **/codes-palette**) : feuille imprimable des codes-barres
  CLÔTURE + Zones A–F (modifiables).

## Rapport « État du colisage » par commande

`report_colisage_commande.xml` (`studio_customization.report_colisage_commande`,
action `ir.actions.report` id 1916, bind sur **project.task**). Bouton *Imprimer →
État du colisage* sur une « Tâche commande pierre ». Liste, par OF de la commande,
les palettes (entières + réparties) avec pièces et emplacement, + totaux.

## Clôture = verrouillage

`stock.package.x_studio_cloturee` (booléen). Au scan de `CLOTURE`, la palette est
imprimée **et verrouillée** : les actions serveur **1585** (scan) et **1914**
(répartition) refusent d'ajouter un OF à une palette clôturée (« 🔒 … est clôturée »).

## Sujet 1 — Palettes sur les lignes de commande

- `sale.order.line.x_studio_palettes` (char, **calculé non stocké**) : liste les
  palettes des OF de la ligne (`PACK001 (4 pcs - A) · PACK002 (3 pcs - B)`).
  Code dans `computed_field_x_studio_palettes.py`.
- `sale_order_line_palettes.xml` (vue héritée `maquignon.sale_order_line_palettes`,
  parent 2614) ajoute la colonne **Palettes** sur les lignes de commande.
- En complément, le rapport PDF `report_colisage_commande.xml` (bind project.task).

## Champs ajoutés (stock.package)

- `x_studio_zone` (char) — emplacement/zone scanné (libellé opérateur).
- `x_studio_cloturee` (booléen) — palette clôturée/verrouillée.

## Emplacements réels + déplacement de stock

- Emplacements internes créés sous « Maq » : **Stock Atelier** et **Stock Usine**
  (`stock.location`, usage interne).
- Action serveur **« Relocaliser palette (emplacement) »** (`server_action_relocate_palette.py`,
  modèle `x_poste_de_scan`, état=code) : à la clôture, mappe `x_studio_zone` →
  `stock.location` (par nom) et fait un **transfert interne réel** de la palette
  vers cet emplacement → l'inventaire Odoo reflète l'emplacement.
- La page `/scan` retrouve l'action par son nom (`RELOC`) et l'exécute juste avant
  de libérer le poste. Si le déplacement échoue, la clôture (impression + verrou)
  est tout de même conservée, avec un avertissement.

## Déploiement multi-bases

`deploy_scan.py` lit `ODOO_URL` / `ODOO_DB` / `ODOO_USER` / `ODOO_PWD` (défaut maquignon).
Déployé sur `maquignon` et la base de test `testmaq2406261629`.
