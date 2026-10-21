# -*- coding: utf-8 -*-
"""Harnais d'équivalence avant/après compaction : exécute l'ancien et le nouveau code sur des objets factices qui imitent
l'ORM (données réelles lues en production, lecture seule) et compare tous les effets (écritures, créations, notes, résultat).
Usage : python harnais.py   (variables ODOO_USER / ODOO_PWD)"""
import os, sys, io, json, copy, datetime, random, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
ICI = os.path.dirname(os.path.abspath(__file__))
URL = 'https://maquignon.odoo.com'; DB = 'maquignon'; U = os.environ['ODOO_USER']; P = os.environ['ODOO_PWD']
uid = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/common').authenticate(DB, U, P, {})
m = xmlrpc.client.ServerProxy(URL + '/xmlrpc/2/object', allow_none=True)
def call(model, meth, *a, **k):
    return m.execute_kw(DB, uid, P, model, meth, list(a), k)
CTX = {'context': {'allowed_company_ids': [1, 3, 4]}}

def cloc(code):
    return sum(1 for l in code.splitlines() if l.strip() and not l.strip().startswith('#'))

def charger(num):
    av = io.open(os.path.join(ICI, 'action_%d_avant.py' % num), encoding='utf-8').read()
    ap = io.open(os.path.join(ICI, 'action_%d_apres.py' % num), encoding='utf-8').read()
    return av, ap

def float_compare(a, b, precision_rounding=0.001):
    r = round((a or 0.0) / precision_rounding) - round((b or 0.0) / precision_rounding)
    return 0 if r == 0 else (1 if r > 0 else -1)

JOURNAL = []

class Rec(object):
    """Enregistrement factice : attributs libres, write/message_post journalisés."""
    _seq = [100000]
    def __init__(self, **kw):
        self.__dict__.update(kw)
        if 'id' not in kw:
            Rec._seq[0] += 1; self.id = Rec._seq[0]
    def write(self, vals):
        JOURNAL.append(('write', self.__class__.__name__, self.id, json.loads(json.dumps(vals, default=str, sort_keys=True))))
        self.__dict__.update(vals); return True
    def message_post(self, **kw):
        JOURNAL.append(('message_post', self.id, json.loads(json.dumps(kw, default=str, sort_keys=True)))); return True
    def exists(self):
        return True
    def __bool__(self):
        return True

class Vide(object):
    id = False
    def __bool__(self): return False
    def __len__(self): return 0
    def __iter__(self): return iter([])
    def __getattr__(self, k): return False

class RS(object):
    """Recordset factice (liste ordonnée)."""
    def __init__(self, items): self.items = list(items)
    def __iter__(self): return iter(self.items)
    def __len__(self): return len(self.items)
    def __bool__(self): return bool(self.items)
    def __getitem__(self, i): return self.items[i]
    def sorted(self, key=None):
        return RS(sorted(self.items, key=(lambda r: getattr(r, key)) if isinstance(key, str) else key))
    def filtered(self, fn): return RS([r for r in self.items if fn(r)])
    def mapped(self, f): return [getattr(r, f) for r in self.items]
    def browse(self): return RS([])
    def write(self, vals):
        for r in self.items: r.write(vals)
        return True
    @property
    def ids(self): return [r.id for r in self.items]

def executer(code, ctx):
    g = {'datetime': datetime, 'float_compare': float_compare, 'Command': None, 'UserError': Exception}
    g.update(ctx); exec(compile(code, 'action', 'exec'), g)
    return g

def fusion(j):
    """Les créations de sections consécutives (une écriture par section avant, une seule après) comptent pour une."""
    out = []
    for e in j:
        if e[0] == 'create_sections' and out and out[-1][0] == 'create_sections':
            out[-1] = ('create_sections', out[-1][1] + e[1])
        else:
            out.append(e)
    return out

def comparer(nom, j1, r1, j2, r2):
    j1, j2 = fusion(j1), fusion(j2)
    ok = j1 == j2 and r1 == r2
    print('  %-60s %s' % (nom, 'identique' if ok else 'DIFFÉRENT'))
    if not ok:
        for k, (a, b) in enumerate(zip(j1, j2)):
            if a != b:
                print('     journal #%d\n       avant : %s\n       après : %s' % (k, str(a)[:300], str(b)[:300])); break
        if len(j1) != len(j2): print('     longueurs journal :', len(j1), len(j2))
        if r1 != r2: print('     résultat avant :', str(r1)[:300], '\n     résultat après :', str(r2)[:300])
    return ok

