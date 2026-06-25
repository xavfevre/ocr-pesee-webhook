# Capacité machines « artificielle » (calendrier 24 h)

## But
Éviter qu'Odoo étale la planification d'une commande sur plusieurs jours
(quand la charge dépasse les heures/jour réelles de la machine).

## Mise en place (maquignon)
- Nouveau calendrier `resource.calendar` **« Machines — capacité étendue (24h planning) »** (id 24) :
  lundi→vendredi, 00:00–24:00 (24 h/jour). `hours_per_day = 24`.
- Affecté à **toutes les machines** (`mrp.workcenter`, société 1, 16 postes)
  via `resource_calendar_id`. Le calendrier RH partagé « Standard 35 heures » (id 1)
  n'est PAS modifié.

## Effet vérifié
Replanification de 20 OF de S07280 → tous retombent sur le **même jour** (25/06)
au lieu d'être étalés.

## Important
- C'est **artificiel** : le board n'affiche plus la capacité réelle, tout s'empile
  sur le jour de départ.
- Les OF **déjà planifiés** gardent leurs anciennes dates : il faut **recliquer
  « Planifier »** (ou replanifier) pour les ré-empiler sur un jour.
- Une charge > 24 h sur un seul jour déborde quand même sur le jour ouvré suivant.

## Réversibilité
Sauvegarde des calendriers d'origine dans `_backup_workcenter_calendars.json`
(toutes les machines étaient sur le calendrier 1). Pour revenir en arrière :
remettre `resource_calendar_id = 1` sur tous les `mrp.workcenter` société 1.
