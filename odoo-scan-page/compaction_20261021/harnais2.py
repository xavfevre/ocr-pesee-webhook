# -*- coding: utf-8 -*-
"""Harnais d'équivalence avant/après, série 2 : 2065 sections imbriquées, 2073 miroir congés, 1979/1980 Fab en cours,
2082 code client Sage. Même principe que harnais.py (faux ORM, données réelles lues en production + cas synthétiques)."""
import os, sys, copy, json, random, datetime
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harnais as H
from harnais import Rec, RS, Vide, call, CTX, charger, cloc, executer, comparer

def J():
    return H.JOURNAL

def raz():
    H.JOURNAL = []
    Rec._seq[0] = 100000

class R(Rec):
    """Enregistrement avec sudo()/with_context() transparents."""
    def sudo(self): return self
    def with_context(self, **kw): return self

class S(RS):
    def sudo(self): return self
    def with_context(self, **kw): return self
    def sorted(self, key=None):
        return S(sorted(self.items, key=(lambda r: getattr(r, key)) if isinstance(key, str) else key))
    def filtered(self, fn): return S([r for r in self.items if fn(r)])

def comp(nom, r1=None, r2=None):
    """Compare les journaux capturés (j1 puis j2 dans H.JOURNAL via raz())."""
    return comparer(nom, comp.j1, r1, comp.j2, r2)

# ─────────────────────────────── 2065
def test_2065():
    av, ap = charger(2065); print('\n== 2065 Sections imbriquées : %d -> %d lignes' % (cloc(av), cloc(ap)))
    moves = call('account.move', 'search_read', [['move_type', '=', 'out_invoice'], ['invoice_origin', '=like', 'S%'], ['invoice_line_ids.sale_line_ids', '!=', False]], fields=['name', 'move_type', 'invoice_origin', 'invoice_line_ids'], order='id desc', limit=14, **CTX)
    ok = True
    for mv in moves:
        origins = [o.strip() for o in mv['invoice_origin'].split(',') if o.strip()]
        sos = call('sale.order', 'search_read', [['name', 'in', origins]], fields=['order_line'], **CTX)
        sol_ids = [i for so in sos for i in so['order_line']]
        sols = call('sale.order.line', 'read', sol_ids, fields=['display_type', 'name', 'sequence', 'is_downpayment'], **CTX) if sol_ids else []
        ils = call('account.move.line', 'read', mv['invoice_line_ids'], fields=['display_type', 'name', 'sequence', 'sale_line_ids'], **CTX)
        for variante in ('tel quel', 'sans sections'):
            def fab():
                raz()
                sol_objs = {l['id']: R(id=l['id'], display_type=l['display_type'], name=l['name'], sequence=l['sequence'], is_downpayment=l['is_downpayment']) for l in sols}
                lignes = [R(id=l['id'], display_type=l['display_type'], name=l['name'], sequence=l['sequence'], sale_line_ids=S([sol_objs[i] for i in l['sale_line_ids'] if i in sol_objs])) for l in ils if not (variante == 'sans sections' and l['display_type'] == 'line_section')]
                move = R(id=mv['id'], move_type=mv['move_type'], invoice_origin=mv['invoice_origin'], invoice_line_ids=S(lignes))
                orders = S([R(id=so['id']) for so in sos]); orders.order_line = S(list(sol_objs.values()))
                class Env(object):
                    def __getitem__(self, model):
                        if model == 'sale.order':
                            class SO(object):
                                def sudo(self): return self
                                def search(self, dom): H.JOURNAL.append(('search', model, dom)); return orders
                            return SO()
                        if model == 'account.move.line':
                            class AML(object):
                                def sudo(self): return self
                                def create(self, vals): H.JOURNAL.append(('create', model, json.loads(json.dumps(vals, default=str, sort_keys=True)))); return R()
                            return AML()
                        raise KeyError(model)
                return {'records': S([move]), 'env': Env()}
            executer(av, fab()); comp.j1 = copy.deepcopy(J())
            executer(ap, fab()); comp.j2 = copy.deepcopy(J())
            ok &= comp('%s / %s (%d lignes, %d lignes de commande)' % (mv['name'], variante, len(ils), len(sols)))
    return ok

