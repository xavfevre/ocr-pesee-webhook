# Registre des blocs de pierre (x_bloc)

Modèle Odoo manuel `x_bloc` (menu **Fabrication → Blocs de pierre**), créé le 23/07/2026.

## Principe
- **Les dimensions facturées par le fournisseur = les dimensions capables** (toisé marchand,
  volume exploitable). Le brut physique est optionnel, à titre indicatif.
- Numérotation automatique `BLC-00001…` (séquence `x.bloc`) + n° carrière/fournisseur
  quand il existe (Rocamat « SI A 6672 », Francepierre « 22443 »…).
- Coût matière = prix €/m³ × volume capable (auto).
- Chaque **OF de tranches** porte un champ `x_studio_bloc` : le rendement matière du bloc
  (m³ de tranches produits ÷ volume capable) et son statut (parc → sciage → débité)
  se recalculent automatiquement quand les OF liés changent.

## Objets Odoo
- Modèle 2685 `x_bloc`, accès complet groupe utilisateurs internes.
- Actions serveur 1988 (création : numéro+calculs), 1989 (recalculs), 1990 (rendement depuis OF)
  · automatisations 79/80/81.
- Vues list/form/search + action 1991 + menu 1048 (Fabrication).
- Rapport 1992 `maquignon.report_fiche_bloc` (fiche A4 avec code-barre, menu Imprimer).

## À suivre (phase 2)
- Tablette TSH2300 : scanner le code-barre du bloc au démarrage du sciage pour lier l'OF.
- OCR des factures fournisseurs de blocs pour créer les fiches automatiquement.
- Tableau de bord « Rendement blocs » (par pierre, par fournisseur).
