# Parc automobile — planning des contrôles obligatoires (06/08/2026)

## Demande
« Faire un planning des différents contrôles obligatoires pour chaque
véhicule avec leur périodicité — rechercher pour chaque véhicule les
contrôles obligatoires. »

## Référentiel réglementaire retenu (sources : service-public, UTAC-OTC,
DEKRA-Norisko, organismes VGP agréés, Légifrance)

| Type | Périodicité | Concerne | Référence |
|---|---|---|---|
| Contrôle technique (léger) | 24 mois (1er à 4 ans) | VL/VUL ≤ 3,5T | Code de la route |
| Contrôle antipollution complémentaire (VUL) | 12 mois | Utilitaires diesel > 4 ans, ≤ 3,5T, hors VP | CT complémentaire annuel |
| Contrôle technique (PL / remorque lourde) | 12 mois (1er à 1 an) | PL, tracteurs, remorques > 3,5T | Code de la route |
| Chronotachygraphe | 24 mois | PL > 3,5T usage pro | Règlement UE |
| Limiteur de vitesse | 12 mois | PL > 3,5T | Arrêté du 2 mai 1986 |
| Extincteur embarqué | 12 mois | PL, engins pro | Vérification technicien agréé |
| VGP annuelle (terrassement) | 12 mois | Pelles, chargeuses, tombereaux, tractopelles | Arrêté du 5 mars 1993 |
| VGP semestrielle (levage) | 6 mois | Chariots élévateurs, chargeurs télescopiques, grues auxiliaires | Arrêté du 1er mars 2004, art. R.4323-23 |

Point vérifié en cours de route : le régime spécifique carrières (RGIE,
titre « équipements de travail ») a été abrogé en 2021 — mines et
carrières suivent désormais le Code du travail standard, donc les mêmes
règles VGP que toute entreprise. Pas de surcouche réglementaire propre à
Maquignon.

Deux ajustements faits en direct avec le client : le contrôle antipollution
complémentaire des VUL (manqué dans la première recherche), et l'extincteur
PL (déjà dans le référentiel mais confirmé explicitement).

## Classement des 66 véhicules du parc

