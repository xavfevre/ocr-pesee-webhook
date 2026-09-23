# -*- coding: utf-8 -*-
"""Export paie / Silae / feuille hebdo : récup et sans solde en heures, écart = heures comptées en récup (x_hs)."""
import io, sys
sys.stdout.reconfigure(encoding='utf-8')
P = 'ocr/export_heures.py'
s = io.open(P, encoding='utf-8').read()
n0 = len(s)


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:90])
    s = s.replace(old, new)


# ── en-tête / types ──────────────────────────────────────────────────────────
rep("""heures effectuées, écart vs horaire contractuel, mentions CP / MALADIE /
FERIE / ABSENCE / RECUP dans les cases, totaux hebdo + récap mensuel.""",
    """heures effectuées, écart compté en récup (heures sup en récup par défaut,
sans solde exclu), heures de récup prises / sans solde, mentions CP / MALADIE /
FERIE / ABSENCE / RECUP / SANS SOLDE dans les cases, totaux hebdo + récap mensuel.""")
rep("""TYPES = {
    'cp': 'CP', 'maladie': 'MALADIE', 'ferie': 'FERIE',
    'absence': 'ABSENT', 'recup': 'RECUP', 'repos': '',
}""", """TYPES = {
    'cp': 'CP', 'maladie': 'MALADIE', 'ferie': 'FERIE',
    'absence': 'ABSENT', 'recup': 'RECUP', 'repos': '', 'sans_solde': 'SANS SOLDE',
}
# jours dont l'écart entre dans le solde « à récupérer » (x_hs) : travaillés,
# journée entière de récup (− horaire), journée sans solde (0)
TYPES_SOLDE = ('travail', 'recup', 'sans_solde')


def _fr(h):
    return ('%.2f' % h).replace('.', ',')""")

# ── build : lecture ───────────────────────────────────────────────────────────
rep("""                fields=['x_employee_id', 'x_date', 'x_type', 'x_m_deb', 'x_m_fin',
                        'x_am_deb', 'x_am_fin', 'x_heures', 'x_theo', 'x_hs', 'x_note', 'x_decouchage'])
    by_emp = {}
    for r in rows:
        by_emp.setdefault(r['x_employee_id'][0], {})[r['x_date']] = r
    # récup : heures mises (x_recup_ligne) et jours/demi-jours récupérés depuis le
    # début de période (01/06), pour le solde « arrêté bureau + mises − récupérées »
    rl_by_emp = {}
    for l in call('x_recup_ligne', 'search_read',
                  [('x_employee_id', 'in', [e['id'] for e in emps])],
                  fields=['x_employee_id', 'x_date', 'x_heures']):
        rl_by_emp.setdefault(l['x_employee_id'][0], []).append(l)
    pstart = date(y if m >= 6 else y - 1, 6, 1)
    pris_by_emp = {}
    for r in call('x_heures_jour', 'search_read',
                  ['&', ('x_employee_id', 'in', [e['id'] for e in emps]),
                   ('x_date', '>=', pstart.strftime('%Y-%m-%d')),
                   '|', ('x_type', '=', 'recup'), ('x_note', 'like', 'Récupération —')],
                  fields=['x_employee_id', 'x_date', 'x_type', 'x_theo', 'x_note']):
        pris_by_emp.setdefault(r['x_employee_id'][0], []).append(r)

    def _recup_pris_h(r, cal):
        \"\"\"Heures récupérées portées par un jour : jour entier -> théo figé ;
        demi-jour (type travail, note Récupération) -> partie non travaillée.\"\"\"
        if r['x_type'] == 'recup':
            return r['x_theo'] or 0.0
        d = datetime.strptime(r['x_date'], '%Y-%m-%d').date()
        return max(_theo_day(cal, d) - (r['x_theo'] or 0.0), 0.0)
""", """                fields=['x_employee_id', 'x_date', 'x_type', 'x_m_deb', 'x_m_fin',
                        'x_am_deb', 'x_am_fin', 'x_heures', 'x_theo', 'x_hs', 'x_note', 'x_decouchage',
                        'x_h_recup', 'x_h_sans_solde', 'x_hs_payees'])
    by_emp = {}
    for r in rows:
        by_emp.setdefault(r['x_employee_id'][0], {})[r['x_date']] = r
    # solde « à récupérer » = arrêté bureau (x_recup_solde à la date de référence)
    # + heures comptées en récup de chaque jour postérieur (x_hs : heures sup en
    # plus, récup prise en moins, sans solde neutre) + lignes manuelles du bureau
    rl_by_emp = {}
    for l in call('x_recup_ligne', 'search_read',
                  [('x_employee_id', 'in', [e['id'] for e in emps])],
                  fields=['x_employee_id', 'x_date', 'x_heures']):
        rl_by_emp.setdefault(l['x_employee_id'][0], []).append(l)
    pstart = date(y if m >= 6 else y - 1, 6, 1)
    hs_by_emp = {}
    for r in call('x_heures_jour', 'search_read',
                  [('x_employee_id', 'in', [e['id'] for e in emps]),
                   ('x_date', '>=', pstart.strftime('%Y-%m-%d')),
                   ('x_type', 'in', list(TYPES_SOLDE))],
                  fields=['x_employee_id', 'x_date', 'x_hs']):
        hs_by_emp.setdefault(r['x_employee_id'][0], []).append(r)
""")

