# -*- coding: utf-8 -*-
"""Tâches planifiées Odoo portées sur le relais (07/10/2026) : zéro ligne de code Python dans Odoo.

Mécanique : le cron Odoo garde son horaire mais son action devient « Créer un enregistrement » dans le modèle
x_relais_tache (nom = clé de la tâche) ; une automatisation « à la création » lance le webhook /odoo/tache (app.py) ;
le relais exécute la tâche ici et écrit l'état et le résultat sur l'enregistrement, journal visible dans Odoo
(Paramètres > Technique > Relais : tâches planifiées). Clé suffixée « :test » = calcul sans envoi ni écriture.
Tâches (code d'origine archivé dans odoo-scan-page/crons_relais_20261007/action_<id>_code.py) :
  parc_controles_hebdo    ex action 2053, cron 123  : contrôles véhicules en retard / sous 30 j / contre-visites
  caces_hebdo             ex action 2094, cron 125  : CACES et habilitations expirés / sous 90 j
  recup_hebdo             ex action 2077, cron 124  : heures mises en récup sur 7 jours
  feries_feuilles_heures  ex action 2049, cron 122  : jours fériés France dans les feuilles d'heures (120 j)
"""
import datetime
import json
from web_actions import _creer

TD = 'padding:6px 10px;border-bottom:1px solid #eee;'
TH = 'text-align:left;padding:6px 10px;'
STYLE = 'font-family:Arial,sans-serif;font-size:13px;color:#0f172a;'
BOUTON = 'background:#0f172a;color:#fff;padding:9px 16px;border-radius:8px;text-decoration:none;font-weight:700;'


def _sans_retour(fn):
    """Méthodes Odoo sans valeur de retour (mail.mail.send) : XML-RPC répond « cannot marshal None »."""
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        if 'cannot marshal None' in str(e):
            return None
        raise


def _param(call, cle):
    try:
        return call('ir.config_parameter', 'get_param', cle, '') or ''
    except Exception:  # noqa: BLE001
        return ''


def _mail(call, sujet, dest, corps):
    """Comme env['mail.mail'].sudo().create({...}).send() dans les actions d'origine."""
    mid = _creer(call, 'mail.mail', {'subject': sujet, 'email_to': dest, 'body_html': corps})
    _sans_retour(lambda: call('mail.mail', 'send', [mid]))
    return mid


def _d(val):
    """'2026-10-15' ou '2026-10-15 08:00:00' -> date."""
    return datetime.date.fromisoformat(str(val)[:10]) if val else None


def _fr(d):
    return d.strftime('%d/%m/%Y')


def _th(*titres):
    return '<tr>' + ''.join('<th style="%s">%s</th>' % (TH, t) for t in titres) + '</tr>'


def _tr(c1, c2, c3, couleur):
    return ('<tr><td style="%s">%s</td><td style="%s">%s</td><td style="%s color:%s;font-weight:700;">%s</td></tr>'
            % (TD, c1, TD, c2, TD, couleur, c3))


def _maintenant():
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')


# ─── parc_controles_hebdo (ex 2053) ───────────────────────────────────────────────────────────────────────────────────

