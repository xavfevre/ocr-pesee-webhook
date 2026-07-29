# Optimisation abonnement — « Modules supplémentaires : Maintenance (par 100 lignes) »

**Alerte** (29/07/2026) : « We detected 30.0 Modules supplémentaires : Maintenance
(par 100 lignes) … but your current subscription includes only 18.0 ».

**Explication** : ce n'est pas l'appli Maintenance (vide). Odoo facture la
maintenance du module importé `studio_customization` — toutes les
personnalisations créées via Studio — par tranche de 100 lignes de code.
La base en comptait ~3 600 (≈36 unités) pour 18 incluses.

**Optimisations appliquées** (validées sur la base de test testmaq290726 avant
la prod — impressions OF/devis/palettisation/worksheet/colisage vérifiées en
PDF, automatisation du poste de scan testée en réel) :

1. **Suppression de 14 vues orphelines + 1 rapport inutilisé** (~780 lignes) :
   - chaîne « worksheet copy_2 » (vues 6902/6903/6904) — ancienne génération du
     rapport de feuille de travail, remplacée par copy_1 ;
   - chaîne « mo_overview copy_1 » (vues 6343–6347) — copie Studio de l'aperçu
     de production, jamais référencée ;
   - matrices produit copy_1/copy_2 (vues 6680/6681/7007/7008) ;
   - rapport 1480 « Ordre de fabrication Rapport » (hors menu Imprimer, doublon
     du 1483) + ses vues 6617/6618.
   Chaque suppression précédée d'une analyse de références exhaustive
   (t-call inter-vues + report_name des actions rapport, sans limite de scan).

2. **Sortie du module facturé** (suppression des étiquettes `ir.model.data`
   module=studio_customization, zéro effet fonctionnel — même régime que les
   vues/actions créées par RPC, jamais comptées) :
   - 7 vues de rapport actives (6635 OF, 7045/7046 palettisation,
     5725/5726/5727 worksheet, 6892 code-barre colis) ;
   - les 38 actions serveur.

**Résultat** : ~1 416 lignes restantes dans `studio_customization`
(≈14 unités < 18 incluses, marge ~25 %).

**Notes** :
- La bannière d'abonnement se rafraîchit au prochain ping Odoo (jusqu'à
  24–48 h) ; vérifier ensuite dans Paramètres → Abonnement.
- Chaque modification de rapport dans Studio recrée des vues « copy(n) »
  comptées : refaire ce ménage si le compteur regrimpe.
- Restent dans le module : 77 vues (1 338 l., surtout les personnalisations de
  formulaires, à conserver sous gestion Studio), 269 champs, automatisations,
  menus, accès.
