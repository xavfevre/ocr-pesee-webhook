# Site « devis instantané » Chatel'Granulats (`chatel_devis/`)

Demande de Xavier du 21/10/2026 : l'équivalent de koncrete.fr pour Chatel'Granulats (société Odoo 3).
Brief d'origine : `BRIEF_chatel_devis_instant.md`.

## Adresse

- Relais : `https://ocr-pesee-webhook.onrender.com/devis/`
- Domaine prévu : `https://devis.chatelgranulats.com` (CNAME `devis` → `ocr-pesee-webhook.onrender.com`, puis
  domaine personnalisé dans Render). Sur ce domaine, `/` redirige vers `/devis/` ; `robots.txt` et `sitemap.xml`
  sont servis à la racine.

## Choix validés par Xavier (21/10/2026)

| Sujet | Choix |
|---|---|
| Services | Livraison de granulats, évacuation de déblais inertes, affrètement de camion, location de benne |
| Transport | €/km/tonne depuis Le Pautron, zone 50 km (au-delà : « nous consulter ») |
| Prix publics | Fourchette type Koncrete (« 23 € – 25 € HT/T prix livré »), prix exact au récapitulatif |
| Paiement | Aucun paiement en ligne : tout en devis |
| Réception | Devis Odoo brouillon société 3 + e-mail à granulats@maquignon.com + accusé de réception au client |

## Pages

Accueil, `/parcours` (4 étapes : service + adresse, produit, quantité / camion / date, récapitulatif + coordonnées),
`/produits`, `/services`, `/usages`, `/pour-qui`, `/faq`, `/contact`, `/recrutement`, `/espace-pro`,
`/ressources` + 4 articles, `/mentions-legales`, `/cgv` (texte à faire valider avant mise en ligne).

## Données Odoo (XML-RPC, identifiants du relais)

- Catalogue : `product.product` vendables, société 3 ou communs, unité « Tonne », hors taxes/transport/reprise
  (regex `exclure`). Prix = liste `liste_public` (3 « Particuliers Avril 2026 ») évaluée localement
  (variante > modèle > catégorie > globale). Familles déduites de la catégorie et du nom (`_famille`).
- Photos : `product.template.image_512` via `/devis/img/<tmpl>` (cache 24 h), pictogramme coloré sinon.
- Cache mémoire 10 min (catalogue, réglages), rafraîchi en arrière-plan : aucune page n'attend Odoo.
  Vider tout de suite : `/devis/api/rafraichir?k=<maquignon.tarifs_key>`.
- Envoi d'une demande : `res.partner` retrouvé par e-mail (sinon créé, société 3) + adresse de livraison
  « Chantier … », `sale.order` brouillon (origine `devis.chatelgranulats.com`, référence client « Demande web »,
  date d'engagement = date + créneau, note = récapitulatif), e-mails via `mail.mail` (expéditeur = e-mail de la société).

## Réglages : paramètre Odoo `chatel.devis_cfg`

JSON fusionné avec `CFG_DEFAUT` (`chatel_devis/app.py`), relu toutes les 10 min. Clés utiles :

- `camions` : `code`, `nom`, `charge` (t), `mini_t` (tonnes facturées mini), `fixe_t` (€/t), `eur_km_t` (€/km/t).
  Transport = max(tonnes, mini_t) × (fixe_t + eur_km_t × km aller), km >= `km_mini`.
- `zone_km`, `km_mini`, `forfait_mini`, `depart` {lat, lon}.
- `contributions` : `[{"id": …, "nom": …, "eur_t": …}]` ajoutées par tonne (Eco contribution, énergie…).
- `affretement` (prix `demi` / `jour` par camion) et `bennes` (`prix`, `jour_sup`) : `null` = « sur devis ».
- `delai_jours`, `jours` (0 = lundi), `creneaux`, `densites` (conversion m³ → t), `usages` (filtres par regex).
- `email_bureau`, `accuse_client`, `test` (true = rien n'est écrit dans Odoo).

## Anti-abus

Pot de miel, jeton signé (4 s mini entre l'affichage et l'envoi), 6 envois / heure / IP.

## SEO

Titre et description par page (`SEO`), balise canonical sur le domaine public, Open Graph, données structurées
`HomeAndConstructionBusiness` (toutes les pages), `FAQPage` (FAQ), `Article` (ressources), `sitemap.xml`,
`robots.txt`, un seul H1 par page, pages légales en `noindex`.

## Test local

`run_local.py` (scratchpad) monte le blueprint seul avec un faux Odoo (20 articles fictifs, mode test) ;
avec `ODOO_URL/ODOO_DB/ODOO_USER/ODOO_PASSWORD` dans l'environnement, il lit le vrai catalogue.