def parc_controles_hebdo(call, option='', today=None):
    """Alerte e-mail hebdomadaire : contrôles véhicules en retard ou sous 30 jours, contre-visites à passer."""
    today = today or datetime.date.today()
    rows = call('x_controle_vehicule', 'search_read', [], fields=['x_cv_limite', 'x_derniere_date', 'x_type_id', 'x_vehicule_id'])
    tids = sorted({r['x_type_id'][0] for r in rows if r['x_type_id']})
    types = {t['id']: t for t in call('x_type_controle', 'read', tids, ['x_periodicite_mois', 'x_name'])} if tids else {}
    retard, proche, cv = [], [], []
    for r in rows:
        t = types.get(r['x_type_id'][0] if r['x_type_id'] else 0) or {}
        veh = r['x_vehicule_id'][1] if r['x_vehicule_id'] else ''
        ctrl = t.get('x_name') or (r['x_type_id'][1] if r['x_type_id'] else '')
        if r['x_cv_limite']:
            cv.append((veh, ctrl, _d(r['x_cv_limite'])))
        if not r['x_derniere_date']:
            continue
        ech = _d(r['x_derniere_date']) + datetime.timedelta(days=30 * int(t.get('x_periodicite_mois') or 0))
        if ech < today:
            retard.append((veh, ctrl, ech))
        elif (ech - today).days <= 30:
            proche.append((veh, ctrl, ech))
    if option == 'test':
        return {'test': True, 'retard': [(v, c, str(e)) for v, c, e in retard], 'proche': [(v, c, str(e)) for v, c, e in proche], 'cv': [(v, c, str(e)) for v, c, e in cv]}
    if not retard and not proche and not cv:
        return {'envoye': False, 'raison': 'rien a signaler'}
    dest = _param(call, 'maquignon.parc_alerte_email')
    if not dest:
        return {'envoye': False, 'raison': 'aucun destinataire configure'}
    corps = '<div style="%s"><h3>🚛 Parc automobile — contrôles à surveiller</h3>' % STYLE
    if retard:
        corps += '<p><b style="color:#991b1b;">%d contrôle(s) en retard :</b></p><table style="border-collapse:collapse;width:100%%;margin-bottom:14px;">' % len(retard)
        corps += _th('Véhicule', 'Contrôle', 'Échéance dépassée le') + ''.join(_tr(v, c, _fr(e), '#991b1b') for v, c, e in sorted(retard, key=lambda r: r[2])) + '</table>'
    if proche:
        corps += '<p><b style="color:#92400e;">%d contrôle(s) à échéance sous 30 jours :</b></p><table style="border-collapse:collapse;width:100%%;">' % len(proche)
        corps += _th('Véhicule', 'Contrôle', 'Échéance') + ''.join(_tr(v, c, _fr(e), '#92400e') for v, c, e in sorted(proche, key=lambda r: r[2])) + '</table>'
    if cv:
        corps += '<p><b style="color:#831843;">%d contre-visite(s) a passer :</b></p><table style="border-collapse:collapse;width:100%%;margin-bottom:14px;">' % len(cv)
        corps += _th('Véhicule', 'Contrôle', 'Avant le') + ''.join(_tr(v, c, _fr(e), '#831843') for v, c, e in sorted(cv, key=lambda r: r[2])) + '</table>'
    corps += '<p style="margin-top:16px;"><a href="https://maquignon.odoo.com/parc-controles" style="%s">Ouvrir le planning des contrôles</a></p></div>' % BOUTON
    _mail(call, '🚛 Parc automobile : %d en retard, %d sous 30 j, %d contre-visite(s)' % (len(retard), len(proche), len(cv)), dest, corps)
    return {'envoye': True, 'retard': len(retard), 'proche': len(proche), 'cv': len(cv), 'dest': dest}


# ─── caces_hebdo (ex 2094) ────────────────────────────────────────────────────────────────────────────────────────────

def caces_hebdo(call, option='', today=None):
    """Alerte e-mail hebdomadaire : certifications (CACES, habilitations...) expirées ou expirant sous 90 jours."""
    today = today or datetime.date.today()
    lignes = call('hr.employee.skill', 'search_read', [['is_certification', '=', True], ['employee_id.active', '=', True]],
                  fields=['valid_to', 'skill_id', 'employee_id'])
    expirees, proches, sans_date = [], [], []
    for l in lignes:
        emp = l['employee_id'][1] if l['employee_id'] else ''
        sk = l['skill_id'][1] if l['skill_id'] else ''
        if not l['valid_to']:
            sans_date.append((emp, sk))
        elif _d(l['valid_to']) < today:
            expirees.append((emp, sk, _d(l['valid_to'])))
        elif (_d(l['valid_to']) - today).days <= 90:
            proches.append((emp, sk, _d(l['valid_to'])))
    if option == 'test':
        return {'test': True, 'expirees': [(e, s, str(d)) for e, s, d in expirees], 'proches': [(e, s, str(d)) for e, s, d in proches], 'sans_date': len(sans_date)}
    if not expirees and not proches:
        return {'envoye': False, 'raison': 'rien a signaler'}
    dest = _param(call, 'maquignon.caces_alerte_email')
    if not dest:
        return {'envoye': False, 'raison': 'aucun destinataire configure (maquignon.caces_alerte_email)'}
    entete = _th('Salarié', 'Certification', 'Fin de validité')
    corps = '<div style="%s"><h3>🎓 CACES &amp; habilitations à surveiller</h3>' % STYLE
    if expirees:
        corps += '<p><b style="color:#991b1b;">%d certification(s) expirée(s) :</b></p><table style="border-collapse:collapse;width:100%%;margin-bottom:14px;">' % len(expirees) + entete
        corps += ''.join(_tr(e, s, _fr(d), '#991b1b') for e, s, d in sorted(expirees, key=lambda r: r[2])) + '</table>'
    if proches:
        corps += '<p><b style="color:#92400e;">%d certification(s) expirant sous 3 mois :</b></p><table style="border-collapse:collapse;width:100%%;margin-bottom:14px;">' % len(proches) + entete
        corps += ''.join(_tr(e, s, _fr(d), '#92400e') for e, s, d in sorted(proches, key=lambda r: r[2])) + '</table>'
    if sans_date:
        corps += '<p style="color:#64748b;">%d certification(s) sans date de fin de validité renseignée.</p>' % len(sans_date)
    corps += ('<p style="margin-top:16px;"><a href="https://maquignon.odoo.com/odoo/action-hr_skills.hr_employee_skill_report_action" style="%s">'
              'Ouvrir l\'analyse des compétences</a></p></div>' % BOUTON)
    _mail(call, '🎓 CACES / habilitations : %d expirée(s), %d sous 3 mois' % (len(expirees), len(proches)), dest, corps)
    return {'envoye': True, 'expirees': len(expirees), 'proches': len(proches), 'dest': dest}