# ─────────────────────────────── 1602 : classement par date de section
def test_1602():
    av, ap = charger(1602); print('\n== 1602 Classement par date de section : %d -> %d lignes' % (cloc(av), cloc(ap)))
    moves = call('account.move', 'search_read', [['move_type', 'in', ['out_invoice', 'out_refund']], ['invoice_line_ids.display_type', '=', 'line_section'], ['invoice_line_ids.name', 'ilike', 'n°']], fields=['name', 'invoice_line_ids'], order='id desc', limit=25, **CTX)
    moves += call('account.move', 'search_read', [['move_type', '=', 'out_invoice'], ['invoice_line_ids.display_type', '=', 'line_section'], ['invoice_line_ids.name', 'ilike', 'solo']], fields=['name', 'invoice_line_ids'], order='id desc', limit=10, **CTX)
    tous_ok = True
    for mv in moves:
        lignes = call('account.move.line', 'read', mv['invoice_line_ids'], fields=['name', 'display_type', 'sequence'], **CTX)
        def fab():
            global JOURNAL; JOURNAL = []
            lines = [Rec(id=l['id'], name=l['name'], display_type=l['display_type'], sequence=l['sequence']) for l in lignes]
            class Move(Rec):
                def write(self, vals):
                    for cmd in vals.get('invoice_line_ids', []):
                        assert cmd[0] == 0
                        self.invoice_line_ids.items.append(Rec(name=cmd[2]['name'], display_type=cmd[2]['display_type'], sequence=cmd[2]['sequence']))
                    JOURNAL.append(('create_sections', [c[2]['name'] for c in vals.get('invoice_line_ids', [])]))
                    return True
            return Move(id=mv['id'], invoice_line_ids=RS(lines))
        Rec._seq[0] = 100000; rec = fab(); executer(av, {'record': rec}); j1 = copy.deepcopy(JOURNAL); r1 = [(l.name, l.sequence) for l in rec.invoice_line_ids]
        Rec._seq[0] = 100000; rec = fab(); executer(ap, {'record': rec}); j2 = copy.deepcopy(JOURNAL); r2 = [(l.name, l.sequence) for l in rec.invoice_line_ids]
        tous_ok &= comparer('%s (%d lignes)' % (mv['name'], len(lignes)), j1, r1, j2, r2)
    # cas synthétiques : sections sans date, numéros décimaux, lignes hors section
    random.seed(4)
    for k in range(40):
        lines = []
        for i in range(random.randint(2, 14)):
            if random.random() < 0.35:
                typ = random.choice(['solo', 'duo', 'fond mouvant', 'inversion de benne', 'camion'])
                nom = random.choice(['%02d/%02d/2026 - n°%s | %s' % (random.randint(1, 28), random.randint(1, 12), random.choice(['123', '03006100.01', 'x']), typ), '- %s -' % typ.title(), 'Transport %s' % typ, ''])
                lines.append(Rec(name=nom, display_type='line_section', sequence=random.choice([10, 20, 20, 9999])))
            else:
                lines.append(Rec(name=random.choice(['Transport solo 8x4', 'Duo', 'Fond-mouvant 30 T', 'Benne', 'Gravier 0/20', None]), display_type='product', sequence=random.choice([10, 20, 30, 9999])))
        snap = [(l.name, l.display_type, l.sequence) for l in lines]
        def fab2():
            global JOURNAL; JOURNAL = []
            ls = [Rec(id=1000 + i, name=n, display_type=d, sequence=s) for i, (n, d, s) in enumerate(snap)]
            class Move(Rec):
                def write(self, vals):
                    for cmd in vals.get('invoice_line_ids', []):
                        self.invoice_line_ids.items.append(Rec(name=cmd[2]['name'], display_type=cmd[2]['display_type'], sequence=cmd[2]['sequence']))
                    JOURNAL.append(('create_sections', [c[2]['name'] for c in vals.get('invoice_line_ids', [])]))
                    return True
            return Move(id=1, invoice_line_ids=RS(ls))
        Rec._seq[0] = 100000; rec = fab2(); executer(av, {'record': rec}); j1 = copy.deepcopy(JOURNAL); r1 = [(l.name, l.sequence) for l in rec.invoice_line_ids]
        Rec._seq[0] = 100000; rec = fab2(); executer(ap, {'record': rec}); j2 = copy.deepcopy(JOURNAL); r2 = [(l.name, l.sequence) for l in rec.invoice_line_ids]
        tous_ok &= comparer('synthétique %d (%d lignes)' % (k, len(snap)), j1, r1, j2, r2)
    return tous_ok

