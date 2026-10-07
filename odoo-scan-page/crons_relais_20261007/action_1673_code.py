# Virement quotidien CB à encaisser → Banque Pop (cron 98, inactif depuis le 2026-07-29 04:00:02) — supprimé le 07/10/2026 à la demande de Xavier
# Virement quotidien CB à encaisser → Banque Pop
# Cherche les lignes non-lettrées du compte 51121000 CB à l'encaissement
# et crée une écriture de virement vers 51211000 Banque Pop

today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)

# Trouver les journaux
journal_cb = env['account.journal'].search([('code', '=', 'CB'), ('company_id', '=', env.company.id)], limit=1)
journal_bq = env['account.journal'].search([('code', '=', 'BQ1'), ('company_id', '=', env.company.id)], limit=1)

if not journal_cb or not journal_bq:
    log('Virement CB: journaux CB ou BQ1 introuvables', level='error')
else:
    # Trouver les comptes
    account_cb = env['account.account'].search([('code', '=', '51121000')], limit=1)
    account_bq = env['account.account'].search([('code', '=', '51211000')], limit=1)

    if not account_cb or not account_bq:
        log('Virement CB: comptes 51121000 ou 51211000 introuvables', level='error')
    else:
        # Chercher les lignes débit non-lettrées sur 51121000 de la veille
        domain = [
            ('account_id', '=', account_cb.id),
            ('journal_id', '=', journal_cb.id),
            ('reconciled', '=', False),
            ('debit', '>', 0),
            ('date', '=', str(yesterday)),
            ('parent_state', '=', 'posted'),
        ]
        lines = env['account.move.line'].search(domain)
        total_cb = sum(lines.mapped('debit'))

        if total_cb > 0:
            move_vals = {
                'journal_id': journal_bq.id,
                'date': str(today),
                'ref': 'Virement CB ' + yesterday.strftime('%d/%m/%Y') + ' - ' + str(round(total_cb, 2)) + ' EUR',
                'line_ids': [
                    (0, 0, {
                        'account_id': account_bq.id,
                        'debit': total_cb,
                        'credit': 0.0,
                        'name': 'Virement CB à encaisser ' + yesterday.strftime('%d/%m/%Y'),
                    }),
                    (0, 0, {
                        'account_id': account_cb.id,
                        'debit': 0.0,
                        'credit': total_cb,
                        'name': 'Virement CB à encaisser ' + yesterday.strftime('%d/%m/%Y'),
                    }),
                ],
            }
            move = env['account.move'].create(move_vals)
            move.action_post()
            log('Virement CB créé: ' + str(total_cb) + ' EUR pour le ' + str(yesterday))
        else:
            log('Virement CB: aucun montant à virer pour le ' + str(yesterday))