# ─── recup_hebdo (ex 2077) ────────────────────────────────────────────────────────────────────────────────────────────

def recup_hebdo(call, option='', today=None):
    """Récap hebdo au bureau : heures mises en récup par les salariés (7 derniers jours)."""
    today = today or datetime.date.today()
    depuis = today - datetime.timedelta(days=7)
    lignes = call('x_recup_ligne', 'search_read', [['create_date', '>=', depuis.strftime('%Y-%m-%d 00:00:00')]],
                  fields=['x_employee_id', 'x_date', 'x_heures', 'x_note'], order='x_employee_id, x_date')
    if option == 'test':
        return {'test': True, 'lignes': [(l['x_employee_id'] and l['x_employee_id'][1], l['x_date'], l['x_heures']) for l in lignes]}
    if not lignes:
        return {'envoye': False, 'raison': 'aucune heure mise en recup cette semaine'}
    dest = _param(call, 'maquignon.recup_alerte_email')
    if not dest:
        return {'envoye': False, 'raison': 'aucun destinataire configure'}
    total = sum((l['x_heures'] or 0.0) for l in lignes)
    emps = {l['x_employee_id'][0] for l in lignes if l['x_employee_id']}
    corps = '<div style="%s"><h3>🔄 Heures mises en récup cette semaine</h3><table style="border-collapse:collapse;width:100%%;">' % STYLE
    corps += _th('Salarié', 'Date', 'Heures', 'Note')
    for l in lignes:
        corps += ('<tr><td style="%s">%s</td><td style="%s">%s</td><td style="%s font-weight:700;color:#0369a1;">+%g h</td><td style="%s color:#64748b;">%s</td></tr>'
                  % (TD, l['x_employee_id'][1] if l['x_employee_id'] else '', TD, _fr(_d(l['x_date'])) if l['x_date'] else '', TD, l['x_heures'] or 0.0, TD, l['x_note'] or ''))
    corps += '</table>'
    corps += ('<p style="margin-top:12px;color:#64748b;">Ces heures s\'ajoutent au solde de récup de chaque salarié (visible sur sa page et sur /heures-admin). '
              'En cas d\'erreur, le salarié peut supprimer sa ligne, ou le bureau peut ajuster le solde arrêté sur la page ⏰ Horaires par défaut.</p></div>')
    _mail(call, '🔄 Récup : %g h mises en récup par %d salarié(s) cette semaine' % (total, len(emps)), dest, corps)
    return {'envoye': True, 'total': total, 'salaries': len(emps), 'dest': dest}


# ─── feries_feuilles_heures (ex 2049) ─────────────────────────────────────────────────────────────────────────────────

def _paques(y):
    a = y % 19; b = y // 100; c = y % 100
    d0 = b // 4; e = b % 4; f = (b + 8) // 25
    g = (b - f + 1) // 3; h = (19 * a + b - d0 - g + 15) % 30
    i = c // 4; k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    return datetime.date(y, (h + l - 7 * m + 114) // 31, ((h + l - 7 * m + 114) % 31) + 1)