# ── build : récap mensuel ─────────────────────────────────────────────────────
rep("""        tot_h = tot_theo = 0.0
        n_cp = n_mal = n_abs = n_fer = n_rec = n_dec = 0
        d = e1
        while d <= e2:
            s = saisies.get(d.strftime('%Y-%m-%d'))
            # théorique de l'écart : jour travail = théo figé (demi-journées gérées),
            # jour vide = calendrier ; les jours posés en absence ne comptent pas
            if s and s['x_type'] == 'travail':
                tot_theo += s['x_theo']
            elif not s:
                tot_theo += _theo_day(cal, d)
            if s:
                t = s['x_type']
                if t == 'travail':
                    tot_h += s['x_heures']
                elif t == 'cp':""", """        tot_h = tot_theo = tot_delta = h_rec = h_ss = hs_pay = 0.0
        n_cp = n_mal = n_abs = n_fer = n_rec = n_ss = n_dec = 0
        d = e1
        while d <= e2:
            s = saisies.get(d.strftime('%Y-%m-%d'))
            # théorique : jour travaillé / récup / sans solde = théo figé (demi-journées
            # de congé gérées), jour vide = calendrier ; congés, maladie, fériés,
            # absences ne comptent pas
            if s and s['x_type'] in TYPES_SOLDE:
                tot_theo += s['x_theo']
                tot_delta += s.get('x_hs') or 0.0
                h_rec += s.get('x_h_recup') or 0.0
                h_ss += s.get('x_h_sans_solde') or 0.0
                if s['x_type'] == 'travail' and s.get('x_hs_payees'):
                    hs_pay += max(s['x_heures'] - s['x_theo'], 0.0)
            elif not s:
                tot_theo += _theo_day(cal, d)
            if s:
                t = s['x_type']
                if t == 'travail':
                    tot_h += s['x_heures']
                elif t == 'sans_solde':
                    n_ss += 1
                elif t == 'cp':""")
