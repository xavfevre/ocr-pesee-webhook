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