def feries_france(today, horizon):
    hols = set()
    for y in {today.year, horizon.year}:
        p = _paques(y)
        hols.update([datetime.date(y, 1, 1), p + datetime.timedelta(days=1), datetime.date(y, 5, 1), datetime.date(y, 5, 8),
                     p + datetime.timedelta(days=39), p + datetime.timedelta(days=50), datetime.date(y, 7, 14), datetime.date(y, 8, 15),
                     datetime.date(y, 11, 1), datetime.date(y, 11, 11), datetime.date(y, 12, 25)])
    return sorted(h for h in hols if today <= h <= horizon)


def feries_feuilles_heures(call, option='', today=None):
    """Crée les jours « férié » dans les feuilles d'heures pour les ~120 prochains jours, pour chaque salarié dont c'est
    un jour ouvré (horaire théorique > 0). Ne touche jamais à un jour déjà saisi."""
    today = today or datetime.date.today()
    horizon = today + datetime.timedelta(days=120)
    hols = feries_france(today, horizon)
    emps = call('hr.employee', 'search_read', [['active', '=', True], ['resource_calendar_id', '!=', False]], fields=['resource_calendar_id'])
    cal_ids = sorted({e['resource_calendar_id'][0] for e in emps})
    cals = {c['id']: c for c in call('resource.calendar', 'read', cal_ids, ['attendance_ids', 'two_weeks_calendar'])} if cal_ids else {}
    att_ids = sorted({a for c in cals.values() for a in c['attendance_ids']})
    atts = {a['id']: a for a in call('resource.calendar.attendance', 'read', att_ids, ['dayofweek', 'display_type', 'week_type', 'hour_from', 'hour_to'])} if att_ids else {}
    if option == 'test':
        return {'test': True, 'feries': [str(h) for h in hols], 'salaries': len(emps)}
    crees = 0
    for e in emps:
        cal = cals[e['resource_calendar_id'][0]]
        for d in hols:
            wt = str(((d - datetime.date(1970, 1, 5)).days // 7) % 2)
            theo = 0.0
            for aid in cal['attendance_ids']:
                att = atts.get(aid)
                if not att or att['dayofweek'] != str(d.weekday()) or att['display_type']:
                    continue
                if cal['two_weeks_calendar'] and att['week_type'] and att['week_type'] != wt:
                    continue
                theo += att['hour_to'] - att['hour_from']
            if theo <= 0:
                continue
            if call('x_heures_jour', 'search_count', [['x_employee_id', '=', e['id']], ['x_date', '=', d.strftime('%Y-%m-%d')]]):
                continue
            _creer(call, 'x_heures_jour', {'x_employee_id': e['id'], 'x_date': d.strftime('%Y-%m-%d'), 'x_type': 'ferie',
                                           'x_m_deb': 0, 'x_m_fin': 0, 'x_am_deb': 0, 'x_am_fin': 0, 'x_heures': 0.0, 'x_theo': theo, 'x_hs': 0.0})
            crees += 1
    return {'crees': crees, 'feries': [str(h) for h in hols]}


# ─── point d'entrée ──────────────────────────────────────────────────────────────────────────────────────────────────

TACHES = {'parc_controles_hebdo': parc_controles_hebdo, 'caces_hebdo': caces_hebdo,
          'recup_hebdo': recup_hebdo, 'feries_feuilles_heures': feries_feuilles_heures}


def executer(call, tache_id, nom):
    """Exécute la tâche nommée par l'enregistrement x_relais_tache et y écrit l'état et le résultat."""
    cle, _, option = (nom or '').partition(':')
    fn = TACHES.get(cle.strip())
    if not fn:
        call('x_relais_tache', 'write', [tache_id], {'x_etat': 'erreur', 'x_resultat': 'tâche inconnue : %r (connues : %s)' % (nom, ', '.join(sorted(TACHES))), 'x_fin': _maintenant()})
        return {'erreur': 'tâche inconnue'}
    call('x_relais_tache', 'write', [tache_id], {'x_etat': 'en_cours', 'x_debut': _maintenant(), 'x_resultat': False})
    try:
        res = fn(call, option.strip())
    except Exception as e:  # noqa: BLE001
        call('x_relais_tache', 'write', [tache_id], {'x_etat': 'erreur', 'x_resultat': ('%s: %s' % (type(e).__name__, e))[-1500:], 'x_fin': _maintenant()})
        raise
    call('x_relais_tache', 'write', [tache_id], {'x_etat': 'fait', 'x_resultat': json.dumps(res, ensure_ascii=False, default=str)[:4000], 'x_fin': _maintenant()})
    return res
