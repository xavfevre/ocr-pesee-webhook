# -*- coding: utf-8 -*-
"""Essais réels sur la base de test tesmaq211026 : pour chaque action compactée, exécution de l'ANCIEN code puis du NOUVEAU
sur les mêmes enregistrements, comparaison des effets et des temps. À la fin, le NOUVEAU code reste installé sur la base de test.
Usage : python test_base_test.py   (ODOO_USER / ODOO_PWD d'Isabelle)"""
import os, sys, io, time, json, xmlrpc.client
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

def run(num, model, ids):
    t0 = time.time()
    res = call('ir.actions.server', 'run', [num], context={'active_model': model, 'active_id': ids[0], 'active_ids': ids, 'allowed_company_ids': [1, 3, 4]})
    return res, round((time.time() - t0) * 1000)

bilan = {}
# ───────────────── 1602 : classement par date de section
print('== 1602 Classement par date de section ==')
moves = call('account.move', 'search_read', [['move_type', '=', 'out_invoice'], ['invoice_line_ids.display_type', '=', 'line_section'], ['invoice_line_ids.name', 'ilike', 'n°']], fields=['name', 'invoice_line_ids', 'state'], order='id desc', limit=6, **CTX)
ok = True; temps = {'avant': [], 'apres': []}
for mv in moves:
    orig = {l['id']: l['sequence'] for l in call('account.move.line', 'read', mv['invoice_line_ids'], fields=['sequence'], **CTX)}
    def etat():
        ls = call('account.move.line', 'search_read', [['move_id', '=', mv['id']], ['display_type', 'in', ['line_section', 'product', 'line_note']]], fields=['name', 'display_type', 'sequence'], order='sequence, id', **CTX) if True else None
        return [(l['name'], l['display_type'], l['sequence']) for l in ls]
    def restaurer():
        for lid, s in orig.items():
            call('account.move.line', 'write', [lid], {'sequence': s}, **CTX)
        for l in call('account.move.line', 'search_read', [['move_id', '=', mv['id']], ['display_type', '=', 'line_section'], ['id', 'not in', list(orig)]], fields=['id'], **CTX):
            call('account.move.line', 'unlink', [l['id']], **CTX)        # sections créées par l'essai (jamais les lignes de taxe)
    installer(1602, 'avant'); _, t1 = run(1602, 'account.move', [mv['id']]); e1 = etat(); restaurer()
    installer(1602, 'apres'); _, t2 = run(1602, 'account.move', [mv['id']]); e2 = etat(); restaurer()
    temps['avant'].append(t1); temps['apres'].append(t2)
    same = e1 == e2; ok &= same
    print('  %s (%s, %d lignes) : %s | %d ms -> %d ms' % (mv['name'], mv['state'], len(orig), 'identique' if same else 'DIFFÉRENT', t1, t2))
    if not same:
        for a, b in zip(e1, e2):
            if a != b: print('     avant', a, '\n     après', b); break
bilan['1602'] = (ok, temps)

# ───────────────── 1594 : créer OF de tranches
print('\n== 1594 Créer OF de tranches ==')
ofs = call('mrp.production', 'search_read', [['state', 'in', ['confirmed', 'progress']], ['x_studio_nbr', '>', 0], ['product_id.default_code', 'ilike', 'HAIMS']], fields=['name'], order='id desc', limit=3, **CTX)
ok = True; temps = {'avant': [], 'apres': []}
CHAMPS = ['product_id', 'product_uom_id', 'product_qty', 'log_note', 'x_detail_tranches', 'x_studio_vol_total', 'x_studio_nom_du_client', 'x_studio_ref_pierre', 'x_studio_nbr', 'x_studio_ref_commande_client', 'x_note_atelier', 'x_studio_tche_commande_pierre', 'company_id']
for lot in ([ofs[0]['id']], [o['id'] for o in ofs]):
    def essai(version):
        installer(1594, version)
        avant_ids = set(call('mrp.production', 'search', [['create_date', '>=', '2026-10-21']], **CTX))
        res, t = run(1594, 'mrp.production', lot)
        nouveaux = [i for i in call('mrp.production', 'search', [['create_date', '>=', '2026-10-21']], **CTX) if i not in avant_ids]
        assert len(nouveaux) == 1, nouveaux
        of = call('mrp.production', 'read', nouveaux, fields=CHAMPS, **CTX)[0]
        msg = call('mail.message', 'search_read', [['model', '=', 'mrp.production'], ['res_id', '=', nouveaux[0]], ['message_type', '=', 'comment']], fields=['body', 'subtype_id'], **CTX)
        # résultat renvoyé : l'action ouvre l'OF créé
        resume = {k: of[k] for k in CHAMPS}; resume['message'] = [(x['body'], x['subtype_id'] and x['subtype_id'][1]) for x in msg]; resume['action'] = {k: v for k, v in (res or {}).items() if k in ('type', 'res_model', 'view_mode', 'target')}
        call('mrp.production', 'action_cancel', nouveaux, **CTX) if False else None
        call('mrp.production', 'unlink', nouveaux, **CTX)
        return resume, t
    r1, t1 = essai('avant'); r2, t2 = essai('apres')
    temps['avant'].append(t1); temps['apres'].append(t2)
    same = r1 == r2; ok &= same
    print('  lot %s : %s | %d ms -> %d ms' % ([o['name'] for o in ofs if o['id'] in lot], 'identique' if same else 'DIFFÉRENT', t1, t2))
    if not same:
        for k in r1:
            if r1[k] != r2[k]: print('     champ', k, '\n       avant', str(r1[k])[:400], '\n       après', str(r2[k])[:400])
