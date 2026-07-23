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

## Saisie manuelle des BL (Céline) — ajouté le 23/07/2026
Les BL fournisseurs étant souvent manuscrits, la saisie se fait par le menu
**Fabrication → Réceptions de blocs (BL)** (modèle `x_bl_bloc`, id 2687) :
- l'en-tête (n° du BL, fournisseur, date, facture, pierre, qualité, prix €/m³,
  emplacement) se saisit une seule fois ;
- les blocs s'enchaînent en lignes (n° carrière + 3 dimensions capables + tonnage) ;
- les infos d'en-tête se recopient automatiquement sur chaque ligne (action 1993 /
  automatisation « BL blocs : propagation en-tête », + héritage à la création via
  l'action 1988), volume et coût calculés ;
- **Imprimer → Fiches blocs (toutes)** (rapport 1995) sort une fiche code-barre
  par bloc, en un seul PDF, à agrafer sur les blocs au parc.
Vérifié avec la facture Francepierre FCM2026X0019 : blocs 22443/22444 → volumes
3,460 / 3,451 m³ et coûts identiques à la facture.

## Scan du bloc à la tablette (TSH2300 / sciage primaire) — ajouté le 23/07/2026
Sur « Ma production », les cartes dont l'opération est un **Sciage Primaire**
(TSH2300, Chauvet, Benetti) portent un bouton **« 🪨 Scanner le bloc »** :
scan du code-barre de la fiche bloc (ou saisie du n° BLC / n° carrière / pierre,
liste des blocs au parc et en sciage filtrable). Action serveur 1996
« Tablette : lier le bloc à l'OF » (résolution BLC → n° carrière → ilike,
refus des blocs au rebut). Une fois lié, le bouton affiche le n° du bloc
(re-cliquable pour changer) et le bloc passe « En sciage » puis « Débité »
avec rendement automatique (automatisation 81).

## Correctif au passage
L'action 1910 « OF terminé quand tous les OT sont faits » terminait aussi les
OF **en cours d'annulation** (OT annulés comptés comme faits → production
fantôme, cf. incident WH/OF/08520). Garde-fou ajouté : ne termine que si tous
les OT sont strictement « done » et aucun annulé. Vérifié : annuler un OF le
laisse bien en « Annulé ».
