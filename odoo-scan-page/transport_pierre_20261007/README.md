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