# ─────────────────────────────── 2073
def test_2073():
    av, ap = charger(2073); print('\n== 2073 Miroir congés : %d -> %d lignes' % (cloc(av), cloc(ap)))
    ok = True; random.seed(11)
    types = [('cp', ''), ('maladie', ''), ('recup', ''), ('sans_solde', ''), ('absence', 'Enfant malade — approuvé'), ('absence', 'Congé paternité approuvé'), ('absence', 'Autre chose'),
             ('travail', 'Congés payés — matin en congé'), ('travail', 'Récupération — après-midi en congé'), ('travail', 'Maladie — matin en congé'), ('travail', 'Enfant malade — après-midi en congé'), ('travail', 'journée normale'), ('ferie', ''), ('cp', 'note libre')]
    cas = 0
    for typ, note in types:
        for exist in ('aucun', 'ok', 'mauvais_type', 'deux', 'non_valide'):
            for reliquat in (2.0, 0.5, 0.0):
                for creation in ('ok', 'exception'):
                    cas += 1
                    def fab():
                        raz()
                        rec = R(id=500 + cas, x_date=datetime.date(2026, 10, 6), x_employee_id=R(id=42), x_note=note, x_type=typ)
                        def feuille(hs, half, state):
                            l = R(holiday_status_id=R(id=hs), request_unit_half=bool(half), request_date_from_period=half or False, state=state)
                            l.action_refuse = lambda: H.JOURNAL.append(('action_refuse', l.id))
                            l.unlink = lambda: H.JOURNAL.append(('unlink', l.id))
                            return l
                        half_attendu = 'am' if 'matin' in note else ('pm' if 'après-midi' in note else False)
                        hs_attendu = {'cp': 1, 'maladie': 2, 'recup': 8, 'sans_solde': 9}.get(typ, 84)
                        if typ == 'absence' and 'Enfant' in note: hs_attendu = 83
                        if typ == 'travail' and 'Congés payés' in note: hs_attendu = 7
                        if typ == 'travail' and 'Récupération' in note: hs_attendu = 8
                        if typ == 'travail' and 'Maladie' in note: hs_attendu = 2
                        if typ == 'travail' and 'Enfant' in note: hs_attendu = 83
                        existants = {'aucun': [], 'ok': [feuille(hs_attendu, half_attendu, 'validate')], 'mauvais_type': [feuille(99, half_attendu, 'validate')],
                                     'deux': [feuille(hs_attendu, half_attendu, 'validate'), feuille(hs_attendu, half_attendu, 'validate')], 'non_valide': [feuille(hs_attendu, half_attendu, 'confirm')]}[exist]
                        class HL(object):
                            def sudo(self): return self
                            def with_context(self, **kw): H.JOURNAL.append(('with_context', sorted(kw.items()))); return self
                            def search(self, dom):
                                H.JOURNAL.append(('search', 'hr.leave', dom))
                                return S(existants) if dom[0][0] == 'x_hj_id' else S([R(number_of_days=1.0), R(number_of_days=0.5)])
                            def create(self, vals):
                                H.JOURNAL.append(('create', 'hr.leave', json.loads(json.dumps(vals, default=str, sort_keys=True))))
                                if creation == 'exception': raise ValueError('refus simulé')
                                l = R(id=777, state='confirm')
                                def approve(): H.JOURNAL.append(('action_approve', 777)); l.state = 'validate'
                                def validate(): H.JOURNAL.append(('action_validate', 777)); l.state = 'validate'
                                l.action_approve, l.action_validate = approve, validate
                                return l
                        class Alloc(object):
                            def sudo(self): return self
                            def search(self, dom): H.JOURNAL.append(('search', 'hr.leave.allocation', dom)); return S([R(number_of_days=reliquat + 1.5)])
                        class Log(object):
                            def sudo(self): return self
                            def create(self, vals): H.JOURNAL.append(('create', 'ir.logging', json.loads(json.dumps(vals, default=str, sort_keys=True)))); return R()
                        class Cr(object):
                            dbname = 'test'
                            def execute(self, q, p): H.JOURNAL.append(('sql', q, [str(x) for x in p]))
                        class Env(object):
                            cr = Cr()
                            def invalidate_all(self): H.JOURNAL.append(('invalidate_all',))
                            def __getitem__(self, model):
                                return {'hr.leave': HL(), 'hr.leave.allocation': Alloc(), 'ir.logging': Log()}[model]
                        return {'records': S([rec]), 'env': Env()}
                    executer(av, fab()); comp.j1 = copy.deepcopy(J())
                    executer(ap, fab()); comp.j2 = copy.deepcopy(J())
                    ok &= comp('%s %r / existant %s / reliquat %s / création %s' % (typ, note[:22], exist, reliquat, creation))
    # jour avant le 01/08 et sans employé : rien ne doit se passer
    for d, emp in ((datetime.date(2026, 7, 31), R(id=1)), (datetime.date(2026, 9, 1), Vide())):
        def fab():
            raz()
            class Env(object):
                def __getitem__(self, model):
                    class HL(object):
                        def sudo(self): return self
                        def with_context(self, **kw): return self
                    return HL()
            return {'records': S([R(id=1, x_date=d, x_employee_id=emp, x_note='', x_type='cp')]), 'env': Env()}
        executer(av, fab()); comp.j1 = copy.deepcopy(J()); executer(ap, fab()); comp.j2 = copy.deepcopy(J())
        ok &= comp('hors périmètre %s / employé %s' % (d, bool(emp)))
    print('  (%d cas)' % (cas + 2))
    return ok