# ─────────────────────────────── 1594 : créer OF de tranches
def test_1594():
    av, ap = charger(1594); print('\n== 1594 Créer OF de tranches : %d -> %d lignes' % (cloc(av), cloc(ap)))
    ofs = call('mrp.production', 'search_read', [['state', 'in', ['confirmed', 'progress', 'draft']], ['x_studio_nbr', '>', 0]], fields=['name', 'x_studio_nom_du_client', 'x_studio_ref_pierre', 'x_studio_long_m_1', 'x_studio_larg_m_1', 'x_studio_haut_m_1', 'x_studio_nbr', 'x_studio_vol_total', 'product_id', 'company_id', 'product_uom_id', 'x_studio_ref_commande_client', 'x_studio_tche_commande_pierre'], order='id desc', limit=12, **CTX)
    prods = {p['id']: p for p in call('product.product', 'read', list({o['product_id'][0] for o in ofs}), fields=['display_name', 'default_code'], **CTX)}
    tous_ok = True
    random.seed(7)
    for k in range(10):
        lot = random.sample(ofs, random.randint(1, 4))
        tr_existe = k % 2 == 0
        def fab():
            global JOURNAL; JOURNAL = []
            recs = [Rec(id=o['id'], name=o['name'], x_studio_nom_du_client=o['x_studio_nom_du_client'], x_studio_ref_pierre=o['x_studio_ref_pierre'], x_studio_long_m_1=o['x_studio_long_m_1'], x_studio_larg_m_1=o['x_studio_larg_m_1'], x_studio_haut_m_1=o['x_studio_haut_m_1'], x_studio_nbr=o['x_studio_nbr'], x_studio_vol_total=o['x_studio_vol_total'],
                        product_id=Rec(id=o['product_id'][0], display_name=prods[o['product_id'][0]]['display_name'], default_code=prods[o['product_id'][0]]['default_code']), company_id=Rec(id=o['company_id'][0]), product_uom_id=Rec(id=o['product_uom_id'][0]),
                        x_studio_ref_commande_client=o['x_studio_ref_commande_client'], x_studio_tche_commande_pierre=Rec(id=o['x_studio_tche_commande_pierre'][0]) if o['x_studio_tche_commande_pierre'] else Vide()) for o in lot]
            class Env(object):
                def __getitem__(self, model):
                    if model == 'product.product':
                        class PP(object):
                            def search(self, dom, limit=None):
                                JOURNAL.append(('search', model, dom))
                                return Rec(id=555, uom_id=Rec(id=9)) if tr_existe else Vide()
                        return PP()
                    if model == 'mrp.production':
                        class MP(object):
                            def create(self, vals):
                                JOURNAL.append(('create', model, json.loads(json.dumps(vals, default=str, sort_keys=True))))
                                return Rec(id=777)
                        return MP()
                    if model == 'mail.message':
                        class MM(object):
                            def new(self, vals): return Rec(body=vals['body'])
                        return MM()
                    raise KeyError(model)
            return {'records': RS(recs), 'env': Env()}
        Rec._seq[0] = 100000; g = executer(av, fab()); j1 = copy.deepcopy(JOURNAL); r1 = g.get('action')
        Rec._seq[0] = 100000; g = executer(ap, fab()); j2 = copy.deepcopy(JOURNAL); r2 = g.get('action')
        tous_ok &= comparer('lot %d : %s (article tranches %s)' % (k, ', '.join(o['name'] for o in lot), 'trouvé' if tr_existe else 'absent'), j1, r1, j2, r2)
    return tous_ok

