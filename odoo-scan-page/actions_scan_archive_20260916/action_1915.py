# 1915 | Retirer une ligne de répartition | Poste de scan
line_id = env.context.get('line_remove_id')
for record in records:
    if not line_id:
        record.write({'x_studio_rsultat': "⚠️ Aucune ligne indiquée"})
        continue
    line = env['x_repartition_palette'].browse(line_id)
    if not line.exists():
        record.write({'x_studio_rsultat': "⚠️ Ligne introuvable"})
        continue
    nm = line.x_studio_of_id.name
    cn = line.x_studio_colis_id.name
    q = line.x_studio_qte
    line.unlink()
    record.write({'x_studio_rsultat': "🗑️ " + str(q) + " pcs de " + nm + " retiré de " + cn})
