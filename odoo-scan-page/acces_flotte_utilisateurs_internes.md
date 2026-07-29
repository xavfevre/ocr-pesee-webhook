# Accès flotte pour les utilisateurs internes (correctif duplication tâches transport)

**Symptôme** : « Erreur d'accès — Véhicule (fleet.vehicle) » quand un utilisateur
sans droit Parc automobile duplique une tâche de transport (ex. Céline CERBELLE,
tâches VEOLIA). Persistait après le passage en `sudo()` des actions 1523/1524.

**Diagnostic** (reproduction serveur avec `with_user(12)` + bissection) :
1. `copy_data()` passe, c'est le `create()` qui bloque, et uniquement si
   `x_vehicle_id` est présent dans les valeurs copiées.
2. Première barrière : ACL — `fleet.vehicle` n'était lisible que par les groupes
   Fleet et « Employees / Officer ».
3. Deuxième barrière (la cause du blocage persistant) : **règle
   d'enregistrement standard** « Hr Officer read rights on vehicle with
   employees assigned » — Céline étant Officier RH, elle ne voyait que les
   véhicules **avec conducteur affecté** (2 sur 66). Le Scania GE-106-QS n'en a
   pas → lecture refusée pendant la chaîne de création.

**Correctif appliqué en production (base maquignon)** :
- ACL lecture seule pour le groupe *Internal User* (base.group_user) sur :
  - `fleet.vehicle` (id 2211)
  - `fleet.vehicle.model` (id 2212)
  - `fleet.vehicle.model.brand` (id 2213)
  - `fleet.vehicle.odometer` (id 2214)
- Règle d'enregistrement id 684 « Véhicules : lecture pour tous les
  utilisateurs internes (multi-société) », groupe base.group_user,
  domaine `[('company_id', 'in', company_ids + [False])]`, lecture seule.
- (Défense en profondeur, déjà en place : `sudo()` sur les accès flotte des
  actions serveur 1523 — liaison véhicule — et 1524 — garde-fou odomètre.)

**Effet** : tous les utilisateurs internes peuvent lire les véhicules de leurs
sociétés autorisées (aucun droit d'écriture ajouté, menus Parc inchangés).
Vérifié par reproduction : `copy()` d'une tâche VEOLIA avec les droits de
Céline → OK.
