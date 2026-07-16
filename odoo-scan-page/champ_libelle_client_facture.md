# Libellé Client sur les lignes de facture — éditable (16/07/2026)

Problème : `x_studio_libell_client` (account.move.line, champ 23900) était un
champ *related* non stocké via `sale_line_ids` (x2many) → structurellement non
modifiable, et la colonne de la vue facture (4961) portait `readonly="True"`.

Correctifs :
- champ converti en **texte stocké éditable** (related supprimé, store=True) ;
- **reprise** des valeurs existantes depuis les lignes de commande (SQL,
  1re ligne de vente liée) ;
- **automatisation 72** « Facture : libellé client depuis la commande »
  (on_create account.move.line) : pré-remplit depuis la ligne de commande ;
- vue 4961 : `readonly="True"` → `force_save="1"` (éditable, y compris sur
  facture validée — écriture vérifiée).

Le rapport « Facture - persos Maquignon (robuste) » (7867) imprime ce champ :
inchangé, il affiche désormais la valeur propre à la facture.
