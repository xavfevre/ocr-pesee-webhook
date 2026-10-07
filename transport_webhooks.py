# -*- coding: utf-8 -*-
"""Webhooks Odoo « transport des commandes pierre » (07/10/2026).

Les actions serveur 2118 (bouton « Demander un tarif transport » du devis), 2119 (automatisation 102 : demande de prix
transport confirmée) et 2122 (automatisation 103 : mode de transport du devis) n'ont plus de code Python dans Odoo
(compteur « Maintenance par 100 lignes » de l'abonnement) : ce sont des webhooks natifs vers /odoo/transport/<quoi>
(app.py) et la logique d'origine (odoo-scan-page/transport_pierre_20261007/transport_devis_setup.py et
transport_ligne_devis_setup.py) est portée ici en XML-RPC.
Payload Odoo : {"_model": ..., "_id": ..., "_action": ..., champs choisis}. Compte rendu : notes dans le fil du devis.
"""
from web_actions import WebErreur, EXP_TRANSPORT_PRODUITS, _creer, _note, _param

TR_PRODUIT_ACHAT = 8586                   # « Transport affrété (achat transporteur) » (service, compte 624200)
TR_TPL_RFQ = 27                           # modèle de mail « Purchase: Request For Quotation »
TR_VARIANTES = EXP_TRANSPORT_PRODUITS     # « Transport de pierres » (forfaits)
TR_DEFAUT = 5899                          # « Transport de pierres (Forfait Palettes) »
TR_NOM_LIGNE = 'Transport de pierres (Forfait Palettes)'
TR_ENLEVEMENT = 'Carrières Maquignon, 51 rue du Prieuré, 86230 Usseau'
TR_ETATS_DEVIS = ('draft', 'sent', 'sale')


def transport_webhook(call, quoi, donnees):
    """Point d'entrée (app.py /odoo/transport/<quoi>). Renvoie un compte rendu court pour le journal Render."""
    rid = int(donnees.get('_id') or 0)
    modele = donnees.get('_model') or ''
    if not rid:
        raise WebErreur('webhook %s : _id absent' % quoi)
    if quoi == 'tarif' and modele == 'sale.order':
        return tarif(call, rid)
    if quoi == 'achat-confirme' and modele == 'purchase.order':
        return achat_confirme(call, rid)
    if quoi == 'mode-devis' and modele == 'sale.order':
        return mode_devis(call, rid)
    raise WebErreur('webhook %s : modèle %s inattendu' % (quoi, modele))


def _sans_retour(fn):
    """Méthodes Odoo sans valeur de retour (button_cancel, parfois send_mail) : XML-RPC répond « cannot marshal None »
    alors que l'opération a réussi."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        if 'cannot marshal None' in str(e):
            return None
        raise


def _fr(val):
    """'2026-10-15' ou '2026-10-15 10:00:00' -> '15/10/2026'."""
    val = str(val or '')
    return '%s/%s/%s' % (val[8:10], val[5:7], val[0:4]) if len(val) >= 10 else 'à convenir'


def _marge(call):
    try:
        pct = float(str(_param(call, 'maquignon.transport_marge_pct', '40') or 0).replace(',', '.'))
    except Exception:  # noqa: BLE001
        pct = 40.0
    return 1.0 + pct / 100.0


def _lignes(call, so_id):
    return call('sale.order.line', 'search_read', [['order_id', '=', so_id]],
                fields=['display_type', 'product_id', 'name', 'sequence', 'price_unit', 'product_uom_qty',
                        'x_studio_poids', 'x_studio_vol', 'x_studio_palettes'], order='sequence, id')


def _existantes(lignes):
    return [l for l in lignes if not l['display_type'] and l['product_id'] and l['product_id'][0] in TR_VARIANTES]


def _vide(l):
    return l['price_unit'] in (0.0, 1.0)


def _ligne_transport(call, so_id, lignes, nom, prix):
    """Ligne « Transport de pierres » juste après la dernière ligne produit ; l'éco-contribution et les notes de fin
    (prix départ carrière, acompte : séquences >= 10000) sont décalées d'un cran."""
    produits = [l for l in lignes if not l['display_type'] and 'Eco-contribution' not in (l['name'] or '')]
    seq = max([l['sequence'] for l in produits] or [10]) + 1
    par_seq = {}
    for l in lignes:
        if l['sequence'] >= seq:
            par_seq.setdefault(l['sequence'], []).append(l['id'])
    for s, ids in par_seq.items():
        call('sale.order.line', 'write', ids, {'sequence': s + 1})
    return _creer(call, 'sale.order.line', {'order_id': so_id, 'product_id': TR_DEFAUT, 'name': nom,
                                            'product_uom_qty': 1.0, 'price_unit': prix, 'sequence': seq})


