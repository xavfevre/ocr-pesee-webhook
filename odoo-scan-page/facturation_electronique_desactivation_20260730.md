# Facturation électronique — champ « eInvoice format » vidé le 30/07/2026

## Contexte

Odoo calcule automatiquement un format de facturation électronique
(`invoice_edi_format` sur `res.partner`) pour les contacts français,
en anticipation de la réforme de facturation électronique B2B. Ce champ
n'était piloté nulle part côté groupe : il se remplissait tout seul
(« Facturation électronique française (UBL 2.1) ») sur chaque contact
français dès sa création.

## Action effectuée

**Le champ a été vidé sur les 7 848 contacts de la base**, toutes sociétés
confondues (SARL MAQUIGNON, DISTRI BETON VIENNE, CHATEL'GRANULATS,
CARRIERE D'HAIMS, SFM), clients comme fournisseurs.

- 319 clients avec facture confirmée (`customer_rank > 0`) — 1er passage.
- 600 clients au total en élargissant aux étiquettes par société
  (Client Maquignon / Chatel / Haims / Distri Beton) — 2ᵉ passage, attrape
  aussi les contacts tagués client mais sans facture encore émise (ex.
  1DAY EXPRESS).
- 88 contacts restants (fournisseurs, contacts sans étiquette) — 3ᵉ passage,
  périmètre total.
- 2 contacts individuels rattachés à une fiche société (ex. MESTIVIER)
  réaffichaient le format hérité de leur société mère : viser aussi la
  société mère résout l'héritage.

Le champ étant calculé (non stocké) tant qu'aucune valeur n'est forcée,
le vidage écrit une valeur explicite « aucun format » (`invoice_edi_format
_store = 'none'`) qui bloque le recalcul automatique.

## Remise en route prévue

**À partir du 1er septembre 2026**, la facturation électronique sera
réactivée **au fur et à mesure**, société par société / client par client,
selon la décision du groupe — pas en un seul bloc. Pour réactiver un
contact : rouvrir sa fiche, onglet Comptabilité, champ « format eInvoice »,
sélectionner le format voulu (UBL 2.1 pour la France).

Aucune automatisation de réactivation n'a été mise en place à ce stade —
la remise en route se fait manuellement, contact par contact, selon le
calendrier du groupe.
