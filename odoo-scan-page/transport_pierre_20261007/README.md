# Transport des commandes pierre — phase 1 (07/10/2026) : devis et transporteurs

Mis en place en production par `transport_devis_setup.py apply` (test de bout en bout sur S12412 puis nettoyage) :

- étiquette de contact **Transporteur** (res.partner.category 13) sur GENDRON TRANSPORTS (18880) et TRANSPORTS P. FRECHOT (18876) ;
- article d'achat **Transport affrété (achat transporteur)** (product.product 8586, service, compte 624200) ;
- champs du devis (sale.order) : `x_mode_transport` (Nos camions / Transporteur extérieur / Enlèvement par le client),
  `x_transporteurs_ids`, `x_transporteur_id`, `x_transport_achat`, `x_ordre_transport_id` ;
- vue 8042 `sale.order.form.transport.pierre` (priorité 200, après la vue Studio 4889) : groupe « Transport de la commande (pierre) »
  sous « Demande de transport Maquignon », société 1 seulement ;
- action serveur 2118 « Devis : demander un tarif transport » (bouton du groupe) : une demande de prix par transporteur coché,
  description = commande, adresses, palettes (ou estimation à 1 500 kg), poids, volume, date souhaitée ; mail (modèle 27) si le
  transporteur a une adresse e-mail ; note dans le fil ; ouvre la liste des demandes (origin = n° de devis) ;
- automatisation 102 sur purchase.order (état = purchase) : report transporteur / prix HT / ordre de transport sur le devis,
  annulation des autres demandes de la commande, note dans le fil.

Phases suivantes : champs de suivi sur la palette, écran Expédition (scan du bon de colisage), lien BL/facture, livraison.

## Phase 2 (07/10/2026) : palettes et écran Expédition

- Champs stock.package : `x_exp_statut` (stock / chargee / enlevee / livree), `x_exp_mode`, `x_exp_transporteur_id`, `x_exp_camion`,
  `x_exp_chauffeur`, `x_exp_date`, `x_exp_par_id`, `x_exp_lot` (CHG-AAAAMMJJ-HHMM), `x_exp_lettre`, `x_livraison_date` ;
  vues Inventaire > Colis : 8043 (formulaire, groupe Expédition) et 8044 (liste, colonnes optionnelles).
- Pages web : `/expedition` (vue 8045, website.page 95) et `/expedition/liste?lot=…` (vue 8046, website.page 96, imprimable).
  Onglet « 🚚 Expédition » ajouté sur le poste de scan (7890) et la tablette (7907) ; menu Logistiques > Expédition palettes (1066).
- Relais : action 2104 `_expedition` (modes scanner / valider / annuler / lots) ; `expedition_setup.py`, `patch_relais_expedition.py`,
  `test_expedition_mock.py` (faux Odoo), `test_expedition_prod.py lecture|cycle <PACK>` (cycle = départ test sans mail puis annulation et nettoyage).
- Règles : palette clôturée et non vide seulement ; refus si déjà partie ; par commande : note dans le fil, tâche Commande Pierres
  → Expédié si tout est parti et si elle est encore avant cette étape ; mail au bureau (clé maquignon.palettes_alerte_email) avec la liste.

## Phase 3 (07/10/2026) : bon de livraison et facturation

- Au départ (`_exp_valider`), pour chaque commande du chargement : `_exp_lignes_livrees` calcule la quantité livrée par ligne
  (OF entier = toute la quantité de sa ligne, en m³ ou tonne ; répartition = prorata des pièces ; plafonné au reste à livrer),
  puis `_exp_bl` valide le transfert en attente (chaîne PICK → PACK → OUT si ancienne route) pour ces quantités :
  `quantity` + `picked=True` sur les mouvements chargés, les autres restent non prélevés, `button_validate` avec
  `skip_backorder` → Odoo crée le reliquat tout seul (mécanique vérifiée sur WH/INT/00008, transfert de test interne neutre).
  Transporteur (camion → delivery.carrier) et référence de suivi (lot, qui, palettes, lettre) écrits sur le BL.
- Les quantités livrées suivent la réalité : la facturation « sur quantités livrées » de Céline se base dessus.
- Paramètre système `maquignon.expedition_bl` = 0 pour désactiver ; mode relais `bl_plan` (lecture seule) pour contrôler.
- En cas d'erreur Odoo sur le BL, le départ reste enregistré et une note « BL non validé automatiquement : … » est posée sur la commande.

## Ajustement (07/10/2026) : le mode de transport vient du devis
- Page /expedition : on scanne d'abord ; le cadre « Transport (prérempli depuis le devis) » affiche « Prévu au devis S… : … »
  (mode `x_mode_transport`, transporteur, ou méthode de livraison → camion) et se préremplit ; les boutons ne servent qu'à corriger,
  avec alerte si le choix diffère du devis ou si le devis ne dit rien. Au départ, un devis sans mode reçoit le mode (et le transporteur) choisis.
- Constat : sur 65 commandes pierre confirmées depuis juillet, aucune n'a de méthode de livraison et une seule a une ligne transport ;
  la seule source fiable est le champ « Mode de transport » du devis, à renseigner par Céline (phase 1).