# ─────────────────────────────── 1979 / 1980
def test_fab(num):
    av, ap = charger(num); print('\n== %d Fab en cours (%s) : %d -> %d lignes' % (num, 'OF' if num == 1979 else 'OT', cloc(av), cloc(ap)))
    sos = call('sale.order', 'search_read', [['x_studio_fab_encours', '=', True]], fields=['name'], order='id desc', limit=5, **CTX)
    sos += call('sale.order', 'search_read', [['x_studio_of_liste', '!=', False], ['x_studio_fab_encours', '=', False]], fields=['name'], order='id desc', limit=3, **CTX)
    ok = True
    for so in sos:
        ofs = call('mrp.production', 'search_read', [['origin', '=', so['name']], ['company_id', '=', 1]], fields=['name', 'state', 'workorder_ids', 'x_studio_catgorie', 'x_studio_nbr', 'x_studio_vol_total'], order='name', **CTX)
        wo_ids = [w for o in ofs for w in o['workorder_ids']]
        wos = {w['id']: w for w in call('mrp.workorder', 'read', wo_ids, fields=['employee_assigned_ids', 'date_start'], **CTX)} if wo_ids else {}
        cats = {c['id']: c['display_name'] for c in call('product.category', 'read', list({o['x_studio_catgorie'][0] for o in ofs if o['x_studio_catgorie']}), fields=['display_name'], **CTX)} if any(o['x_studio_catgorie'] for o in ofs) else {}
        def fab():
            raz()
            of_objs = S([R(id=o['id'], name=o['name'], state=o['state'], x_studio_nbr=o['x_studio_nbr'], x_studio_vol_total=o['x_studio_vol_total'],
                           x_studio_catgorie=R(id=o['x_studio_catgorie'][0], display_name=cats[o['x_studio_catgorie'][0]]) if o['x_studio_catgorie'] else Vide(),
                           workorder_ids=S([R(id=w, employee_assigned_ids=S([R(id=e) for e in wos[w]['employee_assigned_ids']]), date_start=datetime.datetime.fromisoformat(wos[w]['date_start']) if wos[w]['date_start'] else False) for w in o['workorder_ids']])) for o in ofs])
            so_obj = R(id=so['id'], name=so['name'])
            class Precommit(object):
                data = {}
                def add(self, fn): H.JOURNAL.append(('precommit.add', fn.__name__)); self.fn = fn
            class Cr(object):
                precommit = Precommit()
            class Env(object):
                cr = Cr()
                def flush_all(self): H.JOURNAL.append(('flush_all',))
                def __getitem__(self, model):
                    if model == 'sale.order':
                        class SO(object):
                            def search(self, dom): H.JOURNAL.append(('search', model, dom)); return S([so_obj])
                            def __iter__(self): return iter([])
                        return SO()
                    if model == 'mrp.production':
                        class MP(object):
                            def search(self, dom, order=None): H.JOURNAL.append(('search', model, dom, order)); return of_objs
                        return MP()
                    raise KeyError(model)
            recs = S([R(id=o['id'], origin=so['name']) for o in ofs[:2]] + [R(id=1, origin=False)]) if num == 1979 else S([R(id=9, production_id=R(id=o['id'], origin=so['name'])) for o in ofs[:2]])
            return {'records': recs, 'env': Env()}
        def run(code):
            ctx = fab(); g = executer(code, ctx)
            if hasattr(ctx['env'].cr.precommit, 'fn'):
                ctx['env'].cr.precommit.fn()                   # fin de transaction simulée
            return copy.deepcopy(J()), dict(ctx['env'].cr.precommit.data)
        comp.j1, d1 = run(av); comp.j2, d2 = run(ap)
        ok &= comp('%s (%d OF)' % (so['name'], len(ofs)), d1, d2)
    return ok

