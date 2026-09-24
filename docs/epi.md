# EPI — remise aux salariés et stock (24/09/2026)

Demande de Xavier : suivre le stock des EPI et la consommation par salarié. La secrétaire de
l'accueil distribue les EPI, pas de signature, pas de règle de dotation. Deux articles existaient
(chaussures Defender, bottes fourrées), le reste est ajouté par l'entreprise.

## Odoo (script `odoo-scan-page/epi_20260924/epi_setup.py`)
- Catégorie d'articles **EPI** (81, sous All). Un EPI = un article de cette catégorie avec
  « Suivre le stock » coché, achat seulement ; tailles en variantes (attribut **Pointure** 38→47
  créé et posé sur les deux chaussures → 10 variantes chacune). Valorisation périodique, coût
  standard (pas d'écriture comptable).
- Emplacements : **Maq/Stock EPI** (116, interne, accueil) et **EPI remis aux salariés** (117,
  virtuel, usage inventaire = consommation).
- Types d'opération : **Réception EPI** (57, `WH/EPIIN/`, Fournisseurs → Stock EPI) et
  **Dotation EPI** (58, `WH/EPI/`, Stock EPI → remis).
- Champs : `stock.picking.x_employee_id`, `stock.move.x_employee_id` (Salarié, copiés),
  `hr.employee.x_epi_move_ids` (one2many). Vues : Salarié sur le transfert (8007, visible pour les
  deux types EPI), onglet **EPI** sur la fiche salarié (8008).
- Paramètres `maquignon.epi_categ / epi_loc_stock / epi_loc_conso / epi_pt_dot / epi_pt_rec`
  (ids) et **`maquignon.epi_key`** (clé de la page, jamais dans le dépôt).

## Page `/epi?k=<clé>` (vue `website.epi` 8009, website.page 93, `epi_page.py`)
Sans compte Odoo, sur PC ou téléphone : **Remettre un EPI** (salarié, EPI avec stock, quantité,
date, note), **Entrée en stock**, **Stock EPI** (rupture en rouge, ≤ 2 en orange, valeur), **Dernières
remises** avec ↩ annuler, **Consommation par salarié** par année (quantités, détail, coût), filtre
par nom. Aide intégrée : créer un nouvel EPI dans la catégorie EPI.

## Relais Render (`web_actions.py`, autorisées dans `app.py`)
- **2110** remise : contrôle clé, salarié actif, article EPI suivi en stock, quantité 1–200, date
  ≤ aujourd'hui ; refus `STOCK|…` si stock insuffisant (la page propose « remettre quand même »,
  `force=1`) ; transfert Dotation EPI validé (mouvement `quantity`/`picked`, `button_validate`
  sans assistants), salarié sur le transfert et le mouvement, antidatage des mouvements.
- **2111** entrée en stock : transfert Réception EPI validé.
- **2112** annulation : mouvement inverse (remis → Stock EPI), origine `Annulation WH/EPI/…`,
  refus si déjà annulée. La page barre la remise annulée.
- Odoo 19 : `stock.move` n'a plus de champ `name` → `description_picking`.

Tests (`test_epi.py`, article « TEST EPI (à archiver) » archivé ensuite) : clé fausse refusée,
remise sans stock refusée, réception 2, remise 1 à Théo, remise 3 refusée puis forcée (stock −2),
annulation puis double annulation refusée, onglet EPI de la fiche salarié alimenté.

## Code-barres tapé et fiche procédure (24/09, suite)
- La secrétaire n'a pas de douchette : champ **Code-barres** (saisie clavier + Entrée) dans les blocs Remise et
  Entrée en stock, qui sélectionne l'EPI (`data-barcode` sur les options, `product.product.barcode`) ; code inconnu
  = message. Pour un EPI à tailles, le code-barres se saisit sur **chaque variante** (le champ n'apparaît pas sur
  la fiche modèle quand il y a des variantes).
- **`docs/procedure_epi.pdf`** (5 pages, `docs/build_procedure_epi.py`, captures `docs/captures_epi/`, lien de la
  page passé en argument : la copie du dépôt ne contient pas la clé). Copie avec le lien complet :
  `Desktop/Maquignon/Procedure_EPI.pdf`.

## Fournisseurs, stock mini et demandes de prix (24/09, suite)
- **Stock mini / maxi** : colonnes Mini / Maxi dans le tableau Stock EPI de la page, saisies directement
  (action **2113** : règle de réapprovisionnement `stock.warehouse.orderpoint` sur Maq/Stock EPI, déclenchement
  manuel ; mini = maxi = 0 supprime la règle). Rouge = rupture ou sous le mini, orange = au mini.
- **Fournisseurs** : lignes fournisseur de la fiche article (`product.supplierinfo`, onglet Achats), affichées
  dans la colonne Fournisseurs ; « aucun » en orange s'il n'y en a pas.
- **Demandes de prix** (action **2114**, bouton 🛒) : pour chaque EPI sous son mini, une demande de prix
  brouillon **par fournisseur référencé** (quantité = maxi − stock, au moins la quantité mini du fournisseur, prix
  et référence fournisseur repris), origine `EPI stock mini`, type d'opération **Réception EPI** (la réception
  validée dans Odoo entre directement dans Stock EPI). `apercu=1` = calcul seul (la page confirme avant de créer).
  Un nouveau passage met à jour la demande brouillon existante du fournisseur (pas de doublon). Les EPI sans
  fournisseur sont listés. Liste des demandes en cours (brouillon / envoyée / à approuver / commandée) sous le bouton.
- Fiche procédure : section 8 (bureau) ajoutée, PDF 6 pages.
Testé (`test_epi_achats.py`, fournisseur de test archivé ensuite) : règles 2/4 et 1/1, refus d'un mini négatif,
aperçu, création P00120 (2 lignes, 59,90 €, Réception EPI), 2e passage = mise à jour, suppression de règle.
