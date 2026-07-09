# Action serveur « 🗑️ Supprimer l'OF + stock (déploiement) » — id 1954
# Modèle : mrp.production · binding liste + formulaire
# Réservée à Céline (12) et Isabelle (2). Phase de déploiement : supprime un OF
# terminé pour le régénérer avec une autre pierre, ET remet le stock à jour
# (retire le produit fini, restitue les composants consommés).
# Contourne les verrous « terminé » (OT, mouvements de stock faits) via SQL puis
# supprime via l'ORM. Invalidation du cache indispensable entre le SQL et l'unlink.
# Validé en dry-run (rollback) sans supprimer d'OF réel.

if env.user.id not in (2, 12):
    raise UserError("Suppression d'OF termine reservee a Celine et Isabelle.")
n = 0
Q = env['stock.quant']
for rec in records:
    pid = rec.id; name = rec.name
    moves = rec.move_raw_ids | rec.move_finished_ids
    # 1) capturer les ajustements de stock à appliquer après suppression
    adj = []
    for mv in rec.move_finished_ids.filtered(lambda m: m.state == 'done' and m.quantity):
        adj.append((mv.product_id, mv.location_dest_id, -mv.quantity))   # retirer le fini
    for mv in rec.move_raw_ids.filtered(lambda m: m.state == 'done' and m.quantity):
        adj.append((mv.product_id, mv.location_id, mv.quantity))          # restituer le composant
    # 2) lever les verrous puis supprimer
    wo = rec.workorder_ids.ids
    mvids = moves.ids
    if wo:
        env.cr.execute("DELETE FROM mrp_workcenter_productivity WHERE workorder_id = ANY(%s)", (wo,))
        env.cr.execute("UPDATE mrp_workorder SET state='cancel', qty_produced=0 WHERE production_id=%s", (pid,))
    if mvids:
        env.cr.execute("DELETE FROM stock_move_line WHERE move_id = ANY(%s)", (mvids,))
        env.cr.execute("UPDATE stock_move SET state='draft', quantity=0, picked=false WHERE id = ANY(%s)", (mvids,))
    env.cr.execute("UPDATE mrp_production SET state='draft', qty_producing=0 WHERE id=%s", (pid,))
    env.invalidate_all()   # sinon l'unlink lit un cache 'done' périmé et bloque
    rec.with_context(force_delete=True).unlink()
    # 3) appliquer les ajustements de stock (quants indépendants de l'OF supprimé)
    for p, l, d in adj:
        Q._update_available_quantity(p, l, d)
    n += 1
    log('OF %s supprime + stock ajuste (deploiement) par %s' % (name, env.user.name), level='info')
if n == 0:
    raise UserError("Aucun OF selectionne.")
