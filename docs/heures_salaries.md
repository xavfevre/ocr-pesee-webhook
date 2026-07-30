# Heures salariés — saisie web & export paie

## Les pages (vues website Odoo, déployées)
- **`/mes-heures?emp=<id>&t=<token>`** (salariés, toutes sociétés) : accès
  **uniquement par lien personnel signé** (token individuel `x_heures_token`
  sur hr.employee, vérifié aussi côté serveur à chaque sauvegarde) — un
  salarié ne peut pas voir les heures d'un autre. Une carte par jour de la
  semaine pré-remplie avec l'**horaire contractuel du salarié** (son
  `resource.calendar` Odoo, cycles 2 semaines gérés). Boutons : « ✓ Journée
  normale », CP, Maladie, Férié, Absent, Récup — ou saisie fine des 4
  horaires. Totaux de semaine en direct. Bloc **« Demander des congés »**
  (du/au/type/motif) avec suivi du statut de ses demandes.
- **`/heures-admin?k=<clé>`** (Charlotte, protégée par la clé responsables
  `maquignon.rh_admin_key`) : tableau salariés × 7 jours, filtre par société,
  navigation par semaine. Cases cliquables (popup de saisie), **⚡** remplit
  les jours ouvrés vides à l'horaire habituel, **!** signale un jour ouvré
  passé sans saisie, **🔗** copie le lien personnel de chaque salarié (pour
  distribution SMS/WhatsApp). Bouton **⬇ Export paie**.
- **`/planning-rh?k=<clé>`** (responsables) : planning mensuel salariés ×
  jours — heures saisies, CP/maladie/férié/absence/récup en couleurs, jours
  non travaillés grisés, théorique en filigrane sur les jours à venir,
  demandes de congés en attente surlignées en pointillé. Encart de
  **validation des demandes** : ✓ Approuver (inscrit automatiquement les
  jours de congés dans les heures, jours ouvrés du calendrier uniquement)
  ou ✗ Refuser avec motif (visible par le salarié sur sa page).

## Données
- Modèle manuel `x_heures_jour` (unique par salarié+jour) : type de jour,
  4 horaires, heures effectuées, théorique du jour (figé à la saisie), écart.
- Sauvegarde via l'action serveur **2012** (sudo, upsert, calcul du théorique
  depuis le calendrier du salarié — parité des semaines façon Odoo), qui
  exige le token du salarié OU la clé responsables.
- Demandes de congés : modèle `x_demande_conge` (statuts attente/approuvé/
  refusé), actions **2013** (création, token requis) et **2014** (réponse,
  clé requise ; l'approbation génère les jours dans x_heures_jour).
- Les liens personnels et les liens responsables ne sont **jamais commités** :
  fichier de distribution généré à la demande (tokens en base Odoo).

## Export paie (logiciel extérieur)
- Endpoint Render **`/export-heures?mois=YYYY-MM&comp=all|<société>&k=<clé>`**
  (module `export_heures.py`) : un classeur Excel, **un onglet par salarié** —
  récap mensuel (heures, écart, jours CP/maladie/absence/fériés/récup) puis
  blocs hebdomadaires au format du fichier de la comptable (Arrivée/Départ ×2,
  mentions CP/MALADIE/FERIE dans les cases, totaux semaine).
- Clé d'accès stockée uniquement dans Odoo
  (`ir.config_parameter maquignon.heures_export_key`) ; le lien complet est
  généré par la page /heures-admin. **Actif après le prochain merge sur main.**

## Notes
- Les horaires de référence se règlent dans Odoo : fiche employé → Horaires
  de travail. Tout salarié à horaire particulier doit avoir son calendrier.
- Évolutions possibles : jours fériés automatiques, verrouillage du mois après
  export, signature salarié.

## Raccourcis dans le module Présences (30/07)
Menu **Présences → Heures & congés** (déplacé depuis Employés) :
- 🗓 Tableau des heures (web) → /heures-admin (clé incluse dans l'action URL)
- 📅 Planning RH (web) → /planning-rh
- 🔗 Liens salariés (web) → /heures-liens
- ⏰ Horaires par défaut (web) → /heures-horaires
- Saisies des heures → liste x_heures_jour (filtres travail/congés/maladie,
  regroupements, totaux)
- Demandes de congés → liste x_demande_conge (filtre « En attente »)

Sur la **fiche employé** (menu ⚙ Actions, fiche ou liste) :
« 🕐 Ouvrir sa page heures » → ouvre /mes-heures avec le lien signé du salarié
(pratique pour vérifier ou récupérer son lien personnel).

Note : si la clé responsables (`maquignon.rh_admin_key`) est régénérée un
jour, mettre à jour l'URL des deux actions du menu.

## Page de distribution des liens (29/07)
**`/heures-liens?k=<clé>`** (Charlotte) : tous les liens personnels groupés par
société, avec 📋 Copier, 💬 WhatsApp et ✉️ Email pré-rédigés (« voici votre
lien personnel… strictement personnel »), et **♻️ régénération du lien** d'un
salarié (action 2020, clé requise — l'ancien lien devient invalide).
Accessible depuis la barre de /heures-admin. Rend obsolète le fichier texte
de distribution : la page est toujours à jour (nouveaux salariés compris).

## Horaires par défaut — éditeur web (29/07)
**`/heures-horaires?k=<clé>`** (Charlotte) : la semaine type de chaque salarié
en édition directe (matin/après-midi × 7 jours, « Lundi → mar-ven » pour
recopier, total h/sem en direct). À l'enregistrement (action 2021, clé
requise) : création ou mise à jour d'un **calendrier individuel
« Horaire — Nom »** affecté au salarié — jamais de modification d'un
calendrier partagé, donc aucun effet de bord sur les autres salariés.
Les cycles 2 semaines existants sont signalés (l'éditeur enregistre une
semaine simple). Raccourcis depuis /heures-admin et /heures-liens.
