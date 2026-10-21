# OCR transport : N° LVN (lettre de voiture papier) — 21/10/2026

Demande de Xavier : « pour le transport on récupère le numéro de bon, est-il possible de
récupérer le numéro de LVN qui se trouve sur une autre image ? »

## Ce qui se passe maintenant

1. Le chauffeur envoie ses photos depuis « Ma tournée » (ou la feuille de travail) :
   chargement (`x_studio_photo`, souvent la lettre de voiture), bon de pesée (`x_studio_photo_bon`),
   livraison (`x_studio_photo_1`).
2. L'automatisation Odoo 45 déclenche `/ocr-pesee` à l'arrivée du bon : OCR Mistral du bon comme avant
   (numéro, poids, client…), puis **recherche du N° LVN** :
   - si la pièce « bon » est elle-même une lettre de voiture, son numéro est le LVN ;
   - sinon les autres photos passent à Mistral (chargement d'abord, 2 photos maximum, jamais deux fois la
     même image) ; la première reconnue comme lettre de voiture donne le numéro.
3. Résultat écrit dans **`x_lvn`** sur la feuille (après « Numero Bon ») et sur la tâche (après « Km à vide »,
   libellé « N° LVN (papier) »), et ajouté au statut OCR : « ✅ OCR terminé — Poids net : 27520 kg · LVN 27881 ».
4. Photo de chargement envoyée **après** l'OCR du bon : l'upload « charge » de Ma tournée lance la recherche
   du LVN tout seul (si le statut est ✅ et le LVN vide).
5. Reprise manuelle : `POST /ocr-lvn {"_id": <feuille>}` avec l'en-tête `X-Webhook-Secret` (même secret que
   l'action webhook 1729) — tâche de fond, résultat en moins d'une minute.

Le champ `x_studio_lettre_de_voiture_n` (n° CMR généré par la séquence 122) n'est pas touché.

## Reprise de l'historique

- Feuilles dont le bon était déjà une lettre de voiture (`x_studio_type_document = lettre_voiture`) :
  `x_lvn` renseigné directement depuis le numéro de bon (156 feuilles, 21/10/2026).
- Feuilles avec bon de pesée + photo de chargement sans LVN : 496 au 21/10/2026, OCR nécessaire
  (un appel Mistral par feuille, à lancer feuille par feuille via `/ocr-lvn` si Xavier le demande).

Exemple vérifié : feuille 5090 / tâche 7391 « CHATEL GRANULATS - BAILLY », LVN 27881 lu sur la photo de
chargement en 45 s. Réglages Odoo : `pa_test/lvn_setup.py` (champs 54756/54758, vues 8054/8056).

## Où le N° LVN est repris (demande « regarde les automatisations qui en découlent : bons de commande, factures, pages web »)

- **Bon de commande** : la section « Bon n°… | date | client | véhicule | poids » reçoit « | LVN n » —
  à l'OCR (`_section_name(..., lvn)`), à l'arrivée tardive du LVN (`_section_depuis_feuille` après `_ecrire_lvn`,
  via `sale_line_id` de la tâche), sur la route `/add-section`, dans les BC générés par les boutons du planning
  (`web_actions.py` : `_avec_lvn` sur SEDE Veolia et sur les BC par bouton 2081) et dans le bouton Odoo
  « Bon de pesée » des commandes (action 1615, 2 lignes ajoutées). Pas de doublon quand le bon est lui-même la LVN.
- **Facture** : la section est recopiée sur la facture créée depuis la commande (lignes de section Odoo), donc le
  LVN y figure dès que la section est à jour avant facturation. Le message « Données bon de pesée » posté sur la
  commande mentionne aussi « N° LVN ».
- **Rapport feuille de travail** (vue 4261, envoyé aux clients type Veolia) : ligne « N° LVN (papier) » sous
  « Lettre de voiture N° » (vue héritée 8058).
- **Pages web** (vues QWeb website) : `bon_map` contient désormais la feuille entière ; planning transport jour
  (7967 + carte 7966) et page Tâche (6671) affichent « 📎 Bon n°33990 · LVN 27881 », plannings mois transport
  (7883) et TP (7882) mettent les numéros dans l'infobulle du 📎. Copies dans `odoo-scan-page/lvn_20261021/`.

