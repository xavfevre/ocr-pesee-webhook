# Heures salariés — saisie web & export paie

## Les deux pages (vues website Odoo, déployées)
- **`/mes-heures`** (salariés, toutes sociétés) : sélecteur au premier accès
  (mémorisé sur l'appareil), une carte par jour de la semaine pré-remplie avec
  l'**horaire contractuel du salarié** (son `resource.calendar` Odoo, cycles
  2 semaines gérés). Boutons : « ✓ Journée normale », CP, Maladie, Férié,
  Absent, Récup — ou saisie fine des 4 horaires (matin/après-midi).
  Totaux de semaine (effectué / théorique / écart) en direct.
- **`/heures-admin`** (Charlotte) : tableau salariés × 7 jours, filtre par
  société, navigation par semaine. Cases cliquables (popup de saisie),
  **⚡** remplit les jours ouvrés vides d'une ligne à l'horaire habituel,
  **!** signale un jour ouvré passé sans saisie. Totaux et écart par salarié.
  Bouton **⬇ Export paie**.

## Données
- Modèle manuel `x_heures_jour` (unique par salarié+jour) : type de jour,
  4 horaires, heures effectuées, théorique du jour (figé à la saisie), écart.
- Sauvegarde via l'action serveur **2012** (sudo, upsert, calcul du théorique
  depuis le calendrier du salarié — parité des semaines façon Odoo).

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
