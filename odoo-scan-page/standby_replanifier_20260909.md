# Poste « A replanifier (STANDBY) » — 09/09/2026

Poste de travail `mrp.workcenter` id **27**, hors groupes (ni atelier, ni usine…).

## Board machines (`/planning-machines`, vue 7876 `website.planning_machines`)
- Colonne **toujours en 1re position après « À planifier »**, sur tous les boards
  (complet, atelier, usine, primaire, carrière, finition, autres). Variable `m_sb = [27]`,
  groupe `sb` (fond gris `#E2E8F0`, badge « ⏸ Standby — hors planning, invisible des opérateurs »).
- La colonne montre **toutes** les opérations garées dessus, quelle que soit leur date
  (c'est un parking, pas un jour de planning) ; elles ne comptent plus dans « À planifier ».
- Glisser une carte dessus = `write(workcenter_id=27, date_start=jour)` comme pour une machine ;
  la re-glisser sur une machine la replanifie normalement.

## Vue opérateur (`/vue-operateur`, vue 7907 `website.vue_operateur`)
- Le domaine « Ma production » exclut `('workcenter_id','!=',27)` : dès qu'un OT est mis en Standby,
  il **disparaît** de la tablette de l'opérateur (et réapparaît quand il est replanifié).

Sauvegardes avant modification : `live_7876.BEFORE.xml`, `live_7907.BEFORE.xml` (scratchpad du 09/09).
