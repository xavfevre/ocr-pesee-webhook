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

## Connexion aux congés natifs Odoo (12/08)
Chaque jour d'absence posé sur le planning maintient désormais un congé
natif **`hr.leave` validé** dans l'app Congés d'Odoo (compteurs natifs,
calendrier, rapports). Démarrage de gestion : **01/08/2026** (pas de
reprise d'historique antérieur, décision client).
- **Mécanisme** : 2 automatisations `base.automation` sur `x_heures_jour`
  (87/action 2073 création-écriture, 88/action 2074 suppression), lien
  `hr.leave.x_hj_id`. Miroir jour par jour : pose → congé validé,
  requalification → remplacement, suppression → retrait. Aucune
  notification email générée (contextes mail neutralisés).
- **Types** : CP (répartition **N-1 d'abord** puis N, convention paie),
  Maladie → Sick Time Off, Récup → JOURS A RECUPERER, et types natifs
  créés : Congé maternité (80), paternité (81), Événement familial (82),
  Enfant malade (83), Absence injustifiée (84). « Congés sans solde » ne
  requiert plus d'allocation. Le libellé est lu depuis la note du jour.
- **Demi-journées** : congé natif 0,5 j (matin/après-midi). En Odoo 19
  `request_unit_half`/`number_of_days` sont readonly ORM et la durée ne se
  recalcule pas depuis la période → fixation SQL après création (0,5 j +
  fenêtre horaire), vérifiée persistante après validation. Les congés à
  horaires précis (rares) ne sont pas reflétés nativement.
- **Échecs loggés, jamais bloquants** : si Odoo refuse le congé natif
  (ex. aucune attribution CP), le planning fonctionne quand même et
  l'échec est tracé dans `ir.logging` (name `conges_natifs`).
- **Rattrapage août fait** : Céline (7 j N-1 + 8 j N + ½ récup), Delphine
  (10 j N-1). **BERROYER et Isabelle MAQUIGNON : allocations à 0 j** →
  miroir refusé par Odoo ; la saisie de leurs CP acquis (page Horaires)
  **relance automatiquement** le miroir des jours d'août en attente
  (resync intégré à l'action 2021, testé).

## Matricule paie (12/08)
Champ dédié **`x_matricule_paie`** sur la fiche employé. Les champs natifs
étaient inutilisables : `registration_number` n'existe pas sans le module
Paie, et `identification_id` contient déjà des numéros (sécurité sociale /
pièces d'identité) pour 7 salariés — un test l'a confirmé avant bascule,
aucune donnée écrasée (vérifié au chatter).
- **Saisie** : page ⏰ Horaires par défaut, champ « 🆔 matricule » à côté du
  nom, enregistré par le bouton Enregistrer (action 2021, clé `matricule` ;
  champ vidé = matricule effacé).
- **Export paie** : titre de l'onglet salarié (« HEURES — NOM — matricule
  X ») + colonne « Matricule » en tête du récap mensuel (actif après
  déploiement Render).

## Récup dans l'export paie + alerte hebdo (12/08)
- **Export paie** : 3 colonnes ajoutées au récap mensuel — « H. mises en
  récup » (lignes du mois), « H. récupérées » (jours et demi-jours récup
  du mois, en heures), « Solde récup (h) » (arrêté bureau + mises −
  récupérées, **borné à la fin du mois exporté** — un mouvement de
  septembre n'entre pas dans l'export d'août). Actif après déploiement
  Render.
- **Alerte hebdo** : cron **124** (lundis matin) — si des salariés ont mis
  des heures en récup dans les 7 derniers jours, email récapitulatif au
  bureau (salarié, date, heures, note). Pas d'email si rien. Destinataire :
  `ir.config_parameter maquignon.recup_alerte_email`
  (isabelle@maquignon.com). Testé en réel (mail « sent »).

## Écart : les jours d'absence posés ne comptent plus (12/08)
Une semaine 100 % CP affichait « Écart −36 h » : le théorique comptait les
jours posés en congé comme des heures à faire. Corrigé partout — bandeau
de /mes-heures (JS), ligne « Théorique/Écart » de /heures-admin, récap de
l'export paie : le théorique de l'écart = **théo figé des jours travail**
(demi-journées gérées) **+ calendrier des jours vides** ; les jours typés
CP/maladie/férié/absence/récup comptent 0. Vérifié : semaine CP de Céline
→ écart +0,00 ; export août → écart −9 h (= lundi 31/08 non saisi (8 h)
+ 1 h manquante le 05/08), au lieu de −189 h.

## Export Silae — EVP standard provisoire (12/08)
Bouton **« ⬇ Export Silae (EVP) »** sur /heures-admin (même clé que
l'export paie, `format=silae` sur la route Render `/export-heures`).
Classeur 3 onglets :
- **EVP** : une ligne par élément — Matricule / Salarié / Code rubrique /
  Libellé / Valeur. Heures écart du mois (± ; contrôle Charlotte avant
  import) + absences en jours (0,5 pour les demi-journées).
- **Absences** : les mêmes absences par **périodes datées** (Du/Au, jours,
  demi-journée), week-ends enjambés — si le dossier Silae importe par dates.
- **Lisez-moi** : codes utilisés + liste des salariés **sans matricule**.
Codes rubriques par défaut (HS, ABCP, ABMA, ABNJ, ABRC, ABSS, ABMT, ABPT,
ABEF, ABEM) **modifiables sans redéploiement** : paramètre Odoo
`maquignon.silae_codes` (JSON). Format à caler sur le modèle d'import EVP
du dossier Silae au retour de Charlotte. Actif après déploiement Render.

## Tuile Récups pris en jours ET en heures (12/08)
La récup se prend en jours, demi-journées ou heures (« Horaires précis »
dans la demande de congés) : la tuile affiche désormais les deux unités —
« 1 j · soit 7 h » (total de la période, indépendant de la date d'arrêté ;
demi-journées et récups à horaires précis converties via l'horaire du
jour). S'il n'y a que des récups partielles : affichage en heures.

## Initialisation des CP : allocations multiples (12/08)
« Congés payés : 5 demandé mais 27,5 déjà portés par d'autres allocations
validées » — la saisie n'ajustait que la dernière allocation et refusait
quand la valeur visée était inférieure au total des autres (cas MAIGNAN
Charlotte : deux allocations N validées 27,5 + 25). Réécrit en
**consolidation** : l'allocation du plan d'acquisition (sinon la plus
récente) porte seule la valeur saisie, les autres sont **refusées** (une
allocation ne peut pas valoir 0 en v19 ; historique conservé). Appliqué :
MAIGNAN N=5 / N-1=30 au 31/07 (sa saisie qui échouait), vérifié sur la
page. Saisie à 0 = toutes les allocations refusées.

## Étiquettes employé sur les écrans RH (12/08)
- **⏰ Horaires par défaut** : les étiquettes de la fiche employé (Chauffeur,
  ATELIER, Administratif, TP…) s'affichent à côté du nom, aux couleurs du
  kanban Odoo ; **Intérimaire** en rose vif bordé pour être repérable au
  premier coup d'œil.
- **/heures-admin** : badge « INTÉRIM » à côté du nom des intérimaires.

## Contrat mensuel saisi — chauffeurs 190 h (12/08)
Les chauffeurs sont mensualisés au **temps de service transport : 190 h/mois**,
qui ne se déduit pas de l'horaire hebdo × 52 ÷ 12. Champ
`x_contrat_mensuel` (h) sur la fiche employé : s'il est renseigné, il
**prime sur le calcul automatique** partout — carte ⏰ Horaires par défaut
(« 190,00 h/mois (contrat saisi) »), tuile « Mon mois » de /mes-heures,
colonnes Contrat mensuel / H. sup structurelles de l'export paie. Saisie :
champ « 🕐 h/mois » à côté du matricule (action 2021, clé `contrat_mensuel`,
bornes 0–300 ; vide = retour au calcul automatique). Renseigné à **190 h**
pour les 6 chauffeurs permanents (COLLET, DURAND, MAQUIGNON Franck,
MAQUIGNON Théo, ORILLARD, SEGUIN) — les 3 chauffeurs intérimaires ne sont
pas concernés. H. sup structurelles chauffeurs : 190 − 151,67 = 38,33 h.

## Finitions Horaires par défaut + validité des allocations (12/08)
- **Mise en page** : la colonne nom/étiquettes replie son contenu
  (`flex:1 1 0`) — le bloc CP et « Modifier » restent à droite ; les
  **étiquettes sont toujours sur leur propre ligne sous le nom**.
- **Validité des allocations** : les allocations créées/ajustées par la
  saisie CP portaient `date_from` du jour → Odoo refusait les congés
  antérieurs (BERROYER 10-11/08 en échec de miroir). Action 2021 corrigée
  (date_from = début de période 01/06) + 15 allocations existantes
  élargies + relance : BERROYER complet (10 congés natifs N-1).
- Balayage général des jours d'août sans miroir : il ne reste que les
  10 jours CP d'**Isabelle MAQUIGNON** (son allocation est à 0 — sa
  propre saisie CP les débloquera automatiquement).

## Récup et sans solde saisis par le salarié, heures sup en récup par défaut (23/09)

Demande de Xavier (feuille papier de Charlotte pour JOLLY Floran vs feuille
Odoo) : la récup ne passe plus par une demande approuvée, le salarié saisit
lui-même ses récups et son sans solde (les vacances restent sur validation),
Charlotte corrige facilement, l'interface reste explicite (« il n'y a pas que
des prix Nobel »), et **les heures supplémentaires vont par défaut en récup**.

### Modèle `x_heures_jour`
- Nouveaux champs : `x_h_recup` (heures prises en récup ce jour),
  `x_h_sans_solde` (heures sans solde ce jour), `x_hs_payees` (booléen
  « heures sup payées, pas en récup », bureau uniquement). Nouveau type de
  jour **`sans_solde`** (journée entière).
- **`x_hs` = heures comptées dans le solde « à récupérer »** du jour :
  jour travaillé → `travaillé + sans solde − horaire` (heures en plus
  ajoutées au solde, récup prise ou heures manquantes retirées, sans solde
  neutre ; si « HS payées », le surplus n'entre pas) ; journée entière de
  récup → `− horaire` ; sans solde / CP / maladie / férié / absence → 0.
  C'est exactement la logique de la feuille papier (colonne « Heures
  supplémentaires » −4,50 le 14/09 « en récup », −5,00 « sans solde » le
  11/09 hors total, « Heures M-1 » + total = « Reste heures »).
- **Solde à récupérer** (page salarié, badge admin, exports, fiche) =
  arrêté bureau (`x_recup_solde` à `x_cp_ref_date`) + Σ `x_hs` des jours
  postérieurs (types travail / récup / sans solde) + lignes `x_recup_ligne`
  (désormais réservées au bureau : le champ « + heures à récupérer » de la
  page salarié est retiré, le surplus est automatique).

### Action 2012 (`heures_actions.py`)
- Le jeton salarié peut poser `travail`, `recup` et `sans_solde` ; CP,
  maladie, férié, absence, repos restent réservés au bureau (et une journée
  posée par le bureau n'est pas modifiable par le salarié).
- Jour travaillé : `hj_h_recup` / `hj_h_ss` (à la minute, 0–12), refusés
  si récup + sans solde > heures manquantes (message explicite). 0 h
  travaillée + récup = horaire ⇒ normalisé en journée `recup` (idem sans
  solde). `hj_hs_payees` (bureau). Note conservée si `hj_note` absent (sauf
  note automatique « Récup X h » / « Sans solde X h »).
- Bureau, saisie partielle (`hj_periode` matin / après-midi / horaires) :
  récup et sans solde gardent l'horaire entier et remplissent
  `x_h_recup` / `x_h_sans_solde` (note « Récup 4,50 h (bureau) ») ; CP,
  maladie, férié, absence partiels inchangés (horaire réduit).
- Action 2014 (approbation) : sans solde → type `sans_solde`, récup journée
  → `x_hs = −horaire`, partiels → heures.
- Réponse enrichie : `type`, `heures`, `theo`, `hs`, `h_recup`, `h_ss`,
  `payees` (les pages mettent à jour la carte sans recharger).

### Pages
- **/mes-heures** : bandeau explicatif en 4 lignes ; par jour, trois boutons
  « ✓ Journée normale », « 🔄 Toute la journée en récup », « 🚫 Toute la
  journée sans solde » (confirmation), horaires, puis une **ligne de
  contrôle** calculée en direct (« 9,50 h travaillées pour 8,50 h prévues :
  +1,00 h ajoutée à vos heures à récupérer », « Il manque 4,50 h… précisez
  récup ou sans solde ») et un bloc « Heures manquantes » avec « Tout en
  récup » / « Tout sans solde » et les deux champs en heures. Total semaine
  « Travaillé · Horaire · Récup semaine ». Tuiles : « À récupérer » (nouvelle
  formule, détail du calcul en clair), « Récups prises » en heures, « Sans
  solde ». Vue mois : 🔄 / 🚫 sur les jours concernés. Le bloc de demande ne
  propose plus que CP et congés spéciaux.
- **/heures-admin** : popup avec « Sans solde (journée) », champs récup /
  sans solde en heures et case « HS payées » ; cases « 4,00 R 4,5 » /
  « SS 5 » ; colonnes Récup ±, 🔄 h, 🚫 h ; badge solde recalculé ; lien
  **📋** vers la fiche.
- **NOUVEAU /heures-salarie?emp=&mois=&k=** (vue `website.heures_salarie`,
  page 92 en prod) : fiche mensuelle d'un salarié au format de la feuille
  Excel — blocs semaine, Arrivée/Départ ×2, Heures, Récup ±, récup prise,
  sans solde, HS payées, type, note ; **chaque ligne s'enregistre toute
  seule** dès qu'une case change (✓ / ✗ à droite, ⚡ = horaire habituel),
  totaux semaine, récap mois avec **Heures M-1** et **Reste heures** comme
  sur le papier, lien 📄 Feuille Excel.
- **/planning-rh** : type sans solde (SS), exposants R / S sur les jours
  partiels, bouton « Sans solde » dans la popup.

### Exports (`export_heures.py`)
- Paie : colonnes « Écart compté en récup », « H. sup payées », « H. récup
  prises », « H. sans solde », « Jours sans solde » ; lignes hebdo avec
  Récup ± / Récup prise / Sans solde ; solde récup à fin de mois.
- Silae : `hs` = heures sup **payées** seulement, nouveau code `ABSSH`
  (heures sans solde partielles), journées sans solde en absences `ABSS`.
- Feuille hebdo (gabarit papier) : colonne H = `x_hs` en valeur (la formule
  `G − E2` du gabarit est remplacée), mention SANS SOLDE, annotations
  « en récup 4,50 h » / « sans solde (−5,00 h) » / « HS payées » dans Total,
  Heures M-1 = solde à la veille du mois. Vérifié sur JOLLY septembre :
  semaine 38 = 37,50 h / −1,50, sans solde hors total, comme le papier.

### Migration du 23/09 (`migration_rh.py`)
Journées entières de récup (`x_hs = −horaire`), récup partielle de JOLLY
du 14/09 (horaire 8,50, récup 4,50), JOLLY 11/09 absence → sans solde,
automatisation 87 (miroir hr.leave) : `sans_solde` → Congés sans solde (9).
Les lignes `x_recup_ligne` existantes (Delphine, MODDE, RANGER) sont
conservées : aucune ne double un surplus de journée.

### Tests
15 scénarios de l'action 2012 sur MAQUIGNON Théo (prod, juin 2026, tout
supprimé), rendu + saisie des 5 pages par Playwright sur la base de test
`testmaq230926v2` (relais local branché sur la base de test), exports paie /
Silae / feuille sur la base de test. Scripts et vues avant/après :
`odoo-scan-page/rh_recup_sans_solde_20260923/`.

### Fiche et feuille Excel sur la période de paie du salarié (23/09, suite)
Charlotte fait les paies à cheval sur deux mois, avec des dates différentes
selon le salarié (dates mémorisées par ligne dans `/heures-admin`,
paramètre `maquignon.heures_export_exc`). Le bouton **📋** ouvre donc la
fiche `/heures-salarie?emp=&du=&au=&k=` sur les dates de la ligne (sinon
celles de l'en-tête, sinon le mois), comme le bouton 📄. La fiche affiche
alors « du … au … », des semaines couvrant la période, les totaux de la
période, **« Solde au (veille) »** à la place de « Heures M-1 », et son
bouton 📄 Feuille Excel reprend la même période (`build_feuille` avec
du/au : Heures M-1 = solde à la veille du premier jour). Navigation
« période précédente / suivante » (même longueur) et « 📆 mois entier ».

### Récup / sans solde « de telle heure à telle heure » (23/09, suite)
Sur la page salarié, sous chaque nombre d'heures, un créneau facultatif
« ou de … à … » : le créneau est **retiré des heures travaillées** (même
découpe que le bureau : plage entière, début, fin, ou le plus long morceau
si au milieu) et les heures se calculent (à la minute). Le bloc est
repliable (« 🔄 Récup ou 🚫 sans solde pris dans la journée ? ») et s'ouvre
seul quand il manque des heures. Action 2012 : `hj_recup_de/_a`,
`hj_ss_de/_a` (heures décimales), durée = heures, refus si le créneau
chevauche les heures travaillées, note automatique
« Récup 16:00-17:00 · Sans solde 08:00-09:00 » (visible partout, préremplit
les champs au rechargement).

### Fiche : passer d'un salarié à l'autre (23/09, suite)
Barre « ◀ précédent · liste déroulante par société · suivant ▶ » en haut de
la fiche, même ordre que /heures-admin (société puis nom). Le salarié cible
s'ouvre sur **sa** période de paie mémorisée (`maquignon.heures_export_exc`,
dates de sa ligne), sinon sur la période affichée.
