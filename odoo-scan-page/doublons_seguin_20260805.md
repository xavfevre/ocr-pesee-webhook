# Doublons « SEGUIN Simon » — investigation et correctif du 05/08/2026

## Constat

10 fiches salarié « Seguin » trouvées dans la base (actives et archivées).
Aucune automatisation ni bug en cause : deux salariées ont, chacune de leur
côté, **cliqué sur « Créer "SEGUIN Simon" »** en remplissant un champ
Chauffeur/Conducteur/Opérateurs sur des rapports de chantier (transport/TP),
au lieu de sélectionner sa fiche existante dans la liste déroulante — un
piège classique d'Odoo quand la recherche met un instant à s'afficher
(réseau de chantier, frappe rapide sur tablette).

- 3 créations en 2025/2026 (compte « Atelier », Céline CERBELLE) — déjà
  archivées, sans dégâts.
- **4 créations par Delphine SPIQUEL le 04/08 entre 07h38 et 07h42**
  (5 rapports de chantier traités à la suite, société CHATEL'GRANULATS).
- **2 créations par Franck MAQUIGNON le même jour à 15h20-15h22**
  (société SARL MAQUIGNON).

## Vérifications avant nettoyage

- Aucun des 9 doublons n'avait d'heure saisie (`x_heures_jour`), de
  pointage (`hr.attendance`), d'allocation ou de congé — tous des calendriers
  génériques par défaut jamais personnalisés. Rien à perdre.
- Un seul doublon (id 693, « SEGUIN Simon\* ») était référencé quelque part :
  6 tâches de livraison/chantier (champs `x_studio_chauffeur` /
  `x_studio_nomchauffeurft`). Les 8 autres n'étaient référencés nulle part.
- Aucun manager/coach de département ne pointait vers un doublon.
- Les contacts (`res.partner`) créés automatiquement avec chaque doublon
  n'étaient référencés nulle part ailleurs — sauf ceux des 2 très anciens
  doublons archivés, qui partageaient déjà le contact de la vraie fiche.

## Nettoyage effectué

1. Les 6 tâches repointées vers la vraie fiche (id 500, société SFM).
2. Les 9 fiches doublons supprimées (`hr.employee.unlink`, qui supprime en
   cascade leur objet « version RH » d'Odoo 19).
3. Les 7 contacts orphelins créés avec elles supprimés.

Résultat : **une seule fiche « SEGUIN Simon »** (id 500), intacte —
horaire personnalisé 38h/sem, lien /mes-heures, département TP, congés,
et ses 48 tâches d'origine + les 6 récupérées = 54 tâches au total.

## Correctif pour éviter que ça se reproduise

Ajout de l'option `no_create` / `no_create_edit` sur les 3 champs par
lesquels les doublons ont été créés :

- `project.task`, vue Studio 4380 : champs `x_studio_chauffeur` (many2one)
  et `x_studio_operateurs` (many2many_tags).
- `x_project_task_worksheet_template_1`, vue Studio 4379 : champ
  `x_studio_conducteur`.

Concrètement : la liste déroulante ne propose plus « Créer "…" » sur ces
trois champs — seule la sélection d'un salarié existant est possible.
Si un nom ne trouve pas de correspondance (faute de frappe, salarié pas
encore créé), le champ reste vide plutôt que de créer une fiche fantôme ;
il faudra alors créer le salarié depuis l'application Employés puis
revenir sur la tâche.

Le champ `x_studio_nomchauffeurft` est un champ miroir toujours masqué
(`invisible="True"`, alimenté automatiquement depuis `x_studio_chauffeur`
par une automatisation) : jamais saisi à la main, pas besoin d'y toucher.

Vérifié : le domaine existant sur `x_studio_chauffeur`
(`category_ids = [3]`, l'étiquette « Chauffeur ») n'est pas restreint par
société — SEGUIN Simon (étiquettes Chauffeur + TP) reste sélectionnable
depuis n'importe quelle société du groupe, comme avant.
