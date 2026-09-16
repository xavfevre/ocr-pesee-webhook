# -*- coding: utf-8 -*-
"""2103 : second mail « Commandes entièrement produites, non facturées » pour Céline (facturation)."""
import io, ast, sys
sys.stdout.reconfigure(encoding='utf-8')
p = 'ocr/web_actions.py'; s = io.open(p, encoding='utf-8').read()


def rep(old, new):
    global s
    assert s.count(old) == 1, old[:80]; s = s.replace(old, new)


rep("""def _alerte_palettes(call, ctx):""", """def _commandes_produites(call, jours=45):
    \"\"\"Commandes (société 1) dont TOUS les OF sont terminés, avec au moins un OF terminé sur les `jours` derniers
    jours, et dont des OF ne sont pas encore facturés (pas de facture liée, ligne de commande non facturée).
    Destinées à Céline (facturation). Renvoie (lignes, html).\"\"\"
    import datetime as _dt
    import html as _html
    now = _dt.datetime.utcnow()
    dj = (now - _dt.timedelta(days=jours)).strftime('%Y-%m-%d %H:%M:%S')
    ofs = call('mrp.production', 'search_read',
               [['state', '=', 'done'], ['company_id', '=', 1], ['origin', '!=', False], ['x_studio_no_facture', '=', False],
                ['date_finished', '>=', dj]],
               fields=['name', 'origin', 'x_studio_nbr', 'date_finished', 'x_studio_nom_du_client', 'sale_line_id'], limit=6000)
    sl_ids = list({o['sale_line_id'][0] for o in ofs if o['sale_line_id']})
    factures = set()
    if sl_ids:
        for l in call('sale.order.line', 'read', sl_ids, fields=['qty_invoiced', 'product_uom_qty', 'invoice_status']):
            if l['invoice_status'] == 'invoiced' or l['qty_invoiced'] >= (l['product_uom_qty'] or 0) - 1e-6:
                factures.add(l['id'])
    ofs = [o for o in ofs if not (o['sale_line_id'] and o['sale_line_id'][0] in factures)]
    origines = sorted({o['origin'] for o in ofs})
    if not origines:
        return [], ''
    restants = {}
    for o in call('mrp.production', 'search_read',
                  [['origin', 'in', origines], ['state', 'in', ['draft', 'confirmed', 'progress', 'to_close']], ['company_id', '=', 1]],
                  fields=['origin'], limit=6000):
        restants[o['origin']] = restants.get(o['origin'], 0) + 1
    par_cmd = {}
    for o in ofs:
        if restants.get(o['origin']):
            continue
        par_cmd.setdefault(o['origin'], []).append(o)
    rows = sorted(par_cmd.items(), key=lambda kv: max(o['date_finished'] for o in kv[1]), reverse=True)
    h = ['<p>Bonjour,</p><p>Commandes dont <b>tous les OF sont terminés</b> et dont les OF ne sont pas encore facturés '
         '(au %s, OF terminés sur les %d derniers jours) :</p>' % (now.strftime('%d/%m/%Y'), jours),
         '<table border="1" cellpadding="5" style="border-collapse:collapse;font-size:13px"><tr style="background:#eaf4f4">'
         '<th>Commande</th><th>Client</th><th>OF terminés</th><th>Pierres</th><th>Dernier OF terminé</th><th>OF</th></tr>']
    for cmd, lst in rows:
        lst.sort(key=lambda o: o['name'])
        pcs = sum(int(o['x_studio_nbr'] or 1) for o in lst)
        nums = ', '.join(o['name'].replace('WH/OF/', '') for o in lst[:12]) + (' … (+%d)' % (len(lst) - 12) if len(lst) > 12 else '')
        h.append('<tr><td><b>%s</b></td><td>%s</td><td style="text-align:center">%d</td><td style="text-align:center">%d</td><td>%s</td><td style="color:#555">%s</td></tr>' % (
            _html.escape(cmd), _html.escape(lst[0]['x_studio_nom_du_client'] or '-'), len(lst), pcs,
            max(o['date_finished'] for o in lst)[:10], _html.escape(nums)))
    h.append('</table><p style="color:#777;font-size:12px">Généré automatiquement chaque lundi. Les OF déjà facturés ou dont la ligne de commande '
             'est facturée sont exclus ; une commande disparaît de la liste dès qu\\'elle est facturée.</p>')
    return rows, ''.join(h)


def _alerte_palettes(call, ctx):""")
rep("""    res = {'ok': 1, 'n_ops': len(par_op), 'n_of': sum(len(v) for v in par_op.values()), 'n_dormantes': len(dorm), 'html': corps}
    if ctx.get('envoyer'):
        dest = str(_param(call, 'maquignon.palettes_alerte_email', 'isabelle@maquignon.com') or '').strip()
        mid = _creer(call, 'mail.mail', {'subject': 'Palettes : point hebdo du %s' % now.strftime('%d/%m/%Y'),
                                        'email_to': dest, 'body_html': corps, 'auto_delete': False})
        _sur(lambda: call('mail.mail', 'send', [mid]))
        res['envoye_a'] = dest
    return res""",
    """    res = {'ok': 1, 'n_ops': len(par_op), 'n_of': sum(len(v) for v in par_op.values()), 'n_dormantes': len(dorm), 'html': corps}
    if ctx.get('envoyer'):
        dest = str(_param(call, 'maquignon.palettes_alerte_email', 'isabelle@maquignon.com') or '').strip()
        mid = _creer(call, 'mail.mail', {'subject': 'Palettes : point hebdo du %s' % now.strftime('%d/%m/%Y'),
                                        'email_to': dest, 'body_html': corps, 'auto_delete': False})
        _sur(lambda: call('mail.mail', 'send', [mid]))
        res['envoye_a'] = dest
    # commandes entièrement produites, non facturées -> Céline (facturation)
    rows_c, html_c = _commandes_produites(call)
    res['n_commandes_produites'] = len(rows_c)
    res['html_celine'] = html_c
    if (ctx.get('envoyer') or ctx.get('envoyer_celine')) and rows_c:
        dest_c = str(_param(call, 'maquignon.commandes_produites_email', 'celine@maquignon.com') or '').strip()
        mid_c = _creer(call, 'mail.mail', {'subject': 'Commandes entièrement produites, non facturées — %s (%d)' % (now.strftime('%d/%m/%Y'), len(rows_c)),
                                          'email_to': dest_c, 'body_html': html_c, 'auto_delete': False})
        _sur(lambda: call('mail.mail', 'send', [mid_c]))
        res['envoye_celine_a'] = dest_c
    return res""")
ast.parse(s); io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('2103 : mail Céline ajouté')
