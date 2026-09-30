# Saisie des lignes de devis : allègements du 30/09/2026 (prod)

Mesures sur la base de test (devis S07275, 580 lignes, colonnes pierre affichées) : ajouter une ligne 9,7 s -> 1,3 s,
ouverture 12 s -> 4 s avec 30 lignes par page. Cause navigateur : le widget produit (sol_product_many2one) garde une
zone de description cachée par ligne affichée, redimensionnée à chaque rafraîchissement (productAndLabelResizeTextArea).
Remplacer le widget casse l'affichage des sections -> écarté. Côté serveur, chaque saisie de dimension déclenche un
onchange de 1,7 à 2,7 s sur 580 lignes ; la colonne Palettes (calcul non stocké, 2 recherches par ligne) en coûtait 0,5 s.

1. vue 8011 « sale.order.form - lignes par page » : limit 30 (était 60) — vue_8011_lignes_par_page.xml
2. champ calculé sale.order.line.x_studio_palettes : calcul groupé (2 recherches pour toutes les lignes), résultat
   identique sur 42 lignes échantillon — x_studio_palettes_compute_avant.py / _apres.py
3. automatisation 96 « Calcul Poids depuis Volume (serveur) » (on_create_or_write : product_id, nbr, long, larg, epais) :
   poids = Vol. Total x Poids au m3 aussi pour les lignes importées ; l'automatisation 10 (on_change) reste active pour
   l'affichage immédiat — automation_calcul_poids_serveur.json
