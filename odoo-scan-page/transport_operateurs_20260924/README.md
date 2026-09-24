# Tâches de transport : opérateur = chauffeur, champ masqué hors TP (24/09/2026)

- **Automatisation 18 / action 1523** (`transport_operateur_fix.py`) : sur une tâche du projet
  « Demande de transport » sans étiquette TP (id 1), les opérateurs valent exactement `[chauffeur]`
  (remplacement, plus d'ajout) : une duplication ou un changement de chauffeur ne laisse plus
  l'ancien chauffeur. Tâche TP : inchangé (opérateurs des machines + chauffeur ajouté).
  Vérifié en prod (copie de la tâche 7026, chauffeur changé -> opérateurs suivent ; copie TP intacte).
- **Vues 8005 (form, priorité 9995, après la vue Studio 4380) et 8006 (kanban)**
  (`masquer_operateurs.py`) : champ `x_studio_operateurs` invisible si `1 not in tag_ids`
  (formulaire : aussi hors projet 2). Contrôle navigateur : tâche transport -> champ masqué,
  tâche TP -> visible.
- Non fait (en attente de décision) : reprise des 2 222 tâches de transport terminées dont les
  opérateurs diffèrent du chauffeur (`transport_operateur_fix.py prod nettoyage`).
