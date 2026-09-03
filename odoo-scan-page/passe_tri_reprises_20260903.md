# Passe de tri des reprises historiques Sage — 03/09/2026

Contexte : à la bascule compta (02/09), les factures absentes des balances des
tiers Sage ont reçu un « paiement de reprise » (marquées payées dans Odoo).
Or les balances ne contenaient pas le lot de factures de fin juillet → un
paquet de factures **non payées** avait été marqué payé (découvert via CELTAN
BUILDING 19,53 € et Jonathan Parcs et Jardins 635,09 € signalés par Châtel).
Par ailleurs, les « extournes » posées le 02/09 (redécouverte des banques
connectées) étaient sans partenaire et à moitié appliquées.

## Méthode
Croisement de chaque reprise avec les **grands-livres Sage** fournis
(GL Maquignon `excel_m.xlsx` du 02/09, GL Châtel `GL_C.xlsx` du 03/09) :
facture lettrée dans Sage = vraiment payée ; absente/non lettrée = pas payée.
Pour Châtel, contrôle croisé avec les lignes de relevés connectés.

## Résultat (sociétés MAQUIGNON + CHÂTEL — Haims non concernée)
- **51 reprises annulées** (factures rouvertes ≈ 160 k€, dont VERMOREL
  42 600 €, CULTURES FRANCE CHAMPIGNON 13 145 €, LEFÈVRE 15 675 €,
  LE PRIEURÉ 15 082 €, RENAULT-BTP-non… voir `passe_tri_rapport.json`) :
  paiement + miroir + extournes supprimés, les factures redeviennent
  « non payées » et seront réglées par les vrais virements (widget/moteur).
- **2 reprises recréées partiellement** (cas mixtes : RENE FREDERIC 285,82 €,
  DALIMEIDO Châtel 555,65 €) pour les seules factures lettrées dans Sage.
- **~65 reprises confirmées payées** (lettrées au GL) conservées ; leurs
  miroirs 512/5119 et extournes de miroir (paires neutres) ont été purgés :
  le débit 511900 du paiement reste ouvert, lettrable un jour avec la ligne
  de relevé historique correspondante.
- **Toutes les extournes et miroirs supprimés** (0 restant) ; les écritures
  d'ouverture des banques sont revenues à leurs valeurs d'origine
  (BNP MAQ 72 340,02 / BQ1 CHÂTEL 1 700,00) et les soldes 512 sont
  strictement inchangés (contrôlés au centime avant/après).

## État restant (informatif)
- 511900 : débits ouverts = 62 lignes / 126 368,58 € (MAQ) et
  14 lignes / 7 914,09 € (Châtel) — encaissements historiques à rapprocher
  éventuellement avec les vieux relevés (backlog non bloquant).
- Journaux fichiers de travail : `passe_tri_*.json` (scratchpad session).

## À surveiller
- Les factures rouvertes redeviennent relançables — les clients concernés
  paieront pour la plupart courant septembre (lot du 31/07 à 30 jours).
- CELTAN : payée le 02/09 (rapprochée dans Odoo) mais non lettrée dans le GL
  Sage du 03/09 — Charlotte la lettrera avec le relevé de septembre.
