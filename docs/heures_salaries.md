# Heures salariés — saisie web & export paie

## Les pages (vues website Odoo, déployées)
- **`/mes-heures?emp=<id>&t=<token>`** (salariés, toutes sociétés) : accès
  **uniquement par lien personnel signé** (token individuel `x_heures_token`
  sur hr.employee, vérifié aussi côté serveur à chaque sauvegarde) — un
  salarié ne peut pas voir les heures d'un autre. Une carte par jour de la
  semaine pré-remplie avec l'**horaire contractuel du salarié** (son
  `resource.calendar` Odoo, cycles 2 semaines gérés). Le salarié saisit
  **uniquement ses heures travaillées** : bouton « ✓ Journée normale » (qui
  pré-remplit l'horaire habituel) ou saisie fine des 4 horaires. Totaux de
  semaine en direct. Bloc **« Demander des congés »** (du/au/type/motif)
  avec suivi du statut de ses demandes.
  **CP / maladie / férié / absence / récup sont réservés au bureau**
  (Isabelle et Charlotte, via `/heures-admin`) : le salarié les voit sur sa
  semaine sous forme de bandeau coloré en lecture seule, et les champs
  horaires + le bouton d'enregistrement disparaissent sur ces journées.
  Le contrôle est aussi fait **côté serveur** dans l'action 2012 : une
  requête portant un jeton salarié ne peut poser qu'un type `travail`, et ne
  peut pas écraser une journée déjà typée par le bureau.
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

## Enregistrement via le relais Render (03/08) — correctif majeur

Les 5 pages appelaient `/web/dataset/call_kw` pour exécuter les actions
serveur. **Cet endpoint est réservé aux navigateurs connectés au backend
Odoo** : sur les téléphones des salariés (et sur tout poste non logué), chaque
enregistrement échouait en « Session expired » — c'était le message « page
ouverte depuis trop longtemps » en boucle, que régénérer le lien ne corrigeait
pas. Ça marchait en test uniquement parce que le navigateur du bureau était
logué à Odoo.

Les pages passent désormais par `POST /heures/rpc` sur l'app Render
(`ocr-pesee-webhook.onrender.com`), qui exécute l'action via XML-RPC avec le
compte technique. Actions autorisées : 2012, 2013, 2014, 2020, 2021 —
uniquement. La sécurité reste portée par les actions (jeton salarié / clé
responsables vérifiés dans leur code) : le relais n'y change rien, il remplace
seulement l'exigence « être connecté à Odoo » que les liens signés ne peuvent
pas satisfaire. CORS limité à l'origine du site Odoo (`HEURES_ORIGINE`,
défaut `ODOO_URL`).

**Déploiement en deux temps** : 1) merger sur main (Render déploie le relais),
2) `python odoo-scan-page/deploy_heures.py` (pousse les 5 vues corrigées dans
Odoo et vérifie le marqueur du relais en relecture).

## Notes
- Les horaires de référence se règlent dans Odoo : fiche employé → Horaires
  de travail. Tout salarié à horaire particulier doit avoir son calendrier.
- Évolutions possibles : verrouillage du mois après export, signature salarié.

