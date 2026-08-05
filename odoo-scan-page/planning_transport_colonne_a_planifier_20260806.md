# Planning Transport hebdo — colonne « À planifier » par client (06/08/2026)

## Demande

Sur le modèle du planning atelier (`planning_machines_7876.xml`, colonne rouge
« ⚠ À planifier »), ajouter au planning transport hebdomadaire une colonne des
tâches non encore planifiées, **regroupées et mises en évidence par client**.

## Ce qui a été ajouté

Dans `planning_transport_hebdo.xml` (vue Odoo 6671, `website_studio.tache-responsive`) :

- **Nouvelle colonne fixe** en tête de tableau (desktop), largeur 230px,
  fond rouge clair, `rowspan="7"` pour couvrir toute la semaine — comme la
  colonne atelier.
- **Contenu** : toutes les tâches actives du projet « Demande de transport »
  sans `planned_date_begin`, **en excluant** les étapes « Transport Annulé »
  et « TRANSPORT REALISE » (déjà closes, pas de sens à les proposer). Au
  06/08/2026 : **138 tâches, 40 clients**.
- **Groupement par client** : un bloc par client, bordure et bandeau colorés
  (couleur dérivée du nom, palette déjà utilisée pour les chauffeurs — donc
  même client = même couleur d'une session à l'autre), trié par volume de
  tâches en attente décroissant. Les tâches sans client vont dans un bloc
  « Sans client » à part.
- Chaque carte : nom de la tâche, étape, ancienneté (« depuis JJ/MM/AA » —
  certaines dataient d'avril 2025), chauffeur si déjà pré-assigné.
- **Respecte les filtres existants** : si un client ou un chauffeur est
  sélectionné en haut de page, la colonne se limite à son propre backlog.
- **Glisser-déposer fonctionnel** : une carte de cette colonne peut être
  déposée sur n'importe quelle cellule jour × véhicule, exactement comme les
  cartes déjà planifiées. Comme la tâche n'a pas d'heure d'origine, l'heure
  par défaut est **08:00** avec une durée d'1h — à ajuster ensuite si besoin
  depuis la fiche. La page se recharge après la dépose pour que la carte
  s'affiche avec le style complet (chauffeur, statut facturation, photos).

## Non modifié
- La grille jour × véhicule (85 cellules) et les 99 tâches déjà planifiées
  au moment du test — inchangées.
- Le bandeau « Demandes à traiter » en haut de page (liste plate, étape
  « Nouvelle demande » uniquement) — laissé tel quel, il coexiste avec la
  nouvelle colonne qui est plus large (toutes étapes actives sans date).
- La version mobile ne reprend pas cette colonne pour l'instant (le bandeau
  « Demandes à traiter » reste son seul aperçu du backlog) — à ajouter si
  besoin.

## Vérifié
Rendu testé avec session authentifiée (la page nécessite une connexion
interne, non accessible en anonyme) : HTTP 200, aucune trace d'erreur,
colonne présente avec ses 41 blocs (40 clients + « Sans client »), grille
et cartes existantes intactes.

## Complément (06/08/2026) — alignement des deux compteurs

Le bandeau « Demandes à traiter » comptait 69, la nouvelle colonne 51 :
écart de 18 tâches déjà planifiées (jour + véhicule visibles sur la grille)
mais jamais sorties de l'étape « Nouvelle demande ».

- Colonne recentrée sur l'étape « Nouvelle demande » uniquement (au lieu de
  toutes les étapes actives sans date).
- Les 18 tâches déjà planifiées mais bloquées en « Nouvelle demande »
  déplacées vers « In Progress ».
- **Automatisation créée** (id 83, action serveur 2046) : dès qu'une tâche
  du projet « Demande de transport » reçoit une date de planification alors
  qu'elle est encore en « Nouvelle demande », elle passe automatiquement en
  « In Progress ». Les deux compteurs resteront alignés sans intervention
  manuelle.

**Point technique découvert en testant** : sur `project.task`,
`planned_date_begin` est ignoré en écriture s'il n'est pas envoyé **en même
temps** que `date_deadline` (widget de dates couplées) — un `write()` avec
seulement le champ de début est silencieusement sans effet. Le nouveau
glisser-déposer depuis la colonne « À planifier » envoie bien les deux
champs (fin = début + 1h par défaut), donc l'automatisation se déclenche
correctement à chaque dépose.
