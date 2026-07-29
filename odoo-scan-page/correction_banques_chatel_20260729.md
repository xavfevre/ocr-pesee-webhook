# Correction soldes bancaires CHATEL'GRANULATS (29/07/2026)

Soldes attendus (relevés banque) : BNP **31 140,97 €** · Banque Populaire **46 824,52 €**.
Odoo affichait : BNP 27 858,75 € · Banque Populaire 100 724,18 €.

## BNP (journal 76)
- Cause : la reconnexion du lien bancaire a réimporté le virement « FRAIS DE
  SIEGE » de −3 282,22 € du 23/07 (déjà importé par l'ancien lien, identifiants
  de transaction différents).
- Correctif : ligne de relevé 6174 (non lettrée) passée en brouillon puis
  supprimée. → **31 140,97 € ✓**

## Banque Populaire (journal 36)
Trois causes cumulées (pas la reconnexion) :
1. **Double comptabilisation des remises CB depuis le 03/04/2026** : le cron 98
   « Virement quotidien CB à encaisser → Banque Pop » (action 1673) débitait
   512 Banque Pop / créditait CB à l'encaissement chaque jour, alors que la
   synchronisation bancaire importe AUSSI les lignes « REMISE CB »
   (+116 378,55 € en double sur le 512).
2. **Ancien compte « Bank » (3366)** : jusqu'au 21/04 les relevés posaient leur
   jambe banque dessus (61 088,89 €) ; le compte par défaut du journal a changé
   début mai.
3. Écart résiduel de 1 390,00 € (transactions non importées pendant la coupure).

Correctifs (OD 12744/12745/12746 du 29/07, journal Miscellaneous Operations,
testés sur testmaq290726 avant la prod) :
- D 51121000 CB à l'encaissement 116 378,55 / C 512 Banque Pop (annulation cumul cron) ;
- D 512 Banque Pop 61 088,89 / C Bank 3366 (reclassement, ancien compte soldé à 0) ;
- D 512 Banque Pop 1 390,00 / C Compte d'attente (écart à qualifier par la comptable).
→ **46 824,52 € ✓** · Bank (3366) = 0 ✓

## Mesures pour éviter la rechute
- Cron 98 désactivé (redondant avec la synchro : c'est le relevé qui doit
  constater l'arrivée des remises).
- Modèle de lettrage 35 « REMISE CB → CB à l'encaissement » (journal Banque
  Pop, libellé contient REMISE CB, contrepartie 100 % sur 51121000).

## Reste à faire (comptable)
- CB à l'encaissement (51121000) porte un encours de **112 445,02 €** : les
  lignes de relevé REMISE CB historiques sont en compte d'attente au lieu
  d'être pointées sur 51121000. Les lettrer (le modèle 35 les propose
  automatiquement) ramènera l'encours au réel (remises des derniers jours).
- Qualifier l'écart de 1 390,00 € posé au compte d'attente.

## Pointage en masse des remises CB (fait le 29/07, validé sur base de test)
- **186 lignes de relevé « REMISE CB »** (03/04 → 28/07) repointées du compte
  d'attente vers 51121000 CB à l'encaissement, avec **éclatement
  brut/commission lu dans le libellé** (« BRUT x - COM y ») : le brut solde
  l'encaissement, la commission (566,25 € au total) part au 627 « Autres frais
  et commissions sur prestations » (compte 3154).
- Les 30 remises d'avril avaient leur jambe banque sur l'ancien compte
  « Bank » : jambe déplacée vers 512 Banque Populaire ligne à ligne, et l'OD de
  reclassement agrégée réduite d'autant (61 088,89 → **35 209,15**, OD/26-27/07/0002).
- Résultat : CB à l'encaissement passe de **112 445,02 € à −5 618,14 €**.
  Ce solde créditeur résiduel est à qualifier par la comptable — composants
  identifiés : clôtures de caisse créditant le compte (2 483,67 + 857,30),
  une facture client (1 152,10), reliquat ~1 125 ; probablement des crédits
  faisant double emploi avec les remises désormais pointées (avril).
- Soldes bancaires inchangés et re-vérifiés : Banque Populaire 46 824,52 € ✓,
  BNP 31 140,97 € ✓, ancien compte « Bank » 0,00 € ✓. Aucune pièce en brouillon.

## Ajustement affichage vignette (29/07, suite)
La vignette « Banque Pop » du tableau de bord comptable calcule son solde à
partir des seules lignes de relevé — l'OD « écart 1 390 € » (comptable) n'y
apparaissait pas (vignette à 45 434,52). Remplacée par une **ligne de relevé
manuelle** id 6176 du 05/05/2026 (+1 390,00, « Régularisation coupure de
synchronisation — à détailler ») et l'OD/26-27/07/0003 supprimée. GL inchangé
(46 824,52 ✓), vignette désormais à **46 824,52 €** ✓. La contrepartie de la
ligne 6176 reste en compte d'attente jusqu'à qualification par la comptable.

## Caisse (journal 42, compte 4822) — corrigée le 29/07
GL à **−2 200,64 €** (impossible physiquement) alors que la chaîne des fonds de
caisse POS est parfaitement continue — tiroir compté **119,86 €** au 28/07.
Écart total 2 320,50 €, entièrement expliqué :
1. **Pertes d'écart fictives du 06/05** (clôtures POS/00066 et 00067 +20 €) :
   2 097,20 € passés en charges alors que « attendu = compté » (aucune perte
   réelle, l'argent est resté dans le tiroir et a servi de fond aux sessions
   suivantes). → OD 12748 (annulation, contre 658 Sundry operating charges).
2. **Fond de caisse initial 122,60 €** jamais comptabilisé à l'ouverture du POS
   (avril). → OD 12749 (contre compte d'attente, origine à qualifier).
3. Résidu d'avril 100,70 € (écarts de comptage chaotiques d'avril).
   → OD 12750 (contre 658).
Résultat : **caisse = 119,86 € = inventaire physique** ✓ (testé sur base de
test avant prod). Impact P&L : +2 197,90 € de charges annulées sur 2026.

### Ajustement affichage vignette Caisse (même mécanique que Banque Pop)
Les OD 12748/12749/12750 étaient invisibles de la vignette (calculée sur les
transactions du journal de caisse). Remplacées par trois **transactions de
caisse** du 29/07 (lignes 6177/6178/6179 : +2 097,20 contrepartie 658,
+122,60 en compte d'attente, +100,70 contrepartie 658) et les OD supprimées.
GL inchangé : caisse **119,86 €** ✓, vignette **119,86 €** ✓.