# ─────────────────────────────── 1477 : transfert champs BC vers OF
def test_1477():
    av, ap = charger(1477); print('\n== 1477 Transfert champs BC vers OF : %d -> %d lignes' % (cloc(av), cloc(ap)))
    ofs = call('mrp.production', 'search_read', [['sale_line_id', '!=', False], ['origin', '!=', False]], fields=['name', 'origin', 'sale_line_id', 'product_id', 'product_qty', 'product_uom_id', 'x_studio_nom_du_client', 'workorder_ids'], order='id desc', limit=8, **CTX)
    champs_l = ['name', 'order_id', 'product_id', 'sequence', 'x_studio_ref_pierre', 'x_studio_nbr', 'x_studio_long', 'x_studio_larg', 'x_studio_epais', 'x_studio_surf', 'x_studio_vol', 'x_studio_libell_client', 'x_studio_taille_de_p']
    tous_ok = True
    for o in ofs:
        so = call('sale.order', 'search_read', [['name', '=', o['origin']]], fields=['name', 'partner_id', 'client_order_ref', 'order_line', 'x_studio_tache'], limit=1, **CTX)
        if not so: continue
        so = so[0]
        lignes = [l for l in call('sale.order.line', 'read', so['order_line'], fields=champs_l, **CTX) if l['product_id']]
        wos = call('mrp.workorder', 'read', o['workorder_ids'], fields=['name'], **CTX)
        uom = call('uom.uom', 'read', [o['product_uom_id'][0]], fields=['rounding'], **CTX)[0]['rounding']
        for scen in ('ligne_liee', 'sans_ligne', 'deja_rempli', 'doublon', 'taille_pierre'):
            def fab():
                global JOURNAL; JOURNAL = []
                ls = [Rec(id=l['id'], name=l['name'], sequence=l['sequence'], product_id=Rec(id=l['product_id'][0]), order_id=Rec(id=so['id']), x_studio_ref_pierre=l['x_studio_ref_pierre'], x_studio_nbr=l['x_studio_nbr'], x_studio_long=l['x_studio_long'], x_studio_larg=l['x_studio_larg'], x_studio_epais=l['x_studio_epais'], x_studio_surf=l['x_studio_surf'], x_studio_vol=l['x_studio_vol'], x_studio_libell_client=l['x_studio_libell_client'], x_studio_taille_de_p=('45° chanfrein' if scen == 'taille_pierre' else l['x_studio_taille_de_p'])) for l in lignes]
                sol = Rec(id=so['id'], partner_id=Rec(id=so['partner_id'][0], name=so['partner_id'][1]), client_order_ref=so['client_order_ref'], order_line=RS(ls), x_studio_tache=Rec(id=so['x_studio_tache'][0]) if so['x_studio_tache'] else Vide())
                ma_ligne = ([l for l in ls if l.id == o['sale_line_id'][0]] or [Vide()])[0]
                class OF(Rec):
                    def write(self, vals):
                        Rec.write(self, vals)
                        if isinstance(vals.get('sale_line_id'), int):      # comme l'ORM : l'attribut redevient la ligne, pas un entier
                            self.sale_line_id = [l for l in ls if l.id == vals['sale_line_id']][0]
                        return True
                rec = OF(id=o['id'], origin=o['origin'], product_id=Rec(id=o['product_id'][0]), product_qty=o['product_qty'], product_uom_id=Rec(id=o['product_uom_id'][0], rounding=uom),
                          sale_line_id=Vide() if scen == 'sans_ligne' else ma_ligne, x_studio_nom_du_client=(o['x_studio_nom_du_client'] if scen == 'deja_rempli' else False),
                          workorder_ids=RS([Rec(id=w['id'], name=w['name']) for w in wos]))
                class Env(object):
                    def __getitem__(self, model):
                        if model == 'sale.order':
                            class SO(object):
                                def search(self, dom, limit=None): JOURNAL.append(('search', model, dom)); return sol
                                def __bool__(self): return False
                            return SO()
                        if model == 'mrp.production':
                            class MP(object):
                                def search(self, dom): JOURNAL.append(('search', model, dom)); return RS([Rec(id=1, name='WH/OF/00001')]) if scen == 'doublon' else RS([])
                                def search_count(self, dom): JOURNAL.append(('search_count', model, dom)); return 1
                            return MP()
                        if model == 'mail.message':
                            class MM(object):
                                def search_count(self, dom): JOURNAL.append(('search_count', model, dom)); return 0
                            return MM()
                        if model == 'mrp.workcenter':
                            class WC(object):
                                def search(self, dom, limit=None): JOURNAL.append(('search', model, dom)); return Rec(id=42)
                            return WC()
                        if model == 'mrp.workorder':
                            class WO(object):
                                def create(self, vals): JOURNAL.append(('create', model, json.loads(json.dumps(vals, default=str, sort_keys=True)))); rec.workorder_ids.items.append(Rec(name=vals['name'])); return Rec()
                            return WO()
                        raise KeyError(model)
                return {'record': rec, 'env': Env()}
            Rec._seq[0] = 100000; executer(av, fab()); j1 = copy.deepcopy(JOURNAL)
            Rec._seq[0] = 100000; executer(ap, fab()); j2 = copy.deepcopy(JOURNAL)
            # l'après recherche la commande une fois au lieu de 1 à 3 fois et saute un search_count inutile : on compare hors lectures
            e1 = [x for x in j1 if x[0] not in ('search', 'search_count')]; e2 = [x for x in j2 if x[0] not in ('search', 'search_count')]
            tous_ok &= comparer('%s / %s (%d lignes de vente)' % (o['name'], scen, len(lignes)), e1, None, e2, None)
    return tous_ok

if __name__ == '__main__':
    res = {n: f() for n, f in (('1602', test_1602), ('1594', test_1594), ('1477', test_1477))}
    print('\nBILAN :', res)
