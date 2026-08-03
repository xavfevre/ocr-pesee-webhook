# Upgrade Odoo 19.0 → 19.3 — correctifs de pré-migration

## Tentative du 29/07/2026 — ÉCHEC après 7 min 45

**Erreur remontée par l'équipe Upgrade :**
```
odoo.exceptions.UserError:
Cannot insert "Overtime Hours":
Time type "Overtime Hours" of code "OVERTIME" already exists for country "France".
→ en chargeant hr_work_entry/data/hr_work_entry_type_data.xml:1875
   <record id="fr_work_entry_type_overtime" model="hr.work.entry.type">
```

### Diagnostic
La base contient déjà le type d'entrée de temps standard « Overtime Hours »
(id **2**, code `OVERTIME`, pays France, **5 070 entrées de temps rattachées**),
mais **sans identifiant technique (xmlid)** — il a été perdu lors d'une
migration antérieure ou créé manuellement.

En 19.3, `hr_work_entry` déclare ce même enregistrement sous l'identifiant
`hr_work_entry.fr_work_entry_type_overtime`. Le chargeur ne le retrouvant pas,
il tente de le **créer** → violation de la contrainte Python
`_check_code_unicity` (code unique par pays) → arrêt de la migration.

Note : le mécanisme d'appariement automatique de l'upgrade
(`migrations/base/0.0.0/pre-models-match_uniq.py`) sait rattraper les
contraintes SQL, mais pas les contraintes Python `@api.constrains` — d'où
l'échec sur ce cas précis.

### Correctif appliqué (29/07, prod + base de test testmaq2907261453)
Création de l'identifiant technique manquant, pointant sur l'enregistrement
existant :
```
ir.model.data : module=hr_work_entry
                name=fr_work_entry_type_overtime
                model=hr.work.entry.type
                res_id=2
                noupdate=False
```
Vérifié : `check_object_reference('hr_work_entry','fr_work_entry_type_overtime')`
→ `['hr.work.entry.type', 2]`.

**Effet** : lors du prochain upgrade, le chargeur retrouvera l'enregistrement et
fera une **mise à jour** au lieu d'une création. Plus de conflit, et les 5 070
entrées de temps restent rattachées au même type.

**Aucun changement fonctionnel aujourd'hui** : l'enregistrement n'est pas
modifié (nom, code, pays inchangés). Pendant la migration, Odoo l'alignera sur
le standard (`display_code = "OT"`, `is_extra_hours = True`, `color = 4`), ce
qui correspond au comportement d'une base 19.3 neuve. Aucun module de paie
(bulletins) n'est installé — l'impact se limite au marquage des heures
supplémentaires issues des pointages.

### Suite
Relancer une demande d'upgrade de test : elle repartira d'une copie fraîche de
la production, correctif inclus. Le processus s'arrêtant à la **première**
erreur, d'autres conflits du même type peuvent apparaître plus loin — ils se
traitent de la même façon, au cas par cas.

### Contexte à connaître pour les prochains diagnostics
Types d'entrée de temps **sans xmlid** dans la base (candidats à un conflit
futur si 19.3 déclare le même code) :

| id | nom | code | pays |
|----|-----|------|------|
| 1 | Attendance | WORK100 | — |
| 2 | Overtime Hours | OVERTIME | France ← **corrigé** |
| 4 | Compensatory Time Off | LEAVE105 | — |
| 7 | Sick Time Off | LEAVE110 | — |
| 8 | Paid Time Off | LEAVE120 | — |
| 9 | Absence justifiée | ABS J | — |
| 10 | Absences injustifiée | ABS NON J | France |
| 11 | Nombre d'heures à récupérer | A RECUP | France |
| 12 | Nombre d'heures récupérées | RECUP | — |
| 13 | Heures supplémentaires | HS 50% | France |
| 14 | Generic Time Off | LEAVE100 | — |
| 15 | Home Working | WORK110 | — |
| 16 | Unpaid | LEAVE90 | — |

Les codes personnalisés (ABS J, ABS NON J, A RECUP, RECUP, HS 50%) ne
correspondent à aucune donnée standard Odoo : pas de risque de collision. Les
codes génériques (WORK100, LEAVE1xx…) ont été franchis sans erreur lors de la
tentative du 29/07.
