# Backups — Nettoyage du code custom Odoo (2026-06-08)

Sauvegardes des éléments supprimés lors du ménage des customisations Odoo
(vues Studio, champs, actions serveur et automatisations morts / orphelins).
Chaque fichier contient la définition complète des objets supprimés afin de
pouvoir les recréer si besoin.

## Contenu

| Fichier | Éléments sauvegardés | Format |
|---------|----------------------|--------|
| `backup_code_sage_values.json` | 37 valeurs `x_studio_code_sage` sur res.partner (id, nom, code). | JSON lisible |
| `backup_fields_view.json` | 4 champs custom orphelins (`#21501`, `#21499`, `#21726`, `#12606`) + 1 vue de rapport morte (`#6678`). | JSON lisible |
| `backup_orphans.json.b64` | 5 actions serveur (`#1467`, `#1313`, `#1658`, `#1688`, `#1656` Catalogue doublon) + 1 automatisation inerte (`#21`). | base64 |
| `backup_reliquats_studio.b64.part00..02` | 2 vues Studio reliquats (`#4707` product.template, `#5477` res.partner) avec les xpath de la chaîne `x_studio_code_sage`. | base64 en 3 parts |

> Les fichiers contenant du code Python / XML sont stockés en **base64** pour
> garantir une fidélité 100 % (évite tout problème d'échappement). Intégrité
> vérifiée par sha256 après upload.

## Décodage

```bash
# Actions serveur + automatisation
base64 -d backup_orphans.json.b64 > backup_orphans.json

# Vues Studio reliquats (réassembler les 3 parts puis décoder)
cat backup_reliquats_studio.b64.part* | base64 -d > backup_reliquats_studio.json
```

sha256 attendu après décodage :
- `backup_orphans.json` : `5fcf309da2a2a1da50c8f7926cc05e6a30b1fdd67d9f12f6baad5e179d3a28ae`
- `backup_reliquats_studio.json` : `6c6e2b6d86ae91642520fd88b5a3ed0bc8a1f8180f0418faf01f6b3128fbd97e`

## Conservés volontairement (non supprimés)

- Action serveur `#1651` (Calcul Eco-contribution REP Tuffeau) — validée OK.
- Champ `sale.order.line.x_studio_worksheet_id` (`#24616`) — dépendance avec `x_project_task_worksheet_template_1.x_studio_marchandise`.
- Rapport actif « Palettisation » (vue `#7045`).
- Catalogue Tarifs (vue `#7050`, report `#1657`, act_url `#1655`) — seul le lanceur doublon `#1656` a été retiré.

## Restauration

Recréer les objets via le mode développeur Odoo ou par RPC, en réutilisant les
champs sauvegardés (`name`, `model`, `ttype`, `arch_db`, `code`, etc.).
