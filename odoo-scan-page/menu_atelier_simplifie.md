# Menu « Atelier simplifié » (module Fabrication)

Sous-menu ajouté en tête du module Fabrication (menu racine id 729),
visible par tous les utilisateurs internes (aucun groupe restrictif).

| Menu (ir.ui.menu) | id | Action (ir.actions.act_url) | URL |
|---|---|---|---|
| Atelier simplifié (parent) | 1039 | — | — |
| ✅ Ma production | 1040 | Ma production (atelier) | /vue-operateur |
| 🕘 Historique | 1041 | Historique atelier | /vue-operateur?hist=1 |
| 📦 Poste de scan | 1042 | Poste de scan (atelier) | /scan |

Les actions sont de type URL (`target: self`) : elles ouvrent les pages
web opérateur (vue 7907 `website.vue_operateur` et vue 7890 `/scan`).
Le nom d'opérateur mémorisé sur la tablette (localStorage) est restauré
automatiquement à l'ouverture de « Ma production ».

Créé via JSON-RPC (voir scratchpad add_menu.py). Pour supprimer :
Réglages → Technique → Menus.