rep("""        # récup en heures : mises dans le mois, récupérées dans le mois, solde courant
        ref = e.get('x_cp_ref_date') or ''
        lignes_rl = rl_by_emp.get(e['id'], [])
        pris_rows = pris_by_emp.get(e['id'], [])
        m1, m2 = e1.strftime('%Y-%m-%d'), e2.strftime('%Y-%m-%d')
        mises_mois = sum(l['x_heures'] for l in lignes_rl if m1 <= l['x_date'] <= m2)
        recup_mois = sum(_recup_pris_h(r, cal) for r in pris_rows if m1 <= r['x_date'] <= m2)
        # solde arrêté à la fin du mois exporté (les mouvements postérieurs n'y entrent pas)
        solde = ((e.get('x_recup_solde') or 0.0)
                 + sum(l['x_heures'] for l in lignes_rl if (not ref or l['x_date'] > ref) and l['x_date'] <= m2)
                 - sum(_recup_pris_h(r, cal) for r in pris_rows if (not ref or r['x_date'] > ref) and r['x_date'] <= m2))
        heads = ['Matricule', 'Heures effectuées', 'Heures théoriques', 'Écart',
                 'Contrat mensuel (h)', 'Base légale (h)', 'H. sup structurelles/mois',
                 'Jours CP', 'Jours maladie', 'Jours absence', 'Fériés', 'Jours récup',
                 'Découchages',
                 'H. mises en récup', 'H. récupérées', 'Solde récup (h)']
        vals = [mat or '—', round(tot_h, 2), round(tot_theo, 2), round(tot_h - tot_theo, 2),
                round(contrat_mensuel, 2), round(BASE_LEGALE, 2), round(hs_struct, 2),
                n_cp, n_mal, n_abs, n_fer, n_rec, n_dec,
                round(mises_mois, 2), round(recup_mois, 2), round(solde, 2)]""",
    """        # solde à récupérer arrêté à la fin du mois exporté (les jours postérieurs n'y entrent pas)
        ref = e.get('x_cp_ref_date') or ''
        lignes_rl = rl_by_emp.get(e['id'], [])
        m1, m2 = e1.strftime('%Y-%m-%d'), e2.strftime('%Y-%m-%d')
        mises_mois = sum(l['x_heures'] for l in lignes_rl if m1 <= l['x_date'] <= m2)
        solde = ((e.get('x_recup_solde') or 0.0)
                 + sum(l['x_heures'] for l in lignes_rl if (not ref or l['x_date'] > ref) and l['x_date'] <= m2)
                 + sum(r['x_hs'] or 0.0 for r in hs_by_emp.get(e['id'], []) if (not ref or r['x_date'] > ref) and r['x_date'] <= m2))
        heads = ['Matricule', 'Heures effectuées', 'Heures théoriques', 'Écart compté en récup',
                 'H. sup payées', 'H. récup prises', 'H. sans solde',
                 'Contrat mensuel (h)', 'Base légale (h)', 'H. sup structurelles/mois',
                 'Jours CP', 'Jours maladie', 'Jours absence', 'Fériés', 'Jours récup', 'Jours sans solde',
                 'Découchages', 'H. ajoutées par le bureau', 'Solde récup (h)']
        vals = [mat or '—', round(tot_h, 2), round(tot_theo, 2), round(tot_delta, 2),
                round(hs_pay, 2), round(h_rec, 2), round(h_ss, 2),
                round(contrat_mensuel, 2), round(BASE_LEGALE, 2), round(hs_struct, 2),
                n_cp, n_mal, n_abs, n_fer, n_rec, n_ss, n_dec,
                round(mises_mois, 2), round(solde, 2)]""")

# ── build : blocs hebdomadaires ───────────────────────────────────────────────
rep("""            for j in range(1, 10):
                ws.cell(row=r, column=j).fill = WFILL
            r += 1
            for j, h in enumerate(['Jour', 'Date', 'Arrivée', 'Départ', 'Arrivée', 'Départ',
                                   'Heures', 'Écart', 'Note'], 1):
                c = ws.cell(row=r, column=j, value=h); c.font = HDR; c.fill = FILL; c.alignment = CTR
            r += 1
            wtot = wtheo = 0.0""", """            for j in range(1, 12):
                ws.cell(row=r, column=j).fill = WFILL
            r += 1
            for j, h in enumerate(['Jour', 'Date', 'Arrivée', 'Départ', 'Arrivée', 'Départ',
                                   'Heures', 'Récup ±', 'Récup prise', 'Sans solde', 'Note'], 1):
                c = ws.cell(row=r, column=j, value=h); c.font = HDR; c.fill = FILL; c.alignment = CTR
            r += 1
            wtot = wtheo = wdelta = wrec = wss = 0.0""")
