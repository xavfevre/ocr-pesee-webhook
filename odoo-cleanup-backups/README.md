# Backups — Nettoyage du code custom Odoo (2026-06-08)

Sauvegardes des éléments supprimés lors du ménage des customisations Odoo
(vues Studio, champs, actions serveur et automatisations morts / orphelins).
Chaque fichier contient la définition complète des objets supprimés afin de
pouvoir les recréer si besoin.

## Contenu

| Fichier | Éléments sauvegardés |
|---------|----------------------|
| `backup_reliquats_studio.json` | 2 vues Studio reliquats (inactives) : `#4707` product.template, `#5477` res.partner — incluent les xpath sur la chaîne `x_studio_code_sage`. |
| `backup_code_sage_values.json` | 37 valeurs `x_studio_code_sage` sur res.partner (id, nom, code) avant suppression du champ. |
| `backup_orphans.json` | 5 actions serveur (`#1467`, `#1313`, `#1658`, `#1688`, `#1656` Catalogue doublon) + 1 automatisation inerte (`#21`). |
| `backup_fields_view.json` | 4 champs custom orphelins (`#21501`, `#21499`, `#21726`, `#12606`) + 1 vue de rapport morte (`#6678`). |

## Conservés volontairement (non supprimés)

- Action serveur `#1651` (Calcul Eco-contribution REP Tuffeau) — validée OK.
- Champ `sale.order.line.x_studio_worksheet_id` (`#24616`) — dépendance avec `x_project_task_worksheet_template_1.x_studio_marchandise`.
- Rapport actif « Palettisation » (vue `#7045`).
- Catalogue Tarifs (vue `#7050`, report `#1657`, act_url `#1655`) — seul le lanceur doublon `#1656` a été retiré.

## Restauration

Recréer les objets via le mode développeur Odoo ou par RPC, en réutilisant les champs sauvegardés (`name`, `model`, `ttype`, `arch_db`, `code`, etc.).
