# Factures : civilité, en-tête aperçu web, sections imbriquées (06/08/2026)

## 1. Civilité avant le nom du client (PDF + aperçu web)

**Symptôme** : « sur les factures PDF, il n'y a plus la civilité avant le nom ».
Le champ `x_studio_civilit_type_socit` (res.partner, sélection M. / Mme /
SARL / SAS…) est bien rempli sur les clients, et le devis l'affiche — mais le
modèle de facture ne l'avait jamais repris.

**Fausse piste (matinée)** : première insertion via un xpath unique
`//address[@t-field='o.partner_id']`. Un xpath QWeb ne s'applique qu'à la
**première** occurrence, or `account.report_invoice_document` contient
**trois branches** d'adresse selon la configuration de livraison :
`address_not_same_as_shipping`, `address_same_as_shipping`, `no_shipping`.
Quasi toutes les factures Maquignon ont livraison = client → branche 2 →
civilité jamais rendue. (Les deux rendus « réussis » pendant le debug
venaient d'états transitoires de priorités de vues, d'où une fausse piste
« cache Odoo » un moment envisagée.)

**Correctif** : vue « Facture - civilite avant nom client » (id **7973** en
prod, 7971 sur la base de test), héritant de la vue 2370, avec **trois
xpaths** — un par branche. Fichier :
`odoo-scan-page/report_facture_civilite_7973.xml`.

Vérifié en prod sur 3 factures (BLASZYK → SAS, GANDIN → M., ECO CONCEPT →
SARL), rendu stable sur plusieurs passages. Vérifié aussi en PDF sur la base
de test.

## 2. Aperçu web : logo et adresse société inversés

**Symptôme** : dans l'aperçu portail client d'une facture, l'adresse SARL
MAQUIGNON apparaît à gauche du logo (le PDF, lui, est correct).

**Cause** : la personnalisation Studio de la facture (vue 7867) injecte
`table.o_ignore_layout_styling { direction: rtl; }` pour inverser les
colonnes du corps (c'est ce qui place l'adresse client à droite). Le tableau
d'en-tête (logo + adresse société) porte la même classe. En PDF, wkhtmltopdf
rend l'en-tête dans un document séparé, sans ce style → en-tête intact. En
HTML (aperçu portail), tout est dans un seul document → le style déborde sur
l'en-tête et l'inverse.

**Correctif** : sélecteurs préfixés `.article` (le corps du document) dans la
vue 7867, prod + base de test. Le PDF est inchangé, l'aperçu web est remis à
l'endroit. Fichier : `odoo-scan-page/report_facture_7867.xml`.

## 3. Sections imbriquées perdues entre commande et facture

**Symptôme** : sur une commande à sections imbriquées (ex. S11263 :
« Fournisseur n° … - Chantier n° … » > « Commande n° … - BL n° … » >
« Bon n° … du … » > ligne produit), la facture générée ne reprend que la
section la plus proche de chaque ligne (« Bon n° … ») ; les niveaux parents
disparaissent.

**Cause** : mécanisme natif Odoo — la génération de facture ne mémorise
qu'une section « en cours » à la fois, sans notion de hiérarchie. Dès qu'il
y a plus d'un niveau de section consécutif, seul le dernier survit.

**Correctif (DÉPLOYÉ EN PROD le 06/08)** :
- Action serveur **2065** en prod (2063 sur la base de test) « Facturation :
  reprendre les sections imbriquées du bon de commande » : compare la
  facture avec sa/ses commande(s) d'origine (`invoice_origin`), détecte les
  sections parentes manquantes et les réinsère au bon endroit, puis
  reséquence proprement (pas de doublons, idempotent, ne touche jamais les
  montants, fonctionne sur facture validée). Code :
  `odoo-scan-page/action_sections_facture_2065.py`.
- Automatisation **base.automation 84** (prod et test) : déclenche l'action
  à chaque **création** de facture.
- Garde-fou ajouté après incident de rattrapage : une section parente est
  considérée déjà présente si elle est liée à la commande OU si son
  intitulé (préfixe avant « - ») figure déjà dans une section existante de
  la facture — indispensable pour les factures **réparées à la main** (ex.
  FAC/26-27/0585 : sections ajoutées/renommées manuellement sans lien ; le
  premier rattrapage avait créé des doublons, nettoyés depuis, et le re-run
  avec le garde-fou n'insère plus rien).
- Note v19 : `display_type` vaut `'product'` (et non `False`) sur les lignes
  produit — le filtre doit tester l'appartenance à
  `('line_section', 'line_note')`.

Tests validés sur la base de test : rattrapage de la facture de S11263,
idempotence (double exécution sans doublon), et bout-en-bout (duplication de
la commande → confirmation → facturation → la facture brouillon sort
directement complète avec ses 3 niveaux de sections).

**Rattrapage des factures déjà émises** : non lancé en masse — les factures
réparées manuellement sont désormais sans risque grâce au garde-fou, mais le
client n'a pas demandé de rattrapage global ; à faire au cas par cas sur
demande (exécuter l'action serveur 2065 sur la facture concernée).
