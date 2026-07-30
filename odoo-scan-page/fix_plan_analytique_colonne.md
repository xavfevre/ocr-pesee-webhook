# Création de société impossible — colonne de plan analytique manquante (30/07/2026)

## Symptôme
À l'enregistrement d'une nouvelle société :
```
ValueError: Invalid field account.analytic.line.x_plan9_id
in condition ('x_plan9_id', 'in', OrderedSet([26]))
→ analytic/models/analytic_account.py, _check_company_consistency
```
La création d'une société génère automatiquement un projet interne, donc un
compte analytique, dont le contrôle de cohérence interroge **toutes** les
colonnes de plans analytiques des lignes analytiques.

## Cause
Odoo matérialise chaque plan analytique racine par une colonne
`x_plan<id>_id` sur `account.analytic.line`. Les plans 2 à 9 ont été créés le
18/12/2025, mais seules les colonnes `x_plan2_id` → `x_plan8_id` existaient :
celle du plan **9 « Section d'attente »** manquait (création interrompue à
l'époque). Toute opération construisant un domaine sur l'ensemble des plans
— dont la création de société — échouait donc.

## Correctif
Exécution de la méthode native de synchronisation sur tous les plans :
```python
env['account.analytic.plan'].sudo().search([])._sync_all_plan_column()
```
→ colonne `x_plan9_id` (« Section d'attente ») créée, les 8 colonnes
correspondent désormais aux 8 plans.

Vérifié : création d'une société de test réussie dans une transaction annulée
(aucune société parasite créée). Ce correctif est structurel, il ne se
reproduira pas pour les plans existants.

**À savoir** : si un nouveau plan analytique est créé un jour et que sa colonne
manque à nouveau (interruption réseau à la création), relancer la même
commande depuis une action serveur.