rep("""                    c = ws.cell(row=r, column=7, value=round(s['x_heures'], 2)); c.font = FB; c.alignment = CTR
                    c = ws.cell(row=r, column=8, value=round(s['x_hs'], 2)); c.font = F10; c.alignment = CTR
                    if in_month:
                        wtot += s['x_heures']
                elif s:
                    lab = TYPES.get(s['x_type'], s['x_type'].upper())
                    for j in range(3, 7):
                        c = ws.cell(row=r, column=j, value=lab); c.font = FB; c.alignment = CTR
                if s and s.get('x_note'):
                    ws.cell(row=r, column=9, value=s['x_note']).font = F10
                if not in_month:
                    for j in range(1, 10):
                        ws.cell(row=r, column=j).font = Font(name='Arial', size=10, color='AAAAAA')
                for j in range(1, 10):
                    ws.cell(row=r, column=j).border = thin
                r += 1
            ws.cell(row=r, column=6, value='Total semaine (part du mois)').font = FB
            c = ws.cell(row=r, column=7, value=round(wtot, 2)); c.font = FB; c.alignment = CTR
            c = ws.cell(row=r, column=8, value=round(wtot - wtheo, 2)); c.font = FB; c.alignment = CTR
            r += 2
            monday += timedelta(days=7)
        for col, w in zip('ABCDEFGHI', [11, 12, 9, 9, 9, 9, 9, 9, 30]):
            ws.column_dimensions[col].width = w""", """                    c = ws.cell(row=r, column=7, value=round(s['x_heures'], 2)); c.font = FB; c.alignment = CTR
                    if in_month:
                        wtot += s['x_heures']
                elif s:
                    lab = TYPES.get(s['x_type'], s['x_type'].upper())
                    for j in range(3, 7):
                        c = ws.cell(row=r, column=j, value=lab); c.font = FB; c.alignment = CTR
                if s and s['x_type'] in TYPES_SOLDE:
                    c = ws.cell(row=r, column=8, value=round(s.get('x_hs') or 0.0, 2)); c.font = F10; c.alignment = CTR
                    if s.get('x_h_recup'):
                        c = ws.cell(row=r, column=9, value=round(s['x_h_recup'], 2)); c.font = FB; c.alignment = CTR
                    if s.get('x_h_sans_solde'):
                        c = ws.cell(row=r, column=10, value=round(s['x_h_sans_solde'], 2)); c.font = FB; c.alignment = CTR
                    if in_month:
                        wdelta += s.get('x_hs') or 0.0
                        wrec += s.get('x_h_recup') or 0.0
                        wss += s.get('x_h_sans_solde') or 0.0
                note = (s.get('x_note') or '') if s else ''
                if s and s['x_type'] == 'travail' and s.get('x_hs_payees') and s['x_heures'] > s['x_theo']:
                    note = ('HS payées +%s h' % _fr(s['x_heures'] - s['x_theo'])) + (' · ' + note if note else '')
                if note:
                    ws.cell(row=r, column=11, value=note).font = F10
                if not in_month:
                    for j in range(1, 12):
                        ws.cell(row=r, column=j).font = Font(name='Arial', size=10, color='AAAAAA')
                for j in range(1, 12):
                    ws.cell(row=r, column=j).border = thin
                r += 1
            ws.cell(row=r, column=6, value='Total semaine (part du mois)').font = FB
            c = ws.cell(row=r, column=7, value=round(wtot, 2)); c.font = FB; c.alignment = CTR
            c = ws.cell(row=r, column=8, value=round(wdelta, 2)); c.font = FB; c.alignment = CTR
            c = ws.cell(row=r, column=9, value=round(wrec, 2)); c.font = FB; c.alignment = CTR
            c = ws.cell(row=r, column=10, value=round(wss, 2)); c.font = FB; c.alignment = CTR
            r += 2
            monday += timedelta(days=7)
        for col, w in zip('ABCDEFGHIJK', [11, 12, 9, 9, 9, 9, 9, 9, 10, 10, 30]):
            ws.column_dimensions[col].width = w""")

# ── Silae ─────────────────────────────────────────────────────────────────────
rep("""    'hs': 'HS',              # heures d'écart du mois (effectué − théorique)""",
    """    'hs': 'HS',              # heures sup PAYÉES (les autres vont en récup)
    'sans_solde_h': 'ABSSH', # heures sans solde sur des jours travaillés""")
