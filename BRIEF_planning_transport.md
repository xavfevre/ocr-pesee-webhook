# BRIEF — Planning Transport Maquignon + application chauffeur « Ma tournée »

> Document de passation à coller en début de conversation. Il décrit ce qui a déjà
> été construit et comment, pour continuer le travail sans tout redécouvrir.
> Les identifiants Odoo (login admin + mot de passe/clé API) et le WEBHOOK_SECRET
> Render sont à fournir séparément dans la conversation.

## 1. Contexte

- **Odoo v19 SaaS** : `https://maquignon.odoo.com`, base `maquignon`, 4 sociétés
  (1 = SARL MAQUIGNON, 2 = SAS DISTRI BETON VIENNE, 3 = CHATEL'GRANULATS, 4 = CARRIÈRE D'HAIMS).
- Les demandes de transport sont des **`project.task`** du projet **« Demande de transport »** (id 13).
  Champs clés : `x_studio_chauffeur` (m2o `hr.employee`), `x_studio_transport` (m2o `delivery.carrier` = véhicule),
  `planned_date_begin` / `date_deadline`, `partner_id` (client), `x_studio_adresse_de_chargement` (char),
  `x_studio_adresse_de_livraison_3` (text), `x_studio_statut_de_locr` (char), `x_studio_bon_scanne` (bool),
  `sale_line_id.order_id` ou `sale_order_id` → commande liée.
