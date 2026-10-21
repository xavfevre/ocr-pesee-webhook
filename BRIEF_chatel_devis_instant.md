# BRIEF — Site « devis instantané » Chatel'Granulats (équivalent de koncrete.fr)

> Document de passation à lire en début de conversation (écrit le 21/10/2026 à la demande de Xavier :
> « peux-tu me faire pour Chatel Granulats l'équivalent de ce site », « fais des pages supplémentaires »).
> Les identifiants Odoo sont à fournir dans la conversation (jamais dans les fichiers) ; la mémoire
> persistante `C:\Users\xavfe\.claude\projects\C--Users-xavfe\memory\maquignon-odoo-setup.md` décrit
> le contexte Odoo/relais et la façon de travailler de Xavier (`xavier-working-style.md`).

## 1. Ce que Xavier veut

Un site pour **CHATEL'GRANULATS** (société Odoo 3, Le Pautron 86100 Châtellerault, 05 49 90 57 62,
granulats@maquignon.com, site actuel www.chatelgranulats.com) qui reproduit le parcours de
**https://www.koncrete.fr/** (marketplace de granulats livrés, 2 000 fournisseurs, livraison 24/48 h) :

- **Accueil** : titre accrocheur, un bloc « Service + adresse de livraison → Obtenir un devis », badges
  (devis en 2 min, livraison 24/48 h), avis Google, étapes 1 à 6, familles de produits, « Pour qui ? »
  (acheteur / fournisseur / transporteur), FAQ, témoignages, articles.
- **Parcours devis instantané en 4 étapes** (`apps.koncrete.fr/devis-instant/parcours`) :
  1. **Service** : Livraison (granulats) · Évacuation (déblais) · Affrètement (camion) · Location (benne) ;
  2. **Produit** : colonne de familles (Sable, Gravier, Caillou, Grave, Terre), recherche, filtres par
     usage (Tranchée canalisation, Tranchée technique, Béton, …), liste ou cartes, chaque ligne =
     photo, nom (ex. « Sable 0/4 concassé »), mention « Déclassé », **fourchette de prix livré HT/T**
     (ex. 18 € – 24 € HT/T « Prix livré ») ;
  3. **Volume** : quantité en tonnes (ou m³ converti), choix du camion (6x4 13 t, 8x4 17 t,
     semi 30 t), date et créneau de livraison (6 h 30 – 16 h 30, J+2/3 ouvrés) ;
  4. **Récapitulatif** : prix matériau + transport, commande, paiement ou compte pro (tarifs négociés).
- **Pages supplémentaires** demandées : Services, Usages, Pour qui ?, Blog/Ressources (ex. « ISDI,
  ISDND, ISDD : quelles différences », « Double flux : livrer puis évacuer avec le même camion »),
  Contact, Recrutement, Espace pro, FAQ, mentions légales / CGV.

Pour Chatel'Granulats, périmètre réaliste v1 : **Livraison de granulats** (propres produits) +
**Évacuation de déblais inertes** (Chatel reprend les déblais : article « Reprise deblais inerte »
2574, 8,75 €/t) ; affrètement et location de benne seulement si Xavier le confirme.

## 2. Données Odoo disponibles (base `maquignon`, https://maquignon.odoo.com, XML-RPC)

- Société 3 CHATEL'GRANULATS. **162 articles vendus à la tonne** (sale_ok, société 3 ou communs) :
  Sable et Granulats 37, Concassé Déco 63, GALETS 43, Ardoise et Schiste 6, Dallage et pavage 6,
  DIVERS 3, Destockage 1 (+ Contribution Energie et Eco Contribution : taxes, à exclure des listes).
  Prix de base `list_price` en €/t HT ; listes de prix : 3 « Particuliers Avril 2026 »,
  304 « Tarif PRO Avril 2026 », 284 « Tarif PRO 2026 », 305 « Remise Thales 5 % ».
  Articles transport : 2544 « Transport » (forfait), 2575 « Transport à la tonne », 3228 location semi.
- Sites web Odoo existants (module `website` + `website_sale`, `delivery`, `payment_stripe`) :
  1 Maquignon (maquignon.com), 2 Carrière d'Haims (carrierehaims.fr), 3 Châtel'Béton (chatelbeton.fr,
  société 2), **4 Chatel Granulats (chatelgranulats.com, société 3)**, 5 « https://www.koncrete.fr/ »
  (rattaché à Carrière d'Haims — créé récemment, probablement par Xavier en explorant : à clarifier
  avec lui, sans doute à supprimer). Fournisseurs de paiement actifs pour Chatel'Granulats : **Stripe**
  (enabled) et virement. Donc un **paiement en ligne Stripe est déjà possible** via Odoo.
- Clients : fiches `res.partner` société 3, codes `CGxxxxx` ; comptes portail possibles (Espace pro).
- Pont-bascule Chatel : page `/bascule/?site=chatel` du relais (pesées `x_pesee`, bon de commande
  journalier par client) — une commande web livrée pourra être rapprochée des pesées plus tard.

