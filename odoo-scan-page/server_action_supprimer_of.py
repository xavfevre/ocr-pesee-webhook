# Action serveur « 🗑️ Supprimer l'OF (déploiement) » — id 1954
# Modèle : mrp.production · binding liste + formulaire
# Réservée à Céline (user 2? -> 12) et Isabelle (user 2). Phase de déploiement :
# permet de supprimer un OF terminé pour le régénérer avec une autre pierre.
# Lève les verrous « terminé » (OT, mouvements de stock faits) via SQL, puis
# supprime via l'ORM (contourne le bug StudioMixin v19 sur write()).
# NB : ne réajuste PAS le stock déjà produit (à corriger séparément si besoin).

if env.user.id not in (2, 12):
    raise UserError("Suppression d'OF termine reservee a Celine et Isabelle.")
n = 0
for rec in records:
    pid = rec.id; name = rec.name
    wo = rec.workorder_ids.ids
    mv = (rec.move_raw_ids | rec.move_finished_ids).ids
    if wo:
        env.cr.execute("DELETE FROM mrp_workcenter_productivity WHERE workorder_id = ANY(%s)", (wo,))
        env.cr.execute("UPDATE mrp_workorder SET state='cancel', qty_produced=0 WHERE production_id=%s", (pid,))
    if mv:
        env.cr.execute("DELETE FROM stock_move_line WHERE move_id = ANY(%s)", (mv,))
        env.cr.execute("UPDATE stock_move SET state='draft', quantity=0, picked=false WHERE id = ANY(%s)", (mv,))
    env.cr.execute("UPDATE mrp_production SET state='draft', qty_producing=0 WHERE id=%s", (pid,))
    rec.invalidate_recordset()
    rec.with_context(force_delete=True).unlink()
    n += 1
    log('OF %s supprime (deploiement) par %s' % (name, env.user.name), level='info')
if n == 0:
    raise UserError("Aucun OF selectionne.")
