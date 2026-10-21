# -*- coding: utf-8 -*-
"""Essais réels sur la base de test tesmaq211026, série 2 : 2065 (facture depuis commande avec sections), 2073 (miroir congés),
1979/1980 (Fab en cours), 2082 (code client Sage). Ancien code puis nouveau sur les mêmes données, comparaison des effets et temps.
Usage : python test_base_test2.py"""
import os, sys, io, time, json, datetime, xmlrpc.client
sys.stdout.reconfigure(encoding='utf-8')
ICI = os.path.dirname(os.path.abspath(__file__))
HOST = 'https://tesmaq211026.odoo.com'; DB = 'tesmaq211026'
U = os.environ['ODOO_USER']; P = os.environ['ODOO_PWD']
uid = xmlrpc.client.ServerProxy(HOST + '/xmlrpc/2/common').authenticate(DB, U, P, {})
m = xmlrpc.client.ServerProxy(HOST + '/xmlrpc/2/object', allow_none=True)
def call(model, meth, *a, **k):
    return m.execute_kw(DB, uid, P, model, meth, list(a), k)
CTX = {'context': {'allowed_company_ids': [1, 3, 4], 'active_test': False}}
assert call('ir.config_parameter', 'get_param', 'web.base.url') == HOST, 'pas la base de test !'
def code(num, version):
    return io.open(os.path.join(ICI, 'action_%d_%s.py' % (num, version)), encoding='utf-8').read()
def installer(num, version):
    call('ir.actions.server', 'write', [num], {'code': code(num, version)})
def ids(x):
    return x if isinstance(x, list) else [x]
def chrono(fn):
    t0 = time.time(); r = fn(); return r, round((time.time() - t0) * 1000)
def comparer(nom, r1, r2, t1, t2):
    same = r1 == r2
    print('  %s : %s | %d ms -> %d ms' % (nom, 'identique' if same else 'DIFFÉRENT', t1, t2))
    if not same:
        if isinstance(r1, dict):
            for k in r1:
                if r1.get(k) != r2.get(k): print('     ', k, '\n       avant', str(r1.get(k))[:400], '\n       après', str(r2.get(k))[:400])
        else:
            print('     avant', str(r1)[:600], '\n     après', str(r2)[:600])
    return same
bilan = {}

# ───────────────── 2065 : facture créée depuis une commande avec sections imbriquées
print('== 2065 Sections imbriquées ==')
sos = call('sale.order', 'search_read', [['state', '=', 'sale'], ['invoice_status', '=', 'to invoice'], ['company_id', '=', 1], ['order_line.display_type', '=', 'line_section']], fields=['name', 'order_line'], order='id desc', limit=40, **CTX)
choisis = []
for so in sos:
    ls = call('sale.order.line', 'read', so['order_line'], fields=['display_type', 'sequence', 'qty_to_invoice'], **CTX)
    ls.sort(key=lambda l: (l['sequence'], l['id']))
    imbriquees = any(ls[i]['display_type'] == 'line_section' and ls[i + 1]['display_type'] == 'line_section' for i in range(len(ls) - 1))
    if imbriquees and any(l['qty_to_invoice'] > 0 for l in ls):
        choisis.append(so)
    if len(choisis) >= 3: break
ok = True
for so in choisis:
    def essai(version):
        installer(2065, version)
        wiz = ids(call('sale.advance.payment.inv', 'create', [{'advance_payment_method': 'delivered'}], context={'active_model': 'sale.order', 'active_ids': [so['id']], 'active_id': so['id'], 'allowed_company_ids': [1, 3, 4]}))[0]
        _, t = chrono(lambda: call('sale.advance.payment.inv', 'create_invoices', [wiz], context={'active_model': 'sale.order', 'active_ids': [so['id']], 'active_id': so['id'], 'allowed_company_ids': [1, 3, 4]}))
        inv = call('account.move', 'search', [['invoice_origin', '=', so['name']], ['state', '=', 'draft'], ['create_uid', '=', uid]], order='id desc', limit=1, **CTX)
        assert inv, 'facture non créée'
        lignes = call('account.move.line', 'search_read', [['move_id', '=', inv[0]], ['display_type', 'in', ['line_section', 'line_note', 'product']]], fields=['display_type', 'name', 'sequence', 'sale_line_ids'], order='sequence, id', **CTX)
        res = [(l['display_type'], l['name'], l['sequence'], l['sale_line_ids']) for l in lignes]
        call('account.move', 'unlink', inv, **CTX)
        return res, t
    r1, t1 = essai('avant'); r2, t2 = essai('apres')
    ok &= comparer('%s (%d lignes de facture)' % (so['name'], len(r1)), r1, r2, t1, t2)