## 3. Où construire : relais Render (recommandé) + Odoo en arrière-plan

Règle de la maison : **pas de code personnalisé dans Odoo** (chaque ligne de code / JS / XML importé
est facturée par Odoo Online, compteur réduit à grand-peine le 21/10/2026). Toute la logique vit
dans le dépôt **`xavfevre/ocr-pesee-webhook`** (Flask, déployé automatiquement sur Render au merge sur
`main`, `https://ocr-pesee-webhook.onrender.com`, `/health` renvoie le commit) ; Odoo sert de base
(articles, prix, clients, commandes) par XML-RPC avec les identifiants du relais (variables d'env
`ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD` sur Render).

Patron à copier : `tarifs_pierres.py` + `tarifs_pierres_page.html` (blueprint Flask + page HTML/JS
autonome, API JSON `api/...`, jeton `?k=<ir.config_parameter>`), `bascule_web.py` + `bascule_page.html`
(même structure, SITES multi-sociétés). Enregistrement des blueprints dans `app.py` (vers les lignes
1500-1560 : `app.register_blueprint(bp, url_prefix="/…")`).

Architecture proposée :
- blueprint **`/devis`** (ou `/chatel`) : pages publiques (accueil, catalogue, parcours 4 étapes,
  pages annexes), rendu côté serveur ou HTML/JS statique + API JSON ;
- **catalogue** lu dans Odoo (articles société 3 à la tonne, catégories → familles, photos
  `image_1920`, prix selon liste « Particuliers » ou « PRO » si connecté) avec cache mémoire
  (rafraîchi toutes les 10 min) pour la vitesse — Xavier insiste sur le **temps de réponse** ;
- **prix livré** = prix matériau + transport calculé par **distance** depuis Le Pautron (géocodage de
  l'adresse : Nominatim/OSRM gratuits ou Google si Xavier a une clé) × barème €/km/t par type de camion,
  avec minimum de commande et plafond de zone (à faire valider par Xavier) ;
- **commande** : création d'un `sale.order` société 3 (client créé ou retrouvé par e-mail/téléphone,
  lignes article + transport, date de livraison, créneau en note) puis **paiement** : lien de paiement
  Stripe via le portail Odoo (`/my/orders/<id>` + `access_token`) ou commande « à régler à la
  livraison » pour les pros avec compte ; e-mail de confirmation au client et à granulats@maquignon.com ;
- **espace pro** : connexion portail Odoo (tarif PRO) ou simple formulaire « être rappelé » en v1 ;
- domaine : sous-domaine du site existant (ex. `devis.chatelgranulats.com` → CNAME vers Render,
  domaine personnalisé Render) ou lien depuis le site Odoo chatelgranulats.com.

## 4. Questions à poser à Xavier avant de coder (réponses courtes attendues)

1. Zone de livraison (rayon en km autour de Châtellerault ? départements ?) et barème transport :
   camions disponibles (6x4 / 8x4 / semi, charges utiles), prix par tour ou par km et par tonne,
   minimum de commande (tonnes), délai (J+1 ? J+2 ?), créneaux.
2. Prix affichés : liste « Particuliers Avril 2026 » pour le public, « Tarif PRO » après connexion ?
   Afficher une fourchette (comme Koncrete) ou un prix exact ?
3. Services v1 : livraison + évacuation de déblais inertes ? affrètement / location benne ?
4. Paiement : Stripe en ligne obligatoire pour les particuliers ? pros à 30 jours avec compte ?
5. Qui reçoit les commandes (Delphine SPIQUEL, granulats@maquignon.com) et comment (e-mail + commande
   Odoo en devis à confirmer) ; faut-il créer la tâche transport (projet 13, voir BRIEF_planning_transport.md) ?
6. Contenu : textes, photos produits (image_1920 dans Odoo ?), logo Chatel'Granulats, avis Google,
   articles de blog ; le site web Odoo n° 5 nommé « koncrete.fr » sur Haims est-il à supprimer ?
7. Nom de domaine / hébergement : sous-domaine du site Chatel ou remplacement complet du site ?

## 5. Façon de travailler (rappels)

- Français, phrases courtes, validations rapides, **boutons visibles** et parcours simples
  (« il n'y a pas que des prix Nobel »), vérifier le temps de réponse de chaque page.
- Identifiants Odoo uniquement en variables d'environnement sur la ligne de commande
  (`ODOO_USER=… ODOO_PWD=… python script.py`), jamais écrits dans un fichier ni dans le dépôt.
- Ne jamais envoyer d'e-mail ; préparer des brouillons que Xavier envoie.
- Commits en français, message terminé par `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` ;
  après le push, attendre que `/health` renvoie le nouveau commit avant de tester en ligne.
- Documenter dans `docs/` (un fichier Markdown par outil) et mettre à jour la mémoire persistante.
