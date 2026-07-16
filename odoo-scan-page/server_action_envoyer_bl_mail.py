# Action serveur « Envoyer BL par mail » — id 1962 · modèle stock.picking
# Ouvre le compositeur d'email pré-rempli avec le template 16
# (« Shipping: Send by Email », qui joint le bon de livraison PDF au client).
# Appelée par le bouton d'en-tête ajouté dans la vue 6616.

ctx = dict(env.context or {})
ctx.update({
    'default_model': 'stock.picking',
    'default_res_ids': records.ids,
    'default_template_id': 16,
    'default_composition_mode': 'comment',
    'force_email': True,
    'mailing_document_based': True,
})
action = {
    'type': 'ir.actions.act_window',
    'name': 'Envoyer le bon de livraison',
    'res_model': 'mail.compose.message',
    'view_mode': 'form',
    'views': [(False, 'form')],
    'target': 'new',
    'context': ctx,
}
