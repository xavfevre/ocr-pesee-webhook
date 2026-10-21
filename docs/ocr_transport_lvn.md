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
