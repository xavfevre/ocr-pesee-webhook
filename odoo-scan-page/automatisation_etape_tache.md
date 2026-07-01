# Correctif automatisations « Commande de Pierres » (étapes des tâches)

## Symptôme
Des tâches restaient en **« Nouvelle demande »** alors qu'un **devis** leur était rattaché.

## Cause
L'automatisation **« Commande Pierres : étape selon commande »** (base.automation 60,
sur `sale.order`, `on_create_or_write`) ne se déclenchait que sur changement de
`state`, `delivery_status`, `invoice_status`. Elle **ne réagissait pas** au moment où
un devis est **rattaché à la tâche** (champ `sale.order.x_studio_tache`). Donc un devis
créé/confirmé puis rattaché après coup ne faisait jamais avancer l'étape de la tâche.

## Correctif
1. **Déclencheur** : ajout du champ `x_studio_tache` aux `trigger_field_ids` de
   l'automatisation 60. Désormais, rattacher un devis à une tâche recalcule son étape.
2. **Rattrapage** : recalcul de l'étape de toutes les tâches du projet (déplacement
   uniquement vers l'avant), selon la logique existante :

```
STAGES = [Nouvelle demande, Devis, Commande validée, En fabrication, Prêt à expédier, Expédié, Facturé]
idx = 1 si la tâche a au moins un devis (x_studio_devis_commandes_1)
idx = 2 si un devis est en état 'sale' (confirmé)
idx = 3 si un OF est en cours (confirmed/progress/to_close)
idx = 4 si tous les OF sont terminés (done, aucun ouvert)
idx = 5 si livraison complète (delivery_status == 'full')
idx = 6 si facturé (invoice_status == 'invoiced')
On ne déplace la tâche que si idx > étape actuelle.
```

Appliqué sur **maquignon** et la base de test **testmaq2406261629** (5 tâches corrigées sur chaque).