## Verrou de paie (05/08)
Bouton **🔒 Figer** sur `/heures-admin` (à côté de l'export paie) : Charlotte
choisit une date et fige toutes les feuilles d'heures **jusqu'à cette date
incluse**. Les salariés ne peuvent plus modifier ces journées (refus côté
serveur dans l'action 2012 + bannière « Journée verrouillée » sur leur page) ;
**le bureau reste libre** de corriger. Bouton « Déverrouiller » pour retirer
le verrou. Stocké dans `ir.config_parameter maquignon.heures_verrou`,
posé/levé par l'action **2050** (clé responsables, via le relais Render).
Usage type : après l'export paie du mois, figer au dernier jour du mois.

## Présences Odoo alimenté par la saisie web (05/08)
La saisie web **vaut pointage kiosque** : chaque journée « travail »
enregistrée (salarié ou bureau, action 2012) crée les pointages
`hr.attendance` correspondants — un le matin, un l'après-midi — en heure
locale Europe/Paris convertie en UTC. Une correction remplace les pointages
du jour ; une requalification en CP/maladie/férié/absence (2012 ou
approbation de congés 2014) les retire. L'historique des saisies a été
rattrapé (54 pointages recréés). Le planning du module Présences reflète
donc les feuilles d'heures ; l'export paie reste la référence.

Le cron Odoo « Attendance: Detect Absences » reste **désactivé** : il
créait chaque nuit des pointages techniques 0h (blocs rouges) pour tout
salarié « sans badge », redondants avec le « ! » des feuilles d'heures
(54 marqueurs purgés en tout).

## Vue mensuelle salarié (05/08)
Basculeur **Semaine / Mois** en haut de `/mes-heures`. La vue mois affiche
le calendrier du salarié en lecture : heures des jours travaillés (vert),
CP / Maladie / Férié / Absence / Récup en couleur, **« ! » ambre sur les
jours ouvrés passés sans saisie**, théorique pâle sur les jours à venir,
jours sans horaire grisés. Bandeau de totaux du mois (effectué, théorique,
écart + compteurs par type). Un clic sur un jour ouvre la semaine
correspondante pour saisir — la saisie reste exclusivement hebdomadaire.

## Jours fériés automatiques (05/08)
Action serveur **2049** + cron mensuel (**122**) : pour les ~120 prochains
jours, crée une ligne « férié » dans la feuille d'heures de chaque salarié
dont c'est un **jour ouvré selon son calendrier** (parité 2 semaines gérée,
théorique du jour renseigné). Fériés France calculés (11 jours, Pâques par
algorithme — pas de dépendance) ; ne touche jamais un jour déjà saisi, le
bureau peut requalifier un férié travaillé via /heures-admin. Première
exécution : 15/08 créé pour les 2 salariées du samedi, 01/11 (dimanche)
pour personne, 11/11 pour les 33 fiches. Les fériés apparaissent partout
(grille admin, planning, page salarié en bandeau violet, export paie
mention FERIE).

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
**Cycles 2 semaines** : case « Cycle 2 semaines (alternance A / B) » par
salarié → deux grilles Semaine A / Semaine B, bouton « A → B » pour recopier,
totaux par semaine + moyenne. L'enregistrement produit un calendrier
`two_weeks_calendar` avec les lignes de section « Semaine A / Semaine B » et
les `week_type` 0/1, à l'identique des calendriers Odoo standards ; décocher la
case repasse le salarié en semaine simple. Odoo applique A ou B selon la parité
de la semaine, et le pré-remplissage des feuilles d'heures suit automatiquement.
Raccourcis depuis /heures-admin et /heures-liens.

## Correctifs config RH (30/07) — blocages au changement d'horaire
Le changement d'horaire d'un salarié déclenche un recalcul de ses congés ;
trois défauts de configuration le faisaient échouer :

1. **SARL MAQUIGNON — projet interne cassé** : `leave_timesheet_task_id` vide
   (conséquence du compte analytique archivé le 18/12/2025). Tâche « Congés »
   du nouveau projet interne rattachée à la société.
2. **SFM — type de congé de référence manquant** (`l10n_fr_reference_leave_type`)
   → « Vous devez d'abord définir un type de congé de référence pour cette
   société ». Aligné sur SARL MAQUIGNON (« Congés payés »).
3. **Types de congés rattachés à une seule société alors qu'ils servent au
   groupe** : « Congés payés » (CHATEL) est utilisé par les 4 sociétés,
   « JOURS A RECUPERER » (MAQUIGNON) par 2. Les 4 types personnalisés passent
   en **communs à toutes les sociétés**, ce qui reflète l'usage réel et évite
   que tout changement de société casse l'historique de congés.

Vérifié après correctifs : **32 des 33 salariés** acceptent un changement
d'horaire (test automatisé, transaction annulée).

### Point RH réglé le 30/07 — attribution CP de Charlotte
Les attributions de congés payés 2025-2026 n'avaient jamais été créées
(tout le monde s'arrêtait à 2024-05-31 → 2025-05-31, 27,5 j). Charlotte était
la seule à avoir des congés validés après cette date (2-3 juin 2025), donc la
seule bloquée. **Créée le 30/07** : attribution « Congés payés 01/06/2025 →
31/05/2026 (régularisation) », 25 jours, validée — *montant standard à faire
vérifier/ajuster par la comptable*. Son horaire 38 h (L-Me 08:30-12:30 /
13:15-17:45, Je jusqu'à 17:15, Ve 08:30-13:00) a ensuite été enregistré
(calendrier « Horaire — MAIGNAN Charlotte », 38 h/sem).
Audit du même jour sur **tous** les salariés : aucun autre congé validé non
couvert par une attribution, et le test à blanc de changement d'horaire passe
pour les **32 fiches actives sur 32** (la 33ᵉ était le doublon DISTRI BETON de
Christophe MAQUIGNON, archivé le même jour).

## Enrichissement de la page salarié (05/08)
Trois nouveaux blocs sur `/mes-heures`, sous la semaine :
- **🏖 Mes congés** : compteurs de la période CP en cours (01/06 → 31/05) —
  CP pris, récups, maladie, absences — calculés depuis la feuille d'heures
  (`x_heures_jour`, la source fiable du groupe). Le **solde de CP restants**
  ne s'affiche que si une attribution Odoo validée couvre la date du jour
  (droit − pris) ; sinon un message renvoie vers le bureau. Pour que le
  solde apparaisse pour tous, créer les attributions annuelles dans Congés.
- **📊 Mon mois** : heures effectuées vs théorique saisi du mois, écart
  coloré.
- **📇 Mes coordonnées** : le salarié met à jour lui-même portable, email
  perso, adresse, contact d'urgence. Enregistrement via l'action serveur
  **2048** (jeton vérifié, champs limités à cette liste blanche) ; chaque
  modification est **tracée dans le journal de la fiche salarié** (ancienne
  et nouvelle valeur), visible par Charlotte et Isabelle.

## Bug corrigé (30/07) — le lundi n'était pas enregistré
**Symptôme** : tout horaire saisi via /heures-horaires perdait le lundi ;
le total affiché (ex. 28 h au lieu de 35 h) était juste — c'est la donnée
enregistrée qui était amputée.

**Cause** : dans le gabarit, l'attribut `t-att-data-d="i"` n'était pas généré
pour i = 0 (QWeb omet un attribut dont la valeur est falsy, et 0 l'est). Les
champs du lundi n'avaient donc pas de `data-d`, le JavaScript ne les trouvait
pas et envoyait toujours un lundi vide. Corrigé par `t-att-data-d="str(i)"`.

**Réparation des 6 horaires abîmés** (tous saisis avant le correctif) :
CERBELLE Céline, CHEVALIER Christophe, DESPUJOLS Loïc, GILLARD Loïc,
GUERIN Frédéric, LANGLOIS Nicolas — lundi restauré à l'identique du mardi,
ce qui ramène chacun **exactement à ses heures contractuelles** (35 h pour
Céline, 39 h pour les cinq autres), confirmant l'hypothèse.

## Amélioration (30/07) — message clair en cas de session expirée
**Symptôme** : un salarié qui garde sa page ouverte plusieurs jours (onglet
mobile jamais fermé) obtient, en tentant d'enregistrer, une alerte technique
« Échec : Session expired » — incompréhensible et sans action possible
(cas rencontré par TRINQUARD Nicolas).

**Cause** : la session anonyme liée à la page a une durée de vie limitée
côté Odoo ; au-delà, l'appel d'enregistrement échoue avant même d'atteindre
l'action serveur.

**Correctif** : les 5 pages web (Mes heures, Heures admin, Planning RH,
Liens, Horaires) détectent maintenant ce cas précis et affichent
« Votre page était ouverte depuis trop longtemps… elle va se recharger »,
puis rechargent automatiquement la page. La saisie en cours doit être
refaite après le rechargement (elle n'était de toute façon pas enregistrée),
mais le salarié comprend quoi faire au lieu de rester bloqué.

## Validation des congés par le manager (06/08)
- **Types de demande étendus** : CP, récupération, sans solde + **congé
  maternité, congé paternité, événement familial (mariage, naissance,
  décès…), enfant malade** (sélection `x_type` de `x_demande_conge`, options
  du formulaire /mes-heures, libellés /planning-rh). À l'approbation, les
  nouveaux types posent des jours « absence » avec le libellé exact en note
  (action 2014).
- **Email au manager attitré** à chaque création de demande (automatisation
  86 + action 2070) : détails de la demande + boutons **✓ Approuver / ✕
  Refuser**. Destinataire = champ « Manager » de la fiche employé
  (`parent_id.work_email`) ; à défaut, repli sur le paramètre
  `maquignon.conge_alerte_email` (isabelle@maquignon.com). ⚠ 14 salariés
  n'ont pas de manager renseigné — à compléter sur les fiches employés pour
  que le bon responsable reçoive les demandes.
- **Page `/conge-decision?id=…&t=…`** (vue 7974, page 90) : lien signé par
  un jeton propre à chaque demande (`x_token`, généré à la création). La
  page affiche la demande et demande une **confirmation par clic** (rien ne
  se valide à l'ouverture du lien — protection contre les scanners
  d'emails). Décision via l'action **2069** (vérifie jeton + statut
  « attente », puis délègue à la logique métier de 2014 : pose des jours,
  purge des pointages). Une demande déjà traitée affiche son badge et ne
  peut pas être re-décidée.
- **Relais Render** : action 2069 ajoutée à `HEURES_ACTIONS_AUTORISEES`
  (app.py) — les boutons de la page passent par le relais (les managers ne
  sont pas forcément connectés à Odoo). **Actif après merge + déploiement
  Render.**
- Testé bout-en-bout en prod (demande créée puis nettoyée) : jeton généré,
  email envoyé, page OK, mauvais jeton rejeté, approbation → jours posés
  avec libellé, re-décision bloquée, badge affiché.

## Congés : période (jours ET horaires) — 06/08
Nouveaux champs sur `x_demande_conge` : `x_periode` (journée complète /
matin / après-midi / horaires précis) + `x_h_de` / `x_h_a`. Formulaire
/mes-heures : sélecteur de période, champs « de … à … » affichés si
« horaires précis » (action 2013 étendue, horaires validés côté serveur).
Affichage de la période partout : liste « mes demandes », planning RH,
email manager, page /conge-decision.

**À l'approbation (action 2014)** :
- journée(s) complète(s) : comportement historique (jour typé CP/absence,
  pointages purgés) ;
- matin / après-midi / horaires précis : le jour reste en **travail** avec
  les créneaux **complémentaires** pré-remplis depuis l'horaire contractuel
  (ex. « matin en récup » → après-midi 13h30–17h30 posé), théorique aligné
  (pas de fausses heures sup), note explicite « Récupération — matin en
  congé (demande N) ». Les créneaux sont rognés autour des horaires
  demandés ; 2 créneaux affichables max (les 2 plus longs), pointages non
  purgés.

Cas réel corrigé dans la foulée : la demande de Céline (récup « uniquement
le matin » du 01/09), approuvée en journée pleine avant la fonctionnalité,
re-posée en « travail 13h30–17h30 » avec note.

L'email du manager contient aussi un lien **📅 planning global des congés**
(/planning-rh avec la clé responsables).

## Planning RH : congés partiels visibles + historique (06/08)
- Une journée avec congé partiel approuvé (matin/après-midi/horaires)
  s'affiche en **case bicolore orange/vert** avec « 4½ » (heures travaillées
  + ½) ; le survol de la case affiche le détail (« Récupération — matin en
  congé (demande N) »). Légende mise à jour.
- Bloc dépliable **« 🗂 Historique des demandes »** sous les demandes en
  attente : les 30 dernières demandes traitées (badge ✓/✕, salarié, type,
  période, motif, réponse du responsable, date de traitement).
- Rattrapage effectué : les 3 demandes en attente d'avant la mise en place
  (TRINQUARD ×2, DESPUJOLS) ont reçu leur email de validation manager
  (boutons actifs, relais déployé).

## Congés acquis N / N-1 (06/08, suite)
- **Page salarié** : la tuile « CP restants » affiche désormais le total
  N + N-1 avec le détail « (N : 27,5 · N-1 : 10) ».
- **Page ⏰ Horaires par défaut** : chaque carte salarié porte deux champs
  « 🏖 CP acquis N / N-1 » + bouton Enregistrer — écrit les allocations
  Odoo (ajuste la plus récente validée, ou en crée une validée s'il n'y en
  a pas). Action 2021 étendue (`cp_mode`), déjà autorisée au relais.
- **Cumul automatique** : le plan « Congés payés (2,5 jours par mois) »
  existait mais **était arrêté depuis le 31/05/2025** (allocations bornées
  à la période 2024-2025 ; l'acquisition n'a jamais tourné sur 2025-2026).
  Relancé le 06/08/2026 pour 18 salariés actifs : bornes levées, ancrage
  lastcall 31/07/2026 → reprise à 2,5 j/mois à partir d'août, **sans
  rattrapage rétroactif** (soldes vérifiés intacts). 14 actifs restent hors
  plan (comptes techniques, dirigeants, et quelques salariés : BERROYER,
  CLAVELLE, GUERIN, JOLLY, LANGLOIS, ORILLARD, VRILLON, BAULU) — à
  rattacher au plan dans Congés → Configuration si souhaité.

## Heures à récupérer (solde signé) — 06/08
Champ `x_recup_solde` (float) sur `hr.employee` — **peut être négatif**
(heures dues par le salarié).
- **Saisie** : page ⏰ Horaires par défaut, champ « 🔄 Récup (h) » à côté des
  CP N/N-1, même bouton Enregistrer (action 2021, clé `recup_h`, bornes
  ±500, validation serveur).
- **Affichage salarié** (/mes-heures, bloc Mes congés) : ligne « 🔄 Heures à
  récupérer : +4,5 h » (vert si positif, rouge si négatif), masquée à 0.
- **Affichage bureau** (/heures-admin) : badge coloré à côté du nom du
  salarié (vert/rouge selon le signe).
Testé en prod (+4,5 puis −3,25 sur un salarié, affichages vérifiés sur les
trois pages, solde remis à 0).

## Horaire mensuel & heures sup structurelles (06/08)
Principe : pas de nouvelle saisie — l'horaire mensuel contractuel se déduit
de la semaine type déjà configurée : **hebdo × 52 ÷ 12** (moyenne des
semaines A/B pour les cycles). Base légale française : **151,67 h/mois**
(35 h) ; l'écart contractuel = **heures sup structurelles** payées chaque
mois (ex. 39 h/sem → 169 h/mois → 17,33 h sup).
- **⏰ Horaires par défaut** : chaque carte affiche « 39 h/semaine ·
  **169,00 h/mois** — base légale 151,67 h + **17,33 h sup structurelles** ».
- **/mes-heures** (tuile Mon mois) : ligne « Contrat : 169,00 h/mois — base
  légale 151,67 h + 17,33 h sup structurelles ».
- **Export paie** : 3 nouvelles colonnes dans le récap mensuel de chaque
  onglet salarié : Contrat mensuel (h), Base légale (h), H. sup
  structurelles/mois (actif au prochain déploiement Render).

## Date de référence des compteurs CP / récup (12/08)
Les soldes saisis par le bureau (CP acquis N / N-1, heures à récupérer)
sont des **arrêtés à une date** (typiquement la fin de mois de la dernière
fiche de paie, ex. « à fin juillet 2026 »). Champ `x_cp_ref_date` (date)
sur `hr.employee`.
- **Saisie** : page ⏰ Horaires par défaut, champ date « au JJ/MM/AAAA » à
  côté de Récup (h), prérempli avec la dernière date enregistrée (sinon
  aujourd'hui). Enregistré par le même bouton (action 2021, clé `cp_date` ;
  sans date fournie → date du jour).
- **Calcul** : sur /mes-heures, « CP restants » = acquis − CP pris
  **strictement après** la date de référence (les congés antérieurs sont
  déjà intégrés dans le solde saisi — plus de double décompte). Le
  compteur « CP pris » de la tuile reste le total de la période 01/06 →
  aujourd'hui (informatif). Sans date de référence : comportement
  inchangé (déduction depuis le 01/06).
- **Affichage salarié** : ligne « Solde arrêté au 31/07/2026 — seuls les
  CP pris après cette date sont déduits » sous le détail Acquis N/N-1.
- L'acquisition automatique (2,5 j/mois, ancrée au 31/07/2026) s'ajoute
  naturellement par-dessus le solde saisi à fin juillet — cohérent.
Testé en prod sur MAQUIGNON Théo (saisie 27,5 + 10 au 31/07/2026 ; CP test
posé au 15/07 non déduit, CP test au 10/08 déduit, compteur période
inchangé ; lignes de test supprimées).

## Récup : saisie salarié, unités et détail (12/08)
- **Modèle `x_recup_ligne`** (salarié, date, heures, note) : mouvements
  d'heures **mises en récup** par le salarié lui-même.
- **Page /mes-heures, carte « 🔄 Mettre des heures en récup »** : date
  (≤ aujourd'hui), heures (0,25 à 12), note facultative → action 2012
  étendue (`recup_add`, token salarié ou clé bureau, via le relais déjà
  autorisé). Liste des dernières lignes avec 🗑 (suppression par le
  salarié de ses propres lignes, `recup_del`).
- **Solde affiché** = arrêté bureau (`x_recup_solde`, à la date de
  référence `x_cp_ref_date`) **+ heures mises** (lignes après la date)
  **− heures récupérées** (jours posés type récup → `x_theo` ; demi-jours
  récup → partie non travaillée calculée depuis l'horaire du jour), avec
  le détail du calcul en dessous. Masqué tant que le bureau n'a rien
  arrêté et que le salarié n'a rien saisi (pas de faux « −7 h »).
- **Badge /heures-admin** : même solde calculé (détail dans l'infobulle).
- **Verrou paie** : comme la saisie des heures, `recup_add`/`recup_del`
  refusent toute date ≤ `maquignon.heures_verrou` pour un salarié (le
  bureau, avec sa clé, n'est pas bloqué). Testé (verrou factice au 31/07 :
  ajout au 15/07 rejeté, ajout au 11/08 accepté, paramètre restauré).
- **Largeur page Horaires** : 1240 → 1460 px pour que le bouton
  « Modifier » reste à droite malgré le champ date.
- **Tuiles Mes congés** : unités affichées (« 31 j », « sur 35 j
  acquis »…) ; tuile Récups → « Récups pris X j · soit Y h ».
- **Couleurs** : la tuile CP restants passe du vert à l'**ambre** (couleur
  des CP partout : planning, cases, demi-journées) — le **vert reste
  réservé aux jours travaillés** du planning. Récup bleu ciel, maladie
  rouge : inchangés et cohérents.
Testé en prod (Théo : +2 h ajoutées par token salarié → solde +2 h page
et badge admin, suppression OK, mauvais token et 15 h rejetés ; Céline :
récup du 30/07 antérieure à l'arrêté du 31/07 bien exclue, pas de solde
fantôme ; script servi validé node --check).