bilan['2065'] = ok

# ───────────────── 2073 : miroir congés
print('\n== 2073 Miroir congés ==')
rel = call('ir.model', 'read', [call('ir.actions.server', 'read', [2073], fields=['model_id'], **CTX)[0]['model_id'][0]], fields=['model'], **CTX)[0]['model']
champs_hj = call(rel, 'fields_get', attributes=['type'], **CTX)
print('  modèle planning :', rel)
alloc = call('hr.leave.allocation', 'search_read', [['state', '=', 'validate'], ['holiday_status_id', 'in', [1, 7]]], fields=['employee_id'], order='id desc', limit=1, **CTX)
emp = alloc[0]['employee_id'][0]
ok = True
for typ, note, jour in (('cp', '', '2026-12-14'), ('maladie', '', '2026-12-15'), ('travail', 'Congés payés — matin en congé', '2026-12-16'), ('absence', 'Enfant malade — approuvé', '2026-12-17')):
    def essai(version):
        installer(2073, version)
        vals = {'x_employee_id': emp, 'x_date': jour, 'x_type': typ, 'x_note': note}
        if 'x_name' in champs_hj: vals['x_name'] = 'essai compaction'
        rid, t = chrono(lambda: ids(call(rel, 'create', [vals], **CTX))[0])
        leaves = call('hr.leave', 'search_read', [['x_hj_id', '=', rid]], fields=['holiday_status_id', 'state', 'request_date_from', 'request_date_to', 'number_of_days', 'request_unit_half', 'request_date_from_period', 'name'], **CTX)
        res = [{k: v for k, v in l.items() if k != 'id'} for l in leaves]
        call(rel, 'unlink', [rid], **CTX)
        restes = call('hr.leave', 'search', [['x_hj_id', '=', rid]], **CTX)
        if restes:
            try: call('hr.leave', 'action_refuse', restes, **CTX)
            except Exception: pass
            call('hr.leave', 'unlink', restes, **CTX)
        return res, t
    r1, t1 = essai('avant'); r2, t2 = essai('apres')
    ok &= comparer('%s %r -> %s' % (typ, note, [(l['holiday_status_id'][1] if l['holiday_status_id'] else None, l['state'], l['number_of_days']) for l in r1]), r1, r2, t1, t2)
bilan['2073'] = ok

# ───────────────── 1979 / 1980 : Fab en cours
print('\n== 1979 / 1980 Fab en cours ==')
noms_champs = {f['id']: f['name'] for f in call('ir.model.fields', 'read', [18017, 18043, 18162, 18685, 18160], fields=['name'], **CTX)}
print('  champs déclencheurs OF :', [noms_champs[i] for i in (18017, 18043)], '| OT :', [noms_champs[i] for i in (18162, 18685, 18160)])
CH_SO = ['x_studio_fab_encours', 'x_studio_of_non_planifies', 'x_studio_of_non_programmes', 'x_studio_of_tranches', 'x_studio_vol_of', 'x_studio_vol_reste', 'x_studio_produits_fab', 'x_studio_of_liste', 'x_studio_pierres_faites', 'x_studio_date_planif']
ouverts = call('mrp.production', 'search_read', [['state', 'in', ['confirmed', 'progress']], ['company_id', '=', 1], ['origin', '=like', 'S%'], ['workorder_ids', '!=', False]], fields=['name', 'origin', 'workorder_ids'], order='id desc', limit=40, **CTX)
vus, choix = set(), []
for o in ouverts:
    if o['origin'] not in vus:
        vus.add(o['origin']); choix.append(o)
    if len(choix) >= 3: break
