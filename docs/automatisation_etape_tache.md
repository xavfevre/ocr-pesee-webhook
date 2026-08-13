
# Cron des automatisations : panne récurrente corrigée (13/08)

OdooBot désactivait régulièrement le cron « Automation Rules: check and
execute » (30) après 5 échecs (22/07, 29/07, 12/08). Diagnostic par
isolation des 2 règles planifiées : la fautive était **« Note
Autoliquidation »** (règle 52, action 1644) — une action « Créer un
enregistrement » qui tentait de créer une ligne de commande nommée
« TVA » **sans article** (interdit en v19). Elle n'a jamais fonctionné et
plantait le cron dès qu'une commande « TP autoliquidée » récente
existait, bloquant au passage l'autre règle (« Passage aux mines »).

Correctif : action 1644 convertie en **code** — ajoute une **note**
(`display_type = line_note`) « TVA autoliquidée par le preneur — article
283, 2 nonies du CGI (sous-traitance BTP) », idempotente (pas de
doublon). Après relance : cron actif, compteur d'échecs à 0, **41 notes**
posées sur le rattrapage des commandes TP autoliquidée (dont d'anciennes
— sans effet sur la facturation, une note ne se facture pas), aucun email
parasite. Le libellé de la mention légale est ajustable dans l'action.
