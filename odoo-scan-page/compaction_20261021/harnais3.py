# -*- coding: utf-8 -*-
"""Harnais d'équivalence série 3 : 1905 / 1904 / 1911 « Commande Pierres : étape selon OF / commande / tâche »."""
import os, sys, copy, random, itertools
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harnais as H
from harnais import Rec, RS, Vide, call, CTX, charger, cloc, executer, comparer
from harnais2 import R, S, raz, J, comp

class S3(S):
    """mapped() d'un champ relationnel renvoie un recordset (unique, ordre d'apparition), comme l'ORM."""
    def mapped(self, f):
        vals = [getattr(r, f) for r in self.items]
        if vals and all(isinstance(v, (Rec, Vide)) for v in vals):
            out, vus = [], set()
            for v in vals:
                if isinstance(v, Rec) and v.id not in vus:
                    vus.add(v.id); out.append(v)
            return S3(out)
        return vals

def tache(tid, stage, sos, ofs):
    return R(id=tid, stage_id=R(id=stage) if stage else Vide(),
             x_studio_devis_commandes_1=S3([R(id=100 + i, state=a, delivery_status=b, invoice_status=c) for i, (a, b, c) in enumerate(sos)]),
             x_studio_of=S3([R(id=200 + i, state=e) for i, e in enumerate(ofs)]))

def env_fab(taches):
    class Precommit(object):
        data = {}
        def add(self, fn): H.JOURNAL.append(('precommit.add', fn.__name__)); self.fn = fn
    class Cr(object):
        precommit = Precommit()
    class Env(object):
        cr = Cr()
        def flush_all(self): H.JOURNAL.append(('flush_all',))
        def __getitem__(self, model):
            class PT(object):
                def browse(self, ids):
                    H.JOURNAL.append(('browse', model, list(ids)))
                    s = S3([t for i in ids for t in taches if t.id == i]); s.exists = lambda: s
                    return s
            return PT()
    return Env()

def cas_synthetiques():
    random.seed(3)
    etats_so = ['draft', 'sent', 'sale', 'cancel']; livr = ['pending', 'partial', 'full', False]; fact = ['no', 'to invoice', 'invoiced', 'upselling']
    etats_of = ['draft', 'confirmed', 'progress', 'to_close', 'done', 'cancel']
    out = []
    for _ in range(400):
        sos = [(random.choice(etats_so), random.choice(livr), random.choice(fact)) for _ in range(random.randint(0, 3))]
        ofs = [random.choice(etats_of) for _ in range(random.randint(0, 5))]
        out.append((random.choice([113, 119, 114, 115, 116, 117, 118, 999, None]), sos, ofs))
    return out

def cas_reels():
    tasks = call('project.task', 'search_read', [['project_id', '=', 13]], fields=['stage_id', 'x_studio_devis_commandes_1', 'x_studio_of'], order='id desc', limit=40, **CTX)
    out = []
    for t in tasks:
        sos = [(s['state'], s['delivery_status'], s['invoice_status']) for s in call('sale.order', 'read', t['x_studio_devis_commandes_1'], fields=['state', 'delivery_status', 'invoice_status'], **CTX)] if t['x_studio_devis_commandes_1'] else []
        ofs = [o['state'] for o in call('mrp.production', 'read', t['x_studio_of'], fields=['state'], **CTX)] if t['x_studio_of'] else []
        out.append((t['stage_id'][0] if t['stage_id'] else None, sos, ofs))
    return out

def test(num):
    av, ap = charger(num); print('\n== %d : %d -> %d lignes' % (num, cloc(av), cloc(ap)))
    ok = True; cas = cas_reels() + cas_synthetiques()
    for i, (stage, sos, ofs) in enumerate(cas):
        def fab():
            raz()
            t = tache(50 + i, stage, sos, ofs)
            if num == 1911:
                return {'record': t, 'env': env_fab([t])}
            if num == 1904:
                return {'records': S3([R(id=1, x_studio_tache=t), R(id=2, x_studio_tache=Vide()), R(id=3, x_studio_tache=t)]), 'env': env_fab([t])}
            env = env_fab([t])
            return {'records': S3([R(id=11, x_studio_tche_commande_pierre=t), R(id=12, x_studio_tche_commande_pierre=Vide())]), 'env': env}
        def run(code):
            ctx = fab(); executer(code, ctx)
            pc = ctx['env'].cr.precommit
            if hasattr(pc, 'fn'):
                pc.fn(); del pc.fn
            return copy.deepcopy(J())
        comp.j1 = run(av); comp.j2 = run(ap)
        ok &= comp('cas %d stage %s sos %s ofs %s' % (i, stage, [s[0] for s in sos], ofs))
    print('  (%d cas dont %d réels)' % (len(cas), len(cas) - 400))
    return ok

if __name__ == '__main__':
    res = {n: test(n) for n in (1911, 1904, 1905)}
    print('\nBILAN :', res)
