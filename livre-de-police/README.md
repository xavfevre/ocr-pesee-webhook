# Livre de police décharge (ISDI) + DAP — Carrière d'Haims

Génère chaque mois, à partir du relevé du pont bascule (`Factures_MM.YYYY.xlsx`) :

- **Livre_de_police_<mois>.xlsx**
  - *Livre de police* : registre des déchets entrants (n° ordre, date, n° pesée,
    code déchet européen, désignation, code interne TP86170504…, tonnage,
    producteur, chantier, transporteur, immatriculation, n° DAP, n° facture,
    contrôle visuel). Lignes surlignées jaune = DAP à créer. Menu déroulant des
    24 codes de la grille d'identification sur la colonne Code interne.
  - *DAP à créer* : une ligne par couple producteur+chantier+code sans DAP,
    avec un n° proposé (suite de la numérotation existante).
  - *Contrôle* : réceptions du relevé (Feuil1) absentes du livre (Feuil2), à
    vérifier (souvent internes / hors décharge).
  - *Référentiel codes* : les 24 codes TP/BAT/COL/PART × 86/37 × code déchet.
- **DAP_a_signer_<mois>.pdf** : un formulaire DAP pré-rempli par DAP manquante
  (producteur, chantier, code, tonnage, transporteurs, attestation, signatures).

## Utilisation mensuelle
```
python generate_livre_police.py Factures_04.2026.xlsx
```
Prérequis : `pip install openpyxl reportlab`.

Le fichier source doit garder sa structure : Feuil1 = blocs par client avec n°
de facture en colonne A ; Feuil2 = pesées RECEPTION avec colonnes Code et DAP.

## Version intégrée Odoo (juillet 2026)

Menu racine **« Décharge Haims »** dans Odoo :
- **Entrées décharge** (`x_livre_police`) : saisie directe en liste éditable,
  ou **import du fichier bascule** (Favoris → Importer des enregistrements —
  les libellés de champs = les colonnes du relevé, mapping quasi automatique).
  Filtres « Sans DAP », « Sans code », par mois ; regroupements client/code/DAP ;
  édition en masse (multi-sélection) pour codifier vite.
- **DAP** (`x_dap`) : registre des acceptations préalables.
- Menu ⚙ Action sur les entrées : **Générer DAP manquantes** (action 1945,
  regroupe par producteur+chantier+code, numérote à la suite).
- 🖨 Imprimer : **Livre de police** (PDF paysage, trié, totaux — rapport 1946)
  sur les entrées sélectionnées ; **Formulaire DAP** (rapport 1947) sur les DAP.

Champs calculés : tonnage (net/1000), code déchet européen et désignation
dérivés du code interne (sélection des 24 codes de la grille).

Mars 2026 importé : 106 pesées, 16 DAP. Scripts de mise en place :
`dech_models.py`, `dech_views.py`, `dech_reports.py`, `dech_import.py`.
