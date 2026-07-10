# Action facture « Avoir total + OF à refaire »

Action serveur **id 1941** sur `account.move`, liée au menu **⚙ Action**
des factures clients (binding form).

## Ce qu'elle fait (par facture sélectionnée)
1. Contrôles : facture client, validée, non payée (sinon erreur explicite).
2. Crée un **avoir total** via l'assistant `account.move.reversal` puis le **valide**.
3. **Lettre** l'avoir avec la facture (facture → payment_state `reversed`).
4. Remet en production les OF des commandes de `invoice_origin` :
   - `mrp.production` : `done` → `progress` (SQL direct, bug write SaaS)
   - `mrp.workorder` : `done` → `ready`, `qty_produced=0`, `x_studio_nbr_fait=0`
5. Trace dans les logs (`ir.logging`) : facture, avoir(s) créé(s), nb d'OF.

## Limite connue
Les mouvements de stock de la première clôture des OF ne sont pas annulés :
à la re-clôture, contrôler le stock (risque de double comptage → ajustement
d'inventaire si besoin).

## Premier usage réel
FAC/26-27/0354 (3 406,98 €, LEFÈVRE) → avoir RVE/26-27/0011, 40 OF de
S06845 remis en cours, 40 OT « À faire ».