bilan['1594'] = (ok, temps)

# ───────────────── 1477 : transfert BC vers OF (automatisation à la création)
print('\n== 1477 Transfert champs BC vers OF ==')
restes = call('mrp.production', 'search', [['state', '=', 'draft'], ['create_uid', '=', uid], ['create_date', '>=', time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(time.time() - 1800))]], **CTX)
if restes:
    call('mrp.production', 'unlink', restes, **CTX); print('  OF d essai restants supprimés :', len(restes))
modele = call('mrp.production', 'search_read', [['sale_line_id', '!=', False], ['state', '=', 'draft'], ['bom_id', '!=', False]], fields=['name', 'product_id', 'bom_id', 'sale_line_id', 'origin', 'product_qty', 'product_uom_id', 'company_id', 'picking_type_id'], order='id desc', limit=4, **CTX)
CH = ['x_studio_nom_du_client', 'x_studio_ref_commande_client', 'sale_line_id', 'x_studio_ref_pierre', 'x_studio_nbr', 'x_studio_long_m_1', 'x_studio_larg_m_1', 'x_studio_haut_m_1', 'x_studio_surf_total', 'x_studio_vol_total', 'product_qty', 'x_studio_description_article', 'log_note', 'x_studio_tche_commande_pierre']
ok = True; temps = {'avant': [], 'apres': []}
for mo in modele:
    base = {'product_id': mo['product_id'][0], 'bom_id': mo['bom_id'][0], 'origin': mo['origin'], 'product_qty': mo['product_qty'], 'product_uom_id': mo['product_uom_id'][0], 'company_id': mo['company_id'][0], 'picking_type_id': mo['picking_type_id'][0]}
    for variante in ('avec sale_line_id', 'sans sale_line_id'):
        vals = dict(base, **({'sale_line_id': mo['sale_line_id'][0]} if variante == 'avec sale_line_id' else {}))
        def essai(version):
            installer(1477, version)
            t0 = time.time(); nid = call('mrp.production', 'create', [vals], **CTX); t = round((time.time() - t0) * 1000)
            nid = nid[0] if isinstance(nid, list) else nid          # Odoo 19 : create([dict]) renvoie une liste d'ids
            of = call('mrp.production', 'read', [nid], fields=CH + ['workorder_ids'], **CTX)[0]
            wos = call('mrp.workorder', 'read', of['workorder_ids'], fields=['name', 'workcenter_id', 'x_studio_tche_commande_pierre'], **CTX)
            msgs = call('mail.message', 'search_read', [['model', '=', 'mrp.production'], ['res_id', '=', nid], ['subject', '=', 'Doublon OF potentiel']], fields=['body'], **CTX)
            resume = {k: of[k] for k in CH}; resume['workorders'] = sorted((w['name'], w['workcenter_id'] and w['workcenter_id'][1], w['x_studio_tche_commande_pierre'] and w['x_studio_tche_commande_pierre'][1]) for w in wos); resume['doublon'] = [x['body'] for x in msgs]
            call('mrp.production', 'unlink', [nid], **CTX)
            return resume, t
        r1, t1 = essai('avant'); r2, t2 = essai('apres')
        temps['avant'].append(t1); temps['apres'].append(t2)
        same = r1 == r2; ok &= same
        print('  OF modèle %s, %s : %s | création %d ms -> %d ms' % (mo['name'], variante, 'identique' if same else 'DIFFÉRENT', t1, t2))
        if not same:
            for k in r1:
                if r1[k] != r2[k]: print('     champ', k, '\n       avant', str(r1[k])[:300], '\n       après', str(r2[k])[:300])
bilan['1477'] = (ok, temps)
print('\nBILAN :', {k: ('OK' if v[0] else 'ÉCHEC', 'avant %s ms' % v[1]['avant'], 'après %s ms' % v[1]['apres']) for k, v in bilan.items()})
print('état final base de test : nouveau code installé sur 1602, 1594, 1477 =', all(call('ir.actions.server', 'read', [n], fields=['code'])[0]['code'] == code(n, 'apres') for n in (1602, 1594, 1477)))
