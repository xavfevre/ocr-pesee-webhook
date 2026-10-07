# -*- coding: utf-8 -*-
"""Test hors ligne de taches_relais.py avec un faux Odoo en mémoire.   python test_taches_mock.py"""
import os, sys, re, datetime
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import taches_relais as T

AUJ = datetime.date(2026, 10, 7)


class Faux:
    def __init__(self):
        self.d = {
            'x_controle_vehicule': {1: {'id': 1, 'x_cv_limite': False, 'x_derniere_date': '2026-03-01', 'x_type_id': [10, 'CT'], 'x_vehicule_id': [100, 'SEMI GE-106-QS']},     # 6 mois -> 28/08 : retard
                                    2: {'id': 2, 'x_cv_limite': False, 'x_derniere_date': '2026-09-20', 'x_type_id': [11, 'Mines'], 'x_vehicule_id': [101, 'CAMION AB-123-CD']},  # 1 mois -> 20/10 : proche
                                    3: {'id': 3, 'x_cv_limite': '2026-10-20', 'x_derniere_date': False, 'x_type_id': [10, 'CT'], 'x_vehicule_id': [102, 'VL EF-456-GH']},       # contre-visite
                                    4: {'id': 4, 'x_cv_limite': False, 'x_derniere_date': '2026-10-01', 'x_type_id': [10, 'CT'], 'x_vehicule_id': [103, 'VL IJ-789-KL']}},     # 6 mois : rien
            'x_type_controle': {10: {'id': 10, 'x_periodicite_mois': 6, 'x_name': 'Contrôle technique'}, 11: {'id': 11, 'x_periodicite_mois': 1, 'x_name': 'Passage aux mines'}},
            'hr.employee.skill': {1: {'id': 1, 'is_certification': True, 'valid_to': '2026-09-01', 'skill_id': [1, 'CACES R489'], 'employee_id': [5, 'DURAND Mickaël']},
                                  2: {'id': 2, 'is_certification': True, 'valid_to': '2026-12-15', 'skill_id': [2, 'Habilitation élec'], 'employee_id': [6, 'MARTIN Paul']},
                                  3: {'id': 3, 'is_certification': True, 'valid_to': False, 'skill_id': [1, 'CACES R489'], 'employee_id': [7, 'PETIT Léa']},
                                  4: {'id': 4, 'is_certification': True, 'valid_to': '2027-06-01', 'skill_id': [1, 'CACES R489'], 'employee_id': [6, 'MARTIN Paul']}},
            'x_recup_ligne': {1: {'id': 1, 'create_date': '2026-10-03 10:00:00', 'x_employee_id': [5, 'DURAND Mickaël'], 'x_date': '2026-10-02', 'x_heures': 2.5, 'x_note': 'fin de chantier'},
                              2: {'id': 2, 'create_date': '2026-09-20 10:00:00', 'x_employee_id': [6, 'MARTIN Paul'], 'x_date': '2026-09-19', 'x_heures': 1.0, 'x_note': False}},
            'hr.employee': {5: {'id': 5, 'active': True, 'resource_calendar_id': [1, '35 h']}, 6: {'id': 6, 'active': True, 'resource_calendar_id': [2, '2 semaines']}, 7: {'id': 7, 'active': True, 'resource_calendar_id': False}},
            'resource.calendar': {1: {'id': 1, 'attendance_ids': [11, 12, 13, 14, 15], 'two_weeks_calendar': False}, 2: {'id': 2, 'attendance_ids': [21, 22], 'two_weeks_calendar': True}},
            'resource.calendar.attendance': {11: {'id': 11, 'dayofweek': '0', 'display_type': False, 'week_type': False, 'hour_from': 8.0, 'hour_to': 16.0},
                                             12: {'id': 12, 'dayofweek': '1', 'display_type': False, 'week_type': False, 'hour_from': 8.0, 'hour_to': 16.0},
                                             13: {'id': 13, 'dayofweek': '2', 'display_type': False, 'week_type': False, 'hour_from': 8.0, 'hour_to': 16.0},
                                             14: {'id': 14, 'dayofweek': '3', 'display_type': False, 'week_type': False, 'hour_from': 8.0, 'hour_to': 16.0},
                                             15: {'id': 15, 'dayofweek': '4', 'display_type': 'line_section', 'week_type': False, 'hour_from': 0.0, 'hour_to': 0.0},
                                             21: {'id': 21, 'dayofweek': '2', 'display_type': False, 'week_type': '0', 'hour_from': 8.0, 'hour_to': 12.0},
                                             22: {'id': 22, 'dayofweek': '2', 'display_type': False, 'week_type': '1', 'hour_from': 8.0, 'hour_to': 17.0}},
            'x_heures_jour': {900: {'id': 900, 'x_employee_id': [5, 'DURAND'], 'x_date': '2026-11-11'}},
            'x_relais_tache': {77: {'id': 77, 'x_name': 'parc_controles_hebdo', 'x_etat': 'a_faire'}},
            'mail.mail': {},
            'ir.config_parameter': {'maquignon.parc_alerte_email': 'corentin@maquignon.com', 'maquignon.caces_alerte_email': 'isabelle@maquignon.com', 'maquignon.recup_alerte_email': 'isabelle@maquignon.com'},
        }
        self.prochain = 5000
        self.envoyes = []

    def __call__(self, model, method, *params, **kw):
        return getattr(self, 'm_' + method)(model, *params, **kw)

    def _val(self, rec, f):
        if '.' in f:
            a, b = f.split('.', 1)
            return self._val(self.d['hr.employee'][rec[a][0]], b) if rec.get(a) else False
        v = rec.get(f, False)
        return v[0] if isinstance(v, list) and len(v) == 2 and isinstance(v[1], str) else v

    def _ok(self, rec, dom):
        for f, op, v in dom:
            val = self._val(rec, f)
            if op == '=' and val != v: return False
            if op == '!=' and val == v: return False
            if op == '>=' and not (val and str(val) >= str(v)): return False
            if op == 'in' and val not in v: return False
        return True

    def m_search_read(self, model, dom, fields=None, order=None, limit=None, **kw):
        recs = [r for r in self.d[model].values() if self._ok(r, dom)]
        if order:
            recs.sort(key=lambda r: tuple(str(self._val(r, f.strip())) for f in order.split(',')))
        return [{f: r.get(f, False) for f in ['id'] + list(fields or r.keys())} for r in recs]

    def m_search_count(self, model, dom, **kw):
        return len(self.m_search_read(model, dom))

    def m_read(self, model, ids, fields, **kw):
        return [{f: self.d[model][i].get(f, False) for f in ['id'] + list(fields)} for i in ids]

    def m_write(self, model, ids, vals, **kw):
        for i in ids:
            self.d[model][i].update(vals)
        return True

    def m_create(self, model, vals, **kw):
        self.prochain += 1
        self.d[model][self.prochain] = dict(vals, id=self.prochain)
        return self.prochain

    def m_get_param(self, model, cle, defaut='', **kw):
        return self.d['ir.config_parameter'].get(cle, defaut)

    def m_send(self, model, ids, **kw):
        self.envoyes.append(self.d['mail.mail'][ids[0]])
        return None


