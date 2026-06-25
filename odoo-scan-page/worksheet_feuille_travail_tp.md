# Feuille de travail TP (worksheet) — 10 photos

## Objet
Feuille de travail spécifique aux tâches du transport portant l'étiquette **TP** (id 1),
permettant d'attacher jusqu'à 10 photos (appareil photo du téléphone).

## Composants (maquignon)
- **worksheet.template** « Feuille de travail TP » (id 4), res_model project.task.
- Modèle technique généré **x_project_task_worksheet_template_4** (model id 2672)
  + 10 champs image `x_studio_photo_1..10` (binary, widget image).
- Vue formulaire **7902** (template_view_Feuille_de_travail_TP) : section
  « 📷 Photos (jusqu'à 10) » avec les 10 champs image.
- Le champ tâche « Modèle Lettre de voiture » = `project.task.worksheet_template_id`.

## Association à l'étiquette TP
- **base.automation 66** « Tâche TP -> Feuille de travail TP » : sur création/écriture
  de `tag_ids`, si le tag TP (id 1) est présent et le worksheet ≠ 4, met
  `worksheet_template_id = 4`.
- Backfill : les 162 tâches TP existantes ont été basculées de « Bon de transport »
  vers « Feuille de travail TP » (réversible : remettre le worksheet « Bon de transport »).

## Utilisation
Sur une tâche TP, bouton **« Feuille de travail »** (en haut) → fiche avec 10 cadres
photo ; sur mobile, taper un cadre ouvre l'appareil photo.
