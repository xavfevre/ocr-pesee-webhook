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