rep("""    'hs': 'Heures écart (+/−)', 'cp': 'Congés payés', 'maladie': 'Maladie',""",
    """    'hs': 'Heures sup payées', 'sans_solde_h': 'Heures sans solde', 'cp': 'Congés payés', 'maladie': 'Maladie',""")
rep("""    t, note = r['x_type'], r.get('x_note') or ''
    if t in ('cp', 'maladie', 'recup'):""", """    t, note = r['x_type'], r.get('x_note') or ''
    if t == 'sans_solde':
        return 'sans_solde', False
    if t in ('cp', 'maladie', 'recup'):""")
rep("""                fields=['x_employee_id', 'x_date', 'x_type', 'x_heures', 'x_theo', 'x_note', 'x_decouchage'])
    by_emp = {}
    for r in rows:
        by_emp.setdefault(r['x_employee_id'][0], {})[r['x_date']] = r

    wb = Workbook()""", """                fields=['x_employee_id', 'x_date', 'x_type', 'x_heures', 'x_theo', 'x_note', 'x_decouchage',
                        'x_h_sans_solde', 'x_hs_payees'])
    by_emp = {}
    for r in rows:
        by_emp.setdefault(r['x_employee_id'][0], {})[r['x_date']] = r

    wb = Workbook()""")
rep("""        # heures d'écart du mois (jours travaillés uniquement)
        hs = sum((s['x_heures'] - s['x_theo']) for s in saisies.values() if s['x_type'] == 'travail')""",
    """        # heures sup payées (jours cochés « HS payées ») ; les autres heures en plus vont
        # dans le solde à récupérer et ne sont pas un élément de paie
        hs = sum(max(s['x_heures'] - s['x_theo'], 0.0) for s in saisies.values()
                 if s['x_type'] == 'travail' and s.get('x_hs_payees'))
        ss_h = sum(s.get('x_h_sans_solde') or 0.0 for s in saisies.values() if s['x_type'] == 'travail')""")
rep("""        if not jours and abs(hs) < 0.005 and not n_dec:
            continue""", """        if not jours and abs(hs) < 0.005 and abs(ss_h) < 0.005 and not n_dec:
            continue""")
rep("""        if abs(hs) >= 0.005:
            evp['hs'] = round(hs, 2)
        if n_dec:""", """        if abs(hs) >= 0.005:
            evp['hs'] = round(hs, 2)
        if abs(ss_h) >= 0.005:
            evp['sans_solde_h'] = round(ss_h, 2)
        if n_dec:""")
rep("""        "  - Heures écart = effectué − théorique des jours travaillés du mois",
        "    (contrôle Charlotte avant import : peut être négatif).",
        "  - Absences en jours (0,5 pour les demi-journées).",""",
    """        "  - Heures sup payées = surplus des jours cochés « HS payées » ; les",
        "    autres heures en plus vont dans le solde à récupérer (pas de paie).",
        "  - Heures sans solde = heures non payées sur des jours travaillés ;",
        "    les journées entières sans solde sont dans les absences (jours).",
        "  - Absences en jours (0,5 pour les demi-journées).",""")