ok = True
for of in choix:
    so = call('sale.order', 'search_read', [['name', '=', of['origin']]], fields=['name'] + CH_SO, limit=1, **CTX)
    if not so: continue
    so = so[0]
    def essai(num, version):
        installer(num, version)
        # l'automatisation ne part que si la VALEUR d'un champ déclencheur change : aller-retour, mesure sur le retour
        if num == 1979:
            call('mrp.production', 'write', [of['id']], {'origin': 'ESSAI-COMPACTION'}, **CTX)
            call('sale.order', 'write', [so['id']], {'x_studio_of_liste': 'A RECALCULER', 'x_studio_produits_fab': '?'}, **CTX)     # on salit, le recalcul doit tout remettre
            _, t = chrono(lambda: call('mrp.production', 'write', [of['id']], {'origin': of['origin']}, **CTX))
        else:
            wo = of['workorder_ids'][0]        # date_start ne peut pas être modifiée seule (déprogrammation) : on joue sur l'opérateur assigné
            emp = call('mrp.workorder', 'read', [wo], fields=['employee_assigned_ids'], **CTX)[0]['employee_assigned_ids']
            autre = call('hr.employee', 'search', [['id', 'not in', emp], ['company_id', '=', 1]], limit=1, **CTX)
            call('mrp.workorder', 'write', [wo], {'employee_assigned_ids': [(6, 0, autre)]}, **CTX)
            call('sale.order', 'write', [so['id']], {'x_studio_of_liste': 'A RECALCULER', 'x_studio_produits_fab': '?'}, **CTX)
            _, t = chrono(lambda: call('mrp.workorder', 'write', [wo], {'employee_assigned_ids': [(6, 0, emp)]}, **CTX))
        return call('sale.order', 'read', [so['id']], fields=CH_SO, **CTX)[0], t
    for num in (1979, 1980):
        r1, t1 = essai(num, 'avant'); r2, t2 = essai(num, 'apres')
        ok &= comparer('%d %s (%s)' % (num, so['name'], r1['x_studio_of_liste']), r1, r2, t1, t2)
        if r1['x_studio_of_liste'] == 'A RECALCULER': print('     ATTENTION : le recalcul ne s est pas déclenché'); ok = False
bilan['1979/1980'] = ok

# ───────────────── 2082 : code client Sage
print('\n== 2082 Code client Sage ==')
noms_champs = {f['id']: f['name'] for f in call('ir.model.fields', 'read', [943, 8389, 905], fields=['name'], **CTX)}
print('  champs déclencheurs :', list(noms_champs.values()))
ok = True
mere = call('res.partner', 'search', [['is_company', '=', True], ['company_id', '=', 3], ['parent_id', '=', False]], limit=1, **CTX)
cas = [('client Maquignon', {'name': 'ESSAI COMPACTION A', 'customer_rank': 1, 'company_id': 1}),
       ('client Chatel sans société (société active)', {'name': 'ESSAI COMPACTION B', 'customer_rank': 1}),
       ('client Haims avec code d une autre société', {'name': 'ESSAI COMPACTION C', 'customer_rank': 1, 'company_id': 4, 'ref': 'MAQ99999'}),
       ('contact rattaché à une fiche Chatel', {'name': 'ESSAI COMPACTION D', 'parent_id': mere[0]})]
for nom, vals in cas:
    def essai(version):
        installer(2082, version)
        pid, t = chrono(lambda: ids(call('res.partner', 'create', [vals], **CTX))[0])
        r = call('res.partner', 'read', [pid], fields=['ref', 'company_id', 'category_id'], **CTX)[0]
        res = {'ref': r['ref'], 'company_id': r['company_id'], 'categories': sorted(c['name'] for c in call('res.partner.category', 'read', r['category_id'], fields=['name'], **CTX))}
        call('res.partner', 'unlink', [pid], **CTX)
        return res, t
    r1, t1 = essai('avant'); r2, t2 = essai('apres')
    ok &= comparer('%s -> %s' % (nom, r1), r1, r2, t1, t2)
bilan['2082'] = ok
print('\nBILAN :', bilan)
print('état final base de test : nouveau code installé =', all(call('ir.actions.server', 'read', [n], fields=['code'])[0]['code'] == code(n, 'apres') for n in (2065, 2073, 1979, 1980, 2082)))
