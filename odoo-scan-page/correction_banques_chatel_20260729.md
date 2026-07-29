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