# ─── 2118 · bouton « Demander un tarif transport » ───────────────────────────────────────────────────────────────────

def tarif(call, so_id):
    """Une demande de prix (Achats) par transporteur coché, description = commande, enlèvement, livraison, palettes,
    poids, volume, date ; mail (modèle 27) si le transporteur a une adresse, copie à maquignon.transport_tarif_cc et au
    vendeur du devis ; compte rendu avec liens dans le fil du devis. Idempotent : une demande en cours par transporteur."""
    so = call('sale.order', 'read', [so_id], ['name', 'partner_id', 'partner_shipping_id', 'company_id', 'x_mode_transport',
                                            'x_transporteurs_ids', 'user_id', 'x_studio_date_de_livraison_souhait', 'commitment_date'])[0]
    if so['x_mode_transport'] != 'exterieur':
        _note(call, 'sale.order', so_id, "⚠️ Demande de tarif transport non lancée : mettez d'abord « Mode de transport » sur « Transporteur extérieur ».")
        return 'refus : mode %s' % so['x_mode_transport']
    if not so['x_transporteurs_ids']:
        _note(call, 'sale.order', so_id, "⚠️ Demande de tarif transport non lancée : cochez au moins un transporteur à consulter.")
        return 'refus : aucun transporteur coché'
    lignes = [l for l in _lignes(call, so_id) if not l['display_type'] and l['product_id']]
    types = {}
    if lignes:
        types = {p['id']: p['type'] for p in call('product.product', 'read', sorted({l['product_id'][0] for l in lignes}), ['type'])}
    lignes = [l for l in lignes if types.get(l['product_id'][0]) != 'service']
    poids = sum((l['x_studio_poids'] or 0.0) for l in lignes)
    vol = sum((l['x_studio_vol'] or 0.0) for l in lignes)
    palettes = sorted({(l['x_studio_palettes'] or '').strip() for l in lignes if (l['x_studio_palettes'] or '').strip()})
    adr = call('res.partner', 'read', [(so['partner_shipping_id'] or so['partner_id'])[0]], ['name', 'street', 'street2', 'zip', 'city'])[0]
    adresse = ', '.join([t for t in [adr['name'], adr['street'], adr['street2'], ' '.join([t2 for t2 in [adr['zip'], adr['city']] if t2])] if t])
    date = so['x_studio_date_de_livraison_souhait'] or so['commitment_date']
    desc = chr(10).join([
        'Transport de pierres - commande %s (%s)' % (so['name'], so['partner_id'][1]),
        'Enlèvement : ' + TR_ENLEVEMENT,
        'Livraison : ' + adresse,
        'Palettes : ' + (('%d (%s)' % (len(palettes), ', '.join(palettes))) if palettes
                         else ('environ %d (sur la base de 1 500 kg par palette)' % max(1, -(-int(poids) // 1500)))),
        'Poids total estimé : %.0f kg - volume : %.2f m³' % (poids, vol),
        'Date de livraison souhaitée : ' + _fr(date),
        'Merci de nous indiquer votre tarif HT et votre délai.'])
    cc = [a.strip() for a in str(_param(call, 'maquignon.transport_tarif_cc', 'celine@maquignon.com') or '').split(',') if a.strip()]
    if so['user_id']:
        vendeur = call('res.users', 'read', [so['user_id'][0]], ['email'])[0]['email']
        if vendeur and vendeur not in cc:
            cc.append(vendeur)
    crees, envoyes, sans_mail = [], [], []
    for t in call('res.partner', 'read', so['x_transporteurs_ids'], ['name', 'email']):
        if call('purchase.order', 'search', [['origin', '=', so['name']], ['partner_id', '=', t['id']], ['state', 'in', ['draft', 'sent']]], limit=1):
            continue
        po_id = _creer(call, 'purchase.order', {'partner_id': t['id'], 'origin': so['name'], 'company_id': so['company_id'][0],
                                                'order_line': [(0, 0, {'product_id': TR_PRODUIT_ACHAT, 'name': desc, 'product_qty': 1.0, 'price_unit': 0.0})]})
        crees.append((po_id, t['name']))
        if t['email']:
            _sans_retour(lambda: call('mail.template', 'send_mail', [TR_TPL_RFQ], po_id, force_send=True, email_values={'email_cc': ', '.join(cc)}))
            # l'envoi prend quelques secondes : on ne repasse en « envoyé » que si personne n'a touché la demande entre-temps
            if call('purchase.order', 'read', [po_id], ['state'])[0]['state'] == 'draft':
                call('purchase.order', 'write', [po_id], {'state': 'sent'})
            envoyes.append(t['name'])
        else:
            sans_mail.append(t['name'])
    if not crees:
        _note(call, 'sale.order', so_id, "Demandes de tarif transport : rien à créer, une demande est déjà en cours pour chaque transporteur coché (voir Achats, origine %s)." % so['name'])
        return 'rien à créer'
    noms = {p['id']: p['name'] for p in call('purchase.order', 'read', [c[0] for c in crees], ['name'])}
    liens = ', '.join('<a href="/odoo/purchase/%d">%s</a> (%s)' % (pid, noms.get(pid, pid), nom) for pid, nom in crees)
    details = []
    if envoyes:
        details.append('envoyées par mail à %s, copie à %s' % (', '.join(envoyes), ', '.join(cc)))
    if sans_mail:
        details.append("sans envoi pour %s : pas d'adresse e-mail sur la fiche transporteur" % ', '.join(sans_mail))
    _note(call, 'sale.order', so_id, "Demandes de tarif transport créées : %s (%s). Saisir le prix HT reçu sur chaque demande puis la confirmer : "
                                     "le transporteur retenu, son prix et la ligne « Transport de pierres » se reportent sur le devis." % (liens, ' ; '.join(details)))
    return '%d demande(s) créée(s) : %s' % (len(crees), ', '.join(str(n) for n in noms.values()))


# ─── 2119 · automatisation 102 : demande de prix transport confirmée ─────────────────────────────────────────────────

def achat_confirme(call, po_id):
    """Transporteur retenu, prix d'achat et ordre de transport sur le devis d'origine ; autres demandes de la commande
    annulées ; ligne « Transport de pierres » valorisée (achat + marge) ou créée en fin de devis."""
    po = call('purchase.order', 'read', [po_id], ['name', 'state', 'origin', 'partner_id', 'amount_untaxed', 'order_line'])[0]
    if po['state'] != 'purchase' or not po['origin']:
        return 'ignoré : état %s, origine %r' % (po['state'], po['origin'])
    produits = set()
    if po['order_line']:
        produits = {l['product_id'][0] for l in call('purchase.order.line', 'read', po['order_line'], ['product_id']) if l['product_id']}
    if TR_PRODUIT_ACHAT not in produits:
        return 'ignoré : pas de ligne Transport affrété'
    so = call('sale.order', 'search_read', [['name', '=', po['origin']]], fields=['name'], limit=1)
    if not so:
        return 'ignoré : devis %s introuvable' % po['origin']
    so_id, so_nom = so[0]['id'], so[0]['name']
    transporteur = po['partner_id'][1]
    call('sale.order', 'write', [so_id], {'x_transporteur_id': po['partner_id'][0], 'x_transport_achat': po['amount_untaxed'], 'x_ordre_transport_id': po_id})
    autres = call('purchase.order', 'search_read', [['origin', '=', so_nom], ['id', '!=', po_id], ['state', 'in', ['draft', 'sent']],
                                                    ['order_line.product_id', '=', TR_PRODUIT_ACHAT]], fields=['partner_id'])
    if autres:
        _sans_retour(lambda: call('purchase.order', 'button_cancel', [a['id'] for a in autres]))
    _note(call, 'sale.order', so_id, "Transporteur retenu : %s - %.2f EUR HT (ordre de transport %s).%s" % (
        transporteur, po['amount_untaxed'], po['name'],
        (' Autres demandes annulées : %s.' % ', '.join(a['partner_id'][1] for a in autres)) if autres else ''))
    lignes = _lignes(call, so_id)
    existantes = _existantes(lignes)
    vides = [l for l in existantes if _vide(l)]
    marge = _marge(call)
    vente = round(po['amount_untaxed'] * marge, 2)
    nom = TR_NOM_LIGNE + ' - ' + transporteur
    if vides:
        call('sale.order.line', 'write', [l['id'] for l in vides], {'price_unit': vente, 'name': nom})
        _note(call, 'sale.order', so_id, "Ligne « Transport de pierres » : prix d achat %.2f EUR HT + %.0f %% = %.2f EUR HT (à ajuster si besoin)." % (
            po['amount_untaxed'], (marge - 1) * 100, vente))
        ligne = 'ligne valorisée %.2f' % vente
    elif not existantes:
        _ligne_transport(call, so_id, lignes, nom, vente)
        _note(call, 'sale.order', so_id, "Ligne « Transport de pierres » ajoutée en fin de devis : prix d achat %.2f EUR HT + %.0f %% = %.2f EUR HT (à ajuster si besoin)." % (
            po['amount_untaxed'], (marge - 1) * 100, vente))
        ligne = 'ligne ajoutée %.2f' % vente
    else:
        ligne = 'ligne déjà chiffrée, inchangée'
    return '%s retenu sur %s (%d autre(s) annulée(s)) ; %s' % (transporteur, so_nom, len(autres), ligne)


# ─── 2122 · automatisation 103 : mode de transport du devis ──────────────────────────────────────────────────────────

def mode_devis(call, so_id):
    """« Nos camions » / « Transporteur extérieur » sans ligne transport : ligne « Transport de pierres (Forfait Palettes) »
    en fin de devis (prix d'achat + marge si connu, sinon 0 : Céline ajuste). « Enlèvement par le client » : une ligne
    transport encore vide est retirée."""
    so = call('sale.order', 'read', [so_id], ['name', 'state', 'x_mode_transport', 'x_transport_achat', 'x_transporteur_id'])[0]
    if so['state'] not in TR_ETATS_DEVIS:
        return 'ignoré : état %s' % so['state']
    lignes = _lignes(call, so_id)
    existantes = _existantes(lignes)
    mode = so['x_mode_transport']
    if mode in ('camions', 'exterieur') and not existantes:
        marge = _marge(call)
        prix = round(so['x_transport_achat'] * marge, 2) if (mode == 'exterieur' and so['x_transport_achat']) else 0.0
        nom = TR_NOM_LIGNE + ((' - ' + so['x_transporteur_id'][1]) if (mode == 'exterieur' and so['x_transporteur_id']) else '')
        _ligne_transport(call, so_id, lignes, nom, prix)
        _note(call, 'sale.order', so_id, "Ligne « Transport de pierres » ajoutée en fin de devis (%s) : prix de vente à ajuster par Céline%s." % (
            'nos camions' if mode == 'camions' else 'transporteur extérieur',
            (' - prix d achat + %.0f %% = %.2f EUR HT' % ((marge - 1) * 100, prix)) if prix else ''))
        return 'ligne ajoutée (%s, %.2f)' % (mode, prix)
    if mode == 'client' and existantes and all(_vide(l) for l in existantes):
        try:
            call('sale.order.line', 'unlink', [l['id'] for l in existantes])
        except Exception as e:  # noqa: BLE001
            # commande confirmée : Odoo refuse la suppression d'une ligne
            _note(call, 'sale.order', so_id, "Enlèvement par le client : la ligne « Transport de pierres » vide n'a pas pu être retirée (%s) ; la retirer à la main." % str(e)[-160:])
            return 'ligne vide non retirée'
        _note(call, 'sale.order', so_id, "Enlèvement par le client : ligne « Transport de pierres » vide retirée du devis.")
        return 'ligne vide retirée'
    return 'rien à faire (%s, %d ligne(s) transport)' % (mode, len(existantes))