## Phase 4 (07/10/2026) : suivi livraison

- Relais 2104 : `livrer` (palettes ou n° de chargement → statut Livrée + `x_livraison_date`, notes commande « 📍 Livraison le … »
  et tâche, « commande entièrement livrée » quand plus rien n'est en fabrication ni en stock), `a_livrer` (palettes chargées sur nos
  camions, pour la tournée), `lots` enrichi (statut par palette, livrées), `annuler` sur une palette livrée = retour « chargée ».
- « Ma tournée » (app.py) : bloc « 📦 Palettes à livrer » sur chaque mission du même camion et du même client (palettes d'un autre
  client sur le même camion affichées une fois avec la mention), bouton « 📍 Palettes livrées » → POST `/tournee/livraison`
  (jeton de la mission, type livr) → mode `livrer` avec le nom du chauffeur.
- Écran /expedition : départs sur 10 jours, état par chargement (en cours / x livrées / livré le …), bouton « 📍 Marquer livré (n) »
  (transporteur extérieur ou nos camions), annulation d'une livraison ou d'un départ par palette.
- Page Suivi devis/commande (vue 7884) : ligne « 📦 N palette(s) : x en stock · y partie(s) · z livrée(s) · dernier départ … (transporteur ou camion) »
  sur chaque carte de commande ; sauvegarde `vue_7884.BEFORE_livraison.xml` / `AFTER_livraison.xml`.
- Enlèvement client : la palette est « Enlevée » au départ, pas d'étape livraison. Affrètement : Céline marque livré depuis
  l'écran Expédition (ou le statut sur la fiche Colis) quand le transporteur confirme.

## Sans code Python dans Odoo (07/10/2026, fin de journée)

Xavier : « tu as ajouté du code payant » (module « Maintenance par 100 lignes » de l'abonnement Odoo Online, 34,71 € HT
par tranche de 100 lignes et par mois). Les trois actions serveur Python du jour (2118 : 48 lignes, 2119 : 17, 2122 : 23)
n'ont plus de code : `transport_webhooks_setup.py apply` (env `WEBHOOK_TOKEN` = token du relais, `ODOO_URL`/`ODOO_DB`
pour une base de test) les convertit, `retour` remet le code archivé (`action_<id>_code.py`), `etat` contrôle.

- 2118 (bouton « Demander un tarif transport ») et 2122 (automatisation 103, mode de transport) = « Exécuter plusieurs
  actions » : note instantanée dans le fil (« Envoyer un e-mail » en mode Note, modèles de mail statiques « Transport
  pierre : note automatique (…) ») puis « Webhook » vers le relais ; 2119 (automatisation 102, demande de prix confirmée)
  = webhook seul. Filtres resserrés : 102 = état achat + article Transport affrété ; 103 = mode renseigné + société 1.
- Relais : route `/odoo/transport/<tarif|achat-confirme|mode-devis>?token=…` (`patch_relais_webhooks_transport.py`),
  réponse immédiate (Odoo n'attend qu'une seconde, `timeout=1`), traitement dans un thread, logique dans
  `transport_webhooks.py` (XML-RPC, mêmes notes qu'avant, numéros des demandes de prix en texte brut (`message_post` par RPC échappe le HTML), copie au vendeur du devis
  en plus de Céline). `&host=<base de test>` dans l'URL = tout se passe sur cette base.
- Différences visibles : la liste des demandes ne s'ouvre plus (le fil du devis donne leurs numéros, à ouvrir dans Achats) ; la ligne
  « Transport de pierres » apparaît quelques secondes après l'enregistrement (recharger le devis) ; la copie au
  « cliqueur » devient la copie au vendeur du devis (le webhook ne connaît pas l'utilisateur).
- Sécurité : une copie de la production est neutralisée par Odoo (`webhook_url` effacée sur toutes les actions webhook),
  donc aucune action sur une base de test ne touche la production ; sur une base de test voulue, relancer
  `transport_webhooks_setup.py apply` avec `ODOO_URL` de cette base (URL avec `&host=`).
- Tests : `test_transport_webhooks_mock.py` (faux Odoo, 12 cas) ; `test_webhooks_base_test.py <hôte> <S…>` (copie du
  devis, mode camions -> ligne à 0, demande de tarif -> P… + mail en attente, confirmation à 410 -> 574 sur le devis).
- Reste dans la base : 3 720 lignes dans 423 autres actions serveur (+ 320 dans 37 champs calculés), hors périmètre.

**Retour en arrière le 07/10/2026 au soir** (Xavier : « remets comme avant et économise du code sur autre chose ») : les trois actions ont
retrouvé leur code Python (`transport_webhooks_setup.py retour` : code archivé remis, enfants et modèles de mail supprimés, filtres
des automatisations d'origine) pour garder le comportement synchrone (liste des demandes ouverte, ligne visible tout de suite,
copie à la personne qui clique). La route `/odoo/transport/<quoi>` et `transport_webhooks.py` restent dans le relais, inutilisés.
L'économie de lignes se fait sur d'autres actions (voir `odoo-scan-page/crons_relais_20261007/`).