# ── feuille hebdomadaire ──────────────────────────────────────────────────────
rep("""                  fields=['x_date', 'x_type', 'x_m_deb', 'x_m_fin', 'x_am_deb',
                          'x_am_fin', 'x_theo', 'x_heures']):
        jours[r['x_date']] = r

    MENTION = {'cp': 'CP', 'ferie': 'FERIE', 'maladie': 'MALADIE',
               'absence': 'ABSENCE', 'recup': 'RECUP'}
    # couleurs du document papier : texte colore Century Gothic, pas de fond
    COULEURS = {'cp': 'FF00B050', 'ferie': 'FFFF0000', 'maladie': 'FFFFC000',
                'absence': 'FFFF0000', 'recup': 'FF0070C0', 'repos': 'FF808080'}""",
    """                  fields=['x_date', 'x_type', 'x_m_deb', 'x_m_fin', 'x_am_deb',
                          'x_am_fin', 'x_theo', 'x_heures', 'x_hs', 'x_h_recup',
                          'x_h_sans_solde', 'x_hs_payees']):
        jours[r['x_date']] = r

    MENTION = {'cp': 'CP', 'ferie': 'FERIE', 'maladie': 'MALADIE',
               'absence': 'ABSENCE', 'recup': 'RECUP', 'sans_solde': 'SANS SOLDE'}
    # couleurs du document papier : texte colore Century Gothic, pas de fond
    COULEURS = {'cp': 'FF00B050', 'ferie': 'FFFF0000', 'maladie': 'FFFFC000',
                'absence': 'FFFF0000', 'recup': 'FF0070C0', 'repos': 'FF808080',
                'sans_solde': 'FFFF0000'}
    F_ANN = {'recup': Font(name='Century Gothic', size=11, color='FF0070C0', bold=True),
             'sans_solde': Font(name='Century Gothic', size=11, color='FFFF0000', bold=True),
             'payees': Font(name='Century Gothic', size=11, color='FF00B050', bold=True)}""")
rep("""            k = ws.cell(row, 11)
            if isinstance(k.value, str) and k.value.startswith('='):
                k.value = None    # K reste la colonne d'annotations libres du papier
            if not (d1 <= d <= d2):
                continue          # on n'edite que la periode selectionnee
            c = ws.cell(row, 2)
            c.value = d
            c.number_format = '[$-F800]dddd\\\\,\\\\ mmmm\\\\ dd\\\\,\\\\ yyyy'
            if not r:
                continue
            if mention:
                for col in (3, 4, 5, 6):
                    cc = ws.cell(row, col)
                    cc.value = mention
                    cc.font = Font(name='Century Gothic', size=12,
                                   color=COULEURS[r['x_type']])
                if r['x_type'] == 'cp':
                    ws.cell(row, 10).value = 1
                if r['x_type'] == 'maladie' and r.get('x_theo'):
                    ws.cell(row, 9).value = r['x_theo']
            else:
                for col, champ in ((3, 'x_m_deb'), (4, 'x_m_fin'),
                                   (5, 'x_am_deb'), (6, 'x_am_fin')):
                    t = _ft_time(r.get(champ))
                    if t is not None:
                        cc = ws.cell(row, col)
                        cc.value = t
                        cc.number_format = 'HH:MM'""",
    """            k = ws.cell(row, 11)
            if isinstance(k.value, str) and k.value.startswith('='):
                k.value = None    # K reste la colonne d'annotations libres du papier
            if not (d1 <= d <= d2):
                continue          # on n'edite que la periode selectionnee
            c = ws.cell(row, 2)
            c.value = d
            c.number_format = '[$-F800]dddd\\\\,\\\\ mmmm\\\\ dd\\\\,\\\\ yyyy'
            if not r:
                continue
            if mention:
                for col in (3, 4, 5, 6):
                    cc = ws.cell(row, col)
                    cc.value = mention
                    cc.font = Font(name='Century Gothic', size=12,
                                   color=COULEURS[r['x_type']])
                if r['x_type'] == 'cp':
                    ws.cell(row, 10).value = 1
                if r['x_type'] == 'maladie' and r.get('x_theo'):
                    ws.cell(row, 9).value = r['x_theo']
                if r['x_type'] == 'recup':
                    # journée entière de récup : − horaire dans la colonne H (comme le papier)
                    hh = ws.cell(row, 8)
                    hh.value = round(r.get('x_hs') or -(r.get('x_theo') or 0.0), 2)
                    hh.number_format = '0.00'
                    k.value = 'en récup'
                    k.font = F_ANN['recup']
                if r['x_type'] == 'sans_solde':
                    # non payé et non dû : hors total des heures sup, annoté dans Total
                    k.value = 'sans solde (−%s h)' % _fr(r.get('x_theo') or 0.0)
                    k.font = F_ANN['sans_solde']
            else:
                for col, champ in ((3, 'x_m_deb'), (4, 'x_m_fin'),
                                   (5, 'x_am_deb'), (6, 'x_am_fin')):
                    t = _ft_time(r.get(champ))
                    if t is not None:
                        cc = ws.cell(row, col)
                        cc.value = t
                        cc.number_format = 'HH:MM'
                # heures sup / manquantes : valeur comptée en récup (sans solde exclu,
                # HS payées exclues) — la formule du gabarit (G − E2) est remplacée
                hh = ws.cell(row, 8)
                hh.value = round(r.get('x_hs') or 0.0, 2)
                hh.number_format = '0.00'
                ann = []
                if r.get('x_h_recup'):
                    ann.append(('en récup %s h' % _fr(r['x_h_recup']), F_ANN['recup']))
                if r.get('x_h_sans_solde'):
                    ann.append(('sans solde %s h' % _fr(r['x_h_sans_solde']), F_ANN['sans_solde']))
                if r.get('x_hs_payees') and (r.get('x_heures') or 0) > (r.get('x_theo') or 0):
                    ann.append(('HS payées +%s h' % _fr(r['x_heures'] - r['x_theo']), F_ANN['payees']))
                if ann:
                    k.value = ' · '.join(a[0] for a in ann)
                    k.font = ann[0][1]""")