Classement automatique par mots-clés du nom/modèle (pas de champ PTAC natif
dans le module Fleet d'Odoo) :

| Catégorie | Contrôles affectés | Nb |
|---|---|---|
| Voitures (VP) | CT léger | 5 |
| Utilitaires légers (VUL) | CT léger + antipollution | 11 |
| Camions porteurs | CT PL + chrono + limiteur + extincteur (+ VGP semestrielle pour l'Ampiroll, grue auxiliaire) | 4 |
| Tracteurs routiers | CT PL + chrono + limiteur + extincteur | 6 |
| Remorques/semi-remorques | CT PL (>3,5T, confirmé par le client pour les 13) | 13 |
| Engins de terrassement (pelles, mini-pelles, tombereaux, tractopelle, chargeuses sur pneus) | VGP annuelle | 18 |
| Levage (chargeurs télescopiques, chariot élévateur) | VGP semestrielle | 7 |
| Hors périmètre (groupe électrogène, haveuse Fantini) | — | 2 |

Correctif fait en cours de classement : l'IVECO « Camion 3,5 t » était
tombé côté PL par une règle trop large (mot « Camion ») — reclassé en VUL,
qui est son régime réel (≤3,5T).

**106 lignes de suivi créées** (une par couple véhicule × contrôle
applicable), toutes avec date de dernier contrôle **vide** — aucune
information fiable n'existant à ce jour dans Odoo ; à saisir
progressivement par le bureau au fur et à mesure des documents retrouvés
(cartes grises, derniers rapports Bureau Veritas/Socotec/DEKRA…), plutôt
que d'inventer des dates.

## Modèles créés
- `x_type_controle` (référentiel, 8 lignes) : nom, périodicité en mois,
  catégorie (couleur), référence légale.
- `x_controle_vehicule` (table de suivi, 106 lignes) : véhicule, type de
  contrôle, date du dernier contrôle réalisé, note libre.
- Droits d'accès accordés au groupe utilisateurs internes de base.

## Page `/parc-controles`
Tableau véhicules (lignes) × types de contrôle (colonnes), une case par
contrôle applicable (— si non applicable à ce véhicule). Couleur de case :
- 🔴 rouge = échéance dépassée
- 🟡 jaune = échéance dans les 30 jours
- 🟢 vert = à jour
- ⬜ gris = jamais renseigné

Compteurs cliquables en haut (filtrent le tableau par état), filtres par
catégorie de véhicule (fonctionnels : chaque ligne du planning porte
désormais sa catégorie, champ `x_categorie` sur `x_controle_vehicule`).
**Clic sur une case** → popup, saisie de la date du dernier contrôle (ou
bouton **« ✓ Valider aujourd'hui »**), calcul automatique de la prochaine
échéance affiché (date + périodicité). Bouton Effacer pour vider une date.
Écriture directe via `/web/dataset/call_kw` (page interne, accessible aux
utilisateurs connectés à Odoo — pas de lien signé nécessaire, contrairement
aux pages salariés).

### Synchronisation bidirectionnelle avec l'onglet Services (Fleet natif)
La date affichée sur le planning est désormais lue en priorité depuis
l'historique natif `fleet.vehicle.log.services` (dernière ligne à l'état
« Terminé » pour le couple véhicule/type de contrôle) — une saisie faite
directement dans l'onglet Services d'un véhicule remonte donc sur la page
web sans ressaisie.

À chaque validation d'un contrôle sur le planning web (bouton « Valider »
ou date saisie manuellement), l'action serveur **2055** :
1. crée une ligne « Terminé » dans l'historique Fleet à la date saisie ;
2. **planifie automatiquement le contrôle suivant** : crée une ligne
   « Nouveau » dans l'onglet Services, datée de la prochaine échéance
   (date + périodicité), visible directement dans le planning natif Fleet ;
3. annule (sans supprimer) l'ancienne ligne planifiée du même type si elle
   existait, pour éviter les doublons.
Effacer une date annule la planification automatique associée mais
conserve l'historique déjà créé.

Accessible depuis le menu **Parc automobile → 🚗 Contrôles obligatoires**
(en tête de menu).

### Vues calendaires (06/08)
Sélecteur en haut de page : **📋 Tableau / 📅 Semaine / 🗓 Mois / 🗂 Année**
(paramètre `vue=`). Les vues calendaires affichent les **échéances
calculées** (dernier contrôle + périodicité, source : historique Fleet
natif) avec les mêmes couleurs (rouge retard / jaune sous 30 j / vert à
jour). Les filtres catégorie et état restent actifs dans toutes les vues.
- Semaine : 7 colonnes, sélecteur `type=week` + flèches ◀ ▶ ;
- Mois : grille calendaire, sélecteur `type=month` + flèches ;
- Année : 12 cartes mensuelles avec compteur d'échéances — la vue la plus
  utile pour planifier les CT/VGP de l'année.

## Alerte email hebdomadaire
Action serveur **2053** + cron hebdomadaire (**123**, tous les lundis) :
parcourt les 106 lignes, calcule les échéances, et envoie un email (si et
seulement si au moins un contrôle est en retard ou à échéance sous 30
jours — pas de mail « rien à signaler » chaque semaine) listant les
véhicules concernés avec un lien direct vers le planning.

Destinataire configurable sans redéploiement :
`ir.config_parameter maquignon.parc_alerte_email` (actuellement
`isabelle@maquignon.com`). Testé en conditions réelles : base vide → pas
d'envoi ; 1 contrôle en retard forcé → email créé et **envoyé** (`state:
sent`), sujet « 🚗 Parc automobile : 1 en retard, 0 sous 30 j ».

## À faire côté bureau
Saisir les dates de dernier contrôle connu pour chaque véhicule — c'est le
seul travail restant pour que le planning et les alertes soient pleinement
opérationnels. Le tableau se remplit progressivement, aucune urgence
compilée artificiellement.
