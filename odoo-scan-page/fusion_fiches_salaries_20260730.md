# Fusion de fiches salariés + remise à zéro des présences (30/07/2026)

## 1. Remise à zéro du suivi du temps (demande utilisateur)
Le badgeage historique était inexploitable : **15 378 présences** réparties sur
~68 fiches dont une majorité de doublons ou de saisies libres (« SEBASTIEN »,
« JULIEN », « GE106 », « SOUS TRAITRANCE », « NIBODAUD CHEARLOTTE »…), avec
des journées comptées deux fois sur des comptes parallèles.

Supprimé (janvier → juillet 2026) :
- `hr.attendance` : 15 378
- `hr.work.entry` : 13 099
- `hr.attendance.overtime.line` : 15 429

**Conservé** : `mrp.workcenter.productivity` (6 400 temps machine sur OT) —
c'est la donnée de production qui alimente les tableaux de bord Fabrication.

Le suivi repart de zéro sur les nouvelles feuilles d'heures (`/mes-heures`).

## 2. Fusion « Chef atelier » → MAQUIGNON Loïc
Le compte partagé « Chef atelier » portait un historique parallèle à celui de
Loïc (243 jours de présence en commun). Après la remise à zéro, transfert de :
1 765 temps machine, 133 + 22 OT, 9 postes de charge, 4 congés, allocations,
CV, évaluation, catégorie. Fiche archivée.

## 3. Fusion doublon SPIQUEL Delphine
Fiche 501 (503 pointages) fusionnée dans la fiche 608 (compte utilisateur) :
2 congés, 3 allocations, 11 feuilles de temps, CV, évaluation, catégorie.
Fiche archivée.

Effectif actif : 44 → **33 fiches** (8 doublons vides archivés + ces 2 fusions).

## 4. Correctif majeur découvert au passage
La validation d'un congé (et tout écrit créant une feuille de temps) échouait
pour **tous les salariés de SARL MAQUIGNON** :
```
Les feuilles de temps doivent être créées avec au moins un compte
analytique actif défini dans le plan 'Project'.
```
**Cause** : le projet interne de SARL MAQUIGNON était « 210 », dont le compte
analytique a été **archivé le 18/12/2025** lors de la réorganisation des plans
analytiques. Les 4 autres sociétés ont un projet « Interne » avec compte actif.

**Correctif** : création d'un compte analytique « Interne » (plan Project,
SARL MAQUIGNON, id 32) + projet « Interne » (id 18, tâches Congés / Réunion /
Formation) et rattachement comme projet interne de la société. C'est la même
erreur que celle rencontrée sur la page des horaires par défaut.
