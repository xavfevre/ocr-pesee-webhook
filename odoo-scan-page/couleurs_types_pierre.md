# Couleurs des types de pierre dans le board fabrication

## Avant
Les couleurs étaient codées en dur dans le template (6 types). Tout nouveau type
s'affichait en gris.

## Maintenant (dynamique)
- Champ **`product.category.x_studio_couleur_hex`** (char, ex. `#670066`).
- Rempli en **extrayant la couleur moyenne de l'image du produit** de chaque type
  (les images produits sont des aplats de couleur, une par type de pierre).
  Script : voir setcolors2.py (Pillow, couleur moyenne de image_128).
- Le board (`website.planning_machine_card`, vue 7874) lit
  `of.x_studio_catgorie.x_studio_couleur_hex` (repli : ancien dictionnaire, puis gris).
- **Couleur du texte automatique** (clair/foncé selon la luminosité de la couleur).

## Couleurs posées
HAIMS #26CE38 · MIGNE #F3B353 · RICHEMONT #11F6E3 · SIREUIL #FEE829 ·
TERVOUX #F617F6 · TUFFEAU #58A2F0 · TUFFEAU(U) #3333FF · THENAC #670066
(VASSENS : pas encore de produit avec image → gris)

## Nouveau type plus tard
Tant qu'il n'y a pas de recalcul, un nouveau type reste gris. Pour automatiser,
prévoir un CRON quotidien qui réextrait la couleur depuis l'image (PIL dispo côté
Odoo) — non encore mis en place.

## Automatisation (au lieu d'un cron)
Un CRON ne peut PAS extraire la couleur d'une image : les actions serveur Odoo
**interdisent `import`** (donc pas de Pillow). À la place, le board a un **repli
image** : si un type n'a pas encore de couleur enregistrée (`x_studio_couleur_hex`
vide), la carte utilise **directement l'image du produit** comme fond
(`/web/image/product.product/<id>/image_128`). Résultat : la couleur d'un nouveau
type apparaît **immédiatement**, sans cron ni intervention. Les types déjà
renseignés gardent la couleur CSS (plus léger + texte clair/foncé auto).
Optionnel : relancer setcolors2.py pour "figer" la couleur d'un nouveau type dans
le champ (look plus propre), mais l'affichage est déjà automatique.
