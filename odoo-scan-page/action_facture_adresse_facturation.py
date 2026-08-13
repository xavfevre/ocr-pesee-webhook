# action 2085 — règle 92
# Facture client directe : si le client a une adresse de facturation dediee,
# elle devient automatiquement le destinataire (comme dans le flux devis -> facture).
# Ne touche que les brouillons ; le code Sage remonte de toute facon a la fiche mere.
for r in records:
    if r.move_type not in ('out_invoice', 'out_refund') or r.state != 'draft':
        continue
    p = r.partner_id
    if not p or p.type == 'invoice':
        continue
    adr = p.address_get(['invoice']).get('invoice')
    if adr and adr != p.id:
        r.write({'partner_id': adr})
