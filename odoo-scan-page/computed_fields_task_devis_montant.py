# Champs calculés (non stockés) sur project.task pour la carte kanban.
# x_studio_num_devis (char) : références des devis/commandes liés à la tâche.
for record in self:
    names = []
    for so in record.x_studio_devis_commandes_1:
        names.append(so.name)
    record['x_studio_num_devis'] = ', '.join(names)

# x_studio_montant (monetary, devise = currency_id) : total HT des devis/commandes liés.
for record in self:
    tot = 0.0
    for so in record.x_studio_devis_commandes_1:
        tot += so.amount_untaxed
    record['x_studio_montant'] = tot
