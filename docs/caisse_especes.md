# Paiements en espèces — SARL MAQUIGNON

*Mis en place le 13/08/2026.*

## Utilisation

Sur une facture client validée : bouton **Payer** → journal **Espèces** → Enregistrer.
La facture passe directement à l'état **Payé** (plus de blocage « En paiement »).

## Configuration (base `maquignon`, société SARL MAQUIGNON)

- Journal **Espèces** (id 7, code CSH1, type caisse), compte 530001 Cash.
- Les deux méthodes de paiement du journal (entrante id 6 / sortante id 5) ont leur
  **compte de paiement** réglé sur 530001 (`account.payment.method.line.payment_account_id`).

C'est ce compte qui fait toute la différence : sans lui, Odoo 19 crée un paiement
« fantôme » sans écriture comptable, en attente d'un rapprochement bancaire qui
n'arrive jamais pour une caisse → la facture reste indéfiniment « En paiement ».
Avec lui, le paiement génère immédiatement son écriture (530001 ↔ 411) et le
lettrage est automatique.

## Régularisation de l'existant (13/08/2026)

12 paiements espèces « fantômes » (PAY00192 → PAY00269, avril-juin 2026) ont été
annulés puis réenregistrés par le nouveau circuit (écritures `PCSH1/26-27/0001` à
`0012`, mêmes dates et montants). Les 12 factures liées sont passées à « Payé ».

Cas particuliers :
- **FAC/26-27/0258 (DFG, 244,22 €)** avait un **doublon** de paiement
  (PAY00246 + PAY00261) : un seul a été réenregistré, le doublon PAY00261 est
  conservé à l'état « Annulé » pour trace.
- **FAC/26-27/0078 (191,26 €)** : 150 € en espèces (payé) + 41,26 € par banque BP —
  reste « En paiement » jusqu'au rapprochement du relevé BP (circuit bancaire normal).

## Autres sociétés

- **CARRIERE D'HAIMS** : même réglage appliqué le 13/08/2026 — journal Caisse
  (id 49), compte de paiement 4024 (Cash) sur les deux méthodes. Aucun paiement
  fantôme à régulariser.
- **CHATEL'GRANULATS** : passe par le module Caisse (PoS) — journal id 42 non touché.
- **DISTRI BETON** : pas d'espèces — journaux id 15/30 non touchés.
