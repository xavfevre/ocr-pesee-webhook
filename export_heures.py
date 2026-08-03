# -*- coding: utf-8 -*-
"""Export paie des heures salariés — un classeur Excel, un onglet par salarié.

Format inspiré du fichier de travail de la comptable (« Feuille de temps
hebdomadaire ») : blocs par semaine avec Arrivée/Départ matin et après-midi,
heures effectuées, écart vs horaire contractuel, mentions CP / MALADIE /
FERIE / ABSENCE / RECUP dans les cases, totaux hebdo + récap mensuel.

Les données viennent du modèle Odoo `x_heures_jour` (saisie web /mes-heures
et /heures-admin).
"""
import io
import re
from datetime import date, datetime, timedelta

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

TYPES = {
    'cp': 'CP', 'maladie': 'MALADIE', 'ferie': 'FERIE',
    'absence': 'ABSENT', 'recup': 'RECUP', 'repos': '',
}
JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']


def _fmt_h(h):
    """7.5 -> '07:30' ; 0 -> ''"""
    if not h:
        return ''
    return '%02d:%02d' % (int(h), round((h - int(h)) * 60))


def _theo_day(cal, d):
    """Heures théoriques + plages types pour un jour selon le calendrier."""
    if not cal:
        return 0.0
    wt = str(((d - date(1970, 1, 5)).days // 7) % 2)
    tot = 0.0
    for a in cal['attendance_ids']:
        if a['dayofweek'] != str(d.weekday()) or a.get('display_type'):
            continue
        if cal['two_weeks_calendar'] and a.get('week_type') and a['week_type'] != wt:
            continue
        tot += a['hour_to'] - a['hour_from']
    return tot


def build(call, mois, comp='all'):
    """Génère le classeur ; `call(model, method, *args, **kw)` = execute_kw.
    mois = 'YYYY-MM' ; comp = 'all' ou id de société."""
    y, m = int(mois[:4]), int(mois[5:7])
    d1 = date(y, m, 1)
    d2 = (date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)) - timedelta(days=1)
    # semaines couvrant le mois (lundi -> dimanche)
    monday0 = d1 - timedelta(days=d1.weekday())
    dom = [('active', '=', True)]
    if comp != 'all':
        dom.append(('company_id', '=', int(comp)))
    emps = call('hr.employee', 'search_read', dom,
                fields=['name', 'company_id', 'resource_calendar_id'], order='company_id, name')
    cal_ids = sorted(set(e['resource_calendar_id'][0] for e in emps if e['resource_calendar_id']))
    cals = {c['id']: c for c in call('resource.calendar', 'read', cal_ids,
            fields=['name', 'two_weeks_calendar', 'attendance_ids'])} if cal_ids else {}
    att_ids = sorted(set(a for c in cals.values() for a in c['attendance_ids']))
    atts = {a['id']: a for a in call('resource.calendar.attendance', 'read', att_ids,
            fields=['dayofweek', 'hour_from', 'hour_to', 'day_period', 'week_type', 'display_type'])} if att_ids else {}
    for c in cals.values():
        c['attendance_ids'] = [atts[a] for a in c['attendance_ids'] if a in atts]
    rows = call('x_heures_jour', 'search_read',
                [('x_employee_id', 'in', [e['id'] for e in emps]),
                 ('x_date', '>=', monday0.strftime('%Y-%m-%d')),
                 ('x_date', '<=', (d2 + timedelta(days=6)).strftime('%Y-%m-%d'))],
                fields=['x_employee_id', 'x_date', 'x_type', 'x_m_deb', 'x_m_fin',
                        'x_am_deb', 'x_am_fin', 'x_heures', 'x_theo', 'x_hs', 'x_note'])
    by_emp = {}
    for r in rows:
        by_emp.setdefault(r['x_employee_id'][0], {})[r['x_date']] = r

    wb = Workbook()
    wb.remove(wb.active)
    F10 = Font(name='Arial', size=10)
    FB = Font(name='Arial', size=10, bold=True)
    FT = Font(name='Arial', size=13, bold=True)
    HDR = Font(name='Arial', size=9.5, bold=True, color='FFFFFF')
    FILL = PatternFill('solid', start_color='1F4E5F')
    WFILL = PatternFill('solid', start_color='E8EEF1')
    thin = Border(bottom=Side(style='thin', color='CCCCCC'))
    CTR = Alignment(horizontal='center')

    for e in emps:
        title = re.sub(r'[\[\]:*?/\\]', ' ', e['name'])[:31]
        ws = wb.create_sheet(title)
        cal = cals.get(e['resource_calendar_id'][0]) if e['resource_calendar_id'] else None
        saisies = by_emp.get(e['id'], {})
        ws['A1'] = f"HEURES — {e['name']}"
        ws['A1'].font = FT
        ws['A2'] = f"{e['company_id'][1]} · {cal['name'] if cal else 'sans horaire'} · {mois}"
        ws['A2'].font = Font(name='Arial', size=10, italic=True)
        # récap mensuel (calculé sur les jours DU mois uniquement)
        tot_h = tot_theo = 0.0
        n_cp = n_mal = n_abs = n_fer = n_rec = 0
        d = d1
        while d <= d2:
            s = saisies.get(d.strftime('%Y-%m-%d'))
            tot_theo += _theo_day(cal, d)
            if s:
                t = s['x_type']
                if t == 'travail':
                    tot_h += s['x_heures']
                elif t == 'cp':
                    n_cp += 1
                elif t == 'maladie':
                    n_mal += 1
                elif t == 'absence':
                    n_abs += 1
                elif t == 'ferie':
                    n_fer += 1
                elif t == 'recup':
                    n_rec += 1
            d += timedelta(days=1)
        heads = ['Heures effectuées', 'Heures théoriques', 'Écart', 'Jours CP',
                 'Jours maladie', 'Jours absence', 'Fériés', 'Jours récup']
        vals = [round(tot_h, 2), round(tot_theo, 2), round(tot_h - tot_theo, 2),
                n_cp, n_mal, n_abs, n_fer, n_rec]
        for j, (h, v) in enumerate(zip(heads, vals), 1):
            c = ws.cell(row=4, column=j, value=h); c.font = HDR; c.fill = FILL; c.alignment = CTR
            c2 = ws.cell(row=5, column=j, value=v); c2.font = FB; c2.alignment = CTR
        # blocs hebdomadaires
        r = 7
        monday = monday0
        while monday <= d2:
            sunday = monday + timedelta(days=6)
            c = ws.cell(row=r, column=1, value=f"Semaine {monday.isocalendar()[1]} — du {monday.strftime('%d/%m')} au {sunday.strftime('%d/%m')}")
            c.font = FB
            for j in range(1, 10):
                ws.cell(row=r, column=j).fill = WFILL
            r += 1
            for j, h in enumerate(['Jour', 'Date', 'Arrivée', 'Départ', 'Arrivée', 'Départ',
                                   'Heures', 'Écart', 'Note'], 1):
                c = ws.cell(row=r, column=j, value=h); c.font = HDR; c.fill = FILL; c.alignment = CTR
            r += 1
            wtot = wtheo = 0.0
            for i in range(7):
                d = monday + timedelta(days=i)
                in_month = d1 <= d <= d2
                s = saisies.get(d.strftime('%Y-%m-%d'))
                theo = _theo_day(cal, d)
                if in_month:
                    wtheo += theo
                ws.cell(row=r, column=1, value=JOURS[i]).font = F10
                ws.cell(row=r, column=2, value=d.strftime('%d/%m/%Y')).font = F10
                if s and s['x_type'] == 'travail':
                    for j, v in enumerate([_fmt_h(s['x_m_deb']), _fmt_h(s['x_m_fin']),
                                           _fmt_h(s['x_am_deb']), _fmt_h(s['x_am_fin'])], 3):
                        c = ws.cell(row=r, column=j, value=v); c.font = F10; c.alignment = CTR
                    c = ws.cell(row=r, column=7, value=round(s['x_heures'], 2)); c.font = FB; c.alignment = CTR
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
            ws.column_dimensions[col].width = w
        ws.freeze_panes = 'A6'
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