rep("""    ref_f = emp.get('x_cp_ref_date') or ''
    m0 = (d1 - _dt.timedelta(days=1)).isoformat()

    def _pris_h(r):
        if r['x_type'] == 'recup':
            return r['x_theo'] or 0.0
        dj = _dt.date.fromisoformat(str(r['x_date'])[:10])
        return max(_theo_day(cal_f, dj) - (r['x_theo'] or 0.0), 0.0)

    m_1 = (emp.get('x_recup_solde') or 0.0)
    m_1 += sum(l['x_heures'] for l in call(
        'x_recup_ligne', 'search_read',
        [('x_employee_id', '=', emp_id), ('x_date', '<=', m0)],
        fields=['x_date', 'x_heures']) if not ref_f or str(l['x_date'])[:10] > ref_f)
    pstart_f = _dt.date(d1.year if d1.month >= 6 else d1.year - 1, 6, 1)
    m_1 -= sum(_pris_h(r) for r in call(
        'x_heures_jour', 'search_read',
        ['&', ('x_employee_id', '=', emp_id),
         ('x_date', '>=', pstart_f.isoformat()), ('x_date', '<=', m0),
         '|', ('x_type', '=', 'recup'), ('x_note', 'like', 'Récupération —')],
        fields=['x_date', 'x_type', 'x_theo', 'x_note'])
        if not ref_f or str(r['x_date'])[:10] > ref_f)
""", """    ref_f = emp.get('x_cp_ref_date') or ''
    m0 = (d1 - _dt.timedelta(days=1)).isoformat()
    # « Heures M-1 » = arrêté bureau + heures comptées en récup (x_hs) des jours
    # postérieurs à l'arrêté jusqu'à la veille de la période + lignes du bureau
    m_1 = (emp.get('x_recup_solde') or 0.0)
    m_1 += sum(l['x_heures'] for l in call(
        'x_recup_ligne', 'search_read',
        [('x_employee_id', '=', emp_id), ('x_date', '<=', m0)],
        fields=['x_date', 'x_heures']) if not ref_f or str(l['x_date'])[:10] > ref_f)
    pstart_f = _dt.date(d1.year if d1.month >= 6 else d1.year - 1, 6, 1)
    m_1 += sum((r.get('x_hs') or 0.0) for r in call(
        'x_heures_jour', 'search_read',
        [('x_employee_id', '=', emp_id),
         ('x_date', '>=', pstart_f.isoformat()), ('x_date', '<=', m0),
         ('x_type', 'in', list(TYPES_SOLDE))],
        fields=['x_date', 'x_type', 'x_hs'])
        if not ref_f or str(r['x_date'])[:10] > ref_f)
""")
io.open(P, 'w', encoding='utf-8', newline='\n').write(s)
import py_compile
py_compile.compile(P, doraise=True)
print('export_heures.py :', n0, '->', len(s), 'chars ; compilation OK')