# ─────────────────────────────── 2082
def test_2082():
    av, ap = charger(2082); print('\n== 2082 Code client Sage : %d -> %d lignes' % (cloc(av), cloc(ap)))
    ok = True; random.seed(5); n = 0
    refs_existants = ['MAQ00012', 'MAQ00250', 'MAQ0003x', 'HAI00007', 'CG00099', 'DIS00041', 'DIS90001', 'DUPONT', 'MAQ', '']
    for comp_id in (1, 2, 3, 4, 13, None):
        for ref in ('', 'MAQ00012', 'HAI00003', 'DIS00002', 'DUPONT', 'CG00001', ' CG00007 '):
            for cats in ([], ['Client Maquignon'], ['Client Haims'], ['Client Chatel', 'Client Maquignon'], ['Compte odoo'], ['Société du Groupe', 'Client Haims'], ['VIP']):
                for parent in (None, 'avec', 'sans_societe'):
                    for user in (False, True):
                        n += 1
                        def fab():
                            raz()
                            class P(R):
                                def write(self, vals):
                                    R.write(self, vals)
                                    if isinstance(vals.get('company_id'), int):      # comme l'ORM : l'attribut redevient un enregistrement
                                        self.company_id = R(id=vals['company_id'])
                                    return True
                            r = P(id=n, user_ids=S([R(id=5)]) if user else S([]), category_id=S([R(id=100 + i, name=c) for i, c in enumerate(cats)]), ref=ref,
                                  company_id=R(id=comp_id) if comp_id else Vide(),
                                  parent_id=Vide() if parent is None else R(id=900, company_id=R(id=3) if parent == 'avec' else Vide()))
                            class Env(object):
                                company = R(id=1)
                                def __getitem__(self, model):
                                    if model == 'res.partner':
                                        class RP(object):
                                            def sudo(self): return self
                                            def with_context(self, **kw): return self
                                            def search(self, dom): H.JOURNAL.append(('search', model, dom)); return S([R(ref=x) for x in refs_existants])
                                        return RP()
                                    if model == 'res.partner.category':
                                        class RC(object):
                                            def sudo(self): return self
                                            def search(self, dom, limit=None): H.JOURNAL.append(('search', model, dom)); return R(id=55) if dom[0][2] != 'Client Distri Beton' else Vide()
                                        return RC()
                                    raise KeyError(model)
                            return {'records': S([r]), 'env': Env()}
                        executer(av, fab()); comp.j1 = copy.deepcopy(J())
                        executer(ap, fab()); comp.j2 = copy.deepcopy(J())
                        if not comp('société %s / ref %r / cat %s / parent %s / user %s' % (comp_id, ref, cats, parent, user)):
                            ok = False
    print('  (%d cas synthétiques)' % n)
    return ok

if __name__ == '__main__':
    res = {}
    for nom, fn in (('2065', test_2065), ('2073', test_2073), ('1979', lambda: test_fab(1979)), ('1980', lambda: test_fab(1980)), ('2082', test_2082)):
        res[nom] = fn()
    print('\nBILAN :', res)
