# Planning Transport — nouvelle vue jour (06/08/2026)

## Demande

« Peux-tu faire une vue jour sur ce planning, je te laisse ajouter les
détails qui te semblent pertinents » (sur `/model/tache`, la vue semaine),
puis complément : « avec des filtres en vignette des clients du jour ».

## Ce qui a été créé

**Nouvelle page `/planning-transport-jour?day=YYYY-MM-DD`** (par défaut :
aujourd'hui), deux vues Odoo :
- `website.planning_transport_jour` (id 7967) — page principale.
- `website.ptj_task_card` (id 7966) — sous-gabarit de carte tâche, appelé
  en `t-call` (même principe que `website.planning_machine_card` du
  planning atelier).
- Route déclarée via `website.page` (id 88).

### Colonnes
Une colonne par véhicule utilisé ce jour-là (+ « VÉHICULE NON ASSIGNÉ »),
plus la colonne **« ⚠ À planifier »** groupée par client (même mécanique
que celle ajoutée sur la vue semaine — étape « Nouvelle demande », glisser-
déposer sur n'importe quel véhicule pour planifier direct sur ce jour).

### Détails ajoutés, jugés pertinents pour une vue à la journée
Avec beaucoup plus de place que dans la grille semaine (cellules de 120px),
chaque carte affiche en entier : nom de la tâche, statut facturation
(badge coloré), chauffeur, horaire début→fin, **durée estimée en heures**
(nouveau — absent de la vue semaine), étiquettes, et les liens photos/BC
existants (bon de pesée, prise en charge, livraison, bon de commande).

- **En-tête de chaque colonne véhicule** : nombre de tâches, plage horaire
  (première heure de départ → dernière heure de fin), total d'heures
  estimées du véhicule ce jour-là.
- **Bandeau chauffeurs du jour** : une vignette par chauffeur avec son
  nombre de tâches et ses heures totales — vue d'ensemble de la charge de
  chacun en un coup d'œil, difficile à lire sur 7 jours en même temps.
- **Vignettes clients du jour** (ajout demandé) : une pastille colorée par
  client présent ce jour, avec son nombre de tâches ; clic pour
  masquer/afficher ses tâches sur la grille (boutons Tout/Aucun), couleur
  cohérente avec celle utilisée sur les cartes (bordure gauche colorée) et
  avec la colonne « À planifier ». Filtre uniquement les tâches déjà
  planifiées ; la colonne « À planifier » reste toujours visible en entier.
- Sélecteur de date directe (`<input type="date">`) en plus des flèches
  préc./suiv./aujourd'hui.
- Glisser-déposer identique à la vue semaine (heure conservée en cas de
  déplacement entre véhicules, ou 08:00 + 1h par défaut depuis le backlog).

### Navigation croisée
- Vue semaine → bouton **« 📆 Vue jour »**, et chaque case « Jour » de la
  grille est maintenant cliquable vers le détail de ce jour précis.
- Vue mois → bouton **« 📆 Vue jour »**, et chaque numéro de jour du
  calendrier est cliquable vers le détail de ce jour.
- Vue jour → boutons retour vers la vue semaine et la vue mois.

## Vérifié
Rendu testé avec session authentifiée sur plusieurs cas : jour chargé
(28 tâches), jour vide (0 tâche, pas d'erreur), filtre client actif,
chargement par défaut (aujourd'hui). Aucune trace d'erreur sur les 3 pages
après les changements de navigation croisée.