def texte(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html))


f = Faux()
# 1. parc auto
r = T.parc_controles_hebdo(f, today=AUJ)
mail = f.envoyes[-1]
print('1.', r, '|', mail['subject'])
assert r == {'envoye': True, 'retard': 1, 'proche': 1, 'cv': 1, 'dest': 'corentin@maquignon.com'}
assert mail['subject'] == '🚛 Parc automobile : 1 en retard, 1 sous 30 j, 1 contre-visite(s)' and mail['email_to'] == 'corentin@maquignon.com'
t = texte(mail['body_html'])
assert 'SEMI GE-106-QS Contrôle technique 28/08/2026' in t and 'CAMION AB-123-CD Passage aux mines 20/10/2026' in t and 'VL EF-456-GH Contrôle technique 20/10/2026' in t and 'IJ-789-KL' not in t, t
assert T.parc_controles_hebdo(f, 'test', today=AUJ)['retard'] == [('SEMI GE-106-QS', 'Contrôle technique', '2026-08-28')]
f.d['x_controle_vehicule'] = {}
assert T.parc_controles_hebdo(f, today=AUJ) == {'envoye': False, 'raison': 'rien a signaler'}
# 2. CACES
r = T.caces_hebdo(f, today=AUJ); mail = f.envoyes[-1]
print('2.', r, '|', mail['subject'])
assert r == {'envoye': True, 'expirees': 1, 'proches': 1, 'dest': 'isabelle@maquignon.com'}
t = texte(mail['body_html'])
assert 'DURAND Mickaël CACES R489 01/09/2026' in t and 'MARTIN Paul Habilitation élec 15/12/2026' in t and '1 certification(s) sans date' in t and '01/06/2027' not in t, t
assert T.caces_hebdo(f, 'test', today=AUJ)['sans_date'] == 1
# 3. récup
r = T.recup_hebdo(f, today=AUJ); mail = f.envoyes[-1]
print('3.', r, '|', mail['subject'])
assert r == {'envoye': True, 'total': 2.5, 'salaries': 1, 'dest': 'isabelle@maquignon.com'} and '+2.5 h' in texte(mail['body_html']) and 'MARTIN' not in mail['body_html']
assert mail['subject'] == '🔄 Récup : 2.5 h mises en récup par 1 salarié(s) cette semaine'
# 4. fériés : du 07/10/2026 au 04/02/2027 -> 1/11 (dimanche), 11/11 (mercredi), 25/12 (vendredi), 1/1/2027 (vendredi)
r = T.feries_feuilles_heures(f, today=AUJ)
print('4.', r)
assert r['feries'] == ['2026-11-01', '2026-11-11', '2026-12-25', '2027-01-01'], r
crees = [v for k, v in f.d['x_heures_jour'].items() if k != 900]
print('   créés :', sorted((c['x_employee_id'], c['x_date'], c['x_theo']) for c in crees))
# salarié 5 (lun-jeu 8 h) : 11/11 déjà saisi -> rien ; 1/11 dimanche, 25/12 et 1/1 vendredis -> rien. Salarié 6 : mercredi semaine paire/impaire -> 11/11
# seulement ; semaine du 11/11/2026 = type 0 (20764 jours depuis le 05/01/1970, 2966 semaines, paire) -> présence 21 : 4 h.
assert r['crees'] == 1 and sorted((c['x_employee_id'], c['x_date'], c['x_theo'], c['x_type']) for c in crees) == [(6, '2026-11-11', 4.0, 'ferie')], crees
assert T.feries_feuilles_heures(f, 'test', today=AUJ)['salaries'] == 2
assert T._paques(2026) == datetime.date(2026, 4, 5) and T._paques(2027) == datetime.date(2027, 3, 28)
# 5. point d'entrée : état écrit sur la tâche
f.d['x_controle_vehicule'] = {1: {'id': 1, 'x_cv_limite': '2026-10-09', 'x_derniere_date': False, 'x_type_id': [10, 'CT'], 'x_vehicule_id': [100, 'SEMI']}}
res = T.executer(f, 77, 'parc_controles_hebdo')
print('5.', res, '|', f.d['x_relais_tache'][77])
assert f.d['x_relais_tache'][77]['x_etat'] == 'fait' and '"cv": 1' in f.d['x_relais_tache'][77]['x_resultat'] and f.d['x_relais_tache'][77]['x_debut'] and f.d['x_relais_tache'][77]['x_fin']
T.executer(f, 77, 'inconnue'); assert f.d['x_relais_tache'][77]['x_etat'] == 'erreur' and 'inconnue' in f.d['x_relais_tache'][77]['x_resultat']
res = T.executer(f, 77, 'caces_hebdo:test'); assert res.get('test') and f.d['x_relais_tache'][77]['x_etat'] == 'fait'
print()
print('TEST MOCK OK : %d mail(s) envoyé(s)' % len(f.envoyes))