- **Feuille de travail** (worksheet FSM) : modèle custom **`x_project_task_worksheet_template_1`**,
  lien tâche = `x_project_task_id`. Photos : `x_studio_photo` (chargement), `x_studio_photo_1` (livraison),
  `x_studio_photo_bon` (bon de pesée → déclenche l'OCR existant via webhook Odoo).
- **Dépôt GitHub** : `xavfevre/ocr-pesee-webhook` (les vues Odoo sont copiées dans `odoo-scan-page/`,
  l'app Flask est `app.py` à la racine, déployée sur **Render** : `https://ocr-pesee-webhook.onrender.com`,
  build auto au merge sur `main`).

## 2. Plannings transport web (vues QWeb website dans Odoo)

Pages publiées côté website, éditées en écrivant `arch_db` de la vue `ir.ui.view` :

| Page | Vue Odoo | Fichier repo |
|---|---|---|
| Planning hebdo transport (`/model/tache`) | id **6671**, clé `website_studio.tache-4` | `odoo-scan-page/planning_transport_hebdo.xml` |
| Vue mois (`/planning-transport-mois`) | id **7883**, clé `website.planning_transport_mois` | `odoo-scan-page/planning_transport_mois.xml` |

Fonctionnement (hebdo) : tableau lignes = jours (7 j depuis lundi, `week_offset` en
paramètre), colonnes = véhicules (`x_studio_transport` actifs) + « SANS TRANSPORT ».
Vignettes par tâche avec bandeau couleur chauffeur (palette hachée sur le nom),
badge de statut calculé côté QWeb depuis la commande liée :
annulé (nom d'étape contient « annul ») → sinon factures postées (`_so.invoice_ids`,
`payment_state` → PAYÉ/FACTURÉ) → facture brouillon (`state='draft'`) = badge **jaune #eab308**
→ `invoice_status == 'to invoice'` = À FACTURER. Filtre statut JS via `data-status`
+ `localStorage`. Drag & drop des vignettes = write `planned_date_begin` +
`x_studio_transport` via `/web/dataset/call_kw` (session navigateur). Liens photos
worksheet (Bon/Charge/Livr) construits via maps `bon_map/pc_map/liv_map` en début de vue.

## 3. Application chauffeur « Ma tournée » (Flask, sans compte Odoo)

But : chauffeurs **occasionnels** sur téléphone perso, **sans identifiants Odoo**.
Implémentée dans `app.py` du dépôt (même app que le webhook OCR), déployée sur Render.
Les identifiants Odoo restent côté serveur (env vars `ODOO_URL/ODOO_DB/ODOO_USER/ODOO_PASSWORD`),
l'app lit/écrit par XML-RPC avec ce compte technique.

### Routes
- **`GET /ma-tournee?c=<employee_id>&s=<signature>`** : page mobile de la tournée du chauffeur.
  - Sécurité : signature HMAC-SHA256 `driver:<id>` avec `WEBHOOK_SECRET` (20 hex).
    Sans signature valide → 403. **Un chauffeur ne peut pas voir la tournée d'un autre.**
  - Contenu : missions `project.task` du projet « Demande de transport »,
    `x_studio_chauffeur = c`, `planned_date_begin >= aujourd'hui`, groupées par jour.
  - Navigation **un jour à la fois** avec barre collante ◀ / jour / ▶ (blocs
    `.dayblock` masqués/affichés en JS, défaut = aujourd'hui, bandeau orange).
  - Vignette mission : horaire début→fin, étiquettes, client, adresses de
    **chargement** et **livraison** avec liens Google Maps individuels, véhicule,
    statut OCR/poids net.
  - Actions photo : gros bouton **« 📷 Scanner le bon de pesée »** (`x_studio_photo_bon`,
    déclenche l'OCR) + deux boutons **Photo chargt** / **Photo livr.**
    (`x_studio_photo` / `x_studio_photo_1`). `<input type="file" accept="image/*"
    capture="environment">` → FileReader base64 → POST JSON.
- **`POST /tournee/upload`** : `{task_id, kind∈{bon,charge,livr}, token, image}`.
  Token HMAC par (tâche, type). Redimensionne (PIL, JPEG 1024px), **crée la worksheet
  si absente** puis écrit le champ photo.
- **`GET /tournee/liens?token=<WEBHOOK_SECRET>`** : page ADMIN listant le lien signé
  de chaque chauffeur (base URL auto-détectée) — à distribuer par SMS/WhatsApp.

### Points de conception
- Chauffeur = `hr.employee` (28 fiches, PAS de compte utilisateur nécessaire).
- Lien mémorisable en favori ; ajouter un chauffeur = l'assigner à une mission
  puis récupérer son lien sur `/tournee/liens` (rien à redéployer).
- Déploiement : merge sur `main` → Render rebuild (~1-2 min). `requirements.txt` :
  flask, mistralai, gunicorn, Pillow.

## 4. Pièges techniques Odoo v19 SaaS (importants)

1. **Bug SaaS `StudioMixin.write()`** : les `write()` XML-RPC échouent sur beaucoup de
   modèles (« missing 1 required positional argument: 'vals' »). **Contournement** :
   passer par la session web JSON-RPC (`POST /web/session/authenticate` puis
   `/web/dataset/call_kw`) — c'est ce que fait toute l'automatisation de ce projet.
2. `safe_eval` (actions serveur, champs calculés) : **`import` interdit** ;
   `datetime` est pré-injecté ; pour du SQL direct utiliser `env.cr.execute(...)`.
3. **Apostrophes françaises dans les expressions QWeb** (`t-value`, listes Python) :
   utiliser l'apostrophe typographique `’` sinon erreur 500.
4. En v19, vues search : le wrapper `<group>` autour des filtres group_by est
   **invalide** — mettre les `<filter context="{'group_by': ...}">` à plat.
5. Le **mode Tableaux de bord** (spreadsheet dashboard) n'affiche **que la première
   feuille** (pas d'onglets) → tout empiler sur une seule feuille.
6. Modifier une vue website = `ir.ui.view.write({'arch_db': ...})` ; toujours
   sauvegarder l'ancienne version et copier la nouvelle dans le dépôt.

## 5. Ce qui existe déjà autour (ne pas refaire)

- Statut **« Facture brouillon » jaune** ajouté aux plannings hebdo + mois (badge + filtre).
- Page opérateurs atelier `/vue-operateur` (vue 7907) + `/scan` (vue 7890) — hors périmètre transport.
- Webhook OCR bon de pesée (Mistral Vision) : `POST /ocr-pesee` déclenché par webhook
  Odoo quand `x_studio_photo_bon` est rempli ; écrit les champs pesée + statut OCR.
- Menu Odoo « Décharge » (livre de police + DAP) — sujet distinct.

## 6. Demande type pour la suite

« En te basant sur ce brief : [décrire l'évolution voulue — ex. ajouter un bouton
"Livré" sur Ma tournée qui avance l'étape de la mission / notifier le bureau quand
le bon est scanné / etc.]. Les identifiants Odoo et le WEBHOOK_SECRET sont : … »
