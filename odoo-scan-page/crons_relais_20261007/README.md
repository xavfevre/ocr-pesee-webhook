# Crons Odoo sans code Python (07/10/2026)

Xavier : « remets comme avant [les actions transport] et économise du code sur autre chose ». Les tâches planifiées
maison sont les candidates sûres : aucun effet visible pour les utilisateurs, et l'horaire reste géré par Odoo.

| Action | Cron | Tâche relais | Lignes libérées |
|---|---|---|---|
| 2053 Parc auto : alerte email hebdomadaire des contrôles | 123, hebdo | `parc_controles_hebdo` | 59 |
| 2094 RH : alerte email hebdomadaire CACES / habilitations | 125, hebdo | `caces_hebdo` | 46 |
| 2077 Heures : récap hebdo des récups au bureau | 124, hebdo | `recup_hebdo` | 31 |
| 2049 Fériés France → feuilles d'heures (mensuel) | 122, mensuel | `feries_feuilles_heures` | 42 |

## Mécanique (zéro ligne de code dans Odoo)

1. Modèle manuel `x_relais_tache` « Relais : tâche planifiée » (champs `x_name` = clé, `x_etat`, `x_debut`, `x_fin`,
   `x_resultat`), menu Paramètres > Technique > Relais : tâches planifiées (journal des exécutions).
2. Chaque cron garde son horaire et son utilisateur ; son action passe de « Exécuter du code » à « Créer un
   enregistrement » dans `x_relais_tache` avec la clé en nom (`name_create`, aucun enregistrement actif requis).
3. Automatisation « Relais : tâche planifiée créée » (à la création) → action Webhook `/odoo/tache?token=…`
   (`&host=<hôte>` sur une base de test). Odoo n'attend qu'une seconde : la route répond puis traite dans un thread.
4. `taches_relais.py` exécute la tâche (XML-RPC, mêmes mails et mêmes écritures qu'avant) et écrit `x_etat`
   (en_cours → fait / erreur), `x_debut`, `x_fin`, `x_resultat` (JSON). Clé suffixée `:test` = calcul sans envoi.

Scripts : `crons_relais_setup.py dry | apply | retour | etat | test <clé[:test]>` (env `WEBHOOK_TOKEN`, `ODOO_URL`/`ODOO_DB`
pour une base de test), `patch_relais_taches.py` (route app.py + `_appel_thread` partagé), `test_taches_mock.py`
(faux Odoo : parc, CACES, récup, fériés dont calendrier 2 semaines, point d'entrée). Code d'origine : `action_<id>_code.py`.

Non portés (volontairement) : 1900 « report auto des OT » et 1932 « déblocage OT » (SQL direct pour contourner un bug
d'écriture v19, impossible par RPC), 2116 « CA camion » (créé le jour même par ailleurs), 1673 « Virement CB » (inactif,
47 lignes : à supprimer si vraiment abandonné).
