# Fériés France : crée les jours "férié" dans les feuilles d'heures
# pour les ~120 prochains jours, pour chaque salarié dont c'est un jour ouvré.
# Ne touche jamais à un jour déjà saisi. Relancé chaque mois par le cron.
today = datetime.date.today()
horizon = today + datetime.timedelta(days=120)
hols = set()
for y in set([today.year, horizon.year]):
    a = y % 19; b = y // 100; c = y % 100
    d0 = b // 4; e = b % 4; f = (b + 8) // 25
    g = (b - f + 1) // 3; h = (19 * a + b - d0 - g + 15) % 30
    i = c // 4; k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    paques = datetime.date(y, (h + l - 7 * m + 114) // 31, ((h + l - 7 * m + 114) % 31) + 1)
    hols.update([
        datetime.date(y, 1, 1), paques + datetime.timedelta(days=1),
        datetime.date(y, 5, 1), datetime.date(y, 5, 8),
        paques + datetime.timedelta(days=39), paques + datetime.timedelta(days=50),
        datetime.date(y, 7, 14), datetime.date(y, 8, 15), datetime.date(y, 11, 1),
        datetime.date(y, 11, 11), datetime.date(y, 12, 25),
    ])
hols = sorted([x for x in hols if today <= x <= horizon])
HJ = env['x_heures_jour'].sudo()
emps = env['hr.employee'].sudo().search([('active', '=', True), ('resource_calendar_id', '!=', False)])
created = 0
for emp in emps:
    cal = emp.resource_calendar_id
    for d in hols:
        wt = str(((d - datetime.date(1970, 1, 5)).days // 7) % 2)
        theo = 0.0
        for att in cal.attendance_ids:
            if att.dayofweek != str(d.weekday()) or att.display_type:
                continue
            if cal.two_weeks_calendar and att.week_type and att.week_type != wt:
                continue
            theo += (att.hour_to - att.hour_from)
        if theo <= 0:
            continue
        if HJ.search_count([('x_employee_id', '=', emp.id), ('x_date', '=', d.strftime('%Y-%m-%d'))]):
            continue
        HJ.create({'x_employee_id': emp.id, 'x_date': d.strftime('%Y-%m-%d'), 'x_type': 'ferie',
                   'x_m_deb': 0, 'x_m_fin': 0, 'x_am_deb': 0, 'x_am_fin': 0,
                   'x_heures': 0.0, 'x_theo': theo, 'x_hs': 0.0})
        created += 1
action = {'crees': created, 'feries': [str(x) for x in hols]}